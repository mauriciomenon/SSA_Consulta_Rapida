from __future__ import annotations

import sqlite3
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from armazenamento import database
from core import app_logic
from core.app_logic import filter_dataframe, get_filtered_data, parse_search_terms
from core.search_filter import apply_general_search_terms
from gui.mixins import filter_gui_ssa_mixin as filter_mixin
from gui.ssa.search_refinement import can_reuse_refined_search
from interface.table_printer import pretty_print_df


def _get_project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _allow_tmp_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from utils import path_safety

    monkeypatch.setattr(
        path_safety,
        "ALLOWED_ROOTS",
        list(path_safety.ALLOWED_ROOTS) + [tmp_path],
    )


def _init_runtime_ssa_db(db_path: Path) -> None:
    schema_path = _get_project_root() / "config" / "schema.sql"
    assert database.initialize_database(str(db_path), str(schema_path)) is True


def _build_import_df(
    *,
    numero_ssa: str,
    situacao: str,
    setor_executor: str,
    data_cadastro: str,
    descricao_ssa: str,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "numero_ssa": numero_ssa,
                "situacao": situacao,
                "setor_executor": setor_executor,
                "data_cadastro": data_cadastro,
                "descricao_ssa": descricao_ssa,
            }
        ]
    )


def _fake_extract_transition(file_path: str, should_cancel=None):
    _ = should_cancel
    marker = Path(file_path).read_text(encoding="utf-8")
    if marker == "old":
        return _build_import_df(
            numero_ssa="202500001",
            situacao="ADM",
            setor_executor="AAA1",
            data_cadastro="2025-01-01 00:00:00",
            descricao_ssa="SSA antiga",
        )
    return _build_import_df(
        numero_ssa="202500001",
        situacao="STE",
        setor_executor="BBB2",
        data_cadastro="2025-01-02 00:00:00",
        descricao_ssa="SSA atualizada",
    )


def test_search_refinement_reuses_only_safe_simple_terms() -> None:
    assert can_reuse_refined_search(["abc"], ["abcd"]) is True
    assert can_reuse_refined_search(["abc"], ["abc", "extra"]) is True
    assert can_reuse_refined_search(["=abc"], ["=abc"]) is True
    assert can_reuse_refined_search(["=abc"], ["abcd"]) is False
    assert can_reuse_refined_search(["abc"], ["!abcd"]) is False
    assert can_reuse_refined_search(["~abc"], ["~abcd"]) is False


def test_run_importer_logic_accepts_external_root_but_returns_false_without_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from utils import path_safety

    project_root = tmp_path / "project"
    docs_dir = project_root / "docs_entrada"
    docs_dir.mkdir(parents=True)
    external_data_dir = tmp_path / "selected_db"
    external_data_dir.mkdir()

    monkeypatch.setattr(path_safety, "ALLOWED_ROOTS", [project_root])
    monkeypatch.setattr(app_logic, "project_root_path", project_root)

    with pytest.raises(path_safety.PathSafetyError):
        app_logic.run_importer_logic(
            docs_dir=str(docs_dir),
            data_dir=str(external_data_dir),
            db_name="custom.sqlite",
            force_import=False,
        )

    result = app_logic.run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(external_data_dir),
        db_name="custom.sqlite",
        force_import=False,
        extra_allowed_roots=(external_data_dir,),
    )

    assert result is False


def _prepare_import_update_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path, Path]:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "test.db"

    _allow_tmp_path(monkeypatch, tmp_path)
    _init_runtime_ssa_db(db_path)
    monkeypatch.setattr(
        app_logic,
        "_discover_derivadas_sheet_files",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        app_logic,
        "_run_derivadas_sync_phase",
        lambda *args, **kwargs: (True, [], {"db_stats": {}, "merge_stats": {}}),
    )
    monkeypatch.setattr(
        app_logic.extractor,
        "extract_data_from_excel",
        _fake_extract_transition,
    )
    return docs_dir, data_dir, db_path


def _write_real_ssa_excel(
    file_path: Path,
    *,
    numero_ssa: str,
    situacao: str,
    setor_executor: str,
    data_cadastro: str,
    descricao_ssa: str,
) -> None:
    df = pd.DataFrame(
        [
            {
                "Numero SSA": numero_ssa,
                "Situacao": situacao,
                "Setor Executor": setor_executor,
                "Emitida Em": data_cadastro,
                "Descricao": descricao_ssa,
            }
        ]
    )
    df.to_excel(file_path, index=False)


def test_filter_dataframe_preserves_group_or_for_preparsed_terms() -> None:
    df = pd.DataFrame(
        {
            "descricao_ssa": [
                "motor mel4",
                "bomba iee3",
                "valvula geral",
            ]
        }
    )

    terms = [
        {"mode": "contains", "value": "mel4", "negative": False, "group": 0},
        {"mode": "contains", "value": "iee3", "negative": False, "group": 1},
    ]

    out = filter_dataframe(df, terms, ["descricao_ssa"])

    assert len(out) == 2
    assert set(out["descricao_ssa"]) == {"motor mel4", "bomba iee3"}


def test_filter_dataframe_raw_term_modes_match_any_searchable_field() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002", "202500003"],
            "descricao_ssa": ["admin area", "motor mel4", "fechado 2025"],
        }
    )

    out_prefix = filter_dataframe(df, ["^admin"], ["numero_ssa", "descricao_ssa"])
    out_exact = filter_dataframe(df, ["=motor mel4"], ["numero_ssa", "descricao_ssa"])
    out_suffix = filter_dataframe(df, ["2025$"], ["numero_ssa", "descricao_ssa"])

    assert set(out_prefix["numero_ssa"]) == {"202500001"}
    assert set(out_exact["numero_ssa"]) == {"202500002"}
    assert set(out_suffix["numero_ssa"]) == {"202500003"}


def test_apply_general_search_terms_unions_chunks_and_preserves_index() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002", "202500003"],
            "descricao_ssa": ["motor mel4", "bomba iee3", "valvula geral"],
        },
        index=[10, 20, 30],
    )

    out = apply_general_search_terms(
        df,
        [["mel4"], ["iee3"]],
        default_mode="contains",
        general_search_columns=["descricao_ssa"],
    )

    assert list(out.index) == [10, 20]
    assert list(out["numero_ssa"]) == ["202500001", "202500002"]


def test_filter_dataframe_search_columns_support_numeric_dtype() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": [202604849, 202604850],
            "descricao_ssa": ["SVP-03", "SVP-04"],
        }
    )

    out = filter_dataframe(df, ["202604849"], ["numero_ssa"])

    assert list(out["numero_ssa"]) == [202604849]


def test_filter_dataframe_search_columns_support_datetime_dtype() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002"],
            "data_cadastro": pd.to_datetime(["2026-03-31 10:15:00", None]),
        }
    )

    out = filter_dataframe(df, ["2026-03-31"], ["data_cadastro"])

    assert list(out["numero_ssa"]) == ["202500001"]


def test_get_filtered_data_reads_canonical_table_without_legacy_view(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ssa_canonica.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE ssa_table (
            numero_ssa TEXT,
            situacao TEXT,
            descricao_ssa TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO ssa_table (numero_ssa, situacao, descricao_ssa) VALUES (?, ?, ?)",
        ("202500001", "STE", "SSA canonica"),
    )
    conn.commit()
    conn.close()

    out = get_filtered_data(str(db_path))

    assert len(out) == 1
    assert out.iloc[0]["numero_ssa"] == "202500001"
    assert out.iloc[0]["descricao_ssa"] == "SSA canonica"


def test_get_filtered_data_returns_empty_on_database_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "ssa_error.sqlite"
    db_path.write_text("", encoding="utf-8")
    _allow_tmp_path(monkeypatch, tmp_path)

    def _explode(*_args, **_kwargs):
        raise sqlite3.OperationalError("forced db failure")

    monkeypatch.setattr(database, "query_db", _explode)

    out = get_filtered_data(str(db_path))

    assert out.empty


def test_get_filtered_data_ignores_unknown_filter_columns(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "ssa_unknown_filter.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE ssa_table (
            numero_ssa TEXT,
            situacao TEXT,
            segredo_interno TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO ssa_table (numero_ssa, situacao, segredo_interno) VALUES (?, ?, ?)",
        ("202500001", "STE", "bloquear"),
    )
    conn.commit()
    conn.close()

    out = get_filtered_data(str(db_path), filters={"segredo_interno": "bloquear"})

    assert len(out) == 1


def test_filter_dataframe_default_search_columns_match_solicitante_and_setor_executor() -> (
    None
):
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002"],
            "solicitante": ["danilo", "maria"],
            "setor_executor": ["MEL4", "MEL3"],
        }
    )

    out = filter_dataframe(df, ["danilo", "mel4"])

    assert list(out["numero_ssa"]) == ["202500001"]


def test_filter_dataframe_default_search_columns_match_responsavel_execucao_and_setor_executor() -> (
    None
):
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002"],
            "responsavel_execucao": ["danilo", "maria"],
            "setor_executor": ["MEL4", "MEL3"],
        }
    )

    out = filter_dataframe(df, ["danilo", "mel4"])

    assert list(out["numero_ssa"]) == ["202500001"]


def test_filter_dataframe_default_search_columns_require_terms_in_same_row() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002"],
            "solicitante": ["danilo", "maria"],
            "setor_executor": ["MEL3", "MEL4"],
        }
    )

    out = filter_dataframe(df, ["danilo", "mel4"])

    assert out.empty


def test_filter_dataframe_default_search_columns_allow_terms_in_different_columns_same_row() -> (
    None
):
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002"],
            "solicitante": ["danilo", "maria"],
            "responsavel_execucao": ["carlos", "joao"],
            "setor_executor": ["MEL4", "MEL3"],
        }
    )

    out = filter_dataframe(df, ["danilo", "mel4"])

    assert list(out["numero_ssa"]) == ["202500001"]


def test_filter_dataframe_default_search_columns_include_localizacao_fields() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002"],
            "descricao_ssa": ["Painel principal", "Motor auxiliar"],
            "localizacao_codigo": ["A006R001", "B010R002"],
            "descricao_localizacao": ["UTR [SVP-06]", "Area geral"],
        }
    )

    out_codigo = filter_dataframe(df, ["r001"])
    out_descricao = filter_dataframe(df, ["svp-06"])

    assert list(out_codigo["numero_ssa"]) == ["202500001"]
    assert list(out_descricao["numero_ssa"]) == ["202500001"]


def test_filter_dataframe_default_search_columns_allow_same_row_match_with_localizacao() -> (
    None
):
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002", "202500003"],
            "descricao_ssa": [
                "Comissionamento painel SVP-15",
                "Manutencao geral",
                "Revisao eletrica SVP-15",
            ],
            "localizacao_codigo": ["B015R001", "X001", "C100"],
            "descricao_localizacao": [
                "UTR 615",
                "Sala auxiliar",
                "Painel local",
            ],
        }
    )

    out = filter_dataframe(df, ["SVP", "R001"])

    assert list(out["numero_ssa"]) == ["202500001"]


def test_build_gui_general_search_columns_include_priority_week_and_related_fields() -> (
    None
):
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001"],
            "situacao": ["APV"],
            "derivada_de": ["202400001"],
            "localizacao_codigo": ["A006R001"],
            "descricao_localizacao": ["UTR [SVP-06]"],
            "grau_prioridade_emissao": [3],
            "grau_prioridade_planejamento": [2],
            "semana_cadastro": [202501],
            "semana_programada": [202503],
            "semana_executada": [202505],
            "numero_ssa_relacionada_1": ["202500999"],
            "relacao": ["DERIVADA"],
            "data_cadastro": ["2025-01-01"],
            "data_planilha": ["2025-01-02"],
            "tempo_total": ["05:00"],
        }
    )

    columns = filter_mixin.build_gui_general_search_columns(df)

    assert "grau_prioridade_emissao" in columns
    assert "grau_prioridade_planejamento" in columns
    assert "semana_cadastro" in columns
    assert "semana_programada" in columns
    assert "semana_executada" in columns
    assert "numero_ssa_relacionada_1" in columns
    assert "relacao" in columns
    assert "data_cadastro" not in columns
    assert "data_planilha" not in columns
    assert "tempo_total" not in columns


def test_build_gui_general_search_columns_auto_include_new_text_columns_only() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001"],
            "descricao_ssa": ["Painel principal"],
            "coluna_textual_nova": pd.Series(["Observacao nova"], dtype="string"),
            "data_extra": ["2025-01-01"],
            "sn_extra": ["ABC123"],
        }
    )

    columns = filter_mixin.build_gui_general_search_columns(df)

    assert "coluna_textual_nova" in columns
    assert "data_extra" not in columns
    assert "sn_extra" not in columns


def test_filter_dataframe_with_gui_general_search_columns_matches_week_and_priority() -> (
    None
):
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002"],
            "descricao_ssa": ["Painel A", "Painel B"],
            "grau_prioridade_emissao": [3, 1],
            "semana_programada": [202512, 202510],
            "data_cadastro": ["2025-01-01", "2025-01-02"],
        }
    )

    search_columns = filter_mixin.build_gui_general_search_columns(df)
    out = filter_dataframe(df, ["3", "202512"], search_columns=search_columns)

    assert list(out["numero_ssa"]) == ["202500001"]


def test_parse_search_terms_keeps_literals_and_does_not_parse_logical_keywords() -> (
    None
):
    terms = parse_search_terms(["svp", "OU", "mel4"])

    assert [term["value"] for term in terms] == ["svp", "OU", "mel4"]
    assert {term["group"] for term in terms} == {0}


def test_filter_dataframe_general_search_keeps_svp_literal_and_ste_negative() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002", "202500003"],
            "solicitante": ["danilo", "danilo", "danilo"],
            "setor_executor": ["svp mel4", "S/P mel4", "svp mel4"],
            "situacao": ["ADM", "ADM", "STE"],
        }
    )

    out = filter_dataframe(df, ["danilo", "svp", "mel4", "!STE"])

    assert list(out["numero_ssa"]) == ["202500001"]


def test_parse_search_terms_rejects_dataframe_input_without_ambiguous_error() -> None:
    search_df = pd.DataFrame({"termo": ["adm"]})
    parsed = parse_search_terms(search_df)
    assert parsed == []


def test_filter_dataframe_invalid_search_terms_dataframe_returns_unfiltered() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002"],
            "descricao_ssa": ["ADM equipe", "STE equipe"],
        }
    )
    invalid_search_terms = pd.DataFrame({"termo": ["adm"]})
    out = filter_dataframe(df, invalid_search_terms)
    assert list(out["numero_ssa"]) == ["202500001", "202500002"]


def test_filter_dataframe_rebuilds_search_cache_for_refined_subset() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002", "202500003"],
            "descricao_ssa": ["SVP-04 MEL4", "SVP-08 MEL3", "MEL4 geral"],
            "setor_executor": ["MEL4", "MEL3", "MEL4"],
        }
    )

    first = filter_dataframe(df, ["svp"])

    assert "_filter_search_cache" not in first.attrs
    assert "_filter_search_token" not in first.attrs

    refined = filter_dataframe(first, ["mel4"])

    assert list(refined["numero_ssa"]) == ["202500001"]
    assert "_filter_search_cache" not in first.attrs
    assert "_filter_search_token" not in first.attrs
    assert "_filter_search_cache" not in refined.attrs
    assert "_filter_search_token" not in refined.attrs


def test_filter_dataframe_small_anchored_regex_does_not_persist_row_cache() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002", "202500003"],
            "descricao_ssa": ["SVP-04 MEL4", "SVP-08 MEL3", "MEL4 geral"],
            "setor_executor": ["MEL4", "MEL3", "IEE3"],
        }
    )
    df.attrs["ssa_data_revision"] = "regex-cache-test"

    plain = filter_dataframe(df, ["svp"], ["descricao_ssa", "setor_executor"])
    had_cache_before = "_filter_search_cache" in df.attrs

    anchored = filter_dataframe(df, ["~^mel4"], ["descricao_ssa", "setor_executor"])

    assert list(plain["numero_ssa"]) == ["202500001", "202500002"]
    assert had_cache_before is False
    assert list(anchored["numero_ssa"]) == ["202500001", "202500003"]
    assert "_filter_search_cache" not in df.attrs


def test_filter_dataframe_anchored_regex_matches_field_after_separator() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002"],
            "descricao_ssa": ["sem alvo", "sem alvo"],
            "setor_executor": ["MEL4", "IEE3"],
        }
    )
    df.attrs["ssa_data_revision"] = "anchored-field-boundary"

    out = filter_dataframe(df, ["~^IEE3$"], ["descricao_ssa", "setor_executor"])

    assert list(out["numero_ssa"]) == ["202500002"]


def test_filter_dataframe_blocks_heavy_regex_patterns() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002"],
            "descricao_ssa": ["aaaaaaaaaaaaaaaaaaaa", "motor"],
        }
    )

    out = filter_dataframe(df, ["~(a+)+$"], ["descricao_ssa"])

    assert out.empty


def test_parse_search_terms_supports_negative_regex_marker() -> None:
    terms = parse_search_terms(["!~STE"])

    assert terms == [
        {
            "raw": "!~STE",
            "mode": "regex",
            "value": "STE",
            "negative": True,
            "group": 0,
        }
    ]


def test_filter_dataframe_exact_identifier_preserves_text_suffix() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["ABC.0", "ABC"],
            "descricao_ssa": ["sufixo literal", "sem sufixo"],
        }
    )

    out = filter_dataframe(df, ["=ABC.0"], ["numero_ssa"])

    assert list(out["descricao_ssa"]) == ["sufixo literal"]


def test_filter_dataframe_regex_reflects_in_place_value_change_without_row_cache() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001"],
            "descricao_ssa": ["ADM equipe"],
        }
    )
    df.attrs["ssa_data_revision"] = "cache-revision-1"

    first = filter_dataframe(df, ["~adm"], ["descricao_ssa"])
    assert list(first["numero_ssa"]) == ["202500001"]

    df.loc[0, "descricao_ssa"] = "STE equipe"
    df.attrs["ssa_data_revision"] = "cache-revision-2"

    second = filter_dataframe(df, ["~ste"], ["descricao_ssa"])

    assert list(second["numero_ssa"]) == ["202500001"]
    assert "_filter_search_cache" not in df.attrs


def test_filter_dataframe_repeated_regex_search_has_no_row_text_side_effect() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001", "202500002", "202500003"],
            "descricao_ssa": ["MEL4 alfa", "MEL4 beta", "APG gama"],
            "setor_executor": ["IEE3", "IEE3", "MEL4"],
        }
    )

    first = filter_dataframe(df, ["~mel4"], ["descricao_ssa", "setor_executor"])
    second = filter_dataframe(df, ["~mel4"], ["descricao_ssa", "setor_executor"])

    assert list(first["numero_ssa"]) == list(second["numero_ssa"])
    assert "_filter_search_cache" not in df.attrs


def test_filter_dataframe_large_regex_search_does_not_persist_row_text() -> None:
    rows = 16000
    df = pd.DataFrame(
        {
            "numero_ssa": [f"{202500000 + i:09d}" for i in range(rows)],
            "descricao_ssa": [
                f"DESCRICAO MUITO LONGA {i:05d} " + ("A" * 180) for i in range(rows)
            ],
            "descricao_execucao": [
                f"EXECUCAO MUITO LONGA {i:05d} " + ("B" * 180) for i in range(rows)
            ],
            "arquivo_origem": [f"arquivo_{i:05d}.xlsx" for i in range(rows)],
            "descricao_localizacao": [
                f"LOC {i:05d} " + ("C" * 80) for i in range(rows)
            ],
            "setor_executor": ["MEL3" if i % 7 == 0 else "IEE3" for i in range(rows)],
            "setor_emissor": ["MEL3" if i % 11 == 0 else "IEE4" for i in range(rows)],
        }
    )

    out = filter_dataframe(df, ["~mel3"], list(df.columns))

    assert not out.empty
    assert list(out["numero_ssa"][:3]) == ["202500000", "202500007", "202500011"]
    assert "_filter_search_cache" not in df.attrs
    assert "_filter_search_cache" not in out.attrs
    assert "_filter_search_token" not in out.attrs


def test_get_filtered_data_reflects_updated_state_after_explicit_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir, _data_dir, db_path = _prepare_import_update_runtime(tmp_path, monkeypatch)
    old_file = docs_dir / "old.xlsx"
    new_file = docs_dir / "new.xlsx"
    old_file.write_text("old", encoding="utf-8")
    new_file.write_text("new", encoding="utf-8")

    assert (
        app_logic.import_explicit_files_to_database(
            [str(old_file)],
            docs_dir=str(docs_dir),
            db_path=str(db_path),
            raise_on_error=True,
        )
        is True
    )
    assert (
        app_logic.import_explicit_files_to_database(
            [str(new_file)],
            docs_dir=str(docs_dir),
            db_path=str(db_path),
            raise_on_error=True,
        )
        is True
    )

    updated = get_filtered_data(
        str(db_path),
        filters={"situacao": "STE", "setor_executor": "BBB2"},
    )
    stale = get_filtered_data(str(db_path), filters={"situacao": "ADM"})
    searched = filter_dataframe(updated, ["bbb2", "ste"])

    assert list(updated["numero_ssa"]) == ["202500001"]
    assert list(updated["descricao_ssa"]) == ["SSA atualizada"]
    assert list(updated["arquivo_origem"]) == ["new.xlsx"]
    assert stale.empty
    assert list(searched["numero_ssa"]) == ["202500001"]


def test_import_explicit_files_to_database_returns_false_on_importer_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    db_path = tmp_path / "data" / "test.db"
    db_path.parent.mkdir()
    file_path = docs_dir / "entrada.xlsx"
    file_path.write_text("x", encoding="utf-8")

    _allow_tmp_path(monkeypatch, tmp_path)
    monkeypatch.setattr(
        app_logic,
        "run_importer_logic",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            app_logic.ImporterError("forced importer failure")
        ),
    )

    ok = app_logic.import_explicit_files_to_database(
        [str(file_path)],
        docs_dir=str(docs_dir),
        db_path=str(db_path),
    )

    assert ok is False


def test_explicit_import_persists_data_planilha_iso_from_filename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir, _data_dir, db_path = _prepare_import_update_runtime(tmp_path, monkeypatch)
    dated_file = docs_dir / "Consulta SSA - 26-03-2026_0237PM.xlsx"
    dated_file.write_text("new", encoding="utf-8")

    assert (
        app_logic.import_explicit_files_to_database(
            [str(dated_file)],
            docs_dir=str(docs_dir),
            db_path=str(db_path),
            raise_on_error=True,
        )
        is True
    )

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT data_planilha FROM ssa_table WHERE numero_ssa = ?",
            ("202500001",),
        ).fetchone()

    assert row is not None
    assert row[0] == "2026-03-26T14:37:00"


def test_get_filtered_data_reflects_updated_state_after_diff_reimport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir, data_dir, db_path = _prepare_import_update_runtime(tmp_path, monkeypatch)
    tracked_file = docs_dir / "tracked.xlsx"
    tracked_file.write_text("old", encoding="utf-8")

    assert (
        app_logic.run_importer_logic(
            docs_dir=str(docs_dir),
            data_dir=str(data_dir),
            db_name="test.db",
            table_name="ssa_table",
            force_import=False,
        )
        is True
    )

    tracked_file.write_text("new", encoding="utf-8")

    assert (
        app_logic.run_importer_logic(
            docs_dir=str(docs_dir),
            data_dir=str(data_dir),
            db_name="test.db",
            table_name="ssa_table",
            force_import=False,
        )
        is True
    )

    all_rows = get_filtered_data(str(db_path))
    updated = get_filtered_data(str(db_path), filters={"situacao": "STE"})
    searched = filter_dataframe(all_rows, ["atualizada", "bbb2"])

    assert len(all_rows) == 1
    assert list(updated["numero_ssa"]) == ["202500001"]
    assert list(updated["setor_executor"]) == ["BBB2"]
    assert list(updated["arquivo_origem"]) == ["tracked.xlsx"]
    assert list(searched["numero_ssa"]) == ["202500001"]


def test_import_files_to_database_returns_false_on_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    db_path = tmp_path / "data" / "test.db"

    _allow_tmp_path(monkeypatch, tmp_path)
    monkeypatch.setattr(app_logic.os, "makedirs", lambda *_a, **_k: (_ for _ in ()).throw(OSError("forced mkdir failure")))

    ok = app_logic.import_files_to_database(str(docs_dir), str(db_path))

    assert ok is False


def test_cli_render_reflects_updated_state_after_real_excel_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "test.db"
    old_file = docs_dir / "old.xlsx"
    new_file = docs_dir / "new.xlsx"

    _allow_tmp_path(monkeypatch, tmp_path)
    _init_runtime_ssa_db(db_path)
    monkeypatch.setattr(
        app_logic,
        "_discover_derivadas_sheet_files",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        app_logic,
        "_run_derivadas_sync_phase",
        lambda *args, **kwargs: (True, [], {"db_stats": {}, "merge_stats": {}}),
    )

    _write_real_ssa_excel(
        old_file,
        numero_ssa="202500001",
        situacao="ADM",
        setor_executor="AAA1",
        data_cadastro="2025-01-01 00:00:00",
        descricao_ssa="SSA antiga real",
    )
    _write_real_ssa_excel(
        new_file,
        numero_ssa="202500001",
        situacao="STE",
        setor_executor="BBB2",
        data_cadastro="2025-01-02 00:00:00",
        descricao_ssa="SSA atualizada real",
    )

    assert (
        app_logic.import_explicit_files_to_database(
            [str(old_file), str(new_file)],
            docs_dir=str(docs_dir),
            db_path=str(db_path),
            raise_on_error=True,
        )
        is True
    )

    updated = get_filtered_data(
        str(db_path),
        filters={"situacao": "STE", "setor_executor": "BBB2"},
    )
    searched = filter_dataframe(updated, ["atualizada", "bbb2"])

    display_map = {
        "numero_ssa": "Numero SSA",
        "situacao": "Situacao",
        "setor_executor": "Executor",
        "descricao_ssa": "Descricao",
        "data_cadastro": "Data Cadastro",
        "arquivo_origem": "Arquivo",
    }
    settings = {
        "display_settings": {
            "column_visibility": {},
            "column_widths": {},
            "max_auto_scroll_pages": 1,
        },
        "user_preferences": {"auto_scroll_to_end": False},
    }

    with patch("interface.table_printer.get_terminal_size", return_value=(25, 120)):
        with patch("builtins.input", return_value="q"):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                pretty_print_df(searched, display_map, settings)
                output = mock_stdout.getvalue()

    assert list(searched["numero_ssa"]) == ["202500001"]
    assert "SSA atualizada real" in output
    assert "BBB2" in output
    assert "STE" in output
    assert "ADM" not in output
