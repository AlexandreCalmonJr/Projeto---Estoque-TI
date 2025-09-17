# app/models.py

from flask import current_app, session
from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import text, create_engine

# --- Modelo SQLAlchemy (Tabela de Usuários) ---
class User(UserMixin, db.Model):
    __bind_key__ = None
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# --- Funções de Acesso ao Banco de Dados (CORRIGIDAS) ---

def get_asset_db_engine():
    """Obtém o engine do SQLAlchemy para o banco de dados de ativos selecionado na sessão."""
    db_key = session.get('database_key')
    if not db_key: 
        raise ValueError("Nenhuma chave de banco de dados encontrada na sessão")
    
    # Usa a configuração da app para obter a URL do banco de dados
    db_info = current_app.config['ASSET_DATABASES'].get(db_key)
    if not db_info:
        raise ValueError(f"Configuração para banco '{db_key}' não encontrada")
    
    # Cria um engine do SQLAlchemy sob demanda
    return create_engine(db_info['url'])

def db_query(query, params=None):
    """Executa uma consulta SELECT usando SQLAlchemy e retorna uma lista de dicionários."""
    try:
        engine = get_asset_db_engine()
        with engine.connect() as connection:
            result = connection.execute(text(query), params or {})
            return [dict(row._mapping) for row in result]
    except Exception as e:
        print(f"Erro na consulta: {e}")
        return []

def db_execute(query, params=None):
    """Executa uma instrução (INSERT, UPDATE, DELETE) usando SQLAlchemy."""
    try:
        engine = get_asset_db_engine()
        with engine.connect() as connection:
            connection.execute(text(query), params or {})
            connection.commit()
    except Exception as e:
        print(f"Erro na execução: {e}")
        raise e

# --- Classe com a Lógica de Negócio ---
class AssetManager:
    def _log_event(self, id_ativo, evento, detalhes, conn):
        params = {'id_ativo': id_ativo, 'evento': evento, 'detalhes': detalhes}
        conn.execute(text("INSERT INTO historico (id_ativo, evento, detalhes) VALUES (:id_ativo, :evento, :detalhes)"), params)

    def registrar_novo_ativo(self, form_data):
        engine = get_asset_db_engine()
        with engine.connect() as conn:
            
            # Lógica de Quantidade
            try:
                quantidade = int(form_data.get('quantidade', 1))
                if quantidade < 1: quantidade = 1
            except (ValueError, TypeError):
                quantidade = 1

            # Loop para criar múltiplos ativos
            for i in range(quantidade):
                # Lógica para patrimônio opcional
                id_ativo = form_data.get('id_ativo')
                if id_ativo and id_ativo.strip():
                    id_ativo = id_ativo.strip()
                    if quantidade > 1: # Se for mais de um item, anexa um sufixo para evitar duplicatas
                        id_ativo = f"{id_ativo}-{i+1}"
                    
                    result = conn.execute(text("SELECT id FROM ativos WHERE id_ativo = :id_ativo"), {'id_ativo': id_ativo})
                    if result.first():
                        raise ValueError(f"O patrimônio '{id_ativo}' já existe.")
                else:
                    tipo = form_data['tipo_ativo_sigla']
                    ano = datetime.now().year
                    result = conn.execute(text("SELECT COUNT(*) FROM ativos WHERE id_ativo LIKE :like_pattern"), {'like_pattern': f"{tipo}-{ano}-%"})
                    sequencial = result.scalar_one() + 1
                    id_ativo = f"{tipo}-{ano}-{sequencial + i}" # Adiciona o índice do loop para garantir unicidade
                
                # Lógica para número de série
                numero_serie = form_data.get('numero_serie', '').strip()
                if not numero_serie:
                    timestamp = int(time.time() * 1000)
                    numero_serie = f"PROV-{timestamp + i}" # Cria serial provisório
                elif quantidade > 1:
                    numero_serie = f"{numero_serie}-{i+1}" # Anexa sufixo se for mais de um item

                # Lógica de INSERT (o SQL e os params foram atualizados)
                sql = """
                    INSERT INTO ativos (id_ativo, numero_serie, marca, modelo_id, categoria_id, status, nota_fiscal, 
                                    fornecedor, data_aquisicao, localizacao, usuario_responsavel, destino,
                                    cpu, ram_gb, armazenamento_gb, sistema_operacional)
                    VALUES (:id_ativo, :numero_serie, :marca, :modelo_id, :categoria_id, 'Em Estoque', :nota_fiscal, 
                            :fornecedor, :data_aquisicao, :destino, NULL, :destino,
                            :cpu, :ram_gb, :armazenamento_gb, :sistema_operacional)
                """
                params = {
                    'id_ativo': id_ativo, 
                    'numero_serie': numero_serie,
                    'marca': form_data['marca'], 
                    'modelo_id': form_data['modelo'], 
                    'categoria_id': form_data['categoria'], 
                    'nota_fiscal': form_data.get('nota_fiscal'),
                    'fornecedor': form_data.get('fornecedor'), 
                    'data_aquisicao': form_data.get('data_aquisicao') or None,
                    'destino': form_data.get('destino'),
                    'cpu': form_data.get('cpu'), 
                    'ram_gb': form_data.get('ram_gb') or None,
                    'armazenamento_gb': form_data.get('armazenamento_gb') or None, 
                    'sistema_operacional': form_data.get('sistema_operacional')
                }
                conn.execute(text(sql), params)
                self._log_event(id_ativo, "Criação", "Ativo cadastrado em lote e movido para o estoque.", conn)
            
            conn.commit()


    # ADICIONE ESTA NOVA FUNÇÃO DENTRO DA CLASSE AssetManager
    def atualizar_lote_ativos(self, form_data):
        engine = get_asset_db_engine()
        updates = {}
        # Organiza os dados do formulário em um dicionário por ID de banco de dados
        for key, value in form_data.items():
            if key.startswith('db_id_'):
                idx = key.split('_')[-1]
                db_id = int(value)
                if db_id not in updates:
                    updates[db_id] = {}
                updates[db_id]['id_ativo'] = form_data.get(f'id_ativo_{idx}')
                updates[db_id]['numero_serie'] = form_data.get(f'numero_serie_{idx}')

        with engine.connect() as conn:
            for db_id, data in updates.items():
                novo_id_ativo = data['id_ativo']
                novo_numero_serie = data['numero_serie']
                
                # Validações de unicidade
                result = conn.execute(text("SELECT id FROM ativos WHERE id_ativo = :id AND id != :db_id"), {'id': novo_id_ativo, 'db_id': db_id})
                if result.first():
                    raise ValueError(f"Patrimônio '{novo_id_ativo}' já existe.")
                
                result = conn.execute(text("SELECT id FROM ativos WHERE numero_serie = :sn AND id != :db_id"), {'sn': novo_numero_serie, 'db_id': db_id})
                if result.first():
                    raise ValueError(f"Número de Série '{novo_numero_serie}' já existe.")

                # Atualiza o ativo
                sql = "UPDATE ativos SET id_ativo = :id_ativo, numero_serie = :numero_serie WHERE id = :db_id"
                conn.execute(text(sql), {'id_ativo': novo_id_ativo, 'numero_serie': novo_numero_serie, 'db_id': db_id})
                self._log_event(novo_id_ativo, "Atualização em Lote", f"Patrimônio e/ou Serial atualizados para valores definitivos.", conn)

            conn.commit()

    def movimentar(self, id_ativo, novo_status, chamado, detalhes=None):
        engine = get_asset_db_engine()
        with engine.connect() as conn:
            update_fields = {'status': novo_status}
            if detalhes:
                update_fields.update(detalhes)
            
            set_clause = ", ".join([f"{key} = :{key}" for key in update_fields.keys()])
            params = {**update_fields, 'id_ativo': id_ativo}
            
            conn.execute(text(f"UPDATE ativos SET {set_clause} WHERE id_ativo = :id_ativo"), params)
            
            log_detalhes = f"Status alterado para '{novo_status}'. Chamado: {chamado}."
            if 'usuario_responsavel' in update_fields:
                log_detalhes += f" Novo responsável: {update_fields['usuario_responsavel']}."
            
            self._log_event(id_ativo, "Movimentação", log_detalhes, conn)
            conn.commit()

    def baixar(self, id_ativo, chamado):
        self.movimentar(id_ativo, 'Descartado', chamado)
        
    def atualizar_ativo(self, id_ativo_original, form_data):
        engine = get_asset_db_engine()
        with engine.connect() as conn:
            # Pega o novo ID do patrimônio do formulário
            novo_id_ativo = form_data.get('id_ativo').strip()

            # Se o patrimônio foi alterado, verifica se o novo já não está em uso
            if id_ativo_original != novo_id_ativo:
                result = conn.execute(text("SELECT id FROM ativos WHERE id_ativo = :id_ativo"), {'id_ativo': novo_id_ativo})
                if result.first():
                    raise ValueError(f"O novo patrimônio '{novo_id_ativo}' já pertence a outro ativo.")
            
            # Constrói a query de atualização
            sql = """
                UPDATE ativos SET
                    id_ativo = :id_ativo,
                    numero_serie = :numero_serie,
                    marca = :marca,
                    modelo_id = :modelo_id,
                    categoria_id = :categoria_id,
                    nota_fiscal = :nota_fiscal,
                    fornecedor = :fornecedor,
                    data_aquisicao = :data_aquisicao,
                    destino = :destino
                WHERE id_ativo = :id_ativo_original
            """
            params = {
                'id_ativo': novo_id_ativo,
                'numero_serie': form_data['numero_serie'],
                'marca': form_data['marca'],
                'modelo_id': form_data['modelo'],
                'categoria_id': form_data['categoria'],
                'nota_fiscal': form_data.get('nota_fiscal'),
                'fornecedor': form_data.get('fornecedor'),
                'data_aquisicao': form_data.get('data_aquisicao') or None,
                'destino': form_data.get('destino'),
                'id_ativo_original': id_ativo_original
            }
            conn.execute(text(sql), params)
            
            # Registra o evento no histórico se o patrimônio foi alterado
            if id_ativo_original != novo_id_ativo:
                detalhes = f"Patrimônio alterado de '{id_ativo_original}' para '{novo_id_ativo}'."
                self._log_event(novo_id_ativo, "Atualização", detalhes, conn)

            conn.commit()
            return novo_id_ativo # Retorna o novo ID para o redirecionamento    

def get_engine_by_key(key):
    """
    Obtém o engine do SQLAlchemy para uma chave de banco de dados específica.
    Usado pelo painel de admin para iterar sobre todos os bancos.
    """
    db_info = current_app.config['ASSET_DATABASES'].get(key)
    if not db_info:
        raise ValueError(f"Configuração para banco '{key}' não encontrada")
    
    return create_engine(db_info['url'])