import os
import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from app.models import db_query, db_execute, AssetManager, User
from datetime import datetime
from flask_login import login_user, logout_user, current_user, login_required
from . import main_bp
import re
import time
# COMENTÁRIO: Renomeamos o Blueprint para 'main' para seguir uma convenção comum.
# As rotas serão chamadas com url_for('main.nome_da_funcao').
manager = AssetManager()

def get_filter_clauses_and_params():
    """Função auxiliar para construir cláusulas WHERE e parâmetros para a busca avançada."""
    categoria_id = request.args.get('categoria', type=int)
    modelo_id = request.args.get('modelo', type=int)
    q = request.args.get('q', '').strip()
    
    where_clauses = []
    params = {}
    
    # Adiciona filtros de dropdown
    if categoria_id:
        where_clauses.append("a.categoria_id = :categoria_id")
        params['categoria_id'] = categoria_id
    if modelo_id:
        where_clauses.append("a.modelo_id = :modelo_id")
        params['modelo_id'] = modelo_id
        
    # Adiciona filtro de busca por texto
    if q:
        text_search_clause = """
            (a.id_ativo LIKE :search_term OR
            a.numero_serie LIKE :search_term OR
            a.usuario_responsavel LIKE :search_term OR
            a.marca LIKE :search_term OR
            a.localizacao LIKE :search_term OR
            a.destino LIKE :search_term)
        """
        where_clauses.append(text_search_clause)
        params['search_term'] = f"%{q}%"
    
    # Constrói a string SQL final para a cláusula WHERE
    where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    
    # Retorna o dicionário de filtros selecionados para usar na interface
    filtros_selecionados = {'categoria_id': categoria_id, 'modelo_id': modelo_id, 'q': q}
    
    return where_sql, params, filtros_selecionados


# --- Rotas de Autenticação (sem grandes alterações) ---
@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        database_key = request.form.get('database')
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash('Usuário ou senha inválidos.', 'error')
            return redirect(url_for('main.login'))
        if not database_key:
            flash('Por favor, selecione um banco de dados.', 'error')
            return redirect(url_for('main.login'))
        login_user(user)
        session['database_key'] = database_key
        session['database_name'] = current_app.config['ASSET_DATABASES'][database_key]['name']
        return redirect(url_for('main.index'))
    return render_template('login.html', databases=current_app.config['ASSET_DATABASES'])

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('Você foi desconectado com segurança.', 'success')
    return redirect(url_for('main.login'))

# --- Rotas da Aplicação ---

@main_bp.route('/')
@login_required
def index():
    try:
        where_sql, params, filtros_selecionados = get_filter_clauses_and_params()
        
        # Buscas de dados para os filtros
        todas_categorias = db_query("SELECT id, nome FROM categorias ORDER BY nome")
        todos_modelos = db_query("SELECT id, nome, categoria_id FROM modelos ORDER BY nome")

        # Queries para os insights, agora com a cláusula WHERE dinâmica
        total_ativos = db_query(f"SELECT COUNT(a.id) as count FROM ativos a {where_sql}", params)[0]['count']
        
        base_join = "FROM ativos a JOIN categorias c ON a.categoria_id = c.id JOIN modelos m ON a.modelo_id = m.id"

        ativos_por_status = db_query(f"SELECT a.status, COUNT(a.id) as count {base_join} {where_sql} GROUP BY a.status", params)
        
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

        # Query para a lista de ativos na tabela do dashboard
        lista_ativos_filtrados = db_query(f"""
            SELECT a.id_ativo, c.nome as categoria, m.nome as modelo, a.status, a.usuario_responsavel
            FROM ativos a
            JOIN modelos m ON a.modelo_id = m.id
            JOIN categorias c ON a.categoria_id = c.id
            {where_sql}
            ORDER BY a.id_ativo DESC
        """, params)

        # Preparação dos dados
        status_labels = [item['status'] for item in ativos_por_status]
        status_data = [item['count'] for item in ativos_por_status]
        destino_labels = [item['destino'] for item in ativos_por_destino]
        destino_data = [item['count'] for item in ativos_por_destino]
        kpis = {
            'total': total_ativos,
            'em_estoque': next((item['count'] for item in ativos_por_status if item['status'] == 'Em Estoque'), 0),
            'em_uso': next((item['count'] for item in ativos_por_status if item['status'] == 'Em Uso'), 0),
            'em_manutencao': next((item['count'] for item in ativos_por_status if item['status'] == 'Em Manutenção'), 0)
        }
        dashboard_data = {
            'kpis': kpis,
            'status_labels': status_labels, 'status_data': status_data, 
            'destino_labels': destino_labels, 'destino_data': destino_data,
            'ativos_antigos': ativos_antigos, 
            'ativos_provisorios_count': ativos_provisorios_count,
            'lista_ativos': lista_ativos_filtrados
        }

    except Exception as e:
        flash(f"Ocorreu um erro ao carregar os dados do dashboard: {e}", "error")
        # Retorna uma estrutura de dados vazia em caso de erro
        dashboard_data = {
            'kpis': {'total': 0, 'em_estoque': 0, 'em_uso': 0, 'em_manutencao': 0},
            'status_labels': [], 'status_data': [], 'destino_labels': [], 'destino_data': [],
            'ativos_antigos': [], 'ativos_provisorios_count': 0,
            'lista_ativos': []
        }
        todas_categorias, todos_modelos, filtros_selecionados = [], [], {}

    # Passa os dados para o template
    return render_template(
        "index.html", 
        title="Dashboard de Ativos", 
        data=dashboard_data, 
        todas_categorias=todas_categorias,
        todos_modelos=todos_modelos,
        filtros_selecionados=filtros_selecionados
    )

# COMENTÁRIO: Rota para o formulário de cadastro. O título foi alterado para ser mais claro.
@main_bp.route('/ativo/novo', methods=['GET', 'POST'])
@login_required
def form_ativo():
    if request.method == 'POST':
        # COMENTÁRIO: A lógica aqui não muda, pois o AssetManager já foi atualizado
        # para lidar com os novos campos do formulário de especificações.
        try:
            manager.registrar_novo_ativo(request.form)
            flash('Ativo cadastrado com sucesso!', 'success')
            return redirect(url_for('main.index'))
        except Exception as e:
            flash(f'Erro ao cadastrar ativo: {e}', 'error')
    
    categorias = db_query("SELECT *, substr(nome, 1, 2) as sigla FROM categorias ORDER BY nome")
    modelos = db_query("SELECT * FROM modelos ORDER BY nome")
    today = datetime.now().strftime('%Y-%m-%d')
    # COMENTÁRIO: Título alterado para "Cadastramento de Ativos de TI".
    return render_template("form_ativo.html", title="Cadastramento de Ativos de TI", categorias=categorias, modelos=modelos, today=today)

@main_bp.route('/ativo/<id_ativo>')
@login_required
def detalhes_ativo(id_ativo):
    # CORREÇÃO: Usa dicionário para os parâmetros
    query_ativo = "SELECT a.*, m.nome as modelo, c.nome as categoria FROM ativos a JOIN modelos m ON a.modelo_id = m.id JOIN categorias c ON a.categoria_id = c.id WHERE a.id_ativo = :id_ativo"
    ativo_list = db_query(query_ativo, {'id_ativo': id_ativo})

    if not ativo_list:
        flash('Ativo não encontrado.', 'error')
        return redirect(url_for('main.index'))
    
    ativo = ativo_list[0]
    
    # CORREÇÃO: Usa dicionário para os parâmetros
    query_historico = "SELECT * FROM historico WHERE id_ativo = :id_ativo ORDER BY timestamp DESC"
    historico = db_query(query_historico, {'id_ativo': id_ativo})
    
    return render_template("detalhes_ativo.html", title=f"Detalhes: {ativo['id_ativo']}", ativo=ativo, historico=historico)


# --- NOVAS ROTAS ---

# COMENTÁRIO: NOVA ROTA - Aba de Manutenção.
# Esta rota busca e exibe todos os ativos que estão com o status "Em Manutenção".
@main_bp.route('/manutencao')
@login_required
def manutencao():
    # COMENTÁRIO: A query busca informações do ativo e a data em que ele foi enviado
    # para manutenção, pegando o registro mais recente do histórico.
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
    # COMENTÁRIO: Renderiza um novo template específico para a tela de manutenção.
    return render_template("manutencao.html", title="Ativos em Manutenção", ativos=ativos_manutencao)

# COMENTÁRIO: NOVA ROTA - Aba de Relatórios.
# Esta rota gera uma visão geral de todos os ativos, formatada para impressão.
@main_bp.route('/relatorios')
@login_required
def relatorios():
    where_sql, params, filtros_selecionados = get_filter_clauses_and_params()
    
    # Buscas de dados para os filtros
    todas_categorias = db_query("SELECT id, nome FROM categorias ORDER BY nome")
    todos_modelos = db_query("SELECT id, nome, categoria_id FROM modelos ORDER BY nome")

    # Busca principal de ativos com filtros
    ativos = db_query(f"""
        SELECT a.id_ativo, c.nome as categoria, m.nome as modelo, a.numero_serie, a.status, a.usuario_responsavel, a.localizacao
        FROM ativos a
        JOIN modelos m ON a.modelo_id = m.id
        JOIN categorias c ON a.categoria_id = c.id
        {where_sql}
        ORDER BY c.nome, m.nome
    """, params)
    
    total = len(ativos)
    data_geracao = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    return render_template(
        "relatorio_geral.html", 
        title="Relatório Geral de Ativos", 
        ativos=ativos, 
        total=total, 
        data_geracao=data_geracao,
        todas_categorias=todas_categorias,
        todos_modelos=todos_modelos,
        filtros_selecionados=filtros_selecionados
    )

# --- Rotas de Ações (sem grandes alterações) ---
@main_bp.route('/ativo/<id_ativo>/distribuir', methods=['POST'])
@login_required
def distribuir_ativo(id_ativo):
    detalhes = {
        'usuario_responsavel': request.form['usuario_responsavel'], 
        'localizacao': request.form['localizacao']
    }
    chamado = request.form['numero_chamado']
    
    manager = AssetManager()
    manager.movimentar(id_ativo, 'Em Uso', chamado, detalhes)
    
    flash('Ativo distribuído com sucesso! Gerando termo de responsabilidade...', 'success')
    
    query = "SELECT a.*, m.nome as modelo, c.nome as categoria FROM ativos a JOIN modelos m ON a.modelo_id = m.id JOIN categorias c ON a.categoria_id = c.id WHERE a.id_ativo = :id_ativo"
    ativo_info_list = db_query(query, {'id_ativo': id_ativo})

    if not ativo_info_list:
        flash(f'Erro ao gerar termo: Ativo com ID {id_ativo} não foi encontrado após a movimentação.', 'error')
        return redirect(url_for('main.detalhes_ativo', id_ativo=id_ativo))
        
    ativo_info = ativo_info_list[0]
    
    # Prepara os dados para o novo template
    termo_data = {
        'solicitante': current_user.username,
        'unidade': session.get('database_name', 'N/A'), # Pega o nome da base de dados da sessão
        'usuario': detalhes['usuario_responsavel'],
        'localidade': ativo_info.get('localizacao', 'N/A'),
        'setor': detalhes['localizacao'],
        'chamado': chamado,
        'ativos': [ativo_info],
        'data_emissao': datetime.now().strftime('%d/%m/%Y')
    }
    
    return render_template('termo.html', title="Termo de Responsabilidade", **termo_data)

@main_bp.route('/ativo/<id_ativo>/movimentar', methods=['POST'])
@login_required
def movimentar_ativo(id_ativo):
    novo_status = request.form['novo_status']
    chamado = request.form['numero_chamado']
    
    # CORREÇÃO: A lógica foi movida para dentro da função da classe AssetManager
    manager = AssetManager()
    manager.movimentar(id_ativo, novo_status, chamado)
    
    flash(f'Status do ativo alterado para "{novo_status}" com sucesso!', 'success')
    return redirect(url_for('main.detalhes_ativo', id_ativo=id_ativo))

@main_bp.route('/ativo/<id_ativo>/baixar', methods=['POST'])
@login_required
def baixar_ativo(id_ativo):
    chamado = request.form['numero_chamado']
    manager.baixar(id_ativo, chamado)
    flash('Ativo baixado (descartado) com sucesso!', 'success')
    return redirect(url_for('main.detalhes_ativo', id_ativo=id_ativo))

@main_bp.route('/gerenciar', methods=['GET', 'POST'])
@login_required
def gerenciar_tipos():
    if request.method == 'POST':
        form_type, nome = request.form['form_type'], request.form['nome']
        
        if form_type == 'categoria':
            try:
                # Esta parte está correta
                db_execute("INSERT INTO categorias (nome) VALUES (:nome)", {'nome': nome})
                flash(f"Categoria '{nome}' adicionada com sucesso!", 'success')
            except Exception as e:
                flash(f"Erro: Categoria '{nome}' já existe ou ocorreu um problema.", 'error')

        elif form_type == 'modelo':
            categoria_id = request.form['categoria_id']
            
            # LINHA COM ERRO:
            # db_execute("INSERT INTO modelos (nome, categoria_id) VALUES (?, ?)", [nome, categoria_id])

            # CORREÇÃO: Passe os parâmetros como um dicionário
            params = {'nome': nome, 'categoria_id': categoria_id}
            db_execute("INSERT INTO modelos (nome, categoria_id) VALUES (:nome, :categoria_id)", params)
            
            flash(f"Modelo '{nome}' adicionado com sucesso!", 'success')
            
        return redirect(url_for('main.gerenciar_tipos'))
        
    categorias = db_query("SELECT * FROM categorias ORDER BY nome")
    return render_template("gerenciar_tipos.html", title="Gerenciar Categorias e Modelos", categorias=categorias)

@main_bp.route('/importar', methods=['GET', 'POST'])
@login_required
def importar_ativos():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(request.url)

        if file:
            try:
                # --- CORREÇÃO DE LEITURA DE ARQUIVO ---
                if file.filename.endswith('.csv'):
                    try:
                        # Tenta ler com a codificação padrão UTF-8
                        df = pd.read_csv(file, dtype=str).fillna('')
                    except UnicodeDecodeError:
                        # Se falhar, volta ao início do arquivo e tenta com uma codificação comum do Windows
                        file.seek(0)
                        df = pd.read_csv(file, dtype=str, encoding='latin-1').fillna('')
                elif file.filename.endswith('.xlsx'):
                    df = pd.read_excel(file, dtype=str).fillna('')
                else:
                    flash('Formato de arquivo inválido. Use CSV ou XLSX.', 'error')
                    return redirect(request.url)
                # --- FIM DA CORREÇÃO ---

                # Mapeamento e normalização de colunas (código existente)
                column_mapping = {
                    'ativo': 'categoria',
                    'fabricante': 'marca',
                    'nº serie': 'numero_serie',
                    'n. serie': 'numero_serie',
                    'n serie': 'numero_serie',
                    'modelo': 'modelo',
                    'quantidade': 'quantidade'
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
                        # Lógica de quantidade (código existente)
                        try:
                            quantidade = int(row.get('quantidade', 1))
                            if quantidade < 1:
                                quantidade = 1
                        except (ValueError, TypeError):
                            quantidade = 1

                        base_numero_serie = row.get('numero_serie', '').strip()

                        for i in range(quantidade):
                            current_numero_serie = base_numero_serie
                            
                            if not base_numero_serie:
                                timestamp = int(time.time() * 1000)
                                current_numero_serie = f"BA-{timestamp + i}"
                            elif i > 0:
                                match = re.search(r'(\d+)$', base_numero_serie)
                                if not match:
                                    current_numero_serie = f"{base_numero_serie}-{i+1}"
                                else:
                                    num_part_str = match.group(1)
                                    num_part_int = int(num_part_str) + i
                                    prefix = base_numero_serie[:match.start(1)]
                                    current_numero_serie = f"{prefix}{str(num_part_int).zfill(len(num_part_str))}"
                            
                            # Lógica para encontrar/criar categoria e modelo (código existente)
                            categoria_nome = row['categoria'].strip()
                            if not categoria_nome: continue

                            cat_query = db_query("SELECT id, substr(nome, 1, 2) as sigla FROM categorias WHERE nome = :nome", {'nome': categoria_nome})
                            if not cat_query:
                                db_execute("INSERT INTO categorias (nome) VALUES (:nome)", {'nome': categoria_nome})
                                cat_query = db_query("SELECT id, substr(nome, 1, 2) as sigla FROM categorias WHERE nome = :nome", {'nome': categoria_nome})
                            cat_id = cat_query[0]['id']
                            sigla_cat = cat_query[0]['sigla']
                            
                            modelo_nome = row.get('modelo', '').strip() or categoria_nome
                            
                            mod_query = db_query("SELECT id FROM modelos WHERE nome = :nome AND categoria_id = :cat_id", {'nome': modelo_nome, 'cat_id': cat_id})
                            if not mod_query:
                                db_execute("INSERT INTO modelos (nome, categoria_id) VALUES (:nome, :cat_id)", {'nome': modelo_nome, 'cat_id': cat_id})
                                mod_query = db_query("SELECT id FROM modelos WHERE nome = :nome AND categoria_id = :cat_id", {'nome': modelo_nome, 'cat_id': cat_id})
                            mod_id = mod_query[0]['id']
                            
                            # Preparar dados para registro (código existente)
                            form_data = {
                                'id_ativo': '', 
                                'tipo_ativo_sigla': sigla_cat.upper(),
                                'numero_serie': current_numero_serie,
                                'marca': row.get('marca', 'N/A').strip(),
                                'modelo': mod_id,
                                'categoria': cat_id,
                                'data_aquisicao': None,
                                'destino': 'Estoque TI',
                                'nota_fiscal': row.get('nota_fiscal', ''),
                                'fornecedor': row.get('fornecedor', ''),
                                'cpu': row.get('cpu', ''),
                                'ram_gb': row.get('ram_gb', None),
                                'armazenamento_gb': row.get('armazenamento_gb', None),
                                'sistema_operacional': row.get('sistema_operacional', '')
                            }
                            asset_manager.registrar_novo_ativo(form_data)
                            sucesso += 1
                    except Exception as e:
                        erros.append(f"Linha {index + 2}: {e}")
                
                if not erros:
                    flash(f'Importação concluída! {sucesso} ativos importados com sucesso.', 'success')
                else:
                    erros_str = " | ".join(erros[:3])
                    flash(f'{sucesso} ativos importados. Falhas: {len(erros)}. Detalhes: {erros_str}...', 'error')

            except Exception as e:
                flash(f'Ocorreu um erro fatal ao processar o arquivo: {e}', 'error')

        return redirect(url_for('main.importar_ativos'))

    return render_template('importar.html', title="Importar Ativos")

@main_bp.route('/gerar-termo')
@login_required
def gerador_termo():
    """Renderiza a página do gerador de termo de responsabilidade."""
    return render_template('gerador_termo.html', title="Gerador de Termo")

@main_bp.route('/ativo/<id_ativo>/edit', methods=['GET', 'POST'])
@login_required
def edit_ativo(id_ativo):
    manager = AssetManager()
    
    if request.method == 'POST':
        try:
            # Chama a nova função de atualização e pega o novo ID do ativo
            novo_id_ativo = manager.atualizar_ativo(id_ativo, request.form)
            flash('Ativo atualizado com sucesso!', 'success')
            # Redireciona para a página de detalhes com o novo ID
            return redirect(url_for('main.detalhes_ativo', id_ativo=novo_id_ativo))
        except ValueError as e:
            flash(f'Erro ao atualizar: {e}', 'error')
            # Volta para a página de edição em caso de erro
            return redirect(url_for('main.edit_ativo', id_ativo=id_ativo))

    # Método GET: Busca os dados para preencher o formulário
    query_ativo = "SELECT * FROM ativos WHERE id_ativo = :id_ativo"
    ativo_list = db_query(query_ativo, {'id_ativo': id_ativo})

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
        modelos=modelos
    )
    
    
@main_bp.route('/bulk-edit', methods=['GET', 'POST'])
@login_required
def bulk_edit_ativos():
    manager = AssetManager()
    if request.method == 'POST':
        try:
            manager.atualizar_lote_ativos(request.form)
            flash('Ativos atualizados com sucesso!', 'success')
            return redirect(url_for('main.bulk_edit_ativos'))
        except ValueError as e:
            flash(f'Erro ao salvar: {e}', 'error')

    # Busca ativos com serial provisório para exibir no formulário
    query = """
        SELECT a.id, a.id_ativo, a.numero_serie, c.nome as categoria, m.nome as modelo
        FROM ativos a
        JOIN modelos m ON a.modelo_id = m.id
        JOIN categorias c ON a.categoria_id = c.id
        WHERE a.numero_serie LIKE 'PROV-%'
        ORDER BY a.id
    """
    ativos_para_editar = db_query(query)
    
    return render_template('bulk_edit.html', title="Editar Ativos em Lote", ativos=ativos_para_editar)