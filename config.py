# config.py
import os

class Config:
    """
    Configurações base da aplicação. Use variáveis de ambiente para produção.
    """
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'uma-chave-secreta-muito-segura-e-dificil-de-adivinhar'
    
    # --- BANCO DE DADOS DE AUTENTICAÇÃO ---
    # Este é o banco central para validar usuários.
    SQLALCHEMY_DATABASE_URI = os.environ.get('COMMON_DATABASE_URL') or \
        'sqlite:///common.db'
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- DICIONÁRIO DE CONEXÕES DOS BANCOS DE DADOS DE ATIVOS ---
    # Mapeia um nome amigável para a URL de conexão real.
    ASSET_DATABASES = {
        'salvador': {
            'name': 'Salvador (BA)',
            'url': os.environ.get('SALVADOR_DB_URL') or 'sqlite:///salvador_assets.db'
        },
        'minas': {
            'name': 'Minas Gerais (MG)',
            'url': os.environ.get('MINAS_DB_URL') or 'sqlite:///minas_assets.db'
        },
        'geral': {
            'name': 'Geral (Consolidado)',
            'url': os.environ.get('GERAL_DB_URL') or 'sqlite:///geral_assets.db'
        }
    }

    @staticmethod
    def init_app(app):
        """Método para inicializar configurações específicas da aplicação"""
        pass


class DevelopmentConfig(Config):
    """Configurações para ambiente de desenvolvimento"""
    DEBUG = True


class ProductionConfig(Config):
    """Configurações para ambiente de produção"""
    DEBUG = False

    @staticmethod
    def init_app(app):
        Config.init_app(app)
        
        # Log para um arquivo em produção
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not app.debug:
            if not os.path.exists('logs'):
                os.mkdir('logs')
            file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            app.logger.setLevel(logging.INFO)
            app.logger.info('Aplicação iniciada')


class TestConfig(Config):
    """Configurações para ambiente de testes"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# Dicionário de configurações que será importado pelo __init__.py
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestConfig,
    'default': DevelopmentConfig
}