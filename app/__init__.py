# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import config
import os

# Inicializar extensões
db = SQLAlchemy()
login_manager = LoginManager()

def create_app(config_name=None):
    """Factory function para criar a aplicação Flask"""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG') or 'default'
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Inicializar extensões com a app
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'info'
    
    # Configurar SQLAlchemy binds para múltiplos bancos de dados
    binds = {}
    for key, db_info in app.config['ASSET_DATABASES'].items():
        binds[key] = db_info['url']
    app.config['SQLALCHEMY_BINDS'] = binds
    
    # Inicializar engines como None - serão criados quando necessário
    app.asset_engines = {}
    
    # Registrar blueprints
    from app.main import main_bp
    app.register_blueprint(main_bp)
    
    # User loader para Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    # Criar bancos de dados se não existirem
    with app.app_context():
        try:
            # Primeiro inicializar as tabelas do SQLAlchemy
            db.create_all()
            
            # Depois configurar os bancos específicos
            from app.sqlite_setup import setup_database_logic
            setup_database_logic()
            
            print("Bancos de dados configurados com sucesso!")
            
        except Exception as e:
            print(f"Erro ao configurar bancos de dados: {e}")
            # Tentar configuração básica
            from app.sqlite_setup import setup_database_logic
            setup_database_logic()
    
    return app