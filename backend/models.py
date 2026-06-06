from backend.main import db
from datetime import datetime
import json

# ============================================================================
# MODELO: USUARIO
# ============================================================================

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    senha = db.Column(db.String(255), nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_acesso = db.Column(db.DateTime, nullable=True)
    ativo = db.Column(db.Boolean, default=True)
    
    # Relacionamentos
    sessoes = db.relationship('Sessao', backref='usuario', lazy=True, cascade='all, delete-orphan')
    configuracoes = db.relationship('ConfiguracaoUsuario', backref='usuario', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Usuario {self.email}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'data_criacao': self.data_criacao.isoformat(),
            'ultimo_acesso': self.ultimo_acesso.isoformat() if self.ultimo_acesso else None,
            'ativo': self.ativo
        }

# ============================================================================
# MODELO: SESSAO
# ============================================================================

class Sessao(db.Model):
    __tablename__ = 'sessoes'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    nome = db.Column(db.String(255), nullable=True)
    descricao = db.Column(db.Text, nullable=True)
    duracao = db.Column(db.Integer, default=0)  # em segundos
    silencio_pct = db.Column(db.Float, default=0)
    hesitacao_pct = db.Column(db.Float, default=0)
    eventos = db.Column(db.Integer, default=0)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = db.Column(db.String(50), default='concluida')  # concluida, em_progresso, erro
    dados_sessao = db.Column(db.JSON, nullable=True)
    
    # Relacionamentos
    eventos_sessao = db.relationship('EventoSessao', backref='sessao', lazy=True, cascade='all, delete-orphan')
    metricas = db.relationship('MetricaSessao', backref='sessao', lazy=True, cascade='all, delete-orphan')
    
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
            'status': self.status,
            'data_criacao': self.data_criacao.isoformat(),
            'data_atualizacao': self.data_atualizacao.isoformat()
        }

# ============================================================================
# MODELO: EVENTO SESSAO
# ============================================================================

class EventoSessao(db.Model):
    __tablename__ = 'eventos_sessao'
    
    id = db.Column(db.Integer, primary_key=True)
    sessao_id = db.Column(db.Integer, db.ForeignKey('sessoes.id'), nullable=False, index=True)
    tipo_evento = db.Column(db.String(50), nullable=False)  # clique, teclado, pausa, etc
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    intervalo_anterior = db.Column(db.Float, default=0)  # em ms
    coordenadas_x = db.Column(db.Integer, nullable=True)
    coordenadas_y = db.Column(db.Integer, nullable=True)
    dados_evento = db.Column(db.JSON, nullable=True)
    
    def __repr__(self):
        return f'<EventoSessao {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'tipo_evento': self.tipo_evento,
            'timestamp': self.timestamp.isoformat(),
            'intervalo_anterior': self.intervalo_anterior,
            'coordenadas': {
                'x': self.coordenadas_x,
                'y': self.coordenadas_y
            },
            'dados': self.dados_evento
        }

# ============================================================================
# MODELO: METRICA SESSAO
# ============================================================================

class MetricaSessao(db.Model):
    __tablename__ = 'metricas_sessao'
    
    id = db.Column(db.Integer, primary_key=True)
    sessao_id = db.Column(db.Integer, db.ForeignKey('sessoes.id'), nullable=False, index=True)
    tipo_metrica = db.Column(db.String(100), nullable=False)  # pausa_curta, pausa_media, etc
    valor = db.Column(db.Float, nullable=False)
    unidade = db.Column(db.String(50), default='ms')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<MetricaSessao {self.tipo_metrica}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'tipo_metrica': self.tipo_metrica,
            'valor': self.valor,
            'unidade': self.unidade,
            'timestamp': self.timestamp.isoformat()
        }

# ============================================================================
# MODELO: CONFIGURACAO USUARIO
# ============================================================================

class ConfiguracaoUsuario(db.Model):
    __tablename__ = 'configuracoes_usuario'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    chave = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(50), default='string')  # string, int, float, bool, json
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ConfiguracaoUsuario {self.chave}>'
    
    def to_dict(self):
        return {
            'chave': self.chave,
            'valor': self.valor,
            'tipo': self.tipo
        }

# ============================================================================
# MODELO: LOG SISTEMA
# ============================================================================

class LogSistema(db.Model):
    __tablename__ = 'logs_sistema'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True, index=True)
    tipo_log = db.Column(db.String(50), nullable=False)  # info, warning, error, debug
    mensagem = db.Column(db.Text, nullable=False)
    detalhes = db.Column(db.JSON, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<LogSistema {self.tipo_log}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'tipo_log': self.tipo_log,
            'mensagem': self.mensagem,
            'detalhes': self.detalhes,
            'timestamp': self.timestamp.isoformat()
        }

# ============================================================================
# MODELO: CONFIGURACAO TEMPORAL (CRS)
# ============================================================================

class ConfiguracaoTemporal(db.Model):
    __tablename__ = 'configuracoes_temporais'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    pausa_curta_min = db.Column(db.Float, default=100)  # ms
    pausa_curta_max = db.Column(db.Float, default=500)
    pausa_media_min = db.Column(db.Float, default=500)
    pausa_media_max = db.Column(db.Float, default=2000)
    pausa_longa_min = db.Column(db.Float, default=2000)
    pausa_longa_max = db.Column(db.Float, default=10000)
    ritmo_acelerado_threshold = db.Column(db.Float, default=0.8)
    ritmo_desacelerado_threshold = db.Column(db.Float, default=1.2)
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ConfiguracaoTemporal {self.nome}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'pausa_curta': {
                'min': self.pausa_curta_min,
                'max': self.pausa_curta_max
            },
            'pausa_media': {
                'min': self.pausa_media_min,
                'max': self.pausa_media_max
            },
            'pausa_longa': {
                'min': self.pausa_longa_min,
                'max': self.pausa_longa_max
            },
            'ritmo_acelerado_threshold': self.ritmo_acelerado_threshold,
            'ritmo_desacelerado_threshold': self.ritmo_desacelerado_threshold,
            'ativo': self.ativo
        }