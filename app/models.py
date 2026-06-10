import re
import time
from datetime import datetime

from flask import current_app, session
from flask_login import UserMixin
from sqlalchemy import create_engine, text
from werkzeug.security import check_password_hash, generate_password_hash

from . import db


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


def get_asset_db_engine():
    db_key = session.get('database_key')
    if not db_key:
        raise ValueError("Nenhuma chave de banco de dados encontrada na sessão")

    db_info = current_app.config['ASSET_DATABASES'].get(db_key)
    if not db_info:
        raise ValueError(f"Configuração para banco '{db_key}' não encontrada")

    return create_engine(db_info['url'])


def db_query(query, params=None):
    try:
        engine = get_asset_db_engine()
        with engine.connect() as connection:
            result = connection.execute(text(query), params or {})
            return [dict(row._mapping) for row in result]
    except Exception as e:
        print(f"Erro na consulta: {e}")
        return []


def db_execute(query, params=None):
    try:
        engine = get_asset_db_engine()
        with engine.begin() as connection:
            connection.execute(text(query), params or {})
    except Exception as e:
        print(f"Erro na execução: {e}")
        raise


class AssetManager:
    ALLOWED_UPDATE_FIELDS = {
        'status',
        'usuario_responsavel',
        'localizacao',
        'destino',
    }

    def _log_event(self, id_ativo, evento, detalhes, conn):
        conn.execute(
            text("INSERT INTO historico (id_ativo, evento, detalhes) VALUES (:id_ativo, :evento, :detalhes)"),
            {'id_ativo': id_ativo, 'evento': evento, 'detalhes': detalhes},
        )

    def _get_text(self, form_data, key, default=''):
        value = form_data.get(key, default)
        if value is None:
            return default
        return str(value).strip()

    def _require_text(self, form_data, key, label):
        value = self._get_text(form_data, key)
        if not value:
            raise ValueError(f"O campo {label} é obrigatório.")
        return value

    def _get_positive_int(self, form_data, key, default=1):
        try:
            value = int(form_data.get(key, default))
            return value if value > 0 else default
        except (TypeError, ValueError):
            return default

    def _optional_int(self, form_data, key):
        value = self._get_text(form_data, key)
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"O campo {key} deve ser numérico.")

    def _category_sigla(self, conn, categoria_id):
        result = conn.execute(text("SELECT nome FROM categorias WHERE id = :id"), {'id': categoria_id}).first()
        if not result:
            raise ValueError("Categoria selecionada não foi encontrada.")
        normalized = re.sub(r'[^A-Za-z0-9À-ÿ]', '', result._mapping['nome']).upper()
        return (normalized[:2] or 'AT')

    def _location_and_destino(self, form_data):
        destino = self._get_text(form_data, 'destino')
        localidade = self._get_text(form_data, 'localidade')
        setor = self._get_text(form_data, 'setor')

        if localidade and setor:
            localizacao = f"{localidade} - {setor}"
        elif localidade or setor:
            localizacao = localidade or setor
        else:
            localizacao = destino or None

        return localizacao, destino or setor or localizacao or 'Estoque TI'

    def _next_generated_id(self, conn, prefixo, offset=0):
        query_max = text("""
            SELECT MAX(CAST(SUBSTR(id_ativo, LENGTH(:prefix) + 1) AS INTEGER))
            FROM ativos
            WHERE id_ativo LIKE :like_pattern
        """)
        max_seq = conn.execute(
            query_max,
            {'prefix': prefixo, 'like_pattern': f"{prefixo}%"},
        ).scalar_one()
        return f"{prefixo}{(max_seq or 0) + 1 + offset:03d}"

    def registrar_novo_ativo(self, form_data):
        engine = get_asset_db_engine()
        quantidade = self._get_positive_int(form_data, 'quantidade', 1)
        categoria_id = self._require_text(form_data, 'categoria', 'categoria')
        modelo_id = self._require_text(form_data, 'modelo', 'modelo')
        marca = self._require_text(form_data, 'marca', 'marca')
        base_id_ativo = self._get_text(form_data, 'id_ativo')
        base_numero_serie = self._get_text(form_data, 'numero_serie')
        localizacao, destino = self._location_and_destino(form_data)

        with engine.begin() as conn:
            sigla = self._category_sigla(conn, categoria_id)
            prefixo = f"{sigla}-{datetime.now().year}-"

            for i in range(quantidade):
                if base_id_ativo:
                    id_ativo = f"{base_id_ativo}-{i + 1}" if quantidade > 1 else base_id_ativo
                else:
                    id_ativo = self._next_generated_id(conn, prefixo, i)

                result = conn.execute(text("SELECT id FROM ativos WHERE id_ativo = :id_ativo"), {'id_ativo': id_ativo})
                if result.first():
                    raise ValueError(f"O patrimônio '{id_ativo}' já existe.")

                if base_numero_serie:
                    numero_serie = f"{base_numero_serie}-{i + 1}" if quantidade > 1 else base_numero_serie
                else:
                    numero_serie = f"PROV-{int(time.time() * 1000) + i}"

                result_sn = conn.execute(text("SELECT id FROM ativos WHERE numero_serie = :sn"), {'sn': numero_serie})
                if result_sn.first():
                    raise ValueError(f"O Número de Série '{numero_serie}' já está cadastrado.")

                sql = """
                    INSERT INTO ativos (
                        id_ativo, numero_serie, marca, modelo_id, categoria_id, status,
                        nota_fiscal, fornecedor, data_aquisicao, localizacao,
                        usuario_responsavel, destino, cpu, ram_gb, armazenamento_gb,
                        sistema_operacional
                    )
                    VALUES (
                        :id_ativo, :numero_serie, :marca, :modelo_id, :categoria_id,
                        'Em Estoque', :nota_fiscal, :fornecedor, :data_aquisicao,
                        :localizacao, NULL, :destino, :cpu, :ram_gb,
                        :armazenamento_gb, :sistema_operacional
                    )
                """
                params = {
                    'id_ativo': id_ativo,
                    'numero_serie': numero_serie,
                    'marca': marca,
                    'modelo_id': modelo_id,
                    'categoria_id': categoria_id,
                    'nota_fiscal': self._get_text(form_data, 'nota_fiscal') or None,
                    'fornecedor': self._get_text(form_data, 'fornecedor') or None,
                    'data_aquisicao': self._get_text(form_data, 'data_aquisicao') or None,
                    'localizacao': localizacao,
                    'destino': destino,
                    'cpu': self._get_text(form_data, 'cpu') or None,
                    'ram_gb': self._optional_int(form_data, 'ram_gb'),
                    'armazenamento_gb': self._optional_int(form_data, 'armazenamento_gb'),
                    'sistema_operacional': self._get_text(form_data, 'sistema_operacional') or None,
                }
                conn.execute(text(sql), params)
                self._log_event(id_ativo, "Criação", "Ativo cadastrado e movido para o estoque.", conn)

    def atualizar_lote_ativos(self, form_data):
        engine = get_asset_db_engine()
        updates = {}

        for key, value in form_data.items():
            if key.startswith('db_id_'):
                idx = key.split('_')[-1]
                db_id = int(value)
                updates[db_id] = {
                    'id_ativo': self._get_text(form_data, f'id_ativo_{idx}'),
                    'numero_serie': self._get_text(form_data, f'numero_serie_{idx}'),
                }

        with engine.begin() as conn:
            for db_id, data in updates.items():
                novo_id_ativo = data['id_ativo']
                novo_numero_serie = data['numero_serie']
                if not novo_id_ativo or not novo_numero_serie:
                    raise ValueError("Patrimônio e número de série são obrigatórios.")

                current = conn.execute(
                    text("SELECT id_ativo, numero_serie FROM ativos WHERE id = :db_id"),
                    {'db_id': db_id},
                ).first()
                if not current:
                    raise ValueError("Ativo para edição em lote não foi encontrado.")
                current = current._mapping

                result = conn.execute(
                    text("SELECT id FROM ativos WHERE id_ativo = :id AND id != :db_id"),
                    {'id': novo_id_ativo, 'db_id': db_id},
                )
                if result.first():
                    raise ValueError(f"Patrimônio '{novo_id_ativo}' já existe.")

                result = conn.execute(
                    text("SELECT id FROM ativos WHERE numero_serie = :sn AND id != :db_id"),
                    {'sn': novo_numero_serie, 'db_id': db_id},
                )
                if result.first():
                    raise ValueError(f"Número de Série '{novo_numero_serie}' já existe.")

                conn.execute(
                    text("UPDATE ativos SET id_ativo = :id_ativo, numero_serie = :numero_serie WHERE id = :db_id"),
                    {'id_ativo': novo_id_ativo, 'numero_serie': novo_numero_serie, 'db_id': db_id},
                )
                if current['id_ativo'] != novo_id_ativo:
                    conn.execute(
                        text("UPDATE historico SET id_ativo = :novo WHERE id_ativo = :antigo"),
                        {'novo': novo_id_ativo, 'antigo': current['id_ativo']},
                    )
                self._log_event(
                    novo_id_ativo,
                    "Atualização em Lote",
                    "Patrimônio e/ou Serial atualizados para valores definitivos.",
                    conn,
                )

    def movimentar(self, id_ativo, novo_status, chamado, detalhes=None):
        if novo_status not in current_app.config['ASSET_STATUSES']:
            raise ValueError("Status inválido para movimentação.")

        engine = get_asset_db_engine()
        with engine.begin() as conn:
            update_fields = {'status': novo_status}
            if detalhes:
                invalid_fields = set(detalhes) - self.ALLOWED_UPDATE_FIELDS
                if invalid_fields:
                    raise ValueError(f"Campos de atualização inválidos: {', '.join(sorted(invalid_fields))}")
                update_fields.update(detalhes)

            set_clause = ", ".join([f"{key} = :{key}" for key in update_fields.keys()])
            params = {**update_fields, 'id_ativo': id_ativo}
            result = conn.execute(text(f"UPDATE ativos SET {set_clause} WHERE id_ativo = :id_ativo"), params)
            if result.rowcount == 0:
                raise ValueError("Ativo não encontrado.")

            log_detalhes = f"Status alterado para '{novo_status}'. Chamado: {chamado}."
            if 'usuario_responsavel' in update_fields:
                log_detalhes += f" Novo responsável: {update_fields['usuario_responsavel']}."
            self._log_event(id_ativo, "Movimentação", log_detalhes, conn)

    def baixar(self, id_ativo, chamado):
        self.movimentar(id_ativo, 'Descartado', chamado)

    def atualizar_ativo(self, id_ativo_original, form_data):
        engine = get_asset_db_engine()
        novo_id_ativo = self._require_text(form_data, 'id_ativo', 'patrimônio')
        novo_numero_serie = self._require_text(form_data, 'numero_serie', 'número de série')

        with engine.begin() as conn:
            current = conn.execute(
                text("SELECT id, id_ativo, numero_serie FROM ativos WHERE id_ativo = :id_ativo"),
                {'id_ativo': id_ativo_original},
            ).first()
            if not current:
                raise ValueError("Ativo não encontrado.")
            current = current._mapping

            result = conn.execute(
                text("SELECT id FROM ativos WHERE id_ativo = :id_ativo AND id != :db_id"),
                {'id_ativo': novo_id_ativo, 'db_id': current['id']},
            )
            if result.first():
                raise ValueError(f"O novo patrimônio '{novo_id_ativo}' já pertence a outro ativo.")

            result = conn.execute(
                text("SELECT id FROM ativos WHERE numero_serie = :sn AND id != :db_id"),
                {'sn': novo_numero_serie, 'db_id': current['id']},
            )
            if result.first():
                raise ValueError(f"O Número de Série '{novo_numero_serie}' já pertence a outro ativo.")

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
                WHERE id = :db_id
            """
            params = {
                'id_ativo': novo_id_ativo,
                'numero_serie': novo_numero_serie,
                'marca': self._require_text(form_data, 'marca', 'marca'),
                'modelo_id': self._require_text(form_data, 'modelo', 'modelo'),
                'categoria_id': self._require_text(form_data, 'categoria', 'categoria'),
                'nota_fiscal': self._get_text(form_data, 'nota_fiscal') or None,
                'fornecedor': self._get_text(form_data, 'fornecedor') or None,
                'data_aquisicao': self._get_text(form_data, 'data_aquisicao') or None,
                'destino': self._get_text(form_data, 'destino') or None,
                'db_id': current['id'],
            }
            conn.execute(text(sql), params)

            if id_ativo_original != novo_id_ativo:
                conn.execute(
                    text("UPDATE historico SET id_ativo = :novo WHERE id_ativo = :antigo"),
                    {'novo': novo_id_ativo, 'antigo': id_ativo_original},
                )
                detalhes = f"Patrimônio alterado de '{id_ativo_original}' para '{novo_id_ativo}'."
            else:
                detalhes = "Dados cadastrais atualizados."
            self._log_event(novo_id_ativo, "Atualização", detalhes, conn)

            return novo_id_ativo


def get_engine_by_key(key):
    db_info = current_app.config['ASSET_DATABASES'].get(key)
    if not db_info:
        raise ValueError(f"Configuração para banco '{key}' não encontrada")
    return create_engine(db_info['url'])


class Setting(db.Model):
    __bind_key__ = None
    __tablename__ = 'settings'

    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.Text, nullable=True)


class AuditLog(db.Model):
    __bind_key__ = None
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    username = db.Column(db.String(64), nullable=True)
    action = db.Column(db.String(128), nullable=False)
    details = db.Column(db.Text, nullable=True)


def get_setting(key, default=None):
    try:
        setting = Setting.query.filter_by(key=key).first()
        if setting and setting.value is not None:
            return setting.value
        return default
    except Exception:
        return default


def set_setting(key, value):
    try:
        setting = Setting.query.filter_by(key=key).first()
        if not setting:
            setting = Setting(key=key, value=value)
            db.session.add(setting)
        else:
            setting.value = value
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao salvar configuracao {key}: {e}")
        raise


def log_audit(action, details=None):
    try:
        from flask_login import current_user
        username = current_user.username if (current_user and current_user.is_authenticated) else 'Sistema'
        log_entry = AuditLog(username=username, action=action, details=details, timestamp=datetime.now())
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao salvar log de auditoria: {e}")
