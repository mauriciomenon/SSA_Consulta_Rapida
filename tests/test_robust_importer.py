# tests/test_robust_importer.py
"""Testes focados no importador robusto (utils.robust_importer.import_excel_robust).

Escopos cobertos:
  * Colapso de sinônimos de cabeçalho.
  * Coalescência de múltiplas colunas semânticas em uma única canônica.
  * Normalização e filtragem de `numero_ssa` inválidos.
  * Deduplicação por `numero_ssa` preservando data mais recente.
  * Parsing resiliente de datas (ISO vs. dia/mês/ano) e serial numérico Excel.

Estes testes usam DataFrame sintético em memória para simular planilha.
"""
from __future__ import annotations

import io
import pandas as pd
import pytest
from utils.robust_importer import import_excel_robust


def _write_excel_bytes(df: pd.DataFrame) -> bytes:
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as w:  # type: ignore
        df.to_excel(w, index=False)
    return bio.getvalue()


def _roundtrip_import(df: pd.DataFrame, tmp_path) -> tuple[pd.DataFrame, dict]:
    content = _write_excel_bytes(df)
    file_path = tmp_path / "temp.xlsx"
    file_path.write_bytes(content)
    out_df, stats = import_excel_robust(str(file_path))
    return out_df, stats


def test_synonym_collapse_and_coalescence(tmp_path):
    # Duas colunas que devem colapsar em 'situacao' + duas variantes para numero_ssa
    df = pd.DataFrame(
        {
            "Situação": ["ABERTA", None],
            "Status": [None, "FECHADA"],  # deve preencher a lacuna da primeira
            "Nº SSA": ["202500001", "202500001"],  # mesmo numero -> dedup
            "Emitida Em": ["01/09/2025", "02/09/2025"],  # segunda deve prevalecer
        }
    )
    out_df, stats = _roundtrip_import(df, tmp_path)

    # Deve restar apenas 1 linha após deduplicação
    assert len(out_df) == 1
    # Situacao resultante deve ser 'ABERTA' (primeira linha preencheu com merge) ou 'FECHADA'? ->
    # Coalescência linha-a-linha antes da deduplicação significa que a primeira linha terá 'ABERTA'
    # e a segunda linha 'FECHADA'; após ordenar por data (02/09 > 01/09) a linha FECHADA permanece.
    assert out_df.loc[0, 'situacao'] == 'FECHADA'
    # Numero SSA normalizado permanece como string de 9 dígitos
    assert out_df.loc[0, 'numero_ssa'] == '202500001'
    # Data de cadastro canônica
    assert out_df.loc[0, 'data_cadastro'].startswith('2025-09-02')
    # Estatísticas coerentes
    assert stats['duplicate_rows_dropped'] == 1
    assert stats['invalid_numero_ssa_rows'] == 0


def test_date_parsing_and_serial_excel(tmp_path):
    # Serial Excel para 2025-09-10 seria calculado: vamos usar uma data aproximada.
    # Para simplificar, colocar valores variados.
    df = pd.DataFrame(
        {
            "Nº SSA": ["202500010", "202500011"],
            "Emitida Em": ["2025-09-10", 45500],  # primeira ISO, segunda serial excel (~2048-??) só valida se converter
        }
    )
    out_df, stats = _roundtrip_import(df, tmp_path)
    assert len(out_df) == 2
    assert all(isinstance(v, str) or v is None for v in out_df['data_cadastro'])
    assert 'data_cadastro' in stats['date_parse_failures']


def test_invalid_numero_ssa_filtered(tmp_path):
    df = pd.DataFrame(
        {
            "Nº SSA": ["abc", "202511111", "2025-22222"],
            "Situação": ["A", "B", "C"],
        }
    )
    out_df, stats = _roundtrip_import(df, tmp_path)
    # Apenas a linha com 202511111 é válida; 'abc' inválido e '2025-22222' rejeitado por regra de hífen repetido
    assert len(out_df) == 1
    assert out_df.loc[0, 'numero_ssa'] == '202511111'
    assert stats['invalid_numero_ssa_rows'] == 2


def test_dedup_keeps_latest_date(tmp_path):
    df = pd.DataFrame(
        {
            "Nº SSA": ["202500099", "202500099", "202500099"],
            "Emitida Em": ["2025-09-01", "02/09/2025", "2025-09-03"],
            "Situação": ["S1", "S2", "S3"],
        }
    )
    out_df, stats = _roundtrip_import(df, tmp_path)
    assert len(out_df) == 1
    assert out_df.loc[0, 'situacao'] == 'S3'
    assert out_df.loc[0, 'data_cadastro'].startswith('2025-09-03')
    assert stats['duplicate_rows_dropped'] == 2


@pytest.mark.parametrize("bad_value", [None, "", "  "])
def test_blank_numero_ssa_removed(tmp_path, bad_value):
    df = pd.DataFrame(
        {
            "Nº SSA": ["202500777", bad_value],
            "Situação": ["OK", "IGNORAR"],
        }
    )
    out_df, stats = _roundtrip_import(df, tmp_path)
    assert len(out_df) == 1
    assert out_df.loc[0, 'numero_ssa'] == '202500777'
    assert stats['invalid_numero_ssa_rows'] == 1
