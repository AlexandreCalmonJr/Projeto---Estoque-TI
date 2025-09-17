# app/database.py
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2 import errors
from sqlalchemy import inspect, text
from sqlalchemy.engine import url as sa_url
from . import db
from flask import current_app

def create_databases_if_not_exists():
    """
    Verifica e cria os bancos de dados (common e assets) se eles não existirem.
    Conecta-se ao DB 'postgres' padrão para executar os comandos CREATE DATABASE.
    """
    db_urls = [current_app.config['SQLALCHEMY_DATABASE_URI']]
    for db_info in current_app.config['ASSET_DATABASES'].values():
        db_urls.append(db_info['url'])

    processed_urls = set()

    for url_string in db_urls:
        if url_string in processed_urls or url_string.startswith('sqlite'):
            continue
        
        processed_urls.add(url_string)
        conn = None
        
        try:
            url = sa_url.make_url(url_string)
            db_name = url.database
            
            # Conecta ao servidor PostgreSQL (usando o banco de dados 'postgres' padrão)
            conn = psycopg2.connect(
                dbname='postgres',
                user=url.username,
                password=url.password,
                host=url.host,
                port=url.port
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            exists = cursor.fetchone()
            
            if not exists:
                print(f"Banco de dados '{db_name}' não encontrado. Criando...")
                cursor.execute(f'CREATE DATABASE "{db_name}"')
                print(f"Banco de dados '{db_name}' criado com sucesso.")
            
            cursor.close()

        except psycopg2.OperationalError as e:
            print(f"ERRO: Não foi possível conectar ao servidor PostgreSQL. Verifique suas credenciais e se o servidor está rodando. Detalhes: {e}")
            # Em um cenário real, você poderia querer parar a aplicação aqui
            # raise e
        except Exception as e:
            print(f"Ocorreu um erro inesperado ao tentar criar o banco de dados: {e}")
        finally:
            if conn:
                conn.close()

def setup_asset_db_schema(engine):
    """Cria a estrutura de tabelas para um banco de dados de ativos."""
    # (O restante desta função permanece o mesmo)
    with engine.connect() as connection:
        queries = [
            """CREATE TABLE IF NOT EXISTS categorias (id SERIAL PRIMARY KEY, nome TEXT NOT NULL UNIQUE);""",
            """CREATE TABLE IF NOT EXISTS modelos (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, categoria_id INTEGER, FOREIGN KEY (categoria_id) REFERENCES categorias (id));""",
            """CREATE TABLE IF NOT EXISTS ativos (id_ativo TEXT PRIMARY KEY, numero_serie TEXT NOT NULL UNIQUE, marca TEXT NOT NULL, modelo_id INTEGER, categoria_id INTEGER, status TEXT NOT NULL, nota_fiscal TEXT, fornecedor TEXT, localizacao TEXT, usuario_responsavel TEXT, data_aquisicao TEXT NOT NULL, FOREIGN KEY (modelo_id) REFERENCES modelos (id), FOREIGN KEY (categoria_id) REFERENCES categorias (id));""",
            """CREATE TABLE IF NOT EXISTS historico (id SERIAL PRIMARY KEY, id_ativo TEXT, timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, descricao TEXT NOT NULL, numero_chamado TEXT, FOREIGN KEY (id_ativo) REFERENCES ativos (id_ativo));"""
        ]
        for query in queries:
            connection.execute(text(query))
        
        result = connection.execute(text("SELECT COUNT(*) FROM categorias")).scalar()
        if result == 0:
            categorias_iniciais = ["Desktop", "Notebook", "Servidor", "Roteador", "Switch", "Access Point", "Impressora", "Monitor", "Mouse", "Teclado", "Webcam", "Headset", "No-break", "HD Externo"]
            for cat in categorias_iniciais:
                connection.execute(text("INSERT INTO categorias (nome) VALUES (:nome)"), {'nome': cat})
        connection.commit()


def init_all_dbs():
    """Inicializa todos os bancos de dados: o comum e todos os de ativos."""
    # (O restante desta função permanece o mesmo)
    inspector = inspect(db.engine)
    if not inspector.has_table('users'):
        print("Criando tabela de usuários no banco de dados comum...")
        db.create_all()
        print("Tabela 'users' criada.")

    for key, engine in current_app.asset_engines.items():
        asset_inspector = inspect(engine)
        if not asset_inspector.has_table('ativos'):
            print(f"Criando esquema de tabelas para o banco de dados '{key}'...")
            setup_asset_db_schema(engine)
            print(f"Esquema para '{key}' criado com sucesso.")

