import os
import sys

# Determina o diretório base da aplicação. Funciona tanto no modo de desenvolvimento quanto no modo "empacotado" (.exe).
if getattr(sys, 'frozen', False):
    # Se estiver rodando como um .exe (empacotado pelo PyInstaller)
    basedir = os.path.dirname(sys.executable)
else:
    # Se estiver rodando como um script python normal
    basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """
    Configurações base da aplicação.
    """
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'uma-chave-secreta-muito-segura-e-dificil-de-adivinhar'
    
    # --- BANCO DE DADOS DE AUTENTICAÇÃO ---
    # Usa o diretório base para garantir que o caminho esteja sempre correto.
    SQLALCHEMY_DATABASE_URI = os.environ.get('COMMON_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'common.db')
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- DICIONÁRIO DE CONEXÕES DOS BANCOS DE DADOS DE ATIVOS ---
    ASSET_DATABASES = {
        'salvador': {
            'name': 'Salvador (BA)',
            'url': os.environ.get('SALVADOR_DB_URL') or 'sqlite:///' + os.path.join(basedir, 'salvador_assets.db')
        },
        'minas': {
            'name': 'Minas Gerais (MG)',
            'url': os.environ.get('MINAS_DB_URL') or 'sqlite:///' + os.path.join(basedir, 'minas_assets.db')
        },
        # ADICIONE O BLOCO ABAIXO
        'sergipe': {
            'name': 'Sergipe (SE)',
            'url': os.environ.get('SERGIPE_DB_URL') or 'sqlite:///' + os.path.join(basedir, 'sergipe_assets.db')
        },
        # FIM DO NOVO BLOCO
        'geral': {
            'name': 'Geral (Consolidado)',
            'url': os.environ.get('GERAL_DB_URL') or 'sqlite:///' + os.path.join(basedir, 'geral_assets.db')
        }
    }

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

# Dicionário de configurações
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}