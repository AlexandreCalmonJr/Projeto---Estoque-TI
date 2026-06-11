# Usa uma imagem oficial leve do Python
FROM python:3.11-slim

# Evita que o Python grave arquivos .pyc no disco
ENV PYTHONDONTWRITEBYTECODE=1
# Evita que o Python faça buffer de stdout e stderr
ENV PYTHONUNBUFFERED=1

# Configurações de execução
ENV PORT=8000
ENV HOST=0.0.0.0
# Impede que o Python tente abrir o navegador automaticamente dentro do container
ENV OPEN_BROWSER=false
# Define o ambiente como produção
ENV FLASK_CONFIG=production

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia e instala as dependências primeiro para aproveitar o cache de build do Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código da aplicação
COPY . .

# Expõe a porta 8000 para acesso
EXPOSE 8000

# Executa a aplicação usando waitress através do run.py
CMD ["python", "run.py"]
