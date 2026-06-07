from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import os
from datetime import datetime, timedelta
from functools import wraps
import json

# ============================================================================
# INICIALIZAÇÃO
# ============================================================================

app = Flask(__name__)
CORS(app)

# Configuração
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'postgresql://crs_user:crs_password@localhost:5432/crs_db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'sua-chave-secreta-super-segura-2024')
app.config['JWT_EXPIRATION_HOURS'] = 24

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
    api_keys = db.relationship('APIKey', backref='usuario', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Usuario {self.email}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'data_criacao': self.data_criacao.isoformat()
        }

class Sessao(db.Model):
    __tablename__ = 'sessoes'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    nome = db.Column(db.String(255), nullable=True)
    descricao = db.Column(db.Text, nullable=True)
    duracao = db.Column(db.Integer, nullable=True)  # segundos
    silencio_pct = db.Column(db.Float, default=0)
    hesitacao_pct = db.Column(db.Float, default=0)
    eventos = db.Column(db.Integer, default=0)
    transcricao = db.Column(db.Text, nullable=True)
    resposta_ia = db.Column(db.Text, nullable=True)
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
            'transcricao': self.transcricao,
            'resposta_ia': self.resposta_ia,
            'data_criacao': self.data_criacao.isoformat()
        }

class APIKey(db.Model):
    __tablename__ = 'api_keys'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    chave = db.Column(db.String(255), unique=True, nullable=False)
    nome = db.Column(db.String(255), nullable=True)
    plano = db.Column(db.String(50), default='free')  # free, pro, enterprise
    ativa = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<APIKey {self.chave[:10]}...>'

class LogSistema(db.Model):
    __tablename__ = 'logs_sistema'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    tipo = db.Column(db.String(50))  # login, gravacao, erro, etc
    mensagem = db.Column(db.Text)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Log {self.tipo}>'

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

def api_key_requerida(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        chave = request.headers.get('X-API-Key')
        
        if not chave:
            return jsonify({'mensagem': 'API Key ausente'}), 401
        
        api_key = APIKey.query.filter_by(chave=chave, ativa=True).first()
        
        if not api_key:
            return jsonify({'mensagem': 'API Key inválida'}), 401
        
        request.usuario = api_key.usuario
        request.api_key = api_key
        
        return f(*args, **kwargs)
    
    return decorated

# ============================================================================
# ROTAS DE AUTENTICAÇÃO
# ============================================================================

@app.route('/api/auth/registro', methods=['POST'])
def registro():
    try:
        dados = request.get_json()
        
        if not dados or not dados.get('email') or not dados.get('senha') or not dados.get('nome'):
            return jsonify({'mensagem': 'Dados incompletos'}), 400
        
        if Usuario.query.filter_by(email=dados['email']).first():
            return jsonify({'mensagem': 'Email já cadastrado'}), 409
        
        novo_usuario = Usuario(
            nome=dados['nome'],
            email=dados['email'],
            senha=generate_password_hash(dados['senha'])
        )
        
        db.session.add(novo_usuario)
        db.session.commit()
        
        print(f'[CRS-FULL] Novo usuário registrado: {dados["email"]}')
        
        return jsonify({
            'mensagem': 'Usuário registrado com sucesso',
            'usuario': novo_usuario.to_dict()
        }), 201
    
    except Exception as erro:
        db.session.rollback()
        print(f'[CRS-FULL] Erro no registro: {erro}')
        return jsonify({'mensagem': 'Erro ao registrar usuário'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        dados = request.get_json()
        
        if not dados or not dados.get('email') or not dados.get('senha'):
            return jsonify({'mensagem': 'Email ou senha ausentes'}), 400
        
        usuario = Usuario.query.filter_by(email=dados['email']).first()
        
        if not usuario or not check_password_hash(usuario.senha, dados['senha']):
            return jsonify({'mensagem': 'Email ou senha incorretos'}), 401
        
        token = jwt.encode({
            'usuario_id': usuario.id,
            'exp': datetime.utcnow() + timedelta(hours=app.config['JWT_EXPIRATION_HOURS'])
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        print(f'[CRS-FULL] Login bem-sucedido: {dados["email"]}')
        
        return jsonify({
            'mensagem': 'Login bem-sucedido',
            'token': token,
            'usuario': usuario.to_dict()
        }), 200
    
    except Exception as erro:
        print(f'[CRS-FULL] Erro no login: {erro}')
        return jsonify({'mensagem': 'Erro ao fazer login'}), 500

# ============================================================================
# ROTAS DE SESSÕES
# ============================================================================

@app.route('/api/sessoes', methods=['GET'])
@token_requerido
def listar_sessoes():
    try:
        limite = request.args.get('limite', 10, type=int)
        sessoes = Sessao.query.filter_by(usuario_id=request.usuario.id)\
            .order_by(Sessao.data_criacao.desc())\
            .limit(limite)\
            .all()
        
        print(f'[CRS-FULL] Sessões listadas: {len(sessoes)}')
        
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
        sessao = Sessao.query.filter_by(
            id=sessao_id,
            usuario_id=request.usuario.id
        ).first()
        
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
        
        nova_sessao = Sessao(
            usuario_id=request.usuario.id,
            nome=dados.get('nome'),
            descricao=dados.get('descricao'),
            duracao=dados.get('duracao', 0),
            silencio_pct=dados.get('silencio_pct', 0),
            hesitacao_pct=dados.get('hesitacao_pct', 0),
            eventos=dados.get('eventos', 0)
        )
        
        db.session.add(nova_sessao)
        db.session.commit()
        
        print(f'[CRS-FULL] Sessão criada: {nova_sessao.id}')
        
        return jsonify({
            'mensagem': 'Sessão criada com sucesso',
            'sessao': nova_sessao.to_dict()
        }), 201
    
    except Exception as erro:
        db.session.rollback()
        print(f'[CRS-FULL] Erro ao criar sessão: {erro}')
        return jsonify({'mensagem': 'Erro ao criar sessão'}), 500

@app.route('/api/sessoes/<int:sessao_id>', methods=['PUT'])
@token_requerido
def atualizar_sessao(sessao_id):
    try:
        sessao = Sessao.query.filter_by(
            id=sessao_id,
            usuario_id=request.usuario.id
        ).first()
        
        if not sessao:
            return jsonify({'mensagem': 'Sessão não encontrada'}), 404
        
        dados = request.get_json()
        
        sessao.nome = dados.get('nome', sessao.nome)
        sessao.descricao = dados.get('descricao', sessao.descricao)
        sessao.silencio_pct = dados.get('silencio_pct', sessao.silencio_pct)
        sessao.hesitacao_pct = dados.get('hesitacao_pct', sessao.hesitacao_pct)
        
        db.session.commit()
        
        print(f'[CRS-FULL] Sessão atualizada: {sessao_id}')
        
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
        sessao = Sessao.query.filter_by(
            id=sessao_id,
            usuario_id=request.usuario.id
        ).first()
        
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
# ROTAS DE API KEYS
# ============================================================================

@app.route('/api/api-keys', methods=['GET'])
@token_requerido
def listar_api_keys():
    try:
        chaves = APIKey.query.filter_by(usuario_id=request.usuario.id).all()
        
        return jsonify({
            'api_keys': [{
                'id': k.id,
                'nome': k.nome,
                'chave': k.chave[:10] + '...',
                'plano': k.plano,
                'ativa': k.ativa,
                'data_criacao': k.data_criacao.isoformat()
            } for k in chaves]
        }), 200
    
    except Exception as erro:
        print(f'[CRS-FULL] Erro ao listar API keys: {erro}')
        return jsonify({'mensagem': 'Erro ao listar API keys'}), 500

@app.route('/api/api-keys', methods=['POST'])
@token_requerido
def criar_api_key():
    try:
        import secrets
        
        chave = secrets.token_urlsafe(32)
        
        nova_chave = APIKey(
            usuario_id=request.usuario.id,
            chave=chave,
            nome=request.get_json().get('nome', 'Chave padrão'),
            plano='free'
        )
        
        db.session.add(nova_chave)
        db.session.commit()
        
        print(f'[CRS-FULL] API Key criada para usuário {request.usuario.id}')
        
        return jsonify({
            'mensagem': 'API Key criada com sucesso',
            'chave': chave
        }), 201
    
    except Exception as erro:
        db.session.rollback()
        print(f'[CRS-FULL] Erro ao criar API key: {erro}')
        return jsonify({'mensagem': 'Erro ao criar API key'}), 500

# ============================================================================
# ROTAS DE IA (PLACEHOLDER)
# ============================================================================

@app.route('/api/ia/analisar', methods=['POST'])
@token_requerido
def analisar_com_ia():
    try:
        dados = request.get_json()
        
        # TODO: Integrar com Claude/GPT
        resposta = f"Análise de: {dados.get('transcricao', 'N/A')}"
        
        print(f'[CRS-FULL] Análise de IA realizada')
        
        return jsonify({
            'resposta': resposta,
            'metricas': {
                'sentimento': 'positivo',
                'confianca': 0.85
            }
        }), 200
    
    except Exception as erro:
        print(f'[CRS-FULL] Erro na análise de IA: {erro}')
        return jsonify({'mensagem': 'Erro ao analisar com IA'}), 500

@app.route('/api/ia/chat', methods=['POST'])
@token_requerido
def chat_ia():
    try:
        dados = request.get_json()
        mensagem = dados.get('mensagem', '')
        
        # TODO: Integrar com Claude/GPT
        resposta = f"Resposta para: {mensagem}"
        
        return jsonify({'resposta': resposta}), 200
    
    except Exception as erro:
        print(f'[CRS-FULL] Erro no chat: {erro}')
        return jsonify({'mensagem': 'Erro ao processar chat'}), 500

# ============================================================================
# ROTAS PÚBLICAS
# ============================================================================

@app.route('/', methods=['GET'])
def status():
    return jsonify({
        'status': 'ok',
        'message': 'CRS-FULL Backend está rodando!',
        'version': '1.0.0',
        'endpoints': {
            'auth': ['/api/auth/registro', '/api/auth/login'],
            'sessoes': ['/api/sessoes', '/api/sessoes/<id>'],
            'api_keys': ['/api/api-keys'],
            'ia': ['/api/ia/analisar', '/api/ia/chat']
        }
    }), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import os
from datetime import datetime, timedelta
from functools import wraps
import json

# ============================================================================
# INICIALIZAÇÃO
# ============================================================================

app = Flask(__name__)
CORS(app)

# Configuração
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'postgresql://crs_user:crs_password@localhost:5432/crs_db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'sua-chave-secreta-super-segura-2024')
app.config['JWT_EXPIRATION_HOURS'] = 24

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
    api_keys = db.relationship('APIKey', backref='usuario', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Usuario {self.email}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'data_criacao': self.data_criacao.isoformat()
        }

class Sessao(db.Model):
    __tablename__ = 'sessoes'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    nome = db.Column(db.String(255), nullable=True)
    descricao = db.Column(db.Text, nullable=True)
    duracao = db.Column(db.Integer, nullable=True)  # segundos
    silencio_pct = db.Column(db.Float, default=0)
    hesitacao_pct = db.Column(db.Float, default=0)
    eventos = db.Column(db.Integer, default=0)
    transcricao = db.Column(db.Text, nullable=True)
    resposta_ia = db.Column(db.Text, nullable=True)
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
            'transcricao': self.transcricao,
            'resposta_ia': self.resposta_ia,
            'data_criacao': self.data_criacao.isoformat()
        }

class APIKey(db.Model):
    __tablename__ = 'api_keys'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    chave = db.Column(db.String(255), unique=True, nullable=False)
    nome = db.Column(db.String(255), nullable=True)
    plano = db.Column(db.String(50), default='free')  # free, pro, enterprise
    ativa = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<APIKey {self.chave[:10]}...>'

class LogSistema(db.Model):
    __tablename__ = 'logs_sistema'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    tipo = db.Column(db.String(50))  # login, gravacao, erro, etc
    mensagem = db.Column(db.Text)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Log {self.tipo}>'

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

def api_key_requerida(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        chave = request.headers.get('X-API-Key')
        
        if not chave:
            return jsonify({'mensagem': 'API Key ausente'}), 401
        
        api_key = APIKey.query.filter_by(chave=chave, ativa=True).first()
        
        if not api_key:
            return jsonify({'mensagem': 'API Key inválida'}), 401
        
        request.usuario = api_key.usuario
        request.api_key = api_key
        
        return f(*args, **kwargs)
    
    return decorated

# ============================================================================
# ROTAS DE AUTENTICAÇÃO
# ============================================================================

@app.route('/api/auth/registro', methods=['POST'])
def registro():
    try:
        dados = request.get_json()
        
        if not dados or not dados.get('email') or not dados.get('senha') or not dados.get('nome'):
            return jsonify({'mensagem': 'Dados incompletos'}), 400
        
        if Usuario.query.filter_by(email=dados['email']).first():
            return jsonify({'mensagem': 'Email já cadastrado'}), 409
        
        novo_usuario = Usuario(
            nome=dados['nome'],
            email=dados['email'],
            senha=generate_password_hash(dados['senha'])
        )
        
        db.session.add(novo_usuario)
        db.session.commit()
        
        print(f'[CRS-FULL] Novo usuário registrado: {dados["email"]}')
        
        return jsonify({
            'mensagem': 'Usuário registrado com sucesso',
            'usuario': novo_usuario.to_dict()
        }), 201
    
    except Exception as erro:
        db.session.rollback()
        print(f'[CRS-FULL] Erro no registro: {erro}')
        return jsonify({'mensagem': 'Erro ao registrar usuário'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        dados = request.get_json()
        
        if not dados or not dados.get('email') or not dados.get('senha'):
            return jsonify({'mensagem': 'Email ou senha ausentes'}), 400
        
        usuario = Usuario.query.filter_by(email=dados['email']).first()
        
        if not usuario or not check_password_hash(usuario.senha, dados['senha']):
            return jsonify({'mensagem': 'Email ou senha incorretos'}), 401
        
        token = jwt.encode({
            'usuario_id': usuario.id,
            'exp': datetime.utcnow() + timedelta(hours=app.config['JWT_EXPIRATION_HOURS'])
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        print(f'[CRS-FULL] Login bem-sucedido: {dados["email"]}')
        
        return jsonify({
            'mensagem': 'Login bem-sucedido',
            'token': token,
            'usuario': usuario.to_dict()
        }), 200
    
    except Exception as erro:
        print(f'[CRS-FULL] Erro no login: {erro}')
        return jsonify({'mensagem': 'Erro ao fazer login'}), 500

# ============================================================================
# ROTAS DE SESSÕES
# ============================================================================

@app.route('/api/sessoes', methods=['GET'])
@token_requerido
def listar_sessoes():
    try:
        limite = request.args.get('limite', 10, type=int)
        sessoes = Sessao.query.filter_by(usuario_id=request.usuario.id)\
            .order_by(Sessao.data_criacao.desc())\
            .limit(limite)\
            .all()
        
        print(f'[CRS-FULL] Sessões listadas: {len(sessoes)}')
        
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
        sessao = Sessao.query.filter_by(
            id=sessao_id,
            usuario_id=request.usuario.id
        ).first()
        
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
        
        nova_sessao = Sessao(
            usuario_id=request.usuario.id,
            nome=dados.get('nome'),
            descricao=dados.get('descricao'),
            duracao=dados.get('duracao', 0),
            silencio_pct=dados.get('silencio_pct', 0),
            hesitacao_pct=dados.get('hesitacao_pct', 0),
            eventos=dados.get('eventos', 0)
        )
        
        db.session.add(nova_sessao)
        db.session.commit()
        
        print(f'[CRS-FULL] Sessão criada: {nova_sessao.id}')
        
        return jsonify({
            'mensagem': 'Sessão criada com sucesso',
            'sessao': nova_sessao.to_dict()
        }), 201
    
    except Exception as erro:
        db.session.rollback()
        print(f'[CRS-FULL] Erro ao criar sessão: {erro}')
        return jsonify({'mensagem': 'Erro ao criar sessão'}), 500

@app.route('/api/sessoes/<int:sessao_id>', methods=['PUT'])
@token_requerido
def atualizar_sessao(sessao_id):
    try:
        sessao = Sessao.query.filter_by(
            id=sessao_id,
            usuario_id=request.usuario.id
        ).first()
        
        if not sessao:
            return jsonify({'mensagem': 'Sessão não encontrada'}), 404
        
        dados = request.get_json()
        
        sessao.nome = dados.get('nome', sessao.nome)
        sessao.descricao = dados.get('descricao', sessao.descricao)
        sessao.silencio_pct = dados.get('silencio_pct', sessao.silencio_pct)
        sessao.hesitacao_pct = dados.get('hesitacao_pct', sessao.hesitacao_pct)
        
        db.session.commit()
        
        print(f'[CRS-FULL] Sessão atualizada: {sessao_id}')
        
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
        sessao = Sessao.query.filter_by(
            id=sessao_id,
            usuario_id=request.usuario.id
        ).first()
        
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
# ROTAS DE API KEYS
# ============================================================================

@app.route('/api/api-keys', methods=['GET'])
@token_requerido
def listar_api_keys():
    try:
        chaves = APIKey.query.filter_by(usuario_id=request.usuario.id).all()
        
        return jsonify({
            'api_keys': [{
                'id': k.id,
                'nome': k.nome,
                'chave': k.chave[:10] + '...',
                'plano': k.plano,
                'ativa': k.ativa,
                'data_criacao': k.data_criacao.isoformat()
            } for k in chaves]
        }), 200
    
    except Exception as erro:
        print(f'[CRS-FULL] Erro ao listar API keys: {erro}')
        return jsonify({'mensagem': 'Erro ao listar API keys'}), 500

@app.route('/api/api-keys', methods=['POST'])
@token_requerido
def criar_api_key():
    try:
        import secrets
        
        chave = secrets.token_urlsafe(32)
        
        nova_chave = APIKey(
            usuario_id=request.usuario.id,
            chave=chave,
            nome=request.get_json().get('nome', 'Chave padrão'),
            plano='free'
        )
        
        db.session.add(nova_chave)
        db.session.commit()
        
        print(f'[CRS-FULL] API Key criada para usuário {request.usuario.id}')
        
        return jsonify({
            'mensagem': 'API Key criada com sucesso',
            'chave': chave
        }), 201
    
    except Exception as erro:
        db.session.rollback()
        print(f'[CRS-FULL] Erro ao criar API key: {erro}')
        return jsonify({'mensagem': 'Erro ao criar API key'}), 500

# ============================================================================
# ROTAS DE IA (PLACEHOLDER)
# ============================================================================

@app.route('/api/ia/analisar', methods=['POST'])
@token_requerido
def analisar_com_ia():
    try:
        dados = request.get_json()
        
        # TODO: Integrar com Claude/GPT
        resposta = f"Análise de: {dados.get('transcricao', 'N/A')}"
        
        print(f'[CRS-FULL] Análise de IA realizada')
        
        return jsonify({
            'resposta': resposta,
            'metricas': {
                'sentimento': 'positivo',
                'confianca': 0.85
            }
        }), 200
    
    except Exception as erro:
        print(f'[CRS-FULL] Erro na análise de IA: {erro}')
        return jsonify({'mensagem': 'Erro ao analisar com IA'}), 500

@app.route('/api/ia/chat', methods=['POST'])
@token_requerido
def chat_ia():
    try:
        dados = request.get_json()
        mensagem = dados.get('mensagem', '')
        
        # TODO: Integrar com Claude/GPT
        resposta = f"Resposta para: {mensagem}"
        
        return jsonify({'resposta': resposta}), 200
    
    except Exception as erro:
        print(f'[CRS-FULL] Erro no chat: {erro}')
        return jsonify({'mensagem': 'Erro ao processar chat'}), 500

# ============================================================================
# ROTAS PÚBLICAS
# ============================================================================

@app.route('/', methods=['GET'])
def status():
    return jsonify({
        'status': 'ok',
        'message': 'CRS-FULL Backend está rodando!',
        'version': '1.0.0',
        'endpoints': {
            'auth': ['/api/auth/registro', '/api/auth/login'],
            'sessoes': ['/api/sessoes', '/api/sessoes/<id>'],
            'api_keys': ['/api/api-keys'],
            'ia': ['/api/ia/analisar', '/api/ia/chat']
        }
    }), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

# ============================================================================
# INICIALIZAÇÃO
# ============================================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('🔊 CRS-FULL — Backend Iniciado')
        print('Banco de dados: OK')
        print('Autenticação: OK')
        print('Rotas: OK')
        print('---')
        print('Servidor rodando em http://0.0.0.0:5000')
    
    app.run(debug=True, host='0.0.0.0', port=5000)
# ============================================================================
# INICIALIZAÇÃO
# ============================================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('🔊 CRS-FULL — Backend Iniciado')
        print('Banco de dados: OK')
        print('Autenticação: OK')
        print('Rotas: OK')
        print('---')
        print('Servidor rodando em http://0.0.0.0:5000')
    
    app.run(debug=True, host='0.0.0.0', port=5000)