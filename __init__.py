"""
Procuradoria-Geral do Município de Porto Velho
Subprocuradoria Contenciosa — Sistema de Gestão de Prazos Processuais
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Inicializar extensões
db = SQLAlchemy()


def create_app():
    """Factory para criar aplicação Flask."""
    app = Flask(__name__)

    # Configuração
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///pgm_relatorios.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
    app.config['ACCESS_TOKEN'] = os.getenv('ACCESS_TOKEN', 'pgm-contenciosa-2026')
    app.config['ENABLE_SCHEDULER'] = os.getenv('ENABLE_SCHEDULER', 'true').lower() == 'true'

    # Inicializar banco
    db.init_app(app)

    # Registrar blueprints e rotas
    import app_routes as routes
    app.register_blueprint(routes.bp)

    # Criar tabelas
    with app.app_context():
        db.create_all()

    return app

    # Esse é o botão de ligar!
# Esse bloco deve ficar logo abaixo de app = create_app()
app = create_app()

app = create_app()

@app.route('/')
def check_alive():
    from flask import redirect, url_for
    # Isso vai te mandar direto para o dashboard
    return redirect(url_for('main.painel', token=app.config['ACCESS_TOKEN']))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)