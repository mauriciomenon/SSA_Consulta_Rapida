from __future__ import annotations

from pathlib import Path
import sqlite3

import pandas as pd

from scripts import import_excel_file


def test_import_excel_file_returns_2_when_file_is_missing(tmp_path: Path) -> None:
    missing_file = tmp_path / "missing.xlsx"

    result = import_excel_file.main(["--file", str(missing_file)])

    assert result == 2


def test_import_excel_file_allows_empty_dataframe_in_dry_run(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "empty.xlsx"
    source_file.write_text("payload", encoding="utf-8")
    observed = {}

    def _import_excel_robust(_file_path, *, mappings_path):
        observed["mappings_path"] = Path(mappings_path)
        return pd.DataFrame(), {"total_rows_in": 0}

    monkeypatch.setattr(import_excel_file, "import_excel_robust", _import_excel_robust)

    result = import_excel_file.main(["--file", str(source_file), "--dry-run"])

    assert result == 0
    assert observed["mappings_path"] == import_excel_file.DEFAULT_MAPPINGS_PATH


def test_import_excel_file_fails_empty_dataframe_without_dry_run(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "empty.xlsx"
    source_file.write_text("payload", encoding="utf-8")
    monkeypatch.setattr(
        import_excel_file,
        "import_excel_robust",
        lambda *_args, **_kwargs: (pd.DataFrame(), {"total_rows_in": 0}),
    )

    result = import_excel_file.main(["--file", str(source_file)])

    assert result == 4


def test_import_excel_file_rejects_invalid_table_before_extract(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "input.xlsx"
    source_file.write_text("payload", encoding="utf-8")
    monkeypatch.setattr(
        import_excel_file,
        "import_excel_robust",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("import should not run for invalid table")
        ),
    )

    result = import_excel_file.main(["--file", str(source_file), "--table", "bad;sql"])

    assert result == 2


def test_import_excel_file_preserves_insert_failure_exit_code(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "input.xlsx"
    source_file.write_text("payload", encoding="utf-8")
    monkeypatch.setattr(
        import_excel_file,
        "import_excel_robust",
        lambda *_args, **_kwargs: (
            pd.DataFrame({"numero_ssa": ["202699001"]}),
            {"total_rows_in": 1},
        ),
    )
    monkeypatch.setattr(
        import_excel_file.database,
        "insert_dataframe_to_db",
        lambda *_args, **_kwargs: False,
    )

    result = import_excel_file.main(["--file", str(source_file)])

    assert result == 3


def test_import_excel_file_reset_db_uses_unified_schema(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "input.xlsx"
    db_path = tmp_path / "ssas.db"
    source_file.write_text("payload", encoding="utf-8")
    initialized_schemas = []
    monkeypatch.setattr(
        import_excel_file,
        "import_excel_robust",
        lambda *_args, **_kwargs: (
            pd.DataFrame({"numero_ssa": ["202699001"]}),
            {"total_rows_in": 1},
        ),
    )
    monkeypatch.setattr(
        import_excel_file.database,
        "reset_database",
        lambda *_args, **_kwargs: None,
    )

    def _initialize_database(_db_path, schema_path):
        initialized_schemas.append(Path(schema_path))
        return True

    monkeypatch.setattr(
        import_excel_file.database,
        "initialize_database",
        _initialize_database,
    )
    monkeypatch.setattr(
        import_excel_file.database,
        "insert_dataframe_to_db",
        lambda *_args, **_kwargs: False,
    )

    result = import_excel_file.main(
        ["--file", str(source_file), "--db", str(db_path), "--reset-db"]
    )

    assert result == 3
    assert initialized_schemas == [import_excel_file.SCHEMA_PATH]


def test_import_excel_file_uses_scalar_count_after_insert(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "input.xlsx"
    db_path = tmp_path / "ssas.db"
    source_file.write_text("payload", encoding="utf-8")
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE ssas (numero_ssa TEXT)")
        conn.executemany(
            "INSERT INTO ssas VALUES (?)",
            [("202699001",), ("202699002",)],
        )
    monkeypatch.setattr(
        import_excel_file,
        "import_excel_robust",
        lambda *_args, **_kwargs: (
            pd.DataFrame({"numero_ssa": ["202699001"]}),
            {"total_rows_in": 1},
        ),
    )
    monkeypatch.setattr(
        import_excel_file.database,
        "insert_dataframe_to_db",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        import_excel_file.database,
        "query_db",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("query_db should not be used for row count")
        ),
    )

    result = import_excel_file.main(
        ["--file", str(source_file), "--db", str(db_path), "--table", "ssas"]
    )

    assert result == 0
