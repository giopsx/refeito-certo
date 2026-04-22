"""Rotas HTTP - PGM Porto Velho - Subprocuradoria Contenciosa."""
from flask import Blueprint, render_template, request, jsonify, current_app
from functools import wraps
import os, json, requests as http
from datetime import datetime, date, timedelta

bp = Blueprint('main', __name__)

# Configurações do Supabase (Chaves Originais)
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://vmbzykywtgzyxmoxogel.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZtYnp5a3l3dGd6eXhtb3hvZ2VsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjM3NjAyMywiZXhwIjoyMDkxOTUyMDIzfQ.fJlvsVIPLkIg5IXNx1uYfqa5pDj1B8DbRQIUiiTpcEo')

def _sb_headers():
    return {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'resolution=merge-duplicates,return=representation',
    }

# --- HELPERS SUPABASE ---
def _sb_get(table, params=''):
    try:
        r = http.get(f'{SUPABASE_URL}/rest/v1/{table}?{params}', headers=_sb_headers(), timeout=10)
        return r.json() if r.ok else []
    except: return []

def _sb_post(table, data):
    try:
        r = http.post(f'{SUPABASE_URL}/rest/v1/{table}', headers=_sb_headers(), json=data, timeout=10)
        res = r.json()
        return res[0] if r.ok and isinstance(res, list) and res else res
    except: return {}

def _sb_upsert_bulk(table, data_list):
    try:
        h = _sb_headers()
        h['Prefer'] = 'resolution=merge-duplicates,return=minimal'
        r = http.post(f'{SUPABASE_URL}/rest/v1/{table}', headers=h, json=data_list, timeout=15)
        return r.ok
    except: return False

def _sb_patch(table, key, val, data):
    try:
        r = http.patch(f'{SUPABASE_URL}/rest/v1/{table}?{key}=eq.{val}', headers=_sb_headers(), json=data, timeout=10)
        return r.ok
    except: return False

# --- CACHE ---
def cache_set(chave, valor):
    try:
        h = _sb_headers()
        h['Prefer'] = 'resolution=merge-duplicates,return=minimal'
        http.post(f'{SUPABASE_URL}/rest/v1/dados_cache', headers=h,
                  json={'chave': chave, 'valor': valor, 'atualizado': datetime.utcnow().isoformat()}, timeout=10)
    except: pass

def cache_get(chave):
    try:
        rows = _sb_get('dados_cache', f'chave=eq.{chave}&select=valor')
        if rows: return rows[0].get('valor')
    except: pass
    return None

# --- PARSE XLSX ---
def _parse_xlsx(file_obj):
    import openpyxl, warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        wb = openpyxl.load_workbook(file_obj, read_only=True, data_only=True)
    
    # Procura por uma aba que contenha "Prazos" no nome
    sheet_name = None
    for name in wb.sheetnames:
        if "Prazos" in name:
            sheet_name = name
            break
    
    if not sheet_name:
        raise ValueError("Aba 'Prazos 2026' não encontrada na planilha.")

    ws = wb[sheet_name]
    today = date.today()
    processos_lista = []
    
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[1] or not row[4]: continue # Pula linhas sem data ou sem processo
        
        prazo_raw = row[1]
        resp = str(row[2]).strip().upper() if row[2] else 'SEM RESPONSAVEL'
        proc = str(row[4]).strip()
        parte = str(row[5]).strip()[:100] if row[5] else ''
        vara = str(row[6]).strip() if row[6] else ''
        cumpr_val = str(row[13]).strip().upper() if row[13] else ''
        
        if isinstance(prazo_raw, datetime): prazo_d = prazo_raw.date()
        elif isinstance(prazo_raw, date): prazo_d = prazo_raw
        else: continue
        
        status = 'cumprido' if cumpr_val in ('SIM','PARCIAL','PREJUDICADO') else 'aberto'
        
        processos_lista.append({
            'numero_processo': proc, 'parte_ativa': parte, 'responsavel': resp,
            'data_prazo': prazo_d.isoformat(), 'vara': vara, 'status': status
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
@bp.route('/api/upload', methods=['POST'])
@token_required
def upload_file():
    if 'file' not in request.files: return jsonify({'error':'Arquivo nao fornecido'}), 400
    file = request.files['file']
    try:
        processos = _parse_xlsx(file)
        hoje = date.today()
        
        # Estatísticas padrão para evitar erro de 'undefined' no JS
        stats = {
            'total': len(processos),
            'cumpridos': len([p for p in processos if p['status'] == 'cumprido']),
            'vencidos': len([p for p in processos if p['status'] == 'aberto' and date.fromisoformat(p['data_prazo']) < hoje]),
            'proximos': len([p for p in processos if p['status'] == 'aberto' and hoje <= date.fromisoformat(p['data_prazo']) <= hoje + timedelta(days=7)]),
            'ultima_atualizacao': hoje.strftime('%d/%m/%Y')
        }
        stats['taxa'] = round(stats['cumpridos']/stats['total']*100, 1) if stats['total'] > 0 else 0
        
        if processos:
            _sb_upsert_bulk('prazos_processuais', processos)
            cache_set('stats', stats)
            cache_set('filename', file.filename)
            
        return jsonify({'success': True, 'stats': stats, 'count': len(processos)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/dashboard')
@token_required
def get_dashboard():
    stats = cache_get('stats')
    return jsonify({'stats': stats or {}, 'filename': cache_get('filename') or ''})

@bp.route('/api/criticos')
@token_required
def get_criticos():
    hoje = date.today().isoformat()
    daqui_7 = (date.today() + timedelta(days=7)).isoformat()
    vencidos = _sb_get('prazos_processuais', f'status=eq.aberto&data_prazo=lt.{hoje}&order=data_prazo.asc')
    proximos = _sb_get('prazos_processuais', f'status=eq.aberto&data_prazo=gte.{hoje}&data_prazo=lte.{daqui_7}&order=data_prazo.asc')
    
    def fmt(p):
        dt = date.fromisoformat(p['data_prazo'])
        return {'processo': p['numero_processo'], 'parte': p['parte_ativa'], 'responsavel': p['responsavel'],
                'prazo': dt.strftime('%d/%m/%Y'), 'vara': p['vara'], 'dias': abs((dt - date.today()).days)}
    
    return jsonify({'vencidos': [fmt(v) for v in vencidos], 'proximos': [fmt(p) for p in proximos]})

@bp.route('/painel')
@token_required
def painel(): return render_template('dashboard.html')

@bp.route('/')
def index():
    from flask import redirect, url_for
    return redirect(url_for('main.painel', token=current_app.config['ACCESS_TOKEN']))
