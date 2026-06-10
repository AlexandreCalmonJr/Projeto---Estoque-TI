import hmac
import os
import secrets

from flask import Flask, abort, request, session
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

from config import config


db = SQLAlchemy()
login_manager = LoginManager()


def _get_csrf_token():
    token = session.get('_csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['_csrf_token'] = token
    return token


def _csrf_is_valid():
    expected = session.get('_csrf_token')
    provided = request.form.get('_csrf_token') or request.headers.get('X-CSRFToken')
    return bool(expected and provided and hmac.compare_digest(expected, provided))


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG') or 'default'

    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    app.config['SQLALCHEMY_BINDS'] = {
        key: db_info['url'] for key, db_info in app.config['ASSET_DATABASES'].items()
    }

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'info'

    @app.before_request
    def protect_post_requests():
        if not app.config.get('WTF_CSRF_ENABLED', True):
            return None
        if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'} and not _csrf_is_valid():
            abort(400, description='Token CSRF inválido ou ausente.')
        return None

    @app.context_processor
    def inject_csrf_token():
        return {'csrf_token': _get_csrf_token}

    from app.main import main_bp
    app.register_blueprint(main_bp)

    from app.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    with app.app_context():
        db.create_all()

        from app.models import User
        bootstrap_password = app.config.get('BOOTSTRAP_ADMIN_PASSWORD')
        if bootstrap_password and not User.query.filter_by(username='admin').first():
            default_admin = User(username='admin', is_admin=True)
            default_admin.set_password(bootstrap_password)
            db.session.add(default_admin)
            db.session.commit()
            print("Usuário 'admin' criado a partir de BOOTSTRAP_ADMIN_PASSWORD.")

        try:
            from app.sqlite_setup import setup_database_logic
            setup_database_logic()
            print("Bancos de dados de ativos configurados com sucesso!")
        except Exception as e:
            print(f"Erro ao configurar bancos de dados de ativos: {e}")

    return app
