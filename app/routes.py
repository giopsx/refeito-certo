"""Rotas HTTP da aplicação — PGM Porto Velho."""
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
    'SPF','SPJ','SPMA','GEC','AMBIENTAL','FISCAL','COMCEP','VERIFICAR','-',
    'Sem responsável','GABINETE ACOMPANHANDO','CARTORIO/GABINETE','DISTRIBUIR',
    'MANIFESTAÇÃO DESNECESSÁRIA','PREJUDICADO','',
}
_NAO_PESSOAS_PREFIXOS = ('DEVOLVIDO','ESCRITORIO','GABINETE','F704')
_NORMALIZAR = {'ÉRICA':'ERICA','JEFERSON':'JEFFERSON'}

def _normalizar(nome):
    return _NORMALIZAR.get(nome.upper(), nome.upper()) if nome else ''

def _eh_pessoa(nome):
    if not nome or nome in _NAO_PESSOAS: return False
    if nome.startswith(_NAO_PESSOAS_PREFIXOS): return False
    if nome.count('.') >= 3 and nome.count('-') >= 1: return False
    if any(c.isdigit() for c in nome): return False
    if '/' in nome or '&' in nome or '\n' in nome: return False
    return True

def _parse_xlsx(file_obj):
    import openpyxl, warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        wb = openpyxl.load_workbook(file_obj, read_only=True, data_only=True)
    today = date.today()
    ws_p = wb['Prazos 2026']
    performance = {}
    proximos_lista, vencidos_lista = [], []
    total = vencidos_nc = proximos_count = cumpridos = 0

    for row in ws_p.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row): continue
        if row[0] is None and row[1] is None and row[2] is None: continue

        prazo_raw    = row[1]
        responsavel  = _normalizar(str(row[2]).strip() if row[2] else '')
        if not responsavel: responsavel = 'Sem responsável'
        num_proc     = str(row[4]).strip() if row[4] else ''
        parte        = str(row[5]).strip()[:60] if row[5] else ''
        vara         = str(row[6]).strip() if row[6] else ''
        assunto      = str(row[7]).strip()[:80] if row[7] else ''
        cumprido_val = str(row[13]).strip().upper() if row[13] else ''

        prazo_d = None
        if isinstance(prazo_raw, datetime): prazo_d = prazo_raw.date()
        elif isinstance(prazo_raw, date):   prazo_d = prazo_raw
        prazo_str = prazo_d.strftime('%d/%m/%Y') if prazo_d else ''

        if not prazo_d: continue
        total += 1

        ja_cumprido = cumprido_val in ('SIM','PARCIAL','PREJUDICADO')
        if ja_cumprido: cumpridos += 1

        diff = (prazo_d - today).days

        if not ja_cumprido:
            entry = {
                'processo': num_proc, 'parte': parte,
                'responsavel': responsavel, 'prazo': prazo_str,
                'dias': abs(int(diff)), 'assunto': assunto, 'vara': vara,
            }
            if diff < 0:
                vencidos_nc += 1
                vencidos_lista.append(entry)
            elif diff <= 7:
                proximos_count += 1
                proximos_lista.append(entry)

        if responsavel not in performance:
            performance[responsavel] = {'total':0,'cumpridos':0,'criticos':0}
        performance[responsavel]['total'] += 1
        if ja_cumprido: performance[responsavel]['cumpridos'] += 1
        if not ja_cumprido and diff < 0: performance[responsavel]['criticos'] += 1

    taxa = round(cumpridos/total*100,1) if total > 0 else 0
    perf_list = []
    for resp, d in sorted(performance.items()):
        if not _eh_pessoa(resp): continue
        t, c = d['total'], d['cumpridos']
        perf_list.append({
            'responsavel':resp,'total':t,'cumpridos':c,
            'taxa':round(c/t*100,1) if t>0 else 0,'criticos':d['criticos'],
        })
    perf_list.sort(key=lambda x: x['taxa'], reverse=True)
    proximos_lista.sort(key=lambda x: x['dias'])
    vencidos_lista.sort(key=lambda x: x['dias'], reverse=True)
    ant = _cache.get('stats', {})
    return {
        'stats': {
            'total':total,'vencidos':vencidos_nc,'proximos':proximos_count,
            'cumpridos':cumpridos,'taxa':taxa,
            'ultima_atualizacao':today.strftime('%d/%m/%Y'),
        },
        'stats_anterior': ant,
        'performance': perf_list,
        'proximos': proximos_lista,
        'vencidos': vencidos_lista,
    }

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import current_app
        token = (request.args.get('token') or
                 request.headers.get('Authorization','').replace('Bearer ',''))
        if not token or token != current_app.config['ACCESS_TOKEN']:
            return jsonify({'error':'Token inválido ou ausente'}), 401
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
    if 'file' not in request.files: return jsonify({'error':'Arquivo não fornecido'}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({'error':'Arquivo vazio'}), 400
    if not file.filename.lower().endswith('.xlsx'): return jsonify({'error':'Apenas XLSX'}), 400
    try:
        data = _parse_xlsx(file)
        ant = data.get('stats_anterior', {})
        diff_info = {}
        if ant:
            diff_info = {
                'vencidos_delta':  data['stats']['vencidos']  - ant.get('vencidos', 0),
                'cumpridos_delta': data['stats']['cumpridos'] - ant.get('cumpridos', 0),
                'total_delta':     data['stats']['total']     - ant.get('total', 0),
            }
        equipe_salva      = _cache.get('equipe', [])
        cumpridos_manuais = _cache.get('cumpridos_manuais', [])
        _cache.update(data)
        _cache['filename']          = file.filename
        _cache['equipe']            = equipe_salva
        _cache['cumpridos_manuais'] = cumpridos_manuais
        if cumpridos_manuais:
            _cache['vencidos'] = [v for v in _cache['vencidos'] if v['processo'] not in cumpridos_manuais]
            _cache['proximos'] = [v for v in _cache['proximos'] if v['processo'] not in cumpridos_manuais]
        _save_cache()
        return jsonify({'success':True,'stats':data['stats'],'diff':diff_info,'filename':file.filename}), 200
    except KeyError as e:
        return jsonify({'error':f'Aba não encontrada: {e}. Use "Prazos 2026".'}), 422
    except Exception as e:
        return jsonify({'error':str(e)}), 500

@bp.route('/api/dashboard', methods=['GET'])
@token_required
def get_dashboard():
    if not _cache: return jsonify({'sem_dados':True}), 200
    return jsonify({
        'stats':_cache.get('stats',{}),'performance':_cache.get('performance',[]),
        'filename':_cache.get('filename',''),
    })

@bp.route('/api/criticos', methods=['GET'])
@token_required
def get_criticos():
    if not _cache: return jsonify({'sem_dados':True}), 200
    resp_filtro = request.args.get('responsavel','').strip().upper()
    vencidos = _cache.get('vencidos',[])
    proximos = _cache.get('proximos',[])
    if resp_filtro:
        vencidos = [v for v in vencidos if v.get('responsavel','').upper() == resp_filtro]
        proximos = [p for p in proximos if p.get('responsavel','').upper() == resp_filtro]
    return jsonify({'vencidos':vencidos,'proximos':proximos})

@bp.route('/api/cumprido', methods=['POST'])
@token_required
def marcar_cumprido():
    data = request.get_json()
    if not data or 'processo' not in data: return jsonify({'error':'Processo obrigatório'}), 400
    proc = data['processo']
    manuais = _cache.get('cumpridos_manuais',[])
    if proc not in manuais: manuais.append(proc)
    _cache['cumpridos_manuais'] = manuais
    antes_v = len(_cache.get('vencidos',[]))
    antes_p = len(_cache.get('proximos',[]))
    _cache['vencidos'] = [v for v in _cache.get('vencidos',[]) if v['processo'] != proc]
    _cache['proximos'] = [v for v in _cache.get('proximos',[]) if v['processo'] != proc]
    removidos = (antes_v - len(_cache['vencidos'])) + (antes_p - len(_cache['proximos']))
    if removidos > 0 and 'stats' in _cache:
        s = _cache['stats']
        s['cumpridos'] = s.get('cumpridos',0) + 1
        s['vencidos']  = max(0, s.get('vencidos',0) - (antes_v - len(_cache['vencidos'])))
        s['proximos']  = max(0, s.get('proximos',0) - (antes_p - len(_cache['proximos'])))
        total = s.get('total',1)
        s['taxa'] = round(s['cumpridos']/total*100,1) if total > 0 else 0
    _save_cache()
    return jsonify({'success':True,'processo':proc})

@bp.route('/api/equipe', methods=['GET'])
@token_required
def get_equipe():
    return jsonify({'membros':_cache.get('equipe',[])})

@bp.route('/api/equipe', methods=['POST'])
@token_required
def add_membro():
    data = request.get_json()
    if not data or not data.get('nome'): return jsonify({'error':'Nome obrigatório'}), 400
    equipe = _cache.get('equipe',[])
    membro = {
        'id': int(datetime.now().timestamp()*1000),
        'nome':     data.get('nome','').strip(),
        'funcao':   data.get('funcao',''),
        'email':    data.get('email','').strip(),
        'whatsapp': data.get('whatsapp','').strip(),
    }
    equipe.append(membro)
    _cache['equipe'] = equipe
    _save_cache()
    return jsonify({'success':True,'membro':membro}), 201

@bp.route('/api/equipe/<int:membro_id>', methods=['PUT'])
@token_required
def update_membro(membro_id):
    data = request.get_json()
    equipe = _cache.get('equipe',[])
    for m in equipe:
        if m.get('id') == membro_id:
            m.update({k:v for k,v in data.items() if k != 'id'})
            _cache['equipe'] = equipe
            _save_cache()
            return jsonify({'success':True,'membro':m})
    return jsonify({'error':'Não encontrado'}), 404

@bp.route('/api/equipe/<int:membro_id>', methods=['DELETE'])
@token_required
def delete_membro(membro_id):
    equipe = _cache.get('equipe',[])
    nova = [m for m in equipe if m.get('id') != membro_id]
    if len(nova) == len(equipe): return jsonify({'error':'Não encontrado'}), 404
    _cache['equipe'] = nova
    _save_cache()
    return jsonify({'success':True})

@bp.route('/robots.txt', methods=['GET'])
def robots():
    return 'User-agent: *\nDisallow: /', 200, {'Content-Type':'text/plain'}

@bp.after_request
def add_security_headers(response):
    response.headers['X-Robots-Tag']         = 'noindex, nofollow'
    response.headers['X-Content-Type-Options']= 'nosniff'
    response.headers['X-Frame-Options']       = 'DENY'
    return response
