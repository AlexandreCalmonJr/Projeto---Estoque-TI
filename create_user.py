import os
from getpass import getpass
from app import create_app
from app.models import db, User

# Cria uma instância da aplicação para que o script tenha acesso ao contexto
# Isso permite que ele se comunique com o banco de dados corretamente
config_name = os.getenv('FLASK_CONFIG') or 'default'
app = create_app(config_name)

# Usa o contexto da aplicação para executar as operações de banco de dados
with app.app_context():
    print("--- Criar Novo Usuário Administrador ---")
    
    while True:
        username = input("Digite o nome de usuário: ").strip()
        if not username:
            print("O nome de usuário não pode ser vazio.")
        else:
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                print(f"Erro: O nome de usuário '{username}' já existe. Tente outro.")
            else:
                break

    while True:
        password = getpass("Digite a senha: ")
        password2 = getpass("Confirme a senha: ")
        if not password:
            print("A senha não pode ser vazia.")
        elif password != password2:
            print("As senhas não coincidem. Tente novamente.")
        else:
            break
            
    is_admin_input = input("Este usuário deve ser um administrador? (s/n): ").lower()
    is_admin = is_admin_input == 's'

    # Cria o novo usuário
    new_user = User(username=username, is_admin=is_admin)
    new_user.set_password(password)

    # Adiciona ao banco de dados de autenticação
    db.session.add(new_user)
    db.session.commit()

    print("\n-------------------------------------------")
    print(f"✅ Usuário '{username}' criado com sucesso!")
    if is_admin:
        print("   O usuário tem permissões de administrador.")
    print("-------------------------------------------")

