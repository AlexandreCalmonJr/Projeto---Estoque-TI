# run.py
from app import create_app
from waitress import serve
import webbrowser

# Cria a instância da aplicação
app = create_app()

if __name__ == '__main__':
    import os
    import socket
    
    # '0.0.0.0' permite que outros computadores da rede local acessem o site
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 8000))
    
    # Se o host for 0.0.0.0 (rede local), usamos localhost para tentar abrir o navegador na máquina local
    browser_host = '127.0.0.1' if host == '0.0.0.0' else host
    url = f"http://{browser_host}:{port}"
    
    # Tenta descobrir o IP real da máquina na rede local para exibir o link correto
    local_ip = '127.0.0.1'
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Não estabelece conexão real, apenas descobre a interface de rede ativa
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        # Fallback caso esteja sem internet ou offline
        pass
        
    network_url = f"http://{local_ip}:{port}"
    
    # Abre o navegador apenas se não estivermos rodando em modo totalmente oculto/servidor
    # (Pode ser desativado definindo a variável de ambiente OPEN_BROWSER=false)
    if os.environ.get('OPEN_BROWSER', 'true').lower() in ('true', '1', 'yes'):
        webbrowser.open(url)
    
    print(f"Servidor iniciado.")
    print(f"Acesse localmente em: {url}")
    print(f"Acesse de outros computadores da rede em: {network_url}")
    
    # Inicia o servidor de produção Waitress
    serve(app, host=host, port=port)