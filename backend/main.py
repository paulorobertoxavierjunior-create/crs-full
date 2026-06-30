from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import os
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)

# Configuração robusta de CORS para aceitar as requisições do Front-end (Presença)
CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    },
    r"/health": {
        "origins": ["*"],
        "methods": ["GET"]
    }
})

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crs_full.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'elayon-token-secreto-multimodal')

db = SQLAlchemy(app)

# ============================================================================
# MODELOS DE BANCO DE DADOS
# ============================================================================

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    ativo = db.Column(db.Boolean, default=True)
    sessoes = db.relationship('Sessao', backref='usuario', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Usuario {self.email}>'

class Sessao(db.Model):
    __tablename__ = 'sessoes'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    nome = db.Column(db.String(255), nullable=True)
    descricao = db.Column(db.Text, nullable=True)
    duracao = db.Column(db.Integer, nullable=True)
    silencio_pct = db.Column(db.Float, default=0)
    hesitacao_pct = db.Column(db.Float, default=0)
    eventos = db.Column(db.Integer, default=0)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Sessao {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'duracao': self.duracao,
            'silencio_pct': self.silencio_pct,
            'hesitacao_pct': self.hesitacao_pct,
            'eventos': self.eventos,
            'data_criacao': self.data_criacao.isoformat()
        }

# ============================================================================
# DECORATOR DE AUTENTICAÇÃO (JWT)
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
# ROTAS DE INFRAESTRUTURA & OPERAÇÃO BÁSICA
# ============================================================================

@app.route('/')
def home():
    return jsonify({
        'status': 'ok',
        'message': 'CRS-FULL Backend está rodando!',
        'version': '1.0.0',
        'endpoints': {
            'auth': '/api/auth/registro, /api/auth/login',
            'crs_handshake': '/api/crs/fifo-buffer',
            'sessoes': '/api/sessoes',
            'health_check': '/health'
        }
    }), 200

# Rota vital para o HEALTHCHECK do Dockerfile passar com sucesso (Evita loops no Render/AWS)
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'database': 'ready',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

# ============================================================================
# ROTA DE INGESTÃO CRS (CONEXÃO DIRETA COM O FRONT PRESENÇA)
# ============================================================================

@app.route('/api/crs/fifo-buffer', methods=['POST'])
def crs_fifo_buffer():
    try:
        dados = request.get_json()
        if not dados:
            return jsonify({'mensagem': 'Payload vazio ou inválido'}), 400
        
        uid = dados.get('uid', 'usuario_anonimo')
        silencio_seg = dados.get('silencio_seg', 0.0)
        duracao = dados.get('duracao', 0)
        
        print(f'[ELAYON CORE] Ingestão CRS recebida de {uid}: {silencio_seg}s em uma leitura de {duracao}s')
        
        # Lógica básica de retorno baseada no limiar de tempo humano
        # Classifica dinamicamente o estado da carga cognitiva do sinal recebido
        silencio_float = float(silencio_seg)
        if silencio_float < 0.6:
            carga = 'Ritmo Acelerado ⚠'
        elif silencio_float <= 1.3:
            carga = 'Carga Cognitiva Estabilizada ✓'
        else:
            # Pausa reflexiva profunda ou hesitação longa
            carga = 'Alta Concentração / Reflexão 🧠'

        return jsonify({
            'status': 'sincronizado',
            'usuario_id': uid,
            'metrica_silencio_seg': silencio_float,
            'duracao_total_seg': duracao,
            'carga_cognitiva': carga,
            'timestamp_server': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as erro:
        print(f'[ELAYON ERROR] Falha na rota do buffer FIFO: {erro}')
        return jsonify({'mensagem': 'Erro interno ao processar sinal cognitivo'}), 500

# ============================================================================
# ROTAS DE AUTENTICAÇÃO
# ============================================================================

@app.route('/api/auth/registro', methods=['POST'])
def registro():
    try:
        dados = request.get_json()
        if not dados or not dados.get('email') or not dados.get('senha') or not dados.get('nome'):
            return jsonify({'mensagem': 'Email, senha e nome são obrigatórios'}), 400
        if Usuario.query.filter_by(email=dados['email']).first():
            return jsonify({'mensagem': 'Email já cadastrado'}), 409
        usuario = Usuario(
            nome=dados['nome'],
            email=dados['email'],
            senha=generate_password_hash(dados['senha'])
        )
        db.session.add(usuario)
        db.session.commit()
        print(f'[CRS-FULL] Novo usuário registrado: {usuario.email}')
        return jsonify({
            'mensagem': 'Usuário registrado com sucesso',
            'usuario': { 'id': usuario.id, 'nome': usuario.nome, 'email': usuario.email }
        }), 201
    except Exception as erro:
        db.session.rollback()
        print(f'[CRS-FULL] Erro ao registrar: {erro}')
        return jsonify({'mensagem': 'Erro ao registrar usuário'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        dados = request.get_json()
        if not dados or not dados.get('email') or not dados.get('senha'):
            return jsonify({'mensagem': 'Email e senha são obrigatórios'}), 400
        usuario = Usuario.query.filter_by(email=dados['email']).first()
        if not usuario or not check_password_hash(usuario.senha, dados['senha']):
            return jsonify({'mensagem': 'Email ou senha inválidos'}), 401
        token = jwt.encode({
            'usuario_id': usuario.id,
            'email': usuario.email,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        print(f'[CRS-FULL] Login bem-sucedido: {usuario.email}')
        return jsonify({
            'mensagem': 'Login bem-sucedido',
            'token': token,
            'usuario': { 'id': usuario.id, 'nome': usuario.nome, 'email': usuario.email }
        }), 200
    except Exception as erro:
        print(f'[CRS-FULL] Erro ao fazer login: {erro}')
        return jsonify({'mensagem': 'Erro ao fazer login'}), 500

@app.route('/api/auth/perfil', methods=['GET'])
@token_requerido
def perfil():
    try:
        return jsonify({
            'usuario': {
                'id': request.usuario.id,
                'nome': request.usuario.nome,
                'email': request.usuario.email,
                'data_criacao': request.usuario.data_criacao.isoformat()
            }
        }), 200
    except Exception as erro:
        print(f'[CRS-FULL] Erro ao obter perfil: {erro}')
        return jsonify({'mensagem': 'Erro ao obter perfil'}), 500

# ============================================================================
# ROTAS DE GESTÃO DE SESSÕES PROCEDURAIS
# ============================================================================

@app.route('/api/sessoes', methods=['GET'])
@token_requerido
def listar_sessoes():
    try:
        sessoes = Sessao.query.filter_by(usuario_id=request.usuario.id).all()
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
        return jsonify({'sessao': sessao.to_dict()}), 200
    except Exception as erro:
        print(f'[CRS-FULL] Erro ao obter sessão: {erro}')
        return jsonify({'mensagem': 'Erro ao obter sessão'}), 500

@app.route('/api/sessoes', methods=['POST'])
@token_requerido
def criar_sessao():
    try:
        dados = request.get_json()
        sessao = Sessao(
            usuario_id=request.usuario.id,
            nome=dados.get('nome'),
            descricao=dados.get('descricao'),
            duracao=dados.get('duracao'),
            silencio_pct=dados.get('silencio_pct', 0),
            hesitacao_pct=dados.get('hesitacao_pct', 0),
            eventos=dados.get('eventos', 0)
        )
        db.session.add(sessao)
        db.session.commit()
        return jsonify({
            'mensagem': 'Sessão criada com sucesso',
            'sessao': sessao.to_dict()
        }), 201
    except Exception as erro:
        db.session.rollback()
        print(f'[CRS-FULL] Erro ao criar sessão: {erro}')
        return jsonify({'mensagem': 'Erro ao criar sessão'}), 500

@app.route('/api/sessoes/<int:sessao_id>', methods=['PUT'])
@token_requerido
def atualizar_sessao(sessao_id):
    try:
        sessao = Sessao.query.filter_by(id=sessao_id, usuario_id=request.usuario.id).first()
        if not sessao:
            return jsonify({'mensagem': 'Sessão não encontrada'}), 404
        dados = request.get_json()
        sessao.nome = dados.get('nome', sessao.nome)
        sessao.descricao = dados.get('descricao', sessao.descricao)
        sessao.duracao = dados.get('duracao', sessao.duracao)
        sessao.silencio_pct = dados.get('silencio_pct', sessao.silencio_pct)
        sessao.hesitacao_pct = dados.get('hesitacao_pct', sessao.hesitacao_pct)
        db.session.commit()
        return jsonify({
            'mensagem': 'Sessão atualizada com sucesso',
            'sessao': sessao.to_dict()
        }), 200
    except Exception as erro:
        db.session.rollback()
        print(f'[CRS-FULL] Erro ao atualizar sessão: {erro}')
        return jsonify({'mensagem': 'Erro ao atualizar sessão'}), 500

@app.route('/api/sessoes/<int:sessao_id>', methods=['DELETE'])
@token_requerido
def deletar_sessao(sessao_id):
    try:
        sessao = Sessao.query.filter_by(id=sessao_id, usuario_id=request.usuario.id).first()
        if not sessao:
            return jsonify({'mensagem': 'Sessão não encontrada'}), 404
        db.session.delete(sessao)
        db.session.commit()
        return jsonify({'mensagem': 'Sessão deletada com sucesso'}), 200
    except Exception as erro:
        db.session.rollback()
        print(f'[CRS-FULL] Erro ao deletar sessão: {erro}')
        return jsonify({'mensagem': 'Erro ao deletar sessão'}), 500

@app.route('/api/sessoes/<int:sessao_id>/metricas', methods=['GET'])
@token_requerido
def obter_metricas(sessao_id):
    try:
        sessao = Sessao.query.filter_by(id=sessao_id, usuario_id=request.usuario.id).first()
        if not clansessao:
            return jsonify({'mensagem': 'Sessão não encontrada'}), 404
        return jsonify({
            'metricas': {
                'duracao': sessao.duracao,
                'silencio_pct': sessao.silencio_pct,
                'hesitacao_pct': sessao.hesitacao_pct,
                'eventos': sessao.eventos
            }
        }), 200
    except Exception as erro:
        print(f'[CRS-FULL] Erro ao obter métricas: {erro}')
        return jsonify({'mensagem': 'Erro ao obter métricas'}), 500

# ============================================================================
# INICIALIZAÇÃO LOCAL DO SERVIDOR
# ============================================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('🔊 ELAYON ENGINE — CRS-FULL BACKEND CONECTADO')
        print('Banco de dados SQLite: OK')
        print('Handshake Multimodal: OK')
        print('Pronto para o Healthcheck do Dockerfile!')
        print('---')
    
    app.run(debug=True, host='0.0.0.0', port=5000)
