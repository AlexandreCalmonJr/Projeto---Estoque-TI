# app/admin/__init__.py
from flask import Blueprint

# Define o Blueprint para as rotas administrativas
admin_bp = Blueprint(
    'admin', 
    __name__,
    template_folder='templates' # Diz ao Flask para procurar templates na pasta 'templates' deste módulo
)

# Importa as rotas para registrá-las
from . import routes
