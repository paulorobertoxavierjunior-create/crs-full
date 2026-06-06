from flask import request, jsonify
from functools import wraps
from datetime import datetime, timedelta
import jwt
import os
from backend.main import app, db
from backend.models import Usuario, Sessao, EventoSessao, MetricaSessao, ConfiguracaoUsuario, LogSistema, ConfiguracaoTemporal

# ============================================================================
# DECORADORES
# ============================================================================

def token_requerido(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'mensagem': 'Token inválido'}), 401
        
        if not token:
            return jsonify({'mensagem': 'Token ausente'}), 401
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            usuario = Usuario.query.get(data['usuario_id'])
            
            if not usuario:
                return jsonify({'mensagem': 'Usuário não encontrado'}), 404
            
            request.usuario = usuario
        except jwt.ExpiredSignatureError:
            return jsonify({'mensagem': 'Token expirado'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'mensagem': 'Token inválido'}), 401
        
        return f(*args, **kwargs)
    
    return decorated

# ============================================================================
# ROTAS DE AUTENTICAÇÃO
# ============================================================================

@app.route('/api/auth/cadastro', methods=['POST'])
def cadastro():
    try:
        dados = request.get_json()
        
        if not dados or not all(k in dados for k in ['nome', 'email', 'senha']):
            return jsonify({'mensagem': 'Dados incompletos'}), 400
        
        if Usuario.query.filter_by(email=dados['email']).first():
            return jsonify({'mensagem': 'Email já cadastrado'}), 409
        
        usuario = Usuario(
            nome=dados['nome'],
            email=dados['email'],
            senha=dados['senha']
        )
        
        db.session.add(usuario)
        db.session.commit()
        
        print(f'[CRS-FULL] Novo usuário cadastrado: {dados["email"]}')
        
        return jsonify({
            'mensagem': 'Cadastro realizado com sucesso',
            'usuario': usuario.to_dict()
        }), 201
    
    except Exception as erro:
        db.session.rollback()
        print(f'[CRS-FULL] Erro ao cadastrar: {erro}')
        return jsonify({'mensagem': 'Erro ao cadastrar usuário'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        dados = request.get_json()
        
        if not dados or not all(k in dados for k in ['email', 'senha']):
            return jsonify({'mensagem': 'Email e senha obrigatórios'}), 400
        
        usuario = Usuario.query.filter_by(email=dados['email']).first()
        
        if not usuario or usuario.senha != dados['senha']:
            return jsonify({'mensagem': 'Email ou senha inválidos'}), 401
        
        token = jwt.encode(
            {
                'usuario_id': usuario.id,
                'exp': datetime.utcnow() + timedelta(hours=24)
            },
            app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        
        usuario.ultimo_acesso = datetime.utcnow()
        db.session.commit()
        
        print(f'[CRS-FULL] Login bem-sucedido: {dados["email"]}')
        
        return jsonify({
            'mensagem': 'Login bem-sucedido',
            'token': token,
            'usuario': usuario.to_dict()
        }), 200
    
    except Exception as erro:
        print(f'[CRS-FULL] Erro ao fazer login: {erro}')
        return jsonify({'mensagem': 'Erro ao fazer login'}), 500

# ============================================================================
# ROTAS DE SESSÕES
# ============================================================================

@app.route('/api/sessoes/criar', methods=['POST'])
@token_requerido
def criar_sessao():
    try:
        dados = request.get_json()
        
        sessao = Sessao(
            usuario_id=request.usuario.id,
            nome=dados.get('nome', 'Sessão sem título'),
            descricao=dados.get('descricao'),
            duracao=dados.get('duracao', 0),
            silencio_pct=dados.get('silencio_pct', 0),
            hesitacao_pct=dados.get('hesitacao_pct', 0),
            eventos=dados.get('eventos', 0),
            status='concluida',
            dados_sessao=dados.get('dados')
        )
        
        db.session.add(sessao)
        db.session.commit()
        
        print(f'[CRS-FULL] Sessão criada: {sessao.id}')
        
        return jsonify({
            'mensagem': 'Sessão criada com sucesso',
            'sessao': sessao.to_dict()
        }), 201
    
    except Exception as erro:
        db.session.rollback()
        print(f'[CRS-FULL] Erro ao criar sessão: {erro}')
        return jsonify({'mensagem': 'Erro ao criar sessão'}), 500

@app.route('/api/sessoes', methods=['GET'])
@token_requerido
def listar_sessoes():
    try:
        limite = request.args.get('limite', 10, type=int)
        sessoes = Sessao.query.filter_by(usuario_id=request.usuario.id).order_by(Sessao.data_criacao.desc()).limit(limite).all()
        
        print(f'[CRS-FULL] Listadas {len(sessoes)} sessões')
        
        return jsonify({
            'sessoes': [s.to_dict() for s in sessoes],
            'total': len(sessoes)
        }), 200
    
    except Exception as erro:
        print(f'[CRS-FULL] Erro ao listar sessões: {erro}')
        return jsonify({'mensagem': 'Erro ao listar sessões'}), 500

@app.route('/api/sessoes/<int:sessao_id>', methods=['GET'])
@token_requerido
def obter_sessao(sessao_id):
    try:
        sessao = Sessao.query.filter_by(id=sessao_id, usuario_id=request.usuario.id).first()
        
        if not sessao:
            return jsonify({'mensagem': 'Sessão não encontrada'}), 404
        
        print(f'[CRS-FULL] Sessão obtida: {sessao_id}')
        
        return jsonify({
            'sessao': sessao.to_dict(),
            'dados': sessao.dados_sessao
        }), 200
    
    except Exception as erro:
        print(f'[CRS-FULL] Erro ao obter sessão: {erro}')
        return jsonify({'mensagem': 'Erro ao obter sessão'}), 500

@app.route('/api/sessoes/<int:sessao_id>', methods=['DELETE'])
@token_requerido
def deletar_sessao(sessao_id):
    try:
        sessao = Sessao.query.filter_by(id=sessao_id, usuario_id=request.usuario.id).first()
        
        if not sessao:
            return jsonify({'mensagem': 'Sessão não encontrada'}), 404
        
        db.session.delete(sessao)
        db.session.commit()
        
        print(f'[CRS-FULL] Sessão deletada: {sessao_id}')
        
        return jsonify({'mensagem': 'Sessão deletada com sucesso'}), 200
    
    except Exception as erro:
        db.session.rollback()
        print(f'[CRS-FULL] Erro ao deletar sessão: {erro}')
        return jsonify({'mensagem': 'Erro ao deletar sessão'}), 500

# ============================================================================
# ROTAS DE EVENTOS
# ============================================================================

@app.route('/api/sessoes/<int:sessao_id>/eventos', methods=['POST'])
@token_requerido
def adicionar_evento(sessao_id):
    try:
        sessao = Sessao.query.filter_by(id=sessao_id, usuario_id=request.usuario.id).first()
        
        if not sessao:
            return jsonify({'mensagem': 'Sessão não encontrada'}), 404
        
        dados = request.get_json()
        
        evento = EventoSessao(
            sessao_id=sessao_id,
            tipo_evento=dados.get('tipo'),
            timestamp=datetime.utcnow(),
            dados_evento=dados.get('dados')
        )
        
        db.session.add(evento)
        db.session.commit()
        
        print(f'[CRS-FULL] Evento adicionado à sessão {sessao_id}')
        
        return jsonify({
            'mensagem': 'Evento adicionado',
            'evento': evento.to_dict()
        }), 201
    
    except Exception as erro:
        db.session.rollback()
        print(f'[CRS-FULL] Erro ao adicionar evento: {erro}')
        return jsonify({'mensagem': 'Erro ao adicionar evento'}), 500

# ============================================================================
# ROTAS DE MÉTRICAS
# ============================================================================

@app.route('/api/sessoes/<int:sessao_id>/metricas', methods=['GET'])
@token_requerido
def obter_metricas(sessao_id):
    try:
        sessao = Sessao.query.filter_by(id=sessao_id, usuario_id=request.usuario.id).first()
        
        if not sessao:
            return jsonify({'mensagem': 'Sessão não encontrada'}), 404
        
        metricas = MetricaSessao.query.filter_by(sessao_id=sessao_id).all()
        
        print(f'[CRS-FULL] Métricas obtidas para sessão {sessao_id}')
        
        return jsonify({
            'metricas': [m.to_dict() for m in metricas]
        }), 200
    
    except Exception as erro:
        print(f'[CRS-FULL] Erro ao obter métricas: {erro}')
        return jsonify({'mensagem': 'Erro ao obter métricas'}), 500

# ============================================================================
# ROTAS DE CONFIGURAÇÃO
# ============================================================================

@app.route('/api/usuario/configuracoes', methods=['GET'])
@token_requerido
def obter_configuracoes():
    try:
        configs = ConfiguracaoUsuario.query.filter_by(usuario_id=request.usuario.id).all()
        
        print(f'[CRS-FULL] Configurações obtidas para usuário {request.usuario.id}')
        
        return jsonify({
            'configuracoes': [c.to_dict() for c in configs]
        }), 200
    
    except Exception as erro:
        print(f'[CRS-FULL] Erro ao obter configurações: {erro}')
        return jsonify({'mensagem': 'Erro ao obter configurações'}), 500

@app.route('/api/usuario/configuracoes', methods=['POST'])
@token_requerido
def salvar_configuracao():
    try:
        dados = request.get_json()
        
        config = ConfiguracaoUsuario.query.filter_by(
            usuario_id=request.usuario.id,
            chave=dados.get('chave')
        ).first()
        
        if config:
            config.valor = dados.get('valor')
        else:
            config = ConfiguracaoUsuario(
                usuario_id=request.usuario.id,
                chave=dados.get('chave'),
                valor=dados.get('valor'),
                tipo=dados.get('tipo', 'string')
            )
            db.session.add(config)
        
        db.session.commit()
        
        print(f'[CRS-FULL] Configuração salva: {dados.get("chave")}')
        
        return jsonify({
            'mensagem': 'Configuração salva',
            'configuracao': config.to_dict()
        }), 200
    
    except Exception as erro:
        db.session.rollback()
        print(f'[CRS-FULL] Erro ao salvar configuração: {erro}')
        return jsonify({'mensagem': 'Erro ao salvar configuração'}), 500

# ============================================================================
# ROTAS DE HEALTH CHECK
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'online',
        'servico': 'CRS-FULL',
        'versao': '1.0.0',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

print('🔊 CRS-FULL — Routes Carregadas')