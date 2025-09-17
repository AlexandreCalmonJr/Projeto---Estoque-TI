# app/main/__init__.py
from flask import Blueprint

# Define o Blueprint para as rotas principais da aplicação
main_bp = Blueprint('main', __name__)

# Importa as rotas para que sejam registradas com o blueprint
from . import routes