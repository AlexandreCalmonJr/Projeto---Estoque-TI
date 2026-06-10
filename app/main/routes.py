import re
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
from docx import Document
from flask import abort, current_app, flash, redirect, render_template, request, send_file, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.utils import secure_filename

from app.models import AssetManager, User, db_execute, db_query

from . import main_bp


manager = AssetManager()


def _allowed_file(filename):
    if not filename or '.' not in filename:
        return False
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in current_app.config['ALLOWED_UPLOAD_EXTENSIONS']


def _normalize_status(status):
    if status == 'Em Manutencao':
        return 'Em Manutenção'
    return status


def _document_templates():
    return current_app.config['DOCUMENT_TEMPLATES']


def _validate_template_name(template_name):
    if template_name not in _document_templates():
        abort(404)
    template_path = Path(current_app.root_path) / 'document_templates' / template_name
    templates_dir = template_path.parent.resolve()
    resolved_template = template_path.resolve()
    if templates_dir not in resolved_template.parents or not resolved_template.is_file():
        abort(404)
    return resolved_template


def _read_import_file(file_storage):
    filename = secure_filename(file_storage.filename or '')
    if not _allowed_file(filename):
        raise ValueError('Formato de arquivo inválido. Use CSV ou XLSX.')

    extension = filename.rsplit('.', 1)[1].lower()
    if extension == 'csv':
        try:
            return pd.read_csv(file_storage, dtype=str).fillna('')
        except UnicodeDecodeError:
            file_storage.seek(0)
            return pd.read_csv(file_storage, dtype=str, encoding='latin-1').fillna('')

    return pd.read_excel(file_storage, dtype=str).fillna('')


def get_filter_clauses_and_params():
    categoria_id = request.args.get('categoria', type=int)
    modelo_id = request.args.get('modelo', type=int)
    q = request.args.get('q', '').strip()

    where_clauses = []
    params = {}

    if categoria_id:
        where_clauses.append("a.categoria_id = :categoria_id")
        params['categoria_id'] = categoria_id
    if modelo_id:
        where_clauses.append("a.modelo_id = :modelo_id")
        params['modelo_id'] = modelo_id

    if q:
        where_clauses.append("""
            (a.id_ativo LIKE :search_term OR
             a.numero_serie LIKE :search_term OR
             a.usuario_responsavel LIKE :search_term OR
             a.marca LIKE :search_term OR
             a.localizacao LIKE :search_term OR
             a.destino LIKE :search_term)
        """)
        params['search_term'] = f"%{q}%"

    where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    filtros_selecionados = {'categoria_id': categoria_id, 'modelo_id': modelo_id, 'q': q}
    return where_sql, params, filtros_selecionados


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        database_key = request.form.get('database', '').strip()

        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash('Usuário ou senha inválidos.', 'error')
            return redirect(url_for('main.login'))

        if database_key not in current_app.config['ASSET_DATABASES']:
            flash('Por favor, selecione um banco de dados válido.', 'error')
            return redirect(url_for('main.login'))

        login_user(user)
        session['database_key'] = database_key
        session['database_name'] = current_app.config['ASSET_DATABASES'][database_key]['name']
        return redirect(url_for('main.index'))

    return render_template('login.html', databases=current_app.config['ASSET_DATABASES'])


@main_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    session.clear()
    flash('Você foi desconectado com segurança.', 'success')
    return redirect(url_for('main.login'))


@main_bp.route('/')
@login_required
def index():
    try:
        where_sql, params, filtros_selecionados = get_filter_clauses_and_params()
        todas_categorias = db_query("SELECT id, nome FROM categorias ORDER BY nome")
        todos_modelos = db_query("SELECT id, nome, categoria_id FROM modelos ORDER BY nome")

        total_ativos = db_query(f"SELECT COUNT(a.id) as count FROM ativos a {where_sql}", params)[0]['count']
        base_join = "FROM ativos a JOIN categorias c ON a.categoria_id = c.id JOIN modelos m ON a.modelo_id = m.id"
        ativos_por_status = db_query(
            f"SELECT a.status, COUNT(a.id) as count {base_join} {where_sql} GROUP BY a.status",
            params,
        )

        destino_query_base = f"SELECT a.destino, COUNT(a.id) as count {base_join} {where_sql}"
        destino_condition = "a.destino IS NOT NULL AND a.destino != ''"
        final_destino_query = f"{destino_query_base} {'AND' if where_sql else 'WHERE'} {destino_condition} GROUP BY a.destino"
        ativos_por_destino = db_query(final_destino_query, params)

        antigos_query_base = f"""
            SELECT a.id_ativo, a.data_aquisicao, c.nome as categoria, m.nome as modelo
            {base_join} {where_sql}
        """
        antigos_condition = "a.status IN ('Em Uso', 'Em Estoque') AND a.data_aquisicao IS NOT NULL AND a.data_aquisicao != ''"
        final_antigos_query = f"{antigos_query_base} {'AND' if where_sql else 'WHERE'} {antigos_condition} ORDER BY a.data_aquisicao ASC LIMIT 5"
        ativos_antigos = db_query(final_antigos_query, params)

        ativos_provisorios_count = db_query("SELECT COUNT(id) as count FROM ativos WHERE numero_serie LIKE 'PROV-%'")[0]['count']

        lista_ativos_filtrados = db_query(f"""
            SELECT a.id_ativo, c.nome as categoria, m.nome as modelo, a.status, a.usuario_responsavel
            FROM ativos a
            JOIN modelos m ON a.modelo_id = m.id
            JOIN categorias c ON a.categoria_id = c.id
            {where_sql}
            ORDER BY a.id_ativo DESC
        """, params)

        status_labels = [item['status'] for item in ativos_por_status]
        status_data = [item['count'] for item in ativos_por_status]
        destino_labels = [item['destino'] for item in ativos_por_destino]
        destino_data = [item['count'] for item in ativos_por_destino]
        kpis = {
            'total': total_ativos,
            'em_estoque': next((item['count'] for item in ativos_por_status if item['status'] == 'Em Estoque'), 0),
            'em_uso': next((item['count'] for item in ativos_por_status if item['status'] == 'Em Uso'), 0),
            'em_manutencao': next((item['count'] for item in ativos_por_status if item['status'] == 'Em Manutenção'), 0),
        }
        dashboard_data = {
            'kpis': kpis,
            'status_labels': status_labels,
            'status_data': status_data,
            'destino_labels': destino_labels,
            'destino_data': destino_data,
            'ativos_antigos': ativos_antigos,
            'ativos_provisorios_count': ativos_provisorios_count,
            'lista_ativos': lista_ativos_filtrados,
        }
    except Exception as e:
        flash(f"Ocorreu um erro ao carregar os dados do dashboard: {e}", "error")
        dashboard_data = {
            'kpis': {'total': 0, 'em_estoque': 0, 'em_uso': 0, 'em_manutencao': 0},
            'status_labels': [],
            'status_data': [],
            'destino_labels': [],
            'destino_data': [],
            'ativos_antigos': [],
            'ativos_provisorios_count': 0,
            'lista_ativos': [],
        }
        todas_categorias, todos_modelos, filtros_selecionados = [], [], {}

    return render_template(
        "index.html",
        title="Dashboard de Ativos",
        data=dashboard_data,
        todas_categorias=todas_categorias,
        todos_modelos=todos_modelos,
        filtros_selecionados=filtros_selecionados,
    )


@main_bp.route('/ativo/novo', methods=['GET', 'POST'])
@login_required
def form_ativo():
    if request.method == 'POST':
        try:
            manager.registrar_novo_ativo(request.form)
            flash('Ativo cadastrado com sucesso!', 'success')
            return redirect(url_for('main.index'))
        except Exception as e:
            flash(f'Erro ao cadastrar ativo: {e}', 'error')

    categorias = db_query("SELECT *, substr(nome, 1, 2) as sigla FROM categorias ORDER BY nome")
    modelos = db_query("SELECT * FROM modelos ORDER BY nome")
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template(
        "form_ativo.html",
        title="Cadastramento de Ativos de TI",
        categorias=categorias,
        modelos=modelos,
        today=today,
    )


@main_bp.route('/ativo/<id_ativo>')
@login_required
def detalhes_ativo(id_ativo):
    query_ativo = """
        SELECT a.*, m.nome as modelo, c.nome as categoria
        FROM ativos a
        JOIN modelos m ON a.modelo_id = m.id
        JOIN categorias c ON a.categoria_id = c.id
        WHERE a.id_ativo = :id_ativo
    """
    ativo_list = db_query(query_ativo, {'id_ativo': id_ativo})
    if not ativo_list:
        flash('Ativo não encontrado.', 'error')
        return redirect(url_for('main.index'))

    historico = db_query(
        "SELECT * FROM historico WHERE id_ativo = :id_ativo ORDER BY timestamp DESC",
        {'id_ativo': id_ativo},
    )
    return render_template(
        "detalhes_ativo.html",
        title=f"Detalhes: {ativo_list[0]['id_ativo']}",
        ativo=ativo_list[0],
        historico=historico,
        document_templates=_document_templates(),
    )


@main_bp.route('/manutencao')
@login_required
def manutencao():
    ativos_manutencao = db_query("""
        SELECT a.id_ativo, a.numero_serie, a.marca, m.nome as modelo, c.nome as categoria, h.timestamp as data_evento
        FROM ativos a
        JOIN modelos m ON a.modelo_id = m.id
        JOIN categorias c ON a.categoria_id = c.id
        LEFT JOIN (
            SELECT id_ativo, MAX(timestamp) as timestamp
            FROM historico
            WHERE evento = 'Movimentação' AND detalhes LIKE '%Em Manutenção%'
            GROUP BY id_ativo
        ) h ON a.id_ativo = h.id_ativo
        WHERE a.status = 'Em Manutenção'
        ORDER BY h.timestamp DESC
    """)
    return render_template("manutencao.html", title="Ativos em Manutenção", ativos=ativos_manutencao)


@main_bp.route('/relatorios')
@login_required
def relatorios():
    where_sql, params, filtros_selecionados = get_filter_clauses_and_params()
    todas_categorias = db_query("SELECT id, nome FROM categorias ORDER BY nome")
    todos_modelos = db_query("SELECT id, nome, categoria_id FROM modelos ORDER BY nome")
    ativos = db_query(f"""
        SELECT a.id_ativo, c.nome as categoria, m.nome as modelo, a.numero_serie,
               a.status, a.usuario_responsavel, a.localizacao
        FROM ativos a
        JOIN modelos m ON a.modelo_id = m.id
        JOIN categorias c ON a.categoria_id = c.id
        {where_sql}
        ORDER BY c.nome, m.nome
    """, params)

    return render_template(
        "relatorio_geral.html",
        title="Relatório Geral de Ativos",
        ativos=ativos,
        total=len(ativos),
        data_geracao=datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        todas_categorias=todas_categorias,
        todos_modelos=todos_modelos,
        filtros_selecionados=filtros_selecionados,
    )


@main_bp.route('/ativo/<id_ativo>/distribuir', methods=['POST'])
@login_required
def distribuir_ativo(id_ativo):
    form_data = request.form
    template_name = form_data.get('template_name', '')
    _validate_template_name(template_name)

    localidade = form_data.get('localidade', '').strip()
    setor = form_data.get('setor', '').strip()
    localizacao_final = f"{localidade} - {setor}" if localidade and setor else localidade or setor
    detalhes = {
        'usuario_responsavel': form_data.get('usuario_responsavel', '').strip(),
        'localizacao': localizacao_final,
        'destino': setor or localizacao_final,
    }
    chamado = form_data.get('numero_chamado', '').strip()

    manager.movimentar(id_ativo, 'Em Uso', chamado, detalhes)
    flash('Ativo distribuído com sucesso! Gerando documento para download...', 'success')

    return redirect(url_for(
        'main.gerar_documento',
        id_ativo=id_ativo,
        template_name=template_name,
        chamado=chamado,
        unidade=form_data.get('unidade', ''),
        email_usuario=form_data.get('email_usuario', ''),
        localidade=localidade,
        setor=setor,
    ))


@main_bp.route('/ativo/<id_ativo>/movimentar', methods=['POST'])
@login_required
def movimentar_ativo(id_ativo):
    novo_status = _normalize_status(request.form.get('novo_status', '').strip())
    if novo_status not in current_app.config['MOVEMENT_STATUSES']:
        flash('Status inválido para movimentação.', 'error')
        return redirect(url_for('main.detalhes_ativo', id_ativo=id_ativo))

    chamado = request.form.get('numero_chamado', '').strip()
    manager.movimentar(id_ativo, novo_status, chamado)
    flash(f'Status do ativo alterado para "{novo_status}" com sucesso!', 'success')
    return redirect(url_for('main.detalhes_ativo', id_ativo=id_ativo))


@main_bp.route('/ativo/<id_ativo>/baixar', methods=['POST'])
@login_required
def baixar_ativo(id_ativo):
    chamado = request.form.get('numero_chamado', '').strip()
    manager.baixar(id_ativo, chamado)
    flash('Ativo baixado (descartado) com sucesso!', 'success')
    return redirect(url_for('main.detalhes_ativo', id_ativo=id_ativo))


@main_bp.route('/gerenciar', methods=['GET', 'POST'])
@login_required
def gerenciar_tipos():
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        nome = request.form.get('nome', '').strip()
        if not nome:
            flash('Informe um nome válido.', 'error')
            return redirect(url_for('main.gerenciar_tipos'))

        try:
            if form_type == 'categoria':
                db_execute("INSERT INTO categorias (nome) VALUES (:nome)", {'nome': nome})
                flash(f"Categoria '{nome}' adicionada com sucesso!", 'success')
            elif form_type == 'modelo':
                categoria_id = request.form.get('categoria_id', type=int)
                if not categoria_id:
                    raise ValueError('Selecione uma categoria.')
                db_execute(
                    "INSERT INTO modelos (nome, categoria_id) VALUES (:nome, :categoria_id)",
                    {'nome': nome, 'categoria_id': categoria_id},
                )
                flash(f"Modelo '{nome}' adicionado com sucesso!", 'success')
            else:
                flash('Tipo de formulário inválido.', 'error')
        except Exception as e:
            flash(f"Erro ao salvar: {e}", 'error')
        return redirect(url_for('main.gerenciar_tipos'))

    categorias = db_query("SELECT * FROM categorias ORDER BY nome")
    return render_template("gerenciar_tipos.html", title="Gerenciar Categorias e Modelos", categorias=categorias)


@main_bp.route('/importar', methods=['GET', 'POST'])
@login_required
def importar_ativos():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or not file.filename:
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(request.url)

        try:
            df = _read_import_file(file)
            column_mapping = {
                'ativo': 'categoria',
                'fabricante': 'marca',
                'nº serie': 'numero_serie',
                'n° serie': 'numero_serie',
                'n serie': 'numero_serie',
                'n serie': 'numero_serie',
                'numero serie': 'numero_serie',
                'numero_serie': 'numero_serie',
                'modelo': 'modelo',
                'quantidade': 'quantidade',
            }
            df.columns = [str(col).lower().strip().replace('.', '') for col in df.columns]
            df.rename(columns=column_mapping, inplace=True)

            required_columns = ['categoria', 'marca', 'modelo']
            if not all(col in df.columns for col in required_columns):
                flash(f'O arquivo deve conter as colunas obrigatórias: {required_columns}', 'error')
                return redirect(request.url)

            sucesso = 0
            erros = []
            asset_manager = AssetManager()

            for index, row in df.iterrows():
                try:
                    quantidade = int(row.get('quantidade', 1) or 1)
                    if quantidade < 1:
                        quantidade = 1
                except (TypeError, ValueError):
                    quantidade = 1

                base_numero_serie = str(row.get('numero_serie', '')).strip()
                categoria_nome = str(row['categoria']).strip()
                if not categoria_nome:
                    continue

                try:
                    cat_query = db_query("SELECT id FROM categorias WHERE nome = :nome", {'nome': categoria_nome})
                    if not cat_query:
                        db_execute("INSERT INTO categorias (nome) VALUES (:nome)", {'nome': categoria_nome})
                        cat_query = db_query("SELECT id FROM categorias WHERE nome = :nome", {'nome': categoria_nome})
                    cat_id = cat_query[0]['id']

                    modelo_nome = str(row.get('modelo', '')).strip() or categoria_nome
                    mod_query = db_query(
                        "SELECT id FROM modelos WHERE nome = :nome AND categoria_id = :cat_id",
                        {'nome': modelo_nome, 'cat_id': cat_id},
                    )
                    if not mod_query:
                        db_execute(
                            "INSERT INTO modelos (nome, categoria_id) VALUES (:nome, :cat_id)",
                            {'nome': modelo_nome, 'cat_id': cat_id},
                        )
                        mod_query = db_query(
                            "SELECT id FROM modelos WHERE nome = :nome AND categoria_id = :cat_id",
                            {'nome': modelo_nome, 'cat_id': cat_id},
                        )
                    mod_id = mod_query[0]['id']

                    for i in range(quantidade):
                        current_numero_serie = base_numero_serie
                        if base_numero_serie and i > 0:
                            match = re.search(r'(\d+)$', base_numero_serie)
                            if match:
                                num_part = int(match.group(1)) + i
                                prefix = base_numero_serie[:match.start(1)]
                                current_numero_serie = f"{prefix}{str(num_part).zfill(len(match.group(1)))}"
                            else:
                                current_numero_serie = f"{base_numero_serie}-{i + 1}"

                        form_data = {
                            'id_ativo': '',
                            'numero_serie': current_numero_serie,
                            'marca': str(row.get('marca', 'N/A')).strip() or 'N/A',
                            'modelo': mod_id,
                            'categoria': cat_id,
                            'data_aquisicao': None,
                            'destino': 'Estoque TI',
                            'nota_fiscal': row.get('nota_fiscal', ''),
                            'fornecedor': row.get('fornecedor', ''),
                            'cpu': row.get('cpu', ''),
                            'ram_gb': row.get('ram_gb', None),
                            'armazenamento_gb': row.get('armazenamento_gb', None),
                            'sistema_operacional': row.get('sistema_operacional', ''),
                        }
                        asset_manager.registrar_novo_ativo(form_data)
                        sucesso += 1
                except Exception as e:
                    erros.append(f"Linha {index + 2}: {e}")

            if not erros:
                flash(f'Importação concluída! {sucesso} ativos importados com sucesso.', 'success')
            else:
                erros_str = " | ".join(erros[:3])
                flash(f'{sucesso} ativos importados. Falhas: {len(erros)}. Detalhes: {erros_str}', 'error')
        except Exception as e:
            flash(f'Ocorreu um erro fatal ao processar o arquivo: {e}', 'error')

        return redirect(url_for('main.importar_ativos'))

    return render_template('importar.html', title="Importar Ativos")


@main_bp.route('/gerar-termo')
@login_required
def gerador_termo():
    return render_template('gerador_termo.html', title="Gerador de Termo")


@main_bp.route('/ativo/<id_ativo>/edit', methods=['GET', 'POST'])
@login_required
def edit_ativo(id_ativo):
    if request.method == 'POST':
        try:
            novo_id_ativo = manager.atualizar_ativo(id_ativo, request.form)
            flash('Ativo atualizado com sucesso!', 'success')
            return redirect(url_for('main.detalhes_ativo', id_ativo=novo_id_ativo))
        except ValueError as e:
            flash(f'Erro ao atualizar: {e}', 'error')
            return redirect(url_for('main.edit_ativo', id_ativo=id_ativo))

    ativo_list = db_query("SELECT * FROM ativos WHERE id_ativo = :id_ativo", {'id_ativo': id_ativo})
    if not ativo_list:
        flash('Ativo não encontrado.', 'error')
        return redirect(url_for('main.index'))

    categorias = db_query("SELECT * FROM categorias ORDER BY nome")
    modelos = db_query("SELECT * FROM modelos ORDER BY nome")
    return render_template(
        'edit_ativo.html',
        title="Editar Ativo",
        ativo=ativo_list[0],
        categorias=categorias,
        modelos=modelos,
    )


@main_bp.route('/bulk-edit', methods=['GET', 'POST'])
@login_required
def bulk_edit_ativos():
    if request.method == 'POST':
        try:
            manager.atualizar_lote_ativos(request.form)
            flash('Ativos atualizados com sucesso!', 'success')
            return redirect(url_for('main.bulk_edit_ativos'))
        except ValueError as e:
            flash(f'Erro ao salvar: {e}', 'error')

    ativos_para_editar = db_query("""
        SELECT a.id, a.id_ativo, a.numero_serie, c.nome as categoria, m.nome as modelo
        FROM ativos a
        JOIN modelos m ON a.modelo_id = m.id
        JOIN categorias c ON a.categoria_id = c.id
        WHERE a.numero_serie LIKE 'PROV-%'
        ORDER BY a.id
    """)
    return render_template('bulk_edit.html', title="Editar Ativos em Lote", ativos=ativos_para_editar)


@main_bp.route('/ativo/<id_ativo>/gerar_documento/<template_name>')
@login_required
def gerar_documento(id_ativo, template_name):
    template_path = _validate_template_name(template_name)
    try:
        chamado = request.args.get('chamado', '____________________')
        unidade_form = request.args.get('unidade', '____________________')
        email_usuario_form = request.args.get('email_usuario', '____________________')
        localidade_form = request.args.get('localidade', '____________________')
        setor_form = request.args.get('setor', '____________________')

        query = """
            SELECT a.*, m.nome as modelo, c.nome as categoria
            FROM ativos a
            JOIN modelos m ON a.modelo_id = m.id
            JOIN categorias c ON a.categoria_id = c.id
            WHERE a.id_ativo = :id_ativo
        """
        ativo_info_list = db_query(query, {'id_ativo': id_ativo})
        if not ativo_info_list:
            flash('Ativo não encontrado.', 'error')
            return redirect(url_for('main.index'))
        ativo_info = ativo_info_list[0]

        context = {
            '{{solicitante}}': ativo_info.get('usuario_responsavel', '____________________'),
            '{{usuario}}': email_usuario_form,
            '{{matricula}}': '____________________',
            '{{setor}}': setor_form,
            '{{unidade}}': unidade_form,
            '{{localidade}}': localidade_form,
            '{{patrimonio}}': ativo_info.get('id_ativo', ''),
            '{{categoria}}': ativo_info.get('categoria', ''),
            '{{fabricante}}': ativo_info.get('marca', ''),
            '{{modelo}}': ativo_info.get('modelo', ''),
            '{{serie}}': ativo_info.get('numero_serie', ''),
            '{{chamado}}': chamado,
            '{{data_hoje}}': datetime.now().strftime('%d/%m/%Y'),
        }

        document = Document(str(template_path))
        for paragraph in document.paragraphs:
            for key, value in context.items():
                if key in paragraph.text:
                    for run in paragraph.runs:
                        run.text = run.text.replace(key, str(value))

        for table in document.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        for key, value in context.items():
                            if key in paragraph.text:
                                for run in paragraph.runs:
                                    run.text = run.text.replace(key, str(value))

        file_stream = BytesIO()
        document.save(file_stream)
        file_stream.seek(0)
        download_base = template_name.replace(' - modelo.docx', '')
        return send_file(
            file_stream,
            as_attachment=True,
            download_name=f"{download_base}-{id_ativo}.docx",
        )
    except Exception as e:
        flash(f'Ocorreu um erro ao gerar o documento: {e}', 'error')
        return redirect(url_for('main.detalhes_ativo', id_ativo=id_ativo))
