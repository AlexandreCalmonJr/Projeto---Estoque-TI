from flask import render_template, current_app, flash, redirect, url_for, request
from flask_login import login_required, current_user
from functools import wraps
from sqlalchemy import text

from . import admin_bp
from app.models import User, db, db_get_engine_by_key

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
                engine = db_get_engine_by_key(key)
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

@admin_bp.route('/users')
@login_required
@admin_required
def list_users():
    """Lista todos os usuários do sistema."""
    users = User.query.order_by(User.id).all()
    return render_template('admin/users.html', users=users)

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
    return render_template('admin/user_form.html', user=user)

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Deleta um usuário."""
    if user_id == current_user.id:
        flash('Você não pode deletar sua própria conta.', 'error')
        return redirect(url_for('admin.list_users'))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Usuário deletado com sucesso!', 'success')
    return redirect(url_for('admin.list_users'))

