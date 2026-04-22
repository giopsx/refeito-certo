"""Rotas HTTP - PGM Porto Velho - Subprocuradoria Contenciosa."""
from flask import Blueprint, render_template, request, jsonify, current_app
from functools import wraps
import os, json, requests as http
from datetime import datetime, date, timedelta

bp = Blueprint('main', __name__)

# Configurações do Supabase (Chaves originais do seu projeto)
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://vmbzykywtgzyxmoxogel.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZtYnp5a3l3dGd6eXhtb3hvZ2VsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjM3NjAyMywiZXhwIjoyMDkxOTUyMDIzfQ.fJlvsVIPLkIg5IXNx1uYfqa5pDj1B8DbRQIUiiTpcEo')

def _sb_headers():
    return {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation',
    }

# --- HELPERS DO SUPABASE ---

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
        res = r.json()
        return res[0] if r.ok and isinstance(res, list) and res else res
    except Exception as e:
        print(f'[SB POST] {table}: {e}')
        return {}

def _sb_upsert_bulk(table, data_list):
    try:
        h = _sb_headers()
        h['Prefer'] = 'resolution=merge-duplicates,return=minimal'
        r = http.post(f'{SUPABASE_URL}/rest/v1/{table}', headers=h, json=data_list, timeout=15)
        return r.ok
    except Exception as e:
        print(f'[SB UPSERT] {table}: {e}')
        return False

def _sb_patch(table, key, val, data):
    try:
        r = http.patch(f'{SUPABASE_URL}/rest/v1/{table}?{key}=eq.{val}', headers=_sb_headers(), json=data, timeout=10)
        return r.ok
    except Exception as e:
        print(f'[SB PATCH] {e}')
        return False

def _sb_delete(table, key, val):
    try:
        r = http.delete(f'{SUPABASE_URL}/rest/v1/{table}?{key}=eq.{val}', headers=_sb_headers(), timeout=10)
        return r.ok
    except Exception as e:
        print(f'[SB DELETE] {e}')
        return False

# --- GESTÃO DE CACHE (DADOS_CACHE) ---

def cache_get(chave):
    try:
        rows = _sb_get('dados_cache', f'chave=eq.{chave}&select=valor')
        if rows and isinstance(rows, list) and len(rows) > 0:
            return rows[0].get('valor')
    except: pass
    return None

def cache_set(chave, valor):
    try:
        h = _sb_headers()
        h['Prefer'] = 'resolution=merge-duplicates,return=minimal'
        http.post(f'{SUPABASE_URL}/rest/v1/dados_cache', headers=h,
                  json={'chave': chave, 'valor': valor, 'atualizado': datetime.utcnow().isoformat()}, timeout=10)
    except: pass

# --- LÓGICA DE PROCESSAMENTO ---

def _norm(nome):
    return str(nome).strip().upper() if nome else 'SEM RESPONSAVEL'

def _parse_xlsx(file_obj):
    import openpyxl, warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        wb = openpyxl.load_workbook(file_obj, read_only=True, data_only=True)
    
    ws = None
    for name in wb.sheetnames:
        if "Prazos" in name:
            ws = wb[name]
            break
    if not ws: raise ValueError("Aba de Prazos não encontrada.")

    today = date.today()
    perf = {}
    prox, venc, cumpridos_lista = [], [], []
    total = cumpr = 0
    
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[1] or not row[4]: continue
        
        prazo_raw = row[1]
        resp = _norm(row[2])
        proc = str(row[4]).strip()
        parte = str(row[5]).strip()[:80] if row[5] else ''
        vara = str(row[6]).strip() if row[6] else ''
        cumpr_val = str(row[13]).strip().upper() if row[13] else ''
        
        if isinstance(prazo_raw, datetime): prazo_d = prazo_raw.date()
        elif isinstance(prazo_raw, date): prazo_d = prazo_raw
        else: continue
        
        total += 1
        prazo_str = prazo_d.strftime('%d/%m/%Y')
        ja_cumprido = cumpr_val in ('SIM','PARCIAL','PREJUDICADO')
        
        entry = {'processo': proc, 'parte': parte, 'responsavel': resp, 'prazo': prazo_str, 'vara': vara}
        
        if ja_cumprido:
            cumpr += 1
            cumpridos_lista.append(entry)
        else:
            diff = (prazo_d - today).days
            entry['dias'] = abs(int(diff))
            if diff < 0: venc.append(entry)
            elif diff <= 7: prox.append(entry)
            
        if resp not in perf: perf[resp] = {'responsavel': resp, 'total': 0, 'cumpridos': 0, 'criticos': 0}
        perf[resp]['total'] += 1
        if ja_cumprido: perf[resp]['cumpridos'] += 1
        elif (prazo_d - today).days < 0: perf[resp]['criticos'] += 1

    perf_list = []
    for r in perf.values():
        r['taxa'] = round(r['cumpridos']/r['total']*100, 1) if r['total'] > 0 else 0
        perf_list.append(r)

    return {
        'stats': {'total': total, 'vencidos': len(venc), 'proximos': len(prox), 'cumpridos': cumpr, 'taxa': round(cumpr/total*100, 1) if total > 0 else 0},
        'performance': sorted(perf_list, key=lambda x: x['taxa'], reverse=True),
        'proximos': prox, 'vencidos': venc, 'cumpridos_lista': cumpridos_lista
    }

# --- AUTH ---

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.args.get('token') or request.headers.get('Authorization','').replace('Bearer ','')
        if not token or token != current_app.config['ACCESS_TOKEN']:
            return jsonify({'error':'Token invalido'}), 401
        return f(*args, **kwargs)
    return decorated

# --- ROTAS ---

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
    try:
        data = _parse_xlsx(file)
        cache_set('stats', data['stats'])
        cache_set('performance', data['performance'])
        cache_set('proximos', data['proximos'])
        cache_set('vencidos', data['vencidos'])
        cache_set('cumpridos_lista', data['cumpridos_lista'])
        cache_set('filename', file.filename)
        
        try:
            bulk = []
            for p in (data['vencidos'] + data['proximos'] + data['cumpridos_lista']):
                dt = datetime.strptime(p['prazo'], '%d/%m/%Y').date()
                bulk.append({
                    'numero_processo': p['processo'], 'parte_ativa': p['parte'], 'responsavel': p['responsavel'],
                    'data_prazo': dt.isoformat(), 'vara': p['vara'], 'status': 'cumprido' if p in data['cumpridos_lista'] else 'aberto'
                })
            _sb_upsert_bulk('prazos_processuais', bulk)
        except: pass
        return jsonify({'success': True, 'stats': data['stats'], 'filename': file.filename})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/dashboard')
@token_required
def get_dashboard():
    stats = cache_get('stats')
    perf = cache_get('performance')
    if not stats: return jsonify({'sem_dados':True})
    return jsonify({'stats': stats, 'performance': perf or [], 'filename': cache_get('filename') or ''})

@bp.route('/api/criticos')
@token_required
def get_criticos():
    vencidos = cache_get('vencidos') or []
    proximos = cache_get('proximos') or []
    if not vencidos and not proximos:
        hoje = date.today().isoformat()
        db_v = _sb_get('prazos_processuais', f'status=eq.aberto&data_prazo=lt.{hoje}')
        db_p = _sb_get('prazos_processuais', f'status=eq.aberto&data_prazo=gte.{hoje}&data_prazo=lte.{(date.today()+timedelta(days=7)).isoformat()}')
        def fmt(p):
            dt = date.fromisoformat(p['data_prazo'])
            return {'processo': p['numero_processo'], 'parte': p['parte_ativa'], 'responsavel': p['responsavel'], 'prazo': dt.strftime('%d/%m/%Y'), 'vara': p['vara'], 'dias': abs((dt - date.today()).days)}
        vencidos, proximos = [fmt(v) for v in db_v], [fmt(p) for p in db_p]
    return jsonify({'vencidos': vencidos, 'proximos': proximos})

@bp.route('/api/equipe', methods=['GET', 'POST'])
@token_required
def gerenciar_equipe():
    if request.method == 'GET':
        membros = _sb_get('equipe', 'order=id.asc')
        return jsonify({'membros': membros})
    data = request.get_json()
    res = _sb_post('equipe', data)
    return jsonify({'success': True, 'membro': res})

@bp.route('/api/equipe/<int:mid>', methods=['DELETE', 'PUT'])
@token_required
def membro_ops(mid):
    if request.method == 'DELETE':
        ok = _sb_delete('equipe', 'id', mid)
        return jsonify({'success': ok})
    data = request.get_json()
    ok = _sb_patch('equipe', 'id', mid, data)
    return jsonify({'success': ok})

@bp.route('/api/cumprido', methods=['POST'])
@token_required
def marcar_cumprido():
    data = request.get_json()
    proc = data.get('processo')
    if not proc: return jsonify({'error': 'Processo obrigatorio'}), 400
    cache_v = cache_get('vencidos') or []
    cache_p = cache_get('proximos') or []
    cache_set('vencidos', [x for x in cache_v if (x.get('processo') or x.get('proc')) != proc])
    cache_set('proximos', [x for x in cache_p if (x.get('processo') or x.get('proc')) != proc])
    ok = _sb_patch('prazos_processuais', 'numero_processo', proc, {'status': 'cumprido'})
    return jsonify({'success': ok})
