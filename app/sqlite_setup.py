# app/sqlite_setup.py
import sqlite3
from flask import current_app

def create_connection(db_file):
    """Cria uma conexão com o banco de dados SQLite."""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row  # Permite acessar colunas por nome
    except sqlite3.Error as e:
        print(e)
    return conn

def setup_database_logic():
    """Garante que a tabela de usuários e as tabelas de ativos existam."""
    # Lógica para o banco de dados comum (usuários)
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
        
        # Criar usuário admin padrão se não existir
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        if cursor.fetchone()[0] == 0:
            from werkzeug.security import generate_password_hash
            admin_hash = generate_password_hash('admin123')
            cursor.execute(
                "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)",
                ('admin', admin_hash, True)
            )
            print("Usuário admin criado com senha: admin123")
        
        conn.commit()

    # Lógica para os bancos de dados de ativos
    for db_key, db_info in current_app.config['ASSET_DATABASES'].items():
        db_path = db_info['url'].replace('sqlite:///', '')
        with create_connection(db_path) as conn:
            cursor = conn.cursor()
            
            # Criar tabela de categorias
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categorias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT UNIQUE NOT NULL
                );
            """)
            
            # Criar tabela de modelos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS modelos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    categoria_id INTEGER NOT NULL,
                    FOREIGN KEY (categoria_id) REFERENCES categorias (id)
                );
            """)
            
            # Atualizar a tabela de ativos para incluir as novas especificações
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
                    destino TEXT, -- ADICIONE ESTA LINHA
                    cpu TEXT,
                    ram_gb INTEGER,
                    armazenamento_gb INTEGER,
                    sistema_operacional TEXT,
                    FOREIGN KEY (modelo_id) REFERENCES modelos (id),
                    FOREIGN KEY (categoria_id) REFERENCES categorias (id)
                );
            """)
            
            # Criar tabela de histórico
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historico (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_ativo TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    evento TEXT NOT NULL,
                    detalhes TEXT
                );
            """)
            
            # Inserir categorias padrão se a tabela estiver vazia
            cursor.execute("SELECT COUNT(*) FROM categorias")
            if cursor.fetchone()[0] == 0:
                categorias_padrao = [
                    "Desktop", "Notebook", "Servidor", "Roteador", 
                    "Switch", "Access Point", "Impressora", "Monitor", 
                    "Mouse", "Teclado", "Webcam", "Headset", 
                    "No-break", "HD Externo"
                ]
                for categoria in categorias_padrao:
                    cursor.execute("INSERT INTO categorias (nome) VALUES (?)", (categoria,))
                
                print(f"Categorias padrão inseridas no banco {db_key}")
            
            conn.commit()
            print(f"Banco de dados {db_key} configurado com sucesso")