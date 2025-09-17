# app/main/__init__.py
from flask import Blueprint

# 1. O Blueprint é criado aqui e nomeado 'main'.
main_bp = Blueprint('main', __name__)

# 2. As rotas são importadas DEPOIS. O código em routes.py será executado,
#    anexando as rotas ao 'main_bp' que acabamos de criar.
from . import routes