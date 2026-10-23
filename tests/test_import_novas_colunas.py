import sqlite3
from pathlib import Path

import pandas as pd

from utils import robust_importer as ri

# SC-14: banco e planilha em tmp_path, nunca em data/ do repositorio.
SCHEMA_PATH = Path(__file__).resolve().parent.parent / 'config' / 'schema_unified.sql'

SAMPLE_ROWS = [
    {
        'Numero SSA': '202500001',
        'Situação': 'STE',
        'Descrição SSA': 'Teste inclusão novas colunas',
        'Desvio': 2,
        'Justificativa sem APR': 'Justificativa X',
        'Reprogramações': 3,
        'Total Tempo TPE Executada': '1d 02:00',
        'Data Cadastro': '2025-01-02 10:00:00'
    },
    {
        'Numero SSA': '202500002',
        'Situação': 'STE',
        'Descrição SSA': 'Outra linha',
        'Desvio': 0,
        'Justificativa sem APR': '---',
        'Reprogramações': 0,
        'Total Tempo TPE Executada': '0d 05:30',
        'Data Cadastro': '2025-01-03 11:00:00'
    }
]


def setup_db(db_path):
    schema_sql = SCHEMA_PATH.read_text(encoding='utf-8')
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.executescript(schema_sql)
    con.commit()
    con.close()


def test_import_novas_colunas(tmp_path):
    db_path = tmp_path / 'ssas_test.db'
    setup_db(db_path)
    df = pd.DataFrame(SAMPLE_ROWS)
    # Salva Excel temporário para reusar pipeline completo
    temp_xlsx = tmp_path / 'temp_novas_colunas.xlsx'
    df.to_excel(temp_xlsx, index=False)
    norm_df, stats = ri.import_excel_robust(temp_xlsx)

    # Checar se colunas canônicas mapeadas existem
    for expected in ['numero_desvios', 'justificativa', 'num_reprogramacoes', 'total_tempo_tpe_executada', 'numero_ssa']:
        assert expected in norm_df.columns, f"Coluna canônica ausente: {expected} -> colunas={norm_df.columns.tolist()}"

    # Inserir só colunas existentes no schema unificado
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    schema_cols = [c[1] for c in cur.execute("PRAGMA table_info(ssa_table)").fetchall()]
    insert_df = norm_df[[c for c in norm_df.columns if c in schema_cols]].copy()
    insert_df.to_sql('ssa_table', con, if_exists='append', index=False)
    qtd = cur.execute('SELECT COUNT(*) FROM ssa_table').fetchone()[0]
    assert qtd == 2, f"Esperado 2 linhas inseridas, obtido {qtd}"
    # Verificar valores chave
    row = cur.execute("SELECT numero_ssa, numero_desvios, justificativa, num_reprogramacoes, total_tempo_tpe_executada FROM ssa_table WHERE numero_ssa='202500001'").fetchone()
    assert row is not None, 'Linha principal não encontrada.'
    assert row[1] == 2, f"numero_desvios esperado 2 obtido {row[1]}"
    assert row[2] == 'Justificativa X', f"justificativa divergente {row[2]}"
    assert row[3] == 3, f"num_reprogramacoes esperado 3 obtido {row[3]}"
    assert row[4] == '1d 02:00', f"total_tempo_tpe_executada divergente {row[4]}"
    con.close()
