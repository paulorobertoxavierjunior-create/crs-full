import os
from datetime import timedelta

class Config:
    """Configuração base da aplicação"""
    
    # Servidor
    SERVER_PORT = int(os.getenv('SERVER_PORT', 5000))
    SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
    NODE_ENV = os.getenv('NODE_ENV', 'development')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    TESTING = os.getenv('TESTING', 'False').lower() == 'true'
    
    # Banco de dados
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///crs_full.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Segurança
    SECRET_KEY = os.getenv('SECRET_KEY', 'sua-chave-secreta-desenvolvimento')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'sua-chave-jwt-desenvolvimento')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:8000').split(',')
    
    # IA
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/crs_full.log')
    
    # Sessões
    MAX_SESSOES_POR_USUARIO = 10
    SESSAO_TIMEOUT_MINUTOS = 30
    
    # Uploads
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads/')
    MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB
    
    @classmethod
    def init_app(cls, app):
        """Inicializar configurações na aplicação Flask"""
        print(f'[CRS-FULL] Ambiente: {cls.NODE_ENV}')
        print(f'[CRS-FULL] Debug: {cls.DEBUG}')
        print(f'[CRS-FULL] Banco de dados: {cls.SQLALCHEMY_DATABASE_URI}')
        print(f'[CRS-FULL] CORS: {cls.CORS_ORIGINS}')


class DevelopmentConfig(Config):
    """Configuração para desenvolvimento"""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """Configuração para produção"""
    DEBUG = False
    TESTING = False
    SQLALCHEMY_ECHO = False


class TestingConfig(Config):
    """Configuração para testes"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)


# Seletor de configuração
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Retorna a configuração apropriada baseada no NODE_ENV"""
    env = os.getenv('NODE_ENV', 'development')
    return config_by_name.get(env, DevelopmentConfig)