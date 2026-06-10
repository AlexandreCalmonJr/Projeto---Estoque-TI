import sqlite3

from flask import current_app


def create_connection(db_file):
    """Cria uma conexao SQLite com chaves estrangeiras habilitadas."""
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def setup_database_logic():
    """Garante que o schema SQLite exista sem criar credenciais padrao."""
    common_db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
    with create_connection(common_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin BOOLEAN NOT NULL CHECK (is_admin IN (0, 1))
            );
        """)
        conn.commit()

    for db_key, db_info in current_app.config['ASSET_DATABASES'].items():
        db_path = db_info['url'].replace('sqlite:///', '')
        with create_connection(db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categorias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT UNIQUE NOT NULL
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS modelos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    categoria_id INTEGER NOT NULL,
                    FOREIGN KEY (categoria_id) REFERENCES categorias (id)
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ativos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_ativo TEXT UNIQUE NOT NULL,
                    numero_serie TEXT UNIQUE NOT NULL,
                    marca TEXT NOT NULL,
                    modelo_id INTEGER NOT NULL,
                    categoria_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    nota_fiscal TEXT,
                    fornecedor TEXT,
                    localizacao TEXT,
                    usuario_responsavel TEXT,
                    data_aquisicao DATE,
                    destino TEXT,
                    cpu TEXT,
                    ram_gb INTEGER,
                    armazenamento_gb INTEGER,
                    sistema_operacional TEXT,
                    FOREIGN KEY (modelo_id) REFERENCES modelos (id),
                    FOREIGN KEY (categoria_id) REFERENCES categorias (id)
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historico (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_ativo TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    evento TEXT NOT NULL,
                    detalhes TEXT
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS termos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_ativo TEXT NOT NULL,
                    solicitante TEXT NOT NULL,
                    usuario TEXT NOT NULL,
                    email_usuario TEXT,
                    unidade TEXT,
                    localidade TEXT,
                    setor TEXT,
                    chamado TEXT,
                    template_name TEXT,
                    token TEXT UNIQUE NOT NULL,
                    assinado BOOLEAN NOT NULL DEFAULT 0 CHECK (assinado IN (0, 1)),
                    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                    data_assinatura DATETIME,
                    ip_assinatura TEXT,
                    FOREIGN KEY (id_ativo) REFERENCES ativos (id_ativo)
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS consumiveis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT UNIQUE NOT NULL,
                    quantidade INTEGER NOT NULL DEFAULT 0,
                    unidade_medida TEXT NOT NULL DEFAULT 'unidade',
                    estoque_minimo INTEGER NOT NULL DEFAULT 0,
                    localizacao TEXT,
                    fornecedor TEXT,
                    observacoes TEXT
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS consumiveis_historico (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    consumivel_id INTEGER NOT NULL,
                    tipo_movimentacao TEXT NOT NULL,
                    quantidade INTEGER NOT NULL,
                    data_movimentacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                    usuario TEXT NOT NULL,
                    numero_chamado TEXT,
                    detalhes TEXT,
                    FOREIGN KEY (consumivel_id) REFERENCES consumiveis (id)
                );
            """)

            cursor.execute("SELECT COUNT(*) FROM categorias")
            if cursor.fetchone()[0] == 0:
                categorias_padrao = [
                    "Desktop", "Notebook", "Servidor", "Roteador",
                    "Switch", "Access Point", "Impressora", "Monitor",
                    "Mouse", "Teclado", "Webcam", "Headset",
                    "No-break", "HD Externo",
                ]
                for categoria in categorias_padrao:
                    cursor.execute("INSERT INTO categorias (nome) VALUES (?)", (categoria,))
                print(f"Categorias padrao inseridas no banco {db_key}")

            conn.commit()
            print(f"Banco de dados {db_key} configurado com sucesso")
