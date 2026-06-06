from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import os
from datetime import datetime, timedelta
from functools import wraps

# Inicializar Flask
app = Flask(__name__)
CORS(app)

# Configuração do banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///crs_full.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'sua-chave-secreta-aqui')

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
    duracao = db.Column(db.Integer, default=0)  # em segundos
    silencio_pct = db.Column(db.Float, default=0)
    hesitacao_pct = db.Column(db.Float, default=0)
    eventos = db.Column(db.Integer, default=0)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    dados_sessao = db.Column(db.JSON, nullable=True)
    
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
# DECORADORES DE AUTENTICAÇÃO
# ============================================================================

def token_requerido(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]
            except IndexError:
                return jsonify({'mensagem': 'Token inválido'}), 401
        
        if not token:
            return jsonify({'mensagem': 'Token ausente'}), 401
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            usuario_id = data['usuario_id']
            usuario = Usuario.query.get(usuario_id)
            
            if not usuario:
                return jsonify({'mensagem': 'Usuário não encontrado'}), 401
            
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
    dados = request.get_json()
    
    if not dados or not all(k in dados for k in ['nome', 'email', 'senha']):
        return jsonify({'mensagem': 'Dados incompletos'}), 400
    
    if Usuario.query.filter_by(email=dados['email']).first():
        return jsonify({'mensagem': 'Email já registrado'}), 409
    
    try:
        novo_usuario = Usuario(
            nome=dados['nome'],
            email=dados['email'],
            senha=generate_password_hash(dados['senha'])
        )
        
        db.session.add(novo_usuario)
        db.session.commit()
        
        print(f'[CRS-FULL] Novo usuário cadastrado: {dados["email"]}')
        
        return jsonify({
            'mensagem': 'Cadastro realizado com sucesso',
            'usuario_id': novo_usuario.id
        }), 201
    
    except Exception as erro:
        db.session.rollback()
        print(f'[CRS-FULL] Erro ao cadastrar: {erro}')
        return jsonify({'mensagem': 'Erro ao criar conta'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    dados = request.get_json()
    
    if not dados or not all(k in dados for k in ['email', 'senha']):
        return jsonify({'mensagem': 'Email e senha são obrigatórios'}), 400
    
    usuario = Usuario.query.filter_by(email=dados['email']).first()
    
    if not usuario or not check_password_hash(usuario.senha, dados['senha']):
        return jsonify({'mensagem': 'Email ou senha incorretos'}), 401
    
    try:
        token = jwt.encode(
            {
                'usuario_id': usuario.id,
                'exp': datetime.utcnow() + timedelta(days=7)
            },
            app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        
        print(f'[CRS-FULL] Login bem-sucedido: {usuario.email}')
        
        return jsonify({
            'token': token,
            'usuario': {
                'id': usuario.id,
                'nome': usuario.nome,
                'email': usuario.email
            }
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
    dados = request.get_json()
    
    try:
        nova_sessao = Sessao(
            usuario_id=request.usuario.id,
            nome=dados.get('nome', 'Sessão sem título'),
            descricao=dados.get('descricao', ''),
            duracao=dados.get('duracao', 0),
            silencio_pct=dados.get('silencio_pct', 0),
            hesitacao_pct=dados.get('hesitacao_pct', 0),
            eventos=dados.get('eventos', 0),
            dados_sessao=dados.get('dados_sessao', {})
        )
        
        db.session.add(nova_sessao)
        db.session.commit()
        
        print(f'[CRS-FULL] Sessão criada: {nova_sessao.id} (usuário: {request.usuario.email})')
        
        return jsonify({
            'mensagem': 'Sessão criada com sucesso',
            'sessao': nova_sessao.to_dict()
        }), 201
    
    except Exception as erro:
        db.session.rollback()
        print(f'[CRS-FULL] Erro ao criar sessão: {erro}')
        return jsonify({'mensagem': 'Erro ao criar sessão'}), 500

@app.route('/api/sessoes/listar', methods=['GET'])
@token_requerido
def listar_sessoes():
    limite = request.args.get('limite', 10, type=int)
    
    try:
        sessoes = Sessao.query.filter_by(usuario_id=request.usuario.id)\
            .order_by(Sessao.data_criacao.desc())\
            .limit(limite)\
            .all()
        
        print(f'[CRS-FULL] Sessões listadas: {len(sessoes)} (usuário: {request.usuario.email})')
        
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
# ROTA DE HEALTH CHECK
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'online',
        'servico': 'CRS-FULL',
        'versao': '1.0.0',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

# ============================================================================
# TRATAMENTO DE ERROS
# ============================================================================

@app.errorhandler(404)
def nao_encontrado(erro):
    return jsonify({'mensagem': 'Rota não encontrada'}), 404

@app.errorhandler(500)
def erro_interno(erro):
    print(f'[CRS-FULL] Erro interno: {erro}')
    return jsonify({'mensagem': 'Erro interno do servidor'}), 500

# ============================================================================
# INICIALIZAÇÃO
# ============================================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('🔊 CRS-FULL — Backend Iniciado')
        print('Banco de dados: OK')
        print('Autenticação: OK')
        print('---')
    
    app.run(debug=True, host='0.0.0.0', port=5000)