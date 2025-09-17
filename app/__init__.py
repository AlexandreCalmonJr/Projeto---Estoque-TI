# (importações existentes no topo do arquivo)
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import config
import os

db = SQLAlchemy()
login_manager = LoginManager()

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG') or 'default'
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'info'
    
    binds = {}
    for key, db_info in app.config['ASSET_DATABASES'].items():
        binds[key] = db_info['url']
    app.config['SQLALCHEMY_BINDS'] = binds
    
    from app.main import main_bp
    app.register_blueprint(main_bp)

    from app.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    with app.app_context():
        # Cria todas as tabelas (users, etc.)
        db.create_all()
        
        # LÓGICA DE CRIAÇÃO AUTOMÁTICA DO ADMIN
        from app.models import User
        if not User.query.filter_by(username='admin').first():
            print("Nenhum usuário 'admin' encontrado. Criando usuário padrão...")
            default_admin = User(username='admin', is_admin=True)
            default_admin.set_password('admin') # Defina uma senha padrão
            db.session.add(default_admin)
            db.session.commit()
            print("Usuário 'admin' criado com a senha 'admin'. Recomenda-se alterar a senha.")

        try:
            from app.sqlite_setup import setup_database_logic
            setup_database_logic()
            print("Bancos de dados de ativos configurados com sucesso!")
        except Exception as e:
            print(f"Erro ao configurar bancos de dados de ativos: {e}")

    return app