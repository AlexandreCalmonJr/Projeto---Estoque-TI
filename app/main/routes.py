import os
import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from app.models import db_query, db_execute, AssetManager, User
from datetime import datetime
from flask_login import login_user, logout_user, current_user, login_required
from . import main_bp
# COMENTÁRIO: Renomeamos o Blueprint para 'main' para seguir uma convenção comum.
# As rotas serão chamadas com url_for('main.nome_da_funcao').
manager = AssetManager()

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

# COMENTÁRIO: Rota principal, agora com funcionalidade de pesquisa.
@main_bp.route('/')
@login_required
def index():
    # COMENTÁRIO: Obtém o termo de busca da URL (ex: /?q=notebook).
    # O 'q' é o nome do campo de input no formulário de busca.
    search_query = request.args.get('q', '').strip()
    
    # COMENTÁRIO: Query base para buscar todos os ativos, juntando com modelos e categorias.
    query = """
        SELECT a.id_ativo, a.numero_serie, a.marca, m.nome as modelo, c.nome as categoria, a.status, a.localizacao, a.usuario_responsavel
        FROM ativos a
        JOIN modelos m ON a.modelo_id = m.id
        JOIN categorias c ON a.categoria_id = c.id
    """
    params = []
    
    # COMENTÁRIO: Se um termo de busca foi fornecido, adiciona a cláusula WHERE.
    # O '?' é um placeholder para os parâmetros, evitando SQL Injection.
    # O '%' é um curinga que busca por qualquer texto antes ou depois do termo.
    if search_query:
        query += " WHERE a.id_ativo LIKE ? OR a.numero_serie LIKE ? OR a.usuario_responsavel LIKE ?"
        search_term = f"%{search_query}%"
        params.extend([search_term, search_term, search_term])
    
    query += " ORDER BY a.data_aquisicao DESC"
    
    ativos = db_query(query, params)
    
    # COMENTÁRIO: Passa o termo da busca de volta para o template para que ele
    # possa ser exibido no campo de input, mostrando ao usuário o que ele buscou.
    return render_template("index.html", title="Dashboard de Ativos", ativos=ativos, search_query=search_query)

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
    # Correção: Usa :id_ativo como placeholder e passa um dicionário como parâmetro
    query_ativo = "SELECT a.*, m.nome as modelo, c.nome as categoria FROM ativos a JOIN modelos m ON a.modelo_id = m.id JOIN categorias c ON a.categoria_id = c.id WHERE a.id_ativo = :id_ativo"
    ativo_list = db_query(query_ativo, {'id_ativo': id_ativo})

    if not ativo_list:
        flash('Ativo não encontrado.', 'error')
        return redirect(url_for('main.index'))
    
    ativo = ativo_list[0]
    
    # Correção: Aplica o mesmo padrão para a consulta do histórico
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
    # COMENTÁRIO: Busca todos os ativos com informações essenciais para o relatório.
    ativos = db_query("""
        SELECT a.id_ativo, c.nome as categoria, m.nome as modelo, a.numero_serie, a.status, a.usuario_responsavel, a.localizacao
        FROM ativos a
        JOIN modelos m ON a.modelo_id = m.id
        JOIN categorias c ON a.categoria_id = c.id
        ORDER BY c.nome, m.nome
    """)
    total = len(ativos)
    data_geracao = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    # COMENTÁRIO: Renderiza um template especial de relatório, que tem um layout limpo para impressão.
    return render_template("relatorio_geral.html", title="Relatório Geral de Ativos", 
                                                ativos=ativos, total=total, data_geracao=data_geracao)

# --- Rotas de Ações (sem grandes alterações) ---
@main_bp.route('/ativo/<id_ativo>/distribuir', methods=['POST'])
@login_required
def distribuir_ativo(id_ativo):
    detalhes = {'usuario_responsavel': request.form['usuario_responsavel'], 'localizacao': request.form['localizacao']}
    chamado = request.form['numero_chamado']
    
    # Instancia o manager e movimenta o ativo
    manager = AssetManager()
    manager.movimentar(id_ativo, 'Em Uso', chamado, detalhes)
    
    flash('Ativo distribuído com sucesso! Gerando termo de responsabilidade...', 'success')
    
    # CORREÇÃO: Altera a consulta para usar o placeholder :id_ativo e um dicionário de parâmetros
    query = "SELECT a.*, m.nome as modelo, c.nome as categoria FROM ativos a JOIN modelos m ON a.modelo_id = m.id JOIN categorias c ON a.categoria_id = c.id WHERE a.id_ativo = :id_ativo"
    ativo_info_list = db_query(query, {'id_ativo': id_ativo})

    # Adiciona uma verificação para garantir que o ativo foi encontrado antes de gerar o termo
    if not ativo_info_list:
        flash(f'Erro ao gerar termo: Ativo com ID {id_ativo} não foi encontrado após a movimentação.', 'error')
        return redirect(url_for('main.detalhes_ativo', id_ativo=id_ativo))
        
    ativo_info = ativo_info_list[0]
    
    return render_template('termo.html', title="Termo de Responsabilidade", usuario=detalhes['usuario_responsavel'], ativos=[ativo_info], data_emissao=datetime.now().strftime('%d/%m/%Y %H:%M'))

@main_bp.route('/ativo/<id_ativo>/movimentar', methods=['POST'])
@login_required
def movimentar_ativo(id_ativo):
    novo_status = request.form['novo_status']
    chamado = request.form['numero_chamado']
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
                if file.filename.endswith('.csv'):
                    # Garante que os dados sejam lidos como texto para não perder zeros à esquerda
                    df = pd.read_csv(file, dtype=str).fillna('') 
                elif file.filename.endswith('.xlsx'):
                    df = pd.read_excel(file, dtype=str).fillna('')
                else:
                    flash('Formato de arquivo inválido. Use CSV ou XLSX.', 'error')
                    return redirect(request.url)

                df.columns = [col.lower().strip() for col in df.columns]

                required_columns = ['numero_serie', 'categoria', 'modelo', 'marca', 'data_aquisicao']
                if not all(col in df.columns for col in required_columns):
                    flash(f'O arquivo deve conter as colunas obrigatórias: {required_columns}', 'error')
                    return redirect(request.url)

                sucesso = 0
                erros = []
                asset_manager = AssetManager()

                for index, row in df.iterrows():
                    try:
                        # Validação simples
                        if not row['numero_serie']:
                            raise ValueError("O 'numero_serie' não pode estar vazio.")

                        # 1. Encontrar ou criar Categoria
                        categoria_nome = row['categoria'].strip()
                        cat_query = db_query("SELECT id, substr(nome, 1, 2) as sigla FROM categorias WHERE nome = :nome", {'nome': categoria_nome})
                        if not cat_query:
                            db_execute("INSERT INTO categorias (nome) VALUES (:nome)", {'nome': categoria_nome})
                            cat_query = db_query("SELECT id, substr(nome, 1, 2) as sigla FROM categorias WHERE nome = :nome", {'nome': categoria_nome})
                        cat_id = cat_query[0]['id']
                        sigla_cat = cat_query[0]['sigla']
                        
                        # 2. Encontrar ou criar Modelo
                        modelo_nome = row['modelo'].strip()
                        mod_query = db_query("SELECT id FROM modelos WHERE nome = :nome AND categoria_id = :cat_id", {'nome': modelo_nome, 'cat_id': cat_id})
                        if not mod_query:
                            db_execute("INSERT INTO modelos (nome, categoria_id) VALUES (:nome, :cat_id)", {'nome': modelo_nome, 'cat_id': cat_id})
                            mod_query = db_query("SELECT id FROM modelos WHERE nome = :nome AND categoria_id = :cat_id", {'nome': modelo_nome, 'cat_id': cat_id})
                        mod_id = mod_query[0]['id']
                        
                        # 3. Preparar dados para registro
                        form_data = {
                            'id_ativo': row.get('id_ativo', '').strip(), # Patrimônio opcional
                            'tipo_ativo_sigla': sigla_cat.upper(),
                            'numero_serie': row['numero_serie'].strip(),
                            'marca': row['marca'].strip(),
                            'modelo': mod_id,
                            'categoria': cat_id,
                            'nota_fiscal': row.get('nota_fiscal', ''),
                            'fornecedor': row.get('fornecedor', ''),
                            'data_aquisicao': str(row['data_aquisicao']),
                            'cpu': row.get('cpu', ''),
                            'ram_gb': row.get('ram_gb', None) or None,
                            'armazenamento_gb': row.get('armazenamento_gb', None) or None,
                            'sistema_operacional': row.get('sistema_operacional', '')
                        }
                        asset_manager.registrar_novo_ativo(form_data)
                        sucesso += 1
                    except Exception as e:
                        erros.append(f"Linha {index + 2}: {e}")
                
                if not erros:
                    flash(f'Importação concluída! {sucesso} ativos importados com sucesso.', 'success')
                else:
                    erros_str = " | ".join(erros)
                    flash(f'{sucesso} ativos importados. Falhas: {len(erros)}. Detalhes: {erros_str}', 'error')

            except Exception as e:
                flash(f'Ocorreu um erro fatal ao processar o arquivo: {e}', 'error')

        return redirect(url_for('main.importar_ativos'))

    return render_template('importar.html', title="Importar Ativos")