from flask import render_template, current_app, flash, redirect, url_for, request, send_file
from flask_login import login_required, current_user
from functools import wraps
from sqlalchemy import text
import os
import zipfile
import io
from datetime import datetime, timedelta

from . import admin_bp
from app.models import User, db, get_engine_by_key, Setting, AuditLog, get_setting, set_setting, log_audit

# --- Decorator para Rotas de Admin ---
def admin_required(f):
    """Garante que o usuário logado é um administrador."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Acesso negado. Você precisa de permissões de administrador.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


# --- Rotas do Painel ---
@admin_bp.route('/')
@login_required
@admin_required
def admin_dashboard():
    """Exibe o painel principal com estatísticas consolidadas."""
    try:
        total_users = User.query.count()
        stats = {
            'total_assets': 0,
            'assets_by_db': [],
            'assets_by_status': {}
        }

        # Itera sobre cada banco de dados de ativos para coletar estatísticas
        for key, config in current_app.config['ASSET_DATABASES'].items():
            try:
                # Linha que precisa de correção
                engine = get_engine_by_key(key) # Altere 'db_get_engine_by_key' para 'get_engine_by_key'
                with engine.connect() as connection:
                    # Total de ativos por base
                    result = connection.execute(text("SELECT COUNT(*) FROM ativos"))
                    count = result.scalar_one() or 0
                    stats['total_assets'] += count
                    stats['assets_by_db'].append({'name': config['name'], 'count': count})

                    # Ativos por status (consolidado)
                    status_result = connection.execute(text("SELECT status, COUNT(*) as count FROM ativos GROUP BY status"))
                    for row in status_result.mappings():
                        stats['assets_by_status'][row['status']] = stats['assets_by_status'].get(row['status'], 0) + row['count']
            except Exception as e:
                # Se não conseguir conectar a uma base, registra o erro e continua
                stats['assets_by_db'].append({'name': f"{config['name']} (Erro de conexão)", 'count': 0})
                print(f"ERRO: Não foi possível conectar à base de dados '{key}': {e}")
        
        return render_template('admin/dashboard.html', total_users=total_users, stats=stats)
    except Exception as e:
        flash(f'Ocorreu um erro ao carregar o dashboard: {e}', 'error')
        return render_template('admin/dashboard.html', total_users=0, stats={'total_assets': 0, 'assets_by_db': [], 'assets_by_status': {}})

# --- ROTAS DE CRUD DE USUÁRIOS ---

@admin_bp.route('/users')
@login_required
@admin_required
def list_users():
    """Lista todos os usuários do sistema."""
    users = User.query.order_by(User.username).all()
    return render_template('admin/users.html', title="Gerenciar Usuários", users=users)

@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    """Exibe o formulário e processa a criação de um novo usuário."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        is_admin = 'is_admin' in request.form

        # Verifica se o usuário já existe
        if User.query.filter_by(username=username).first():
            flash('Este nome de usuário já existe. Tente outro.', 'error')
            return redirect(url_for('admin.create_user'))

        if not password:
            flash('O campo senha é obrigatório para novos usuários.', 'error')
            return redirect(url_for('admin.create_user'))

        new_user = User(username=username, is_admin=is_admin)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash(f'Usuário "{username}" criado com sucesso!', 'success')
        return redirect(url_for('admin.list_users'))

    return render_template('admin/user_form.html', title="Criar Novo Usuário", user=None)

@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edita os dados de um usuário."""
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.username = request.form['username']
        
        # Evita que o admin se remova da função de admin
        if user.id == current_user.id and 'is_admin' not in request.form:
             flash('Você não pode remover suas próprias permissões de administrador.', 'error')
        else:
            user.is_admin = 'is_admin' in request.form
        
        password = request.form.get('password')
        if password:
            user.set_password(password)
        
        db.session.commit()
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('admin.list_users'))

    return render_template('admin/user_form.html', title="Editar Usuário", user=user)

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Deleta um usuário."""
    # Evita que o usuário delete a si mesmo
    if user_id == current_user.id:
        flash('Você não pode deletar sua própria conta.', 'error')
        return redirect(url_for('admin.list_users'))

    user_to_delete = User.query.get_or_404(user_id)
    db.session.delete(user_to_delete)
    db.session.commit()
    flash('Usuário deletado com sucesso!', 'success')
    return redirect(url_for('admin.list_users'))


@admin_bp.route('/databases')
@login_required
@admin_required
def list_databases():
    """Lista todos os bancos de dados configurados e seu status."""
    from config import basedir
    databases_info = []
    
    for key, config_info in current_app.config['ASSET_DATABASES'].items():
        db_path = config_info['url'].replace('sqlite:///', '')
        
        # Tenta resolver o caminho absoluto se não for absoluto
        if not os.path.isabs(db_path):
            db_path = os.path.abspath(os.path.join(basedir, db_path))
            
        # Verifica tamanho físico do arquivo
        size_str = "N/A"
        if os.path.exists(db_path):
            size_bytes = os.path.getsize(db_path)
            if size_bytes >= 1024 * 1024:
                size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
            else:
                size_str = f"{size_bytes / 1024:.2f} KB"
        
        # Testar conexão e contar ativos
        status = "Offline"
        ativos_count = 0
        try:
            engine = get_engine_by_key(key)
            with engine.connect() as conn:
                status = "Online"
                result = conn.execute(text("SELECT COUNT(*) FROM ativos"))
                ativos_count = result.scalar_one() or 0
        except Exception as e:
            print(f"Erro ao conectar ao banco {key}: {e}")
            
        databases_info.append({
            'key': key,
            'name': config_info['name'],
            'path': db_path,
            'size': size_str,
            'status': status,
            'ativos_count': ativos_count
        })
        
    return render_template('admin/databases.html', title="Bancos de Dados", databases=databases_info)


@admin_bp.route('/audit-logs')
@login_required
@admin_required
def list_audit_logs():
    """Exibe o histórico de logs de auditoria."""
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(150).all()
    return render_template('admin/audit_logs.html', title="Auditoria do Sistema", logs=logs)


@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def system_settings():
    """Gerencia as configurações SMTP do e-mail, texto de cláusulas e outros parâmetros."""
    if request.method == 'POST':
        # E-mail
        set_setting('mail_server', request.form.get('mail_server', '').strip())
        set_setting('mail_port', request.form.get('mail_port', '').strip())
        set_setting('mail_username', request.form.get('mail_username', '').strip())
        set_setting('mail_default_sender', request.form.get('mail_default_sender', '').strip())
        
        # A senha só é atualizada se for digitada
        smtp_pass = request.form.get('mail_password', '').strip()
        if smtp_pass:
            set_setting('mail_password', smtp_pass)
            
        set_setting('mail_use_tls', 'true' if 'mail_use_tls' in request.form else 'false')
        
        # Gerais
        set_setting('company_name', request.form.get('company_name', '').strip())
        set_setting('only_digital_signature', 'true' if 'only_digital_signature' in request.form else 'false')
        set_setting('termo_texto', request.form.get('termo_texto', ''))
        
        # Upload de Logotipo
        logo_file = request.files.get('logo')
        if logo_file and logo_file.filename:
            ext = logo_file.filename.rsplit('.', 1)[1].lower() if '.' in logo_file.filename else ''
            if ext in ('png', 'jpg', 'jpeg'):
                from config import basedir
                uploads_dir = os.path.join(basedir, 'uploads')
                os.makedirs(uploads_dir, exist_ok=True)
                logo_path = os.path.join(uploads_dir, 'logo_custom.png')
                try:
                    logo_file.save(logo_path)
                    flash('Logotipo da empresa atualizado com sucesso!', 'success')
                except Exception as logo_err:
                    flash(f'Erro ao salvar o logotipo: {logo_err}', 'error')
            else:
                flash('Extensão de imagem inválida para o logotipo. Use PNG, JPG ou JPEG.', 'error')

        log_audit('Atualização de Configurações', 'Configurações de e-mail, logotipo e termos atualizadas.')
        flash('Configurações atualizadas com sucesso!', 'success')
        return redirect(url_for('admin.system_settings'))

    # Coleta valores atuais
    settings_data = {
        'mail_server': get_setting('mail_server', ''),
        'mail_port': get_setting('mail_port', ''),
        'mail_username': get_setting('mail_username', ''),
        'mail_default_sender': get_setting('mail_default_sender', ''),
        'mail_use_tls': get_setting('mail_use_tls', 'false') == 'true',
        'company_name': get_setting('company_name', 'Almoxarifado Digital'),
        'only_digital_signature': get_setting('only_digital_signature', 'false') == 'true',
        'termo_texto': get_setting('termo_texto', '')
    }
    
    return render_template('admin/settings.html', title="Configurações do Sistema", settings=settings_data)


@admin_bp.route('/maintenance', methods=['GET', 'POST'])
@login_required
@admin_required
def maintenance_page():
    """Página contendo download de backups e utilitários de limpeza/manutenção."""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'purge_history':
            try:
                months = int(request.form.get('months', 6))
                cutoff = (datetime.now() - timedelta(days=months * 30)).strftime('%Y-%m-%d %H:%M:%S')
                
                # Executa a limpeza em todos os bancos de ativos
                purged_dbs = []
                for key in current_app.config['ASSET_DATABASES'].keys():
                    try:
                        engine = get_engine_by_key(key)
                        with engine.begin() as conn:
                            # Limpa os históricos antigos
                            conn.execute(text("DELETE FROM historico WHERE timestamp < :cutoff"), {'cutoff': cutoff})
                            # Executa VACUUM para liberar espaço no SQLite
                            conn.execute(text("VACUUM"))
                        purged_dbs.append(key)
                    except Exception as db_err:
                        print(f"Erro ao limpar banco {key}: {db_err}")
                
                log_audit('Limpeza de Dados', f'Histórico de movimentações com mais de {months} meses excluído nos bancos: {", ".join(purged_dbs)}')
                flash(f'Limpeza concluída! Históricos com mais de {months} meses foram removidos com sucesso.', 'success')
            except Exception as e:
                flash(f'Erro ao realizar limpeza de dados: {e}', 'error')
                
        elif action == 'reset_password':
            try:
                username = request.form.get('target_username', '').strip()
                new_password = request.form.get('new_password', '').strip()
                
                if not username or not new_password:
                    flash('Informe o usuário e a nova senha.', 'error')
                else:
                    user = User.query.filter_by(username=username).first()
                    if not user:
                        flash('Usuário não encontrado.', 'error')
                    else:
                        user.set_password(new_password)
                        db.session.commit()
                        log_audit('Redefinição de Senha', f'Senha do usuário "{username}" alterada pelo administrador.')
                        flash(f'Senha do usuário "{username}" redefinida com sucesso!', 'success')
            except Exception as e:
                flash(f'Erro ao redefinir senha: {e}', 'error')
                
        return redirect(url_for('admin.maintenance_page'))
        
    # GET: renderiza página
    users = User.query.order_by(User.username).all()
    return render_template('admin/backup.html', title="Backup & Limpeza", users=users)


@admin_bp.route('/backup/download')
@login_required
@admin_required
def download_backup():
    """Gera um arquivo ZIP em memória contendo todos os arquivos .db e inicia o download."""
    try:
        from config import basedir
        memory_file = io.BytesIO()
        
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in os.listdir(basedir):
                if file.endswith('.db'):
                    file_path = os.path.join(basedir, file)
                    zipf.write(file_path, file)
                    
        memory_file.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_audit('Backup de Dados', 'Download do backup consolidado de bancos de dados efetuado.')
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'backup_almoxarifado_{timestamp}.zip'
        )
    except Exception as e:
        flash(f'Erro ao gerar o backup: {e}', 'error')
        return redirect(url_for('admin.maintenance_page'))

