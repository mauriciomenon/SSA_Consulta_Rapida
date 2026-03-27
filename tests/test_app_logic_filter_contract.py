from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from armazenamento import database
from core import app_logic
from core.app_logic import filter_dataframe, get_filtered_data, parse_search_terms


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


def _fake_extract_transition(file_path: str, should_cancel=None):  # noqa: ARG001
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

    cached_search_data = first.attrs["_filter_search_cache"]

    assert list(refined["numero_ssa"]) == ["202500001"]
    assert cached_search_data["token"][2] == len(first.index)
    assert len(cached_search_data["base_lower_df"]) == len(first.index)
    assert len(cached_search_data["row_search_text"]) == len(first.index)
    assert "_filter_search_cache" not in refined.attrs
    assert "_filter_search_token" not in refined.attrs


def test_filter_dataframe_invalidates_cache_after_in_place_value_change() -> None:
    df = pd.DataFrame(
        {
            "numero_ssa": ["202500001"],
            "descricao_ssa": ["ADM equipe"],
        }
    )

    first = filter_dataframe(df, ["adm"], ["descricao_ssa"])
    assert list(first["numero_ssa"]) == ["202500001"]
    cached_before = df.attrs["_filter_search_cache"]
    token_before = cached_before["token"]

    df.loc[0, "descricao_ssa"] = "STE equipe"

    second = filter_dataframe(df, ["ste"], ["descricao_ssa"])
    cached_after = df.attrs["_filter_search_cache"]

    assert list(second["numero_ssa"]) == ["202500001"]
    assert cached_after["token"] != token_before
    assert list(cached_after["row_search_text"]) == ["ste equipe"]


def test_get_filtered_data_reflects_updated_state_after_explicit_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir, _data_dir, db_path = _prepare_import_update_runtime(
        tmp_path, monkeypatch
    )
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


def test_get_filtered_data_reflects_updated_state_after_diff_reimport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs_dir, data_dir, db_path = _prepare_import_update_runtime(
        tmp_path, monkeypatch
    )
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
