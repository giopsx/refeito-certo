"""Rotas HTTP - PGM Porto Velho - Subprocuradoria Contenciosa."""
from flask import Blueprint, render_template, request, jsonify, current_app
from functools import wraps
import os, json, requests as http
from datetime import datetime, date

bp = Blueprint('main', __name__)

# Supabase
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://vmbzykywtgzyxmoxogel.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZtYnp5a3l3dGd6eXhtb3hvZ2VsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjM3NjAyMywiZXhwIjoyMDkxOTUyMDIzfQ.fJlvsVIPLkIg5IXNx1uYfqa5pDj1B8DbRQIUiiTpcEo')

def _sb_headers():
    return {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation',
    }

def _sb_get(table, params=''):
    try:
        r = http.get(f'{SUPABASE_URL}/rest/v1/{table}?{params}', headers=_sb_headers(), timeout=10)
        return r.json() if r.ok else []
    except Exception as e:
        print(f'[SB GET] {table}: {e}')
        return []

def _sb_post(table, data):
    try:
        r = http.post(f'{SUPABASE_URL}/rest/v1/{table}', headers=_sb_headers(), json=data, timeout=10)
        result = r.json()
        return result[0] if r.ok and isinstance(result, list) and result else result
    except Exception as e:
        print(f'[SB POST] {table}: {e}')
        return {}

def _sb_patch(table, key, val, data):
    try:
        r = http.patch(f'{SUPABASE_URL}/rest/v1/{table}?{key}=eq.{val}',
                       headers=_sb_headers(), json=data, timeout=10)
        return r.ok
    except Exception as e:
        print(f'[SB PATCH] {e}')
        return False

def _sb_delete(table, key, val):
    try:
        r = http.delete(f'{SUPABASE_URL}/rest/v1/{table}?{key}=eq.{val}',
                        headers=_sb_headers(), timeout=10)
        return r.ok
    except Exception as e:
        print(f'[SB DELETE] {e}')
        return False

# Cache: Supabase dados_cache + fallback memoria
_mem = {}

def cache_get(chave):
    try:
        rows = _sb_get('dados_cache', f'chave=eq.{chave}&select=valor')
        if rows and isinstance(rows, list) and rows[0].get('valor') is not None:
            _mem[chave] = rows[0]['valor']
            return rows[0]['valor']
    except Exception:
        pass
    return _mem.get(chave)

def cache_set(chave, valor):
    _mem[chave] = valor
    try:
        h = _sb_headers()
        h['Prefer'] = 'resolution=merge-duplicates,return=minimal'
        http.post(f'{SUPABASE_URL}/rest/v1/dados_cache', headers=h,
                  json={'chave': chave, 'valor': valor,
                        'atualizado': datetime.utcnow().isoformat()}, timeout=10)
    except Exception as e:
        print(f'[CACHE SET] {chave}: {e}')

# Parse xlsx
_NAO_PESSOAS = {
    'SPF','SPJ','SPMA','GEC','AMBIENTAL','FISCAL','COMCEP','VERIFICAR','-',
    'Sem responsavel','GABINETE ACOMPANHANDO','CARTORIO/GABINETE','DISTRIBUIR',
    'MANIFESTACAO DESNECESSARIA','PREJUDICADO','',
}
_NAO_PESSOAS_PREFIXOS = ('DEVOLVIDO','ESCRITORIO','GABINETE','F704')
_NORMALIZAR = {'ERICA':'ERICA','JEFERSON':'JEFFERSON'}

def _norm(nome):
    return _NORMALIZAR.get(nome.upper(), nome.upper()) if nome else ''

def _eh_pessoa(nome):
    if not nome or nome in _NAO_PESSOAS: return False
    if nome.startswith(_NAO_PESSOAS_PREFIXOS): return False
    if nome.count('.') >= 3 and nome.count('-') >= 1: return False
    if any(c.isdigit() for c in nome): return False
    if '/' in nome or '&' in nome or '\n' in nome: return False
    return True

def _parse_xlsx(file_obj, inativos=None):
    import openpyxl, warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        wb = openpyxl.load_workbook(file_obj, read_only=True, data_only=True)
    today = date.today()
    ws = wb['Prazos 2026']
    perf = {}
    prox, venc = [], []
    total = venc_nc = prox_count = cumpr = 0
    manuais = cache_get('cumpridos_manuais') or []

    cumpridos_lista = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in row): continue
        if row[0] is None and row[1] is None and row[2] is None: continue
        prazo_raw = row[1]
        resp  = _norm(str(row[2]).strip() if row[2] else '')
        if not resp: resp = 'Sem responsavel'
        proc  = str(row[4]).strip() if row[4] else ''
        parte = str(row[5]).strip()[:60] if row[5] else ''
        vara  = str(row[6]).strip() if row[6] else ''
        cumpr_val = str(row[13]).strip().upper() if row[13] else ''
        prazo_d = None
        if isinstance(prazo_raw, datetime): prazo_d = prazo_raw.date()
        elif isinstance(prazo_raw, date):   prazo_d = prazo_raw
        if not prazo_d: continue
        total += 1
        prazo_str = prazo_d.strftime('%d/%m/%Y')
        ja_cumprido = cumpr_val in ('SIM','PARCIAL','PREJUDICADO') or proc in manuais
        if ja_cumprido:
            cumpr += 1
            prazo_str2 = prazo_d.strftime('%d/%m/%Y') if prazo_d else ''
            cumpridos_lista.append({'processo':proc,'parte':parte,'responsavel':resp,'prazo':prazo_str2,'vara':vara})
        diff = (prazo_d - today).days
        if not ja_cumprido:
            entry = {'processo':proc,'parte':parte,'responsavel':resp,
                     'prazo':prazo_str,'dias':abs(int(diff)),'vara':vara}
            if diff < 0:   venc_nc += 1; venc.append(entry)
            elif diff <= 7: prox_count += 1; prox.append(entry)
        if resp not in perf: perf[resp] = {'total':0,'cumpridos':0,'criticos':0}
        perf[resp]['total'] += 1
        if ja_cumprido: perf[resp]['cumpridos'] += 1
        if not ja_cumprido and diff < 0: perf[resp]['criticos'] += 1

    taxa = round(cumpr/total*100,1) if total > 0 else 0
    # Filtrar inativos da performance
    inativos_upper = set(n.upper() for n in (inativos or []))

    perf_list = []
    for r2, d in sorted(perf.items()):
        if not _eh_pessoa(r2): continue
        if r2.upper() in inativos_upper: continue  # ocultar inativos
        t, c = d['total'], d['cumpridos']
        perf_list.append({'responsavel':r2,'total':t,'cumpridos':c,
                          'taxa':round(c/t*100,1) if t>0 else 0,'criticos':d['criticos']})
    perf_list.sort(key=lambda x: x['taxa'], reverse=True)
    prox.sort(key=lambda x: x['dias'])
    venc.sort(key=lambda x: x['dias'], reverse=True)
    return {
        'stats': {'total':total,'vencidos':venc_nc,'proximos':prox_count,
                  'cumpridos':cumpr,'taxa':taxa,
                  'ultima_atualizacao':today.strftime('%d/%m/%Y')},
        'performance': perf_list,
        'proximos': prox,
        'vencidos': venc,
        'cumpridos_lista': cumpridos_lista,
    }

# Auth
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = (request.args.get('token') or
                 request.headers.get('Authorization','').replace('Bearer ',''))
        if not token or token != current_app.config['ACCESS_TOKEN']:
            return jsonify({'error':'Token invalido'}), 401
        return f(*args, **kwargs)
    return decorated

# Rotas
@bp.route('/')
def index():
    from flask import redirect, url_for
    return redirect(url_for('main.painel', token=current_app.config['ACCESS_TOKEN']))

@bp.route('/painel')
@token_required
def painel():
    return render_template('dashboard.html')

@bp.route('/api/upload', methods=['POST'])
@token_required
def upload_file():
    if 'file' not in request.files: return jsonify({'error':'Arquivo nao fornecido'}), 400
    file = request.files['file']
    if not file.filename.lower().endswith('.xlsx'): return jsonify({'error':'Apenas XLSX'}), 400
    try:
        # Buscar servidores inativos do Supabase
        membros_raw = _sb_get('equipe', 'select=nome,ativo')
        inativos = [m['nome'] for m in membros_raw if isinstance(m, dict) and m.get('ativo') is False]
        data = _parse_xlsx(file, inativos=inativos)
        stats_ant = cache_get('stats') or {}
        diff_info = {}
        if stats_ant:
            diff_info = {
                'vencidos_delta':  data['stats']['vencidos']  - stats_ant.get('vencidos', 0),
                'cumpridos_delta': data['stats']['cumpridos'] - stats_ant.get('cumpridos', 0),
                'total_delta':     data['stats']['total']     - stats_ant.get('total', 0),
            }
        cache_set('stats',           data['stats'])
        cache_set('performance',     data['performance'])
        cache_set('proximos',        data['proximos'])
        cache_set('vencidos',        data['vencidos'])
        cache_set('cumpridos_lista', data['cumpridos_lista'])
        cache_set('filename',        file.filename)
        return jsonify({'success':True,'stats':data['stats'],'diff':diff_info,'filename':file.filename})
    except KeyError as e:
        return jsonify({'error':f'Aba nao encontrada: {e}. Use "Prazos 2026".'}), 422
    except Exception as e:
        return jsonify({'error':str(e)}), 500

@bp.route('/api/dashboard')
@token_required
def get_dashboard():
    stats = cache_get('stats')
    if not stats: return jsonify({'sem_dados':True})
    perf = cache_get('performance') or []
    # Mostrar APENAS servidores cadastrados na equipe E ativos
    try:
        membros_raw = _sb_get('equipe', 'select=nome,ativo')
        if membros_raw:
            ativos = set(
                m['nome'].upper() for m in membros_raw
                if isinstance(m, dict) and m.get('ativo') is not False
            )
            perf = [p for p in perf if p.get('responsavel','').upper() in ativos]
    except Exception:
        pass
    return jsonify({'stats':stats,'performance':perf,
                    'filename':cache_get('filename') or ''})

@bp.route('/api/criticos')
@token_required
def get_criticos():
    from datetime import datetime
    hoje = date.today()

    # Recalcular dias dinamicamente baseado na data atual
    todos_proximos = cache_get('proximos') or []
    todos_vencidos = cache_get('vencidos') or []

    proximos_atualizados = []
    vencidos_atualizados = []

    # Reprocessar proximos (podem ter vencido desde a importacao)
    for p in todos_proximos:
        try:
            prazo_d = datetime.strptime(p['prazo'], '%d/%m/%Y').date()
            diff = (prazo_d - hoje).days
            entry = dict(p)
            entry['dias'] = abs(diff)
            if diff < 0:
                # Virou vencido depois da importacao
                vencidos_atualizados.append(entry)
            elif diff <= 7:
                proximos_atualizados.append(entry)
        except Exception:
            proximos_atualizados.append(p)

    # Reprocessar vencidos (atualizar quantos dias vencido)
    for v in todos_vencidos:
        try:
            prazo_d = datetime.strptime(v['prazo'], '%d/%m/%Y').date()
            diff = (prazo_d - hoje).days
            entry = dict(v)
            entry['dias'] = abs(diff)
            vencidos_atualizados.append(entry)
        except Exception:
            vencidos_atualizados.append(v)

    # Ordenar
    proximos_atualizados.sort(key=lambda x: x['dias'])
    vencidos_atualizados.sort(key=lambda x: x['dias'], reverse=True)

    f = request.args.get('responsavel','').strip().upper()
    if f:
        proximos_atualizados = [p for p in proximos_atualizados if p.get('responsavel','').upper()==f]
        vencidos_atualizados = [v for v in vencidos_atualizados if v.get('responsavel','').upper()==f]

    return jsonify({'vencidos': vencidos_atualizados, 'proximos': proximos_atualizados})

@bp.route('/api/cumpridos')
@token_required
def get_cumpridos():
    lista = cache_get('cumpridos_lista') or []
    resp_filtro = request.args.get('responsavel','').strip().upper()
    if resp_filtro:
        lista = [c for c in lista if c.get('responsavel','').upper() == resp_filtro]
    return jsonify({'cumpridos': lista})

@bp.route('/api/cumprido', methods=['POST'])
@token_required
def marcar_cumprido():
    data = request.get_json()
    if not data or 'processo' not in data: return jsonify({'error':'Processo obrigatorio'}), 400
    proc = data['processo']
    manuais = cache_get('cumpridos_manuais') or []
    if proc not in manuais: manuais.append(proc)
    cache_set('cumpridos_manuais', manuais)
    vencidos = [v for v in (cache_get('vencidos') or []) if v['processo'] != proc]
    proximos = [p for p in (cache_get('proximos') or []) if p['processo'] != proc]
    cache_set('vencidos', vencidos)
    cache_set('proximos', proximos)
    stats = cache_get('stats') or {}
    if stats:
        stats['cumpridos'] = stats.get('cumpridos',0) + 1
        stats['vencidos']  = len(vencidos)
        stats['proximos']  = len(proximos)
        t = stats.get('total',1)
        stats['taxa'] = round(stats['cumpridos']/t*100,1) if t>0 else 0
        cache_set('stats', stats)
    return jsonify({'success':True})

# Equipe via Supabase
@bp.route('/api/equipe')
@token_required
def get_equipe():
    membros = _sb_get('equipe', 'select=id,nome,funcao,email,whatsapp,ativo&order=id.asc')
    return jsonify({'membros': membros if isinstance(membros, list) else []})

@bp.route('/api/equipe', methods=['POST'])
@token_required
def add_membro():
    data = request.get_json()
    if not data or not data.get('nome'): return jsonify({'error':'Nome obrigatorio'}), 400
    result = _sb_post('equipe', {
        'nome':data.get('nome','').strip(), 'funcao':data.get('funcao',''),
        'email':data.get('email','').strip(), 'whatsapp':data.get('whatsapp','').strip()
    })
    if result and isinstance(result, dict) and 'id' in result:
        return jsonify({'success':True,'membro':result}), 201
    return jsonify({'error':'Falha ao salvar'}), 500

@bp.route('/api/equipe/<int:mid>', methods=['PUT'])
@token_required
def update_membro(mid):
    data = request.get_json()
    campos = {k:v for k,v in data.items() if k in ('nome','funcao','email','whatsapp','ativo')}
    ok = _sb_patch('equipe','id',mid,campos)
    return jsonify({'success':ok}) if ok else (jsonify({'error':'Nao encontrado'}),404)

@bp.route('/api/equipe/<int:mid>', methods=['DELETE'])
@token_required
def delete_membro(mid):
    ok = _sb_delete('equipe','id',mid)
    return jsonify({'success':ok}) if ok else (jsonify({'error':'Nao encontrado'}),404)

@bp.route('/robots.txt')
def robots():
    return 'User-agent: *\nDisallow: /', 200, {'Content-Type':'text/plain'}

@bp.after_request
def security(response):
    response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    return response
