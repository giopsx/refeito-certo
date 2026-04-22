def _sb_upsert_bulk(table, data_list):
    """Insere ou atualiza múltiplos registros de uma vez no Supabase."""
    try:
        headers = _sb_headers()
        # 'resolution=merge-duplicates' faz o papel do 'ON CONFLICT DO UPDATE'
        headers['Prefer'] = 'resolution=merge-duplicates,return=minimal'
        
        r = http.post(
            f'{SUPABASE_URL}/rest/v1/{table}', 
            headers=headers, 
            json=data_list, 
            timeout=15
        )
        return r.ok
    except Exception as e:
        print(f'[SB UPSERT BULK] Erro: {e}')
        return False
