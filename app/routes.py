"""Rotas HTTP - PGM Porto Velho - Subprocuradoria Contenciosa."""
from flask import Blueprint, render_template, request, jsonify, current_app
from functools import wraps
import os, json, requests as http
from datetime import datetime, date, timedelta

bp = Blueprint('main', __name__)

# Configurações do Supabase
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
        result = r.json()
        return result[0] if r.ok and isinstance(result, list) and result else result
    except Exception as e:
        print(f'[SB POST] {table}: {e}')
        return {}

def _sb_upsert_bulk(table, data_list):
    """Insere ou atualiza múltiplos registros de uma vez (Upsert)."""
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

# --- GESTÃO DE CACHE ---

def cache_get(chave):
    try:
        rows = _sb_get('dados_cache', f'chave=eq.{chave}&select=valor')
        if rows and isinstance(rows, list):
            return rows[0].get('valor')
    except: pass
    return None

def cache_set(chave, valor):
    try:
        h = _sb_headers()
        h['Prefer'] = 'resolution=merge-duplicates,return=minimal'
        http.post(f'{SUPABASE_URL}/rest/v1/dados_cache', headers=h,
                  json={'chave': chave, 'valor': valor, 'atualizado': datetime.utcnow().isoformat()}, timeout=10)
    except Exception as e:
        print(f'[CACHE SET] {chave}: {e}')

# --- LÓGICA DE PARSE ---

_NAO_PESSOAS = {'SPF','SPJ','SPMA','GEC','AMBIENTAL','FISCAL','COMCEP','VERIFICAR','-','Sem responsavel','DISTRIBUIR',''}
_NORMALIZAR = {'ERICA':'ERICA','JEFERSON':'JEFFERSON'}

def _norm(nome):
    return _NORMALIZAR.get(nome.upper(), nome.upper()) if nome else 'Sem responsavel'

def _parse_xlsx(file_obj):
    import openpyxl, warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        wb = openpyxl.load_workbook(file_obj, read_only=True, data_only=True)
    
    ws = wb['Prazos 2026']
    today = date.today()
    processos_lista = []
    
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not any(row): continue
        prazo_raw = row[1]
        resp = _norm(str(row[2]).strip() if row[2] else '')
        proc = str(row[4]).strip() if row[4] else ''
        parte = str(row[5]).strip()[:100] if row[5] else ''
        vara = str(row[6]).strip() if row[6] else ''
        cumpr_val = str(row[13]).strip().upper() if row[13] else ''
        
        prazo_d = None
        if isinstance(prazo_raw, datetime): prazo_d = prazo_raw.date()
        elif isinstance(prazo_raw, date): prazo_d = prazo_raw
        
        if not prazo_d or not proc: continue
        status = 'cumprido' if cumpr_val in ('SIM','PARCIAL','PREJUDICADO') else 'aberto'
        
        processos_lista.append({
            'numero_processo': proc,
            'parte_ativa': parte,
            'responsavel': resp,
            'data_prazo': prazo_d.isoformat(),
            'vara': vara,
            'status': status
        })
    return processos_lista

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
        processos = _parse_xlsx(file)
        if processos:
            _sb_upsert_bulk('prazos_processuais', processos)
            total = len(processos)
            cumpridos = len([p for p in processos if p['status'] == 'cumprido'])
            taxa = round(cumpridos/total*100, 1) if total > 0 else 0
            stats = {'total': total, 'vencidos': 0, 'proximos': 0, 'cumpridos': cumpridos, 'taxa': taxa, 'ultima_atualizacao': date.today().strftime('%d/%m/%Y')}
            cache_set('stats', stats)
            cache_set('filename', file.filename)
        return jsonify({'success': True, 'count': len(processos), 'filename': file.filename})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/dashboard')
@token_required
def get_dashboard():
    stats = cache_get('stats')
    if not stats: return jsonify({'sem_dados':True})
    return jsonify({'stats': stats, 'filename': cache_get('filename') or ''})

@bp.route('/api/criticos')
@token_required
def get_criticos():
    hoje = date.today().isoformat()
    daqui_7 = (date.today() + timedelta(days=7)).isoformat()
    vencidos = _sb_get('prazos_processuais', f'status=eq.aberto&data_prazo=lt.{hoje}&order=data_prazo.asc')
    proximos = _sb_get('prazos_processuais', f'status=eq.aberto&data_prazo=gte.{hoje}&data_prazo=lte.{daqui_7}&order=data_prazo.asc')
    
    def format_item(p):
        d_prazo = datetime.strptime(p['data_prazo'], '%Y-%m-%d').date()
        diff = (d_prazo - date.today()).days
        return {
            'processo': p['numero_processo'],
            'parte': p['parte_ativa'],
            'responsavel': p['responsavel'],
            'prazo': d_prazo.strftime('%d/%m/%Y'),
            'vara': p['vara'],
            'dias': abs(int(diff))
        }
    return jsonify({'vencidos': [format_item(v) for v in vencidos], 'proximos': [format_item(p) for p in proximos]})

@bp.route('/api/cumprido', methods=['POST'])
@token_required
def marcar_cumprido():
    data = request.get_json()
    proc = data.get('processo')
    if not proc: return jsonify({'error':'Processo obrigatorio'}), 400
    ok = _sb_patch('prazos_processuais', 'numero_processo', proc, {'status': 'cumprido'})
    return jsonify({'success': ok})

@bp.route('/api/equipe', methods=['GET', 'POST'])
@token_required
def gerenciar_equipe():
    if request.method == 'GET':
        membros = _sb_get('equipe', 'order=id.asc')
        return jsonify({'membros': membros})
    data = request.get_json()
    result = _sb_post('equipe', data)
    return jsonify({'success': True, 'membro': result})

@bp.route('/api/equipe/<int:mid>', methods=['DELETE', 'PUT'])
@token_required
def membro_ops(mid):
    if request.method == 'DELETE':
        ok = _sb_delete('equipe', 'id', mid)
        return jsonify({'success': ok})
    data = request.get_json()
    ok = _sb_patch('equipe', 'id', mid, data)
    return jsonify({'success': ok})
