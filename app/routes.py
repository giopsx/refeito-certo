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
    'VERIFICAR', '-', 'Sem responsável', 'GABINETE ACOMPANHANDO', 'CARTORIO/GABINETE',
}
_NAO_PESSOAS_PREFIXOS = ('DEVOLVIDO', 'ESCRITORIO', 'GABINETE', 'F704')


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
        if row[0] is None:
            continue
        prazo_raw    = row[1]
        responsavel  = str(row[2]).strip() if row[2] else 'Sem responsável'
