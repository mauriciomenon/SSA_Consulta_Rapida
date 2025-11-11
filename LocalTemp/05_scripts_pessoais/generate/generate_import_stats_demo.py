"""Gera estatísticas de importação usando import_excel_robust em planilha sintética.

Cria arquivo temporário Excel com linhas válidas e inválidas e imprime o JSON
`reports/last_import_stats.json` resultante.
"""
from __future__ import annotations
import io, json, os
import pandas as pd
from utils.robust_importer import import_excel_robust


def main():
    df = pd.DataFrame({
        'Nº SSA': ['202500001', 'abc', '2025-22222', '202500002'],
        'Situação': ['S1','S2','S3','S4'],
        'Emitida Em': ['2025-09-10', '10/09/2025', '2025/09/11', '2025-09-12']
    })
    bio = io.BytesIO(); df.to_excel(bio, index=False); bio.seek(0)
    path = 'tmp_import_stats.xlsx'
    with open(path,'wb') as f: f.write(bio.getvalue())
    out, stats = import_excel_robust(path)
    print('Saida linhas:', len(out))
    print('Stats carregadas (inline):')
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    if os.path.exists('reports/last_import_stats.json'):
        print('\nArquivo reports/last_import_stats.json:')
        print(open('reports/last_import_stats.json', encoding='utf-8').read())
    else:
        print('Arquivo de stats não encontrado.')
    os.remove(path)

if __name__ == '__main__':
    main()
