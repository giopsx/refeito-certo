"""
Procuradoria-Geral do Municipio de Porto Velho
Subprocuradoria Contenciosa - Sistema de Gestao de Prazos Processuais
"""
import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()


def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY']         = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
    app.config['ACCESS_TOKEN']       = os.getenv('ACCESS_TOKEN', 'pgm-contenciosa-2026')

    from . import routes
    app.register_blueprint(routes.bp)

    return app
