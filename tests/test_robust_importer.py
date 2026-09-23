# tests/test_robust_importer.py
"""Testes focados no importador robusto (utils.robust_importer.import_excel_robust).

Escopos cobertos:
  * Colapso de sinonimos de cabecalho.
  * Coalescencia de multiplas colunas semanticas em uma unica canonica.
  * Normalizacao e filtragem de `numero_ssa` invalidos.
  * Deduplicacao por `numero_ssa` preservando data mais recente.
  * Parsing resiliente de datas (ISO vs. dia/mes/ano) e serial numerico Excel.

Estes testes usam DataFrame sintetico em memoria para simular planilha.
"""

from __future__ import annotations

import io

import pandas as pd
import pytest

from utils.robust_importer import import_excel_robust


def _write_excel_bytes(df: pd.DataFrame) -> bytes:
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    return bio.getvalue()


def _roundtrip_import(df: pd.DataFrame, tmp_path) -> tuple[pd.DataFrame, dict]:
    content = _write_excel_bytes(df)
    file_path = tmp_path / "temp.xlsx"
    file_path.write_bytes(content)
    out_df, stats = import_excel_robust(str(file_path))
    return out_df, stats


def test_raw_mode_preserves_derivadas_columns_with_excelfile_input(tmp_path):
    file_path = tmp_path / "derivadas_raw.xlsx"
    derivadas_df = pd.DataFrame(
        {
            "parent_ssa": ["202500001", "202500001"],
            "child_ssa": ["202500002", "202500003"],
            "relation_label": ["Derivada da", "Derivada da"],
        }
    )
    other_df = pd.DataFrame({"Numero SSA": ["202500999"], "Status": ["ABERTA"]})

    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        other_df.to_excel(writer, sheet_name="Resumo", index=False)
        derivadas_df.to_excel(writer, sheet_name="Derivadas", index=False)

    with pd.ExcelFile(file_path) as workbook:
        out_df, stats = import_excel_robust(
            workbook,
            sheet_name="Derivadas",
            raw_mode=True,
            raise_on_error=True,
        )

    assert list(out_df.columns) == ["parent_ssa", "child_ssa", "relation_label"]
    assert out_df["parent_ssa"].astype(str).tolist() == ["202500001", "202500001"]
    assert out_df["child_ssa"].astype(str).tolist() == ["202500002", "202500003"]
    assert out_df["relation_label"].tolist() == ["Derivada da", "Derivada da"]
    assert stats["total_rows_in"] == 2
    assert stats["total_rows_out"] == 2
    assert stats["mapped_columns_count"] == 3


def test_raise_on_error_propagates_excel_read_failure(tmp_path):
    file_path = tmp_path / "corrupt.xlsx"
    file_path.write_bytes(b"not-a-real-workbook")

    with pytest.raises(Exception):
        import_excel_robust(str(file_path), raise_on_error=True)


def test_raise_on_error_propagates_missing_workbook(tmp_path):
    file_path = tmp_path / "missing.xlsx"

    with pytest.raises(FileNotFoundError):
        import_excel_robust(str(file_path), raise_on_error=True)


def test_import_excel_robust_rejects_size_before_read(tmp_path, monkeypatch):
    from extracao.extractor import ExtractionError
    from utils import robust_importer

    file_path = tmp_path / "large.xlsx"
    file_path.write_bytes(b"12345")
    read_called = False
    monkeypatch.setattr("extracao.extractor.MAX_XLSX_FILE_BYTES", 4)

    def _unexpected_read(*_args, **_kwargs):
        nonlocal read_called
        read_called = True
        raise AssertionError("read_excel must not run")

    monkeypatch.setattr(robust_importer.pd, "read_excel", _unexpected_read)

    with pytest.raises(ExtractionError, match="excede o limite"):
        import_excel_robust(str(file_path), raise_on_error=True)

    assert read_called is False


def test_synonym_collapse_and_coalescence(tmp_path):
    # Duas colunas que devem colapsar em 'situacao' + duas variantes para numero_ssa
    df = pd.DataFrame(
        {
            "Situa\u00e7\u00e3o": ["ABERTA", None],
            "Status": [None, "FECHADA"],  # deve preencher a lacuna da primeira
            "N\u00ba SSA": ["202500001", "202500001"],  # mesmo numero -> dedup
            "Emitida Em": ["01/09/2025", "02/09/2025"],  # segunda deve prevalecer
        }
    )
    out_df, stats = _roundtrip_import(df, tmp_path)

    # Deve restar apenas 1 linha apos deduplicacao
    assert len(out_df) == 1
    # Situacao resultante deve ser 'ABERTA' (primeira linha preencheu com merge) ou 'FECHADA'? ->
    # Coalescencia linha-a-linha antes da deduplicacao significa que a primeira linha tera 'ABERTA'
    # e a segunda linha 'FECHADA'; apos ordenar por data (02/09 > 01/09) a linha FECHADA permanece.
    assert out_df.loc[0, "situacao"] == "FECHADA"
    # Numero SSA normalizado permanece como string de 9 digitos
    assert out_df.loc[0, "numero_ssa"] == "202500001"
    # Data de cadastro canonica
    assert str(out_df.loc[0, "data_cadastro"]).startswith("2025-09-02")
    # Estatisticas coerentes
    assert stats["duplicate_rows_dropped"] == 1
    assert stats["invalid_numero_ssa_rows"] == 0


def test_date_parsing_and_serial_excel(tmp_path):
    # Serial Excel para 2025-09-10 seria calculado: vamos usar uma data aproximada.
    # Para simplificar, colocar valores variados.
    df = pd.DataFrame(
        {
            "N\u00ba SSA": ["202500010", "202500011"],
            "Emitida Em": [
                "2025-09-10",
                45500,
            ],  # primeira ISO, segunda serial excel (~2048-??) so valida se converter
        }
    )
    out_df, stats = _roundtrip_import(df, tmp_path)
    assert len(out_df) == 2
    assert all(isinstance(v, str) or v is None for v in out_df["data_cadastro"])
    assert "data_cadastro" in stats["date_parse_failures"]


def test_invalid_numero_ssa_filtered(tmp_path):
    df = pd.DataFrame(
        {
            "N\u00ba SSA": ["abc", "202511111", "2025-22222"],
            "Situa\u00e7\u00e3o": ["A", "B", "C"],
        }
    )
    out_df, stats = _roundtrip_import(df, tmp_path)
    # Apenas a linha com 202511111 e valida; 'abc' invalido e '2025-22222' rejeitado por regra de hifen repetido
    assert len(out_df) == 1
    assert out_df.loc[0, "numero_ssa"] == "202511111"
    assert stats["invalid_numero_ssa_rows"] == 2


def test_dedup_keeps_latest_date(tmp_path):
    df = pd.DataFrame(
        {
            "N\u00ba SSA": ["202500099", "202500099", "202500099"],
            "Emitida Em": ["2025-09-01", "02/09/2025", "2025-09-03"],
            "Situa\u00e7\u00e3o": ["S1", "S2", "S3"],
        }
    )
    out_df, stats = _roundtrip_import(df, tmp_path)
    assert len(out_df) == 1
    assert out_df.loc[0, "situacao"] == "S3"
    assert str(out_df.loc[0, "data_cadastro"]).startswith("2025-09-03")
    assert stats["duplicate_rows_dropped"] == 2


def test_semantic_duplicate_columns_are_resolved_before_upsert(tmp_path):
    df = pd.DataFrame(
        {
            "N\u00ba SSA": ["202500100"],
            "SN": ["RET-001"],
            "SN.1": ["INS-001"],
            "Desde": ["01/09/2025"],
            "Desde.1": ["02/09/2025"],
            "At\u00e9": ["03/09/2025"],
            "At\u00e9.1": ["04/09/2025"],
            "Emitida Em": ["01/09/2025"],
        }
    )

    out_df, _stats = _roundtrip_import(df, tmp_path)

    assert "sn_retirado" in out_df.columns
    assert "sn_instalado" in out_df.columns
    assert "desde" in out_df.columns
    assert "desde_1" in out_df.columns
    assert "ate" in out_df.columns
    assert "ate_1" in out_df.columns
    assert "sn" not in out_df.columns
    assert "sn_1" not in out_df.columns
    assert "desde.1" not in out_df.columns
    assert "ate.1" not in out_df.columns
    assert out_df.loc[0, "sn_retirado"] == "RET-001"
    assert out_df.loc[0, "sn_instalado"] == "INS-001"


def test_dotted_semantic_suffix_without_base_maps_to_known_slot(tmp_path):
    df = pd.DataFrame(
        {
            "N\u00ba SSA": ["202500101"],
            "SN.1": ["INS-ONLY"],
            "Emitida Em": ["01/09/2025"],
        }
    )

    out_df, _stats = _roundtrip_import(df, tmp_path)

    assert "sn_instalado" in out_df.columns
    assert "sn_1" not in out_df.columns
    assert out_df.loc[0, "sn_instalado"] == "INS-ONLY"


def test_related_dotted_aliases_map_to_related_canonical_columns(tmp_path):
    df = pd.DataFrame(
        [
            [
                "202500102",
                "MEL1",
                "IEE1",
                "SPG",
                "202500103",
                "MEL2",
                "IEE2",
                "STE",
                "202500104",
                "MEL3",
                "IEE3",
                "SPM",
                "01/09/2025",
            ]
        ],
        columns=[
            "N\u00famero da SSA",
            "Setor Emissor",
            "Setor Executor",
            "Situacao",
            "N\u00famero da SSA.1",
            "Setor Emissor.1",
            "Setor Executor.1",
            "Situacao.1",
            "N\u00famero da SSA.2",
            "Setor Emissor.2",
            "Setor Executor.2",
            "Situacao.2",
            "Emitida Em",
        ],
    )

    out_df, _stats = _roundtrip_import(df, tmp_path)

    for col in out_df.columns:
        assert "." not in col
    assert "numero_ssa_relacionada_1" in out_df.columns
    assert "numero_ssa_relacionada_2" in out_df.columns
    assert "setor_emissor_relacionado_1" in out_df.columns
    assert "setor_emissor_relacionado_2" in out_df.columns
    assert "setor_executor_relacionado_1" in out_df.columns
    assert "setor_executor_relacionado_2" in out_df.columns
    assert "situacao_relacionada_1" in out_df.columns
    assert "situacao_relacionada_2" in out_df.columns
    assert str(out_df.loc[0, "numero_ssa_relacionada_1"]) == "202500103"
    assert str(out_df.loc[0, "numero_ssa_relacionada_2"]) == "202500104"


def test_ssa_identifier_columns_strip_decimal_artifacts(tmp_path):
    df = pd.DataFrame(
        {
            "Numero SSA": ["202500001.0", "202500002"],
            "Derivada de": ["202400123.0", None],
            "Numero da SSA.1": ["202500777.0", "202500888.0"],
            "Numero da SSA.2": ["202500999.0", None],
            "Emitida Em": ["01/09/2025", "02/09/2025"],
        }
    )

    out_df, _stats = _roundtrip_import(df, tmp_path)

    assert out_df["numero_ssa"].tolist() == ["202500001", "202500002"]
    assert out_df["derivada_de"].tolist() == ["202400123", pd.NA]
    assert out_df["numero_ssa_relacionada_1"].tolist() == ["202500777", "202500888"]
    assert out_df["numero_ssa_relacionada_2"].tolist() == ["202500999", pd.NA]
    assert str(out_df["numero_ssa"].dtype) == "string"
    assert str(out_df["derivada_de"].dtype) == "string"
    assert str(out_df["numero_ssa_relacionada_1"].dtype) == "string"


def test_unknown_dotted_columns_never_keep_dot_suffixes(tmp_path):
    df = pd.DataFrame(
        {
            "N\u00ba SSA": ["202500105"],
            "Campo Novo.1": ["A"],
            "Campo Novo.2": ["B"],
            "Emitida Em": ["01/09/2025"],
        }
    )

    out_df, _stats = _roundtrip_import(df, tmp_path)

    for col in out_df.columns:
        assert "." not in col
    assert "campo novo_1" in out_df.columns
    assert "campo novo_2" in out_df.columns
    assert out_df.loc[0, "campo novo_1"] == "A"
    assert out_df.loc[0, "campo novo_2"] == "B"


@pytest.mark.parametrize("bad_value", [None, "", "  "])
def test_blank_numero_ssa_removed(tmp_path, bad_value):
    df = pd.DataFrame(
        {
            "N\u00ba SSA": ["202500777", bad_value],
            "Situa\u00e7\u00e3o": ["OK", "IGNORAR"],
        }
    )
    out_df, stats = _roundtrip_import(df, tmp_path)
    assert len(out_df) == 1
    assert out_df.loc[0, "numero_ssa"] == "202500777"
    assert stats["invalid_numero_ssa_rows"] == 1
