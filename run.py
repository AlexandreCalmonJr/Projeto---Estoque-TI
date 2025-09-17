# run.py
from app import create_app

app = create_app()

if __name__ == '__main__':
    # O modo debug não é recomendado para produção.
    app.run(debug=True)

