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
    from . import routes
    app.register_blueprint(routes.bp)

    # Criar tabelas
    with app.app_context():
        db.create_all()

    return app
