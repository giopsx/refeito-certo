"""Rotas HTTP da aplicação."""
from flask import Blueprint, render_template, request, jsonify
from functools import wraps
import os, json
from datetime import datetime, date

bp = Blueprint('main', __name__)

_CACHE_FILE = '/tmp/pgm_data_cache.json'
_cache = {}


def _load_cache():
    global _cache
    if os.path.exists(_CACHE_FILE):
        try:
            with open(_CACHE_FILE, encoding='utf-8') as f:
                _cache = json.load(f)
        except Exception:
            _cache = {}


def _save_cache():
    with open(_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(_cache, f, ensure_ascii=False, indent=2)


_load_cache()

_NAO_PESSOAS = {
    'SPF', 'SPJ', 'SPMA', 'GEC', 'AMBIENTAL', 'FISCAL', 'COMCEP',
    'VERIFICAR', '-', 'Sem responsável', 'GABINETE ACOMPANHANDO',
    'CARTORIO/GABINETE', 'DISTRIBUIR', 'MANIFESTAÇÃO DESNECESSÁRIA',
    'PREJUDICADO', '',
}
_NAO_PESSOAS_PREFIXOS = ('DEVOLVIDO', 'ESCRITORIO', 'GABINETE', 'F704')

_NORMALIZAR = {
    'ÉRICA': 'ERICA',
    'JEFERSON': 'JEFFERSON',
}


def _normalizar(nome):
    return _NORMALIZAR.get(nome.upper(), nome.upper()) if nome else ''


def _eh_pessoa(nome):
    if not nome or nome in _NAO_PESSOAS:
        return False
    if nome.startswith(_NAO_PESSOAS_PREFIXOS):
        return False
    if nome.count('.') >= 3 and nome.count('-') >= 1:
        return False
    if any(c.isdigit() for c in nome):
        return False
    if '/' in nome or '&' in nome or '\n' in nome:
        return False
    return True


def _parse_xlsx(file_obj):
    import openpyxl, warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        wb = openpyxl.load_workbook(file_obj, read_only=True, data_only=True)

    today = date.today()
    ws_p = wb['Prazos 2026']
    performance = {}
    proximos_lista = []
    vencidos_lista = []
    total = 0
    vencidos_nc = 0
    proximos_count = 0
    cumpridos = 0

    for row in ws_p.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row):
            continue
        if row[0] is None and row[1] is None and row[2] is None:
            continue

        total += 1

        prazo_raw    = row[1]
        responsavel  = _normalizar(str(row[2]).strip() if row[2] else '')
        if not responsavel:
            responsavel = 'Sem responsável'
        num_proc     = str(row[4]).strip() if row[4] else ''
        vara         = str(row[6]).strip() if row[6] else ''
        assunto      = str(row[7]).strip()[:80] if row[7] else ''
        status       = str(row[12]).strip().upper() if row[12] else ''
        cumprido_val = str(row[13]).strip().upper() if row[13] else ''

        prazo_d = None
        if isinstance(prazo_raw, datetime):
            prazo_d = prazo_raw.date()
        elif isinstance(prazo_raw, date):
            prazo_d = prazo_raw
        prazo_str = prazo_d.strftime('%d/%m/%Y') if prazo_d else ''

        if cumprido_val == 'SIM':
            cumpridos += 1

        if status == 'VENCIDO':
            vencidos_nc += 1
            dias = (today - prazo_d).days if prazo_d else 0
            vencidos_lista.append({
                'processo': num_proc, 'responsavel': responsavel,
                'prazo': prazo_str, 'dias': dias,
                'assunto': assunto, 'vara': vara,
            })
        elif status in ('VENCE HOJE', 'URGENTE'):
            proximos_count += 1
            diff = (prazo_d - today).days if prazo_d else 0
            proximos_lista.append({
                'processo': num_proc, 'responsavel': responsavel,
                'prazo': prazo_str, 'dias': diff,
                'assunto': assunto, 'vara': vara,
            })

        if responsavel not in performance:
            performance[responsavel] = {'total': 0, 'cumpridos': 0, 'criticos': 0}
        performance[responsavel]['total'] += 1
        if cumprido_val == 'SIM':
            performance[responsavel]['cumpridos'] += 1
        if status == 'VENCIDO':
            performance[responsavel]['criticos'] += 1

    taxa = round(cumpridos / total * 100, 1) if total > 0 else 0

    perf_list = []
    for resp, d in sorted(performance.items()):
        if not _eh_pessoa(resp):
            continue
        t, c = d['total'], d['cumpridos']
        perf_list.append({
            'responsavel': resp, 'total': t, 'cumpridos': c,
            'taxa': round(c / t * 100, 1) if t > 0 else 0,
            'criticos': d['criticos'],
        })
    perf_list.sort(key=lambda x: x['taxa'], reverse=True)
    proximos_lista.sort(key=lambda x: x['dias'])
    vencidos_lista.sort(key=lambda x: x['dias'], reverse=True)

    return {
        'stats': {
            'total': total, 'vencidos': vencidos_nc,
            'proximos': proximos_count, 'cumpridos': cumpridos,
            'taxa': taxa, 'ultima_atualizacao': today.strftime('%d/%m/%Y'),
        },
        'performance': perf_list,
        'proximos': proximos_lista,
        'vencidos': vencidos_lista[:50],
    }


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import current_app
        token = request.args.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token or token != current_app.config['ACCESS_TOKEN']:
            return jsonify({'error': 'Token inválido ou ausente'}), 401
        return f(*args, **kwargs)
    return decorated


@bp.route('/', methods=['GET'])
def index():
    from flask import redirect, url_for, current_app
    return redirect(url_for('main.painel', token=current_app.config['ACCESS_TOKEN']))


@bp.route('/painel', methods=['GET'])
@token_required
def painel():
    return render_template('dashboard.html')


@bp.route('/api/upload', methods=['POST'])
@token_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Arquivo não fornecido'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Arquivo vazio'}), 400
    if not file.filename.lower().endswith('.xlsx'):
        return jsonify({'error': 'Apenas arquivos XLSX são permitidos'}), 400
    try:
        data = _parse_xlsx(file)
        _cache.update(data)
        _cache['filename'] = file.filename
        _save_cache()
        return jsonify({
            'success': True,
            'message': 'Planilha importada com sucesso',
            'stats': data['stats'],
            'filename': file.filename,
        }), 200
    except KeyError as e:
        return jsonify({'error': f'Aba não encontrada: {e}. A aba deve se chamar "Prazos 2026".'}), 422
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/dashboard', methods=['GET'])
@token_required
def get_dashboard():
    if not _cache:
        return jsonify({'sem_dados': True}), 200
    return jsonify({
        'stats': _cache.get('stats', {}),
        'performance': _cache.get('performance', []),
        'filename': _cache.get('filename', ''),
    })


@bp.route('/api/criticos', methods=['GET'])
@token_required
def get_criticos():
    if not _cache:
        return jsonify({'sem_dados': True}), 200
    return jsonify({
        'vencidos': _cache.get('vencidos', []),
        'proximos': _cache.get('proximos', []),
    })


@bp.route('/api/relatorios/<tipo>', methods=['POST'])
@token_required
def gerar_relatorio(tipo):
    if tipo not in ['semanal', 'mensal', 'individual']:
        return jsonify({'error': 'Tipo inválido'}), 400
    return jsonify({'success': True, 'message': f'Relatório {tipo} gerado', 'url': '/r/abc123'}), 200


@bp.route('/api/equipe', methods=['GET'])
@token_required
def get_equipe():
    return jsonify({'membros': []})


@bp.route('/api/equipe', methods=['POST'])
@token_required
def add_membro():
    data = request.json
    if not all(f in data for f in ['nome', 'funcao', 'email', 'whatsapp']):
        return jsonify({'error': 'Campos obrigatórios faltando'}), 400
    return jsonify({'success': True, 'message': 'Membro adicionado'}), 201


@bp.route('/robots.txt', methods=['GET'])
def robots():
    return 'User-agent: *\nDisallow: /', 200, {'Content-Type': 'text/plain'}


@bp.after_request
def add_security_headers(response):
    response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    return response
