# ============================================================================
# CRS-FULL — BACKEND
# ============================================================================
# Versão cirúrgica: mantém as MESMAS rotas e os MESMOS contratos de resposta.
# Corrige apenas risco de segurança e de operação. Nada de refactor aqui —
# a reestruturação acontece no repositório novo.
#
# ---------------------------------------------------------------------------
# ATENÇÃO — ORDEM DE INSTALAÇÃO
# O serviço NÃO SOBE sem as variáveis abaixo cadastradas no painel do Render.
# Cadastre TODAS antes de publicar esta versão.
#
#   DATABASE_URL      Internal Database URL do Postgres do Render
#   SECRET_KEY        mínimo 32 caracteres
#                     python -c "import secrets; print(secrets.token_hex(32))"
#   ALLOWED_ORIGINS   ex.: https://elayon-front.onrender.com
#   TOKEN_INTERNO     opcional; se existir, a rota do CRS passa a exigir
#                     o cabeçalho X-CRS-Token
# ---------------------------------------------------------------------------

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)

# ============================================================================
# CONFIGURAÇÃO — FONTE ÚNICA, SEM VALOR PADRÃO PARA SEGREDO
# ============================================================================

def _obrigatoria(nome, minimo=0):
    """Lê variável de ambiente obrigatória. Ausente ou curta = processo não sobe.

    Servidor que sobe com chave de exemplo é servidor que vai a produção com
    chave de exemplo. Falhar alto aqui é mais seguro que subir em silêncio.
    """
    valor = (os.getenv(nome) or '').strip()
    if not valor:
        raise RuntimeError(f'{nome} ausente — o serviço não sobe sem esta variável')
    if minimo and len(valor) < minimo:
        raise RuntimeError(f'{nome} curta — mínimo de {minimo} caracteres')
    return valor


# --- BANCO DE DADOS ---------------------------------------------------------
# ANTES: 'sqlite:///crs_full.db' fixo.
# No Render o disco é descartável: cada deploy ou reinício apagava todos os
# usuários e sessões. O banco tem que ser externo e persistente.
_db_url = _obrigatoria('DATABASE_URL')

# O Render entrega a URL no formato antigo "postgres://", que o SQLAlchemy 2
# recusa. Sem esta normalização o serviço sobe e morre na primeira consulta.
if _db_url.startswith('postgres://'):
    _db_url = _db_url.replace('postgres://', 'postgresql+psycopg2://', 1)
elif _db_url.startswith('postgresql://'):
    _db_url = _db_url.replace('postgresql://', 'postgresql+psycopg2://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = _db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,   # descarta conexão morta antes de usar
    'pool_recycle': 280,     # o Render encerra conexões ociosas
}

# --- SEGURANÇA --------------------------------------------------------------
# ANTES: os.getenv('SECRET_KEY', 'elayon-token-secreto-multimodal').
# O repositório era público. Qualquer pessoa que lesse o código assinava um
# JWT válido e entrava em /api/auth/perfil como qualquer usuário.
app.config['SECRET_KEY'] = _obrigatoria('SECRET_KEY', minimo=32)

# --- CORS -------------------------------------------------------------------
# ANTES: origins ["*"] — qualquer site do mundo chamava sua API.
_origins = [o.strip() for o in (os.getenv('ALLOWED_ORIGINS') or '').split(',') if o.strip()]
if not _origins:
    raise RuntimeError('ALLOWED_ORIGINS ausente — CORS não pode ficar aberto')

CORS(app, resources={
    r"/api/*": {
        "origins": _origins,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-CRS-Token"]
    },
    # /health segue aberto de propósito: monitoramento precisa bater nele
    # sem credencial.
    r"/health": {
        "origins": ["*"],
        "methods": ["GET"]
    }
})

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
            # db.session.get substitui Query.get, removido no SQLAlchemy 2.
            usuario = db.session.get(Usuario, data['usuario_id'])
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


# Rota vital para o HEALTHCHECK do Dockerfile passar (evita o loop de restart)
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'database': 'ready',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

# ============================================================================
# ROTA DE INGESTÃO CRS (HANDSHAKE MULTIMODAL)
# ============================================================================

@app.route('/api/crs/fifo-buffer', methods=['POST'])
def crs_fifo_buffer():
    # Trava de ingestão. A chave só é exigida quando TOKEN_INTERNO existir no
    # ambiente — permite girar a fechadura sem derrubar o frontend de uma vez.
    _token = (os.getenv('TOKEN_INTERNO') or '').strip()
    if _token:
        _recebido = request.headers.get('X-CRS-Token', '')
        if not secrets.compare_digest(_recebido, _token):
            return jsonify({'mensagem': 'Não autorizado'}), 401

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
        # TODO(crs-core): substituir por motor puro. O vocabulário devolvido
        # aqui contraria o FUNDAMENTOS-CRS.md ("não é diagnóstico") — fica como
        # está para não quebrar o frontend atual.
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
# ROTAS DE SESSÕES
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
        # CORRIGIDO: a versão anterior comparava uma variável inexistente
        # ("clansessao"), o que levantava NameError em toda chamada e fazia
        # esta rota responder 500 sempre. Sessão existente nunca era servida.
        if not sessao:
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
# INICIALIZAÇÃO DAS TABELAS
# ============================================================================

# O Dockerfile roda "gunicorn main:app". Nesse modo o bloco
# if __name__ == '__main__' NUNCA executa — e o db.create_all() que morava
# lá dentro nunca rodava em produção. Resultado: as tabelas não existiam no
# servidor. Aqui a criação acontece na importação, valendo para gunicorn e
# para execução local.
#
# TODO(crs-core): trocar por migrações versionadas (Alembic). create_all()
# não altera tabela existente, só cria o que falta.
with app.app_context():
    try:
        db.create_all()
    except Exception as erro:
        print(f'[CRS-FULL] Falha ao criar tabelas: {erro}')


if __name__ == '__main__':
    print('🔊 ELAYON ENGINE — CRS-FULL BACKEND CONECTADO')
    print('Handshake Multimodal: OK')
    print('Pronto para o Healthcheck do Dockerfile!')
    print('---')
    # debug=True expõe console de execução de código no servidor. Nunca em
    # produção. A porta vem do ambiente; o Render injeta PORT.
    app.run(debug=False, host='0.0.0.0', port=int(os.getenv('PORT', '5000')))