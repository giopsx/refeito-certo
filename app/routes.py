"""Rotas HTTP da aplicação."""
from flask import Blueprint, render_template, request, jsonify, send_file
from functools import wraps
import os

bp = Blueprint('main', __name__)


def token_required(f):
    """Decorator para validar token de acesso."""
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import current_app
        token = request.args.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token or token != current_app.config['ACCESS_TOKEN']:
            return jsonify({'error': 'Token inválido ou ausente'}), 401
        
        return f(*args, **kwargs)
    return decorated


# APAGUE ISSO:
@bp.route('/', methods=['GET'])
def index():
    from flask import redirect, url_for, current_app
    return redirect(url_for('main.painel', token=current_app.config['ACCESS_TOKEN']))


@bp.route('/painel', methods=['GET'])
@token_required
def painel():
    """Página principal do dashboard."""
    return render_template('dashboard.html')


@bp.route('/api/upload', methods=['POST'])
@token_required
def upload_file():
    """Endpoint para upload de planilha."""
    if 'file' not in request.files:
        return jsonify({'error': 'Arquivo não fornecido'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Arquivo vazio'}), 400
    
    if not file.filename.endswith('.xlsx'):
        return jsonify({'error': 'Apenas arquivos XLSX são permitidos'}), 400
    
    try:
        # Aqui você implementaria o parser da planilha
        # from .parser import parse_xlsx
        # prazos = parse_xlsx(file)
        return jsonify({
            'success': True,
            'message': 'Planilha importada com sucesso',
            'prazos_count': 0  # Será preenchido pelo parser
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/dashboard', methods=['GET'])
@token_required
def get_dashboard():
    """API para dados do dashboard."""
    # Aqui você retornaria estatísticas do banco
    return jsonify({
        'total_processos': 128,
        'vencidos': 12,
        'proximos': 8,
        'cumpridos': 108,
        'taxa_cumprimento': 84.4
    })


@bp.route('/api/criticos', methods=['GET'])
@token_required
def get_criticos():
    """API para processos críticos."""
    return jsonify({
        'criticos': []
    })


@bp.route('/api/relatorios/<tipo>', methods=['POST'])
@token_required
def gerar_relatorio(tipo):
    """Endpoint para gerar relatório PDF."""
    # Tipos válidos: semanal, mensal, individual
    if tipo not in ['semanal', 'mensal', 'individual']:
        return jsonify({'error': 'Tipo de relatório inválido'}), 400
    
    try:
        # Aqui você implementaria a geração de PDF
        # from .pdf_gen import gerar_pdf
        # pdf_path = gerar_pdf(tipo)
        # return send_file(pdf_path, ...)
        return jsonify({
            'success': True,
            'message': f'Relatório {tipo} gerado com sucesso',
            'url': f'/r/abc123def456'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/equipe', methods=['GET'])
@token_required
def get_equipe():
    """API para listar membros da equipe."""
    return jsonify({
        'membros': []
    })


@bp.route('/api/equipe', methods=['POST'])
@token_required
def add_membro():
    """Endpoint para adicionar membro da equipe."""
    data = request.json
    
    required_fields = ['nome', 'funcao', 'email', 'whatsapp']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Campos obrigatórios faltando'}), 400
    
    try:
        # Aqui você criaria um novo membro no banco
        return jsonify({
            'success': True,
            'message': 'Membro adicionado com sucesso'
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/robots.txt', methods=['GET'])
def robots():
    """Bloquear indexação por bots."""
    return 'User-agent: *\nDisallow: /', 200, {'Content-Type': 'text/plain'}


@bp.after_request
def add_security_headers(response):
    """Adicionar headers de segurança e privacidade."""
    response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    return response
