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
    
    # Registrar blueprints
    from app.main import main_bp
    app.register_blueprint(main_bp)

    from app.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin') # Adicionar prefixo para rotas de admin
    
    # User loader para Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    # Criar tabelas e popular dados iniciais
    with app.app_context():
        # Cria a tabela 'users' a partir do modelo SQLAlchemy
        db.create_all() 
        
        # ADICIONE ESTAS LINHAS:
        # Importa e executa a lógica para criar as tabelas de ativos (categorias, etc.)
        # e popular as categorias padrão.
        try:
            from app.sqlite_setup import setup_database_logic
            setup_database_logic()
            print("Bancos de dados de ativos configurados com sucesso!")
        except Exception as e:
            print(f"Erro ao configurar bancos de dados de ativos: {e}")

    return app