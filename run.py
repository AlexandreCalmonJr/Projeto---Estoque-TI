# run.py
from app import create_app
from waitress import serve
import webbrowser

# Cria a instância da aplicação
app = create_app()

if __name__ == '__main__':
    # Define o endereço e a porta
    host = '127.0.0.1'
    port = 8000
    
    # Monta a URL completa
    url = f"http://{host}:{port}"
    
    # Abre o navegador na URL da aplicação um pouco antes de iniciar o servidor
    webbrowser.open(url)
    
    print(f"Servidor iniciado. Acesse a aplicação em: {url}")
    
    # Inicia o servidor de produção Waitress
    serve(app, host=host, port=port)