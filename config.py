import os
import secrets
import sys


if getattr(sys, 'frozen', False):
    basedir = os.path.dirname(sys.executable)
else:
    basedir = os.path.abspath(os.path.dirname(__file__))


def _get_bool_env(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on', 's', 'sim'}


def _get_int_env(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _load_or_create_secret_key():
    env_secret = os.environ.get('SECRET_KEY')
    if env_secret:
        return env_secret

    key_file = os.environ.get('SECRET_KEY_FILE') or os.path.join(basedir, '.estoqueti_secret')
    try:
        if os.path.exists(key_file):
            with open(key_file, 'r', encoding='utf-8') as file:
                secret = file.read().strip()
                if secret:
                    return secret

        secret = secrets.token_urlsafe(48)
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        with open(key_file, 'w', encoding='utf-8') as file:
            file.write(secret)
        return secret
    except OSError:
        # Last-resort fallback for read-only locations. Sessions will reset
        # between app restarts, but the app will still boot.
        return secrets.token_urlsafe(48)


class Config:
    SECRET_KEY = _load_or_create_secret_key()

    SQLALCHEMY_DATABASE_URI = os.environ.get('COMMON_DATABASE_URL') or (
        'sqlite:///' + os.path.join(basedir, 'common.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = _get_bool_env('SESSION_COOKIE_SECURE', False)
    WTF_CSRF_ENABLED = _get_bool_env('WTF_CSRF_ENABLED', True)
    MAX_UPLOAD_MB = _get_int_env('MAX_UPLOAD_MB', 10)
    MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024
    BOOTSTRAP_ADMIN_PASSWORD = os.environ.get('BOOTSTRAP_ADMIN_PASSWORD')

    ALLOWED_UPLOAD_EXTENSIONS = {'csv', 'xlsx'}
    ASSET_STATUSES = {'Em Estoque', 'Em Uso', 'Em Manutenção', 'Em Manutencao', 'Descartado'}
    MOVEMENT_STATUSES = {'Em Estoque', 'Em Manutenção', 'Em Manutencao'}
    DOCUMENT_TEMPLATES = {
        'Termo de Entrega de Ativos - modelo.docx': 'Termo de Entrega',
        'Termo de Responsabilidade de Ativos - modelo.docx': 'Termo de Responsabilidade',
        'Termo de Comodato - Notebook - modelo.docx': 'Termo de Comodato (Notebook)',
    }

    ASSET_DATABASES = {
        'salvador': {
            'name': 'Salvador (BA)',
            'url': os.environ.get('SALVADOR_DB_URL') or 'sqlite:///' + os.path.join(basedir, 'salvador_assets.db'),
        },
        'minas': {
            'name': 'Minas Gerais (MG)',
            'url': os.environ.get('MINAS_DB_URL') or 'sqlite:///' + os.path.join(basedir, 'minas_assets.db'),
        },
        'sergipe': {
            'name': 'Sergipe (SE)',
            'url': os.environ.get('SERGIPE_DB_URL') or 'sqlite:///' + os.path.join(basedir, 'sergipe_assets.db'),
        },
        'geral': {
            'name': 'Geral (Consolidado)',
            'url': os.environ.get('GERAL_DB_URL') or 'sqlite:///' + os.path.join(basedir, 'geral_assets.db'),
        },
    }

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    DEBUG = False
    SECRET_KEY = 'testing-secret-key'
    WTF_CSRF_ENABLED = True
    BOOTSTRAP_ADMIN_PASSWORD = None


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}
