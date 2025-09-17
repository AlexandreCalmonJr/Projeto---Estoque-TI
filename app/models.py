from flask import current_app, session
from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime
import sqlite3

# --- Modelo SQLAlchemy (Tabela de Usuários) ---
class User(UserMixin, db.Model):
    __bind_key__ = None  # Usa o banco principal
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# --- Função para obter engine por chave ---
def db_get_engine_by_key(key):
    """Obtém o engine do SQLAlchemy para uma chave de banco específica."""
    try:
        return db.get_engine(bind=key)
    except KeyError:
        # Se não conseguir pelo bind, cria uma conexão SQLite direta
        db_info = current_app.config['ASSET_DATABASES'].get(key)
        if db_info:
            from sqlalchemy import create_engine
            return create_engine(db_info['url'])
        else:
            raise KeyError(f"Banco de dados '{key}' não encontrado na configuração")

# --- Funções de Acesso Direto ao Banco de Dados de Ativos ---
def get_asset_db_connection():
    db_key = session.get('database_key')
    if not db_key: 
        raise ValueError("Nenhuma chave de banco de dados encontrada na sessão")
    
    db_info = current_app.config['ASSET_DATABASES'].get(db_key)
    if not db_info:
        raise ValueError(f"Configuração para banco '{db_key}' não encontrada")
    
    db_path = db_info['url'].replace('sqlite:///', '')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def db_query(query, params=None):
    try:
        with get_asset_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or [])
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Erro na consulta: {e}")
        return []

def db_execute(query, params=None):
    try:
        with get_asset_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or [])
            conn.commit()
    except Exception as e:
        print(f"Erro na execução: {e}")
        raise e

# --- Classe com a Lógica de Negócio ---
class AssetManager:
    def _log_event(self, id_ativo, evento, detalhes, conn):
        cursor = conn.cursor()
        cursor.execute("INSERT INTO historico (id_ativo, evento, detalhes) VALUES (?, ?, ?)",
                       (id_ativo, evento, detalhes))

    def registrar_novo_ativo(self, form_data):
        with get_asset_db_connection() as conn:
            cursor = conn.cursor()
            
            tipo = form_data['tipo_ativo_sigla']
            ano = datetime.now().year
            
            cursor.execute("SELECT COUNT(*) FROM ativos WHERE id_ativo LIKE ?", (f"{tipo}-{ano}-%",))
            sequencial = cursor.fetchone()[0] + 1
            id_ativo = f"{tipo}-{ano}-{sequencial:03d}"
            
            # A query de inserção foi atualizada para incluir
            # os novos campos de especificações técnicas que vêm do formulário.
            # Usamos .get() para os campos opcionais para evitar erros se não forem preenchidos.
            sql = """
                INSERT INTO ativos (id_ativo, numero_serie, marca, modelo_id, categoria_id, status, nota_fiscal, 
                                fornecedor, data_aquisicao, localizacao, usuario_responsavel,
                                cpu, ram_gb, armazenamento_gb, sistema_operacional)
                VALUES (?, ?, ?, ?, ?, 'Em Estoque', ?, ?, ?, 'Estoque TI', NULL, ?, ?, ?, ?)
            """
            params = (
                id_ativo, form_data['numero_serie'], form_data['marca'], form_data['modelo'],
                form_data['categoria'], form_data['nota_fiscal'], form_data['fornecedor'],
                form_data['data_aquisicao'],
                # Novos campos
                form_data.get('cpu'),
                form_data.get('ram_gb') or None, # Salva None se o campo estiver vazio
                form_data.get('armazenamento_gb') or None,
                form_data.get('sistema_operacional')
            )
            cursor.execute(sql, params)
            self._log_event(id_ativo, "Criação", "Ativo cadastrado e movido para o estoque.", conn)
            conn.commit()

    def movimentar(self, id_ativo, novo_status, chamado, detalhes=None):
        with get_asset_db_connection() as conn:
            update_fields = {'status': novo_status}
            if detalhes:
                update_fields.update(detalhes)
            
            set_clause = ", ".join([f"{key} = ?" for key in update_fields.keys()])
            params = list(update_fields.values()) + [id_ativo]
            
            cursor = conn.cursor()
            cursor.execute(f"UPDATE ativos SET {set_clause} WHERE id_ativo = ?", params)
            
            log_detalhes = f"Status alterado para '{novo_status}'. Chamado: {chamado}."
            if 'usuario_responsavel' in update_fields:
                log_detalhes += f" Novo responsável: {update_fields['usuario_responsavel']}."
            
            self._log_event(id_ativo, "Movimentação", log_detalhes, conn)
            conn.commit()

    def baixar(self, id_ativo, chamado):
        self.movimentar(id_ativo, 'Descartado', chamado)