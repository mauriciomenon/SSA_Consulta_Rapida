import importlib.util
import sqlite3
from pathlib import Path

import pytest


def _load_module(module_path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _create_test_db(
    db_path: Path, rows: list[tuple[str, str, str, str, str, str]] | None = None
) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path = Path(__file__).resolve().parents[1] / "config" / "schema_unified.sql"
    if rows is None:
        data_rows = [
            ("1001", "ABERTA", "desc 1", "LOC1", "SET1", "2026-W01"),
            ("1002", "FECHADA", "desc 2", "LOC2", "SET2", "2026-W02"),
        ]
    else:
        data_rows = rows
    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema_path.read_text(encoding="utf-8"))
        conn.executemany(
            """
            INSERT INTO ssa_table (
                numero_ssa, situacao, descricao_ssa,
                localizacao_codigo, setor_executor, semana_cadastro
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            data_rows,
        )


def test_analyze_db_integrity_uses_ssa_table_and_runs(tmp_path, monkeypatch):
    db_path = tmp_path / "data" / "ssas.db"
    _create_test_db(db_path)
    monkeypatch.chdir(tmp_path)

    module = _load_module(
        Path(__file__).resolve().parents[1]
        / "scripts_manutencao"
        / "analyze_db_integrity.py",
        "analyze_db_integrity_test",
    )
    result = module.analyze_database_integrity()

    assert module.TABLE_NAME == "ssa_table"
    assert isinstance(result, dict)
    assert result["total_records"] == 2


def test_analyze_db_integrity_reports_empty_fields_as_aggregate_flag(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "data" / "ssas.db"
    _create_test_db(
        db_path,
        rows=[
            ("", "ABERTA", "desc 1", "LOC1", "SET1", "2026-W01"),
            ("1002", "FECHADA", "desc 2", "LOC2", "SET2", "2026-W02"),
        ],
    )
    monkeypatch.chdir(tmp_path)

    module = _load_module(
        Path(__file__).resolve().parents[1]
        / "scripts_manutencao"
        / "analyze_db_integrity.py",
        "analyze_db_integrity_aggregate_flag_test",
    )
    result = module.analyze_database_integrity()

    assert result["empty_fields"] is True


def test_analyze_db_integrity_handles_empty_table_without_zero_division(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "data" / "ssas.db"
    _create_test_db(db_path, rows=[])
    monkeypatch.chdir(tmp_path)

    module = _load_module(
        Path(__file__).resolve().parents[1]
        / "scripts_manutencao"
        / "analyze_db_integrity.py",
        "analyze_db_integrity_empty_table_test",
    )
    result = module.analyze_database_integrity()

    assert result["total_records"] == 0
    assert result["empty_fields"] is False


def test_analyze_db_integrity_duplicate_count_not_limited_to_top10(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "data" / "ssas.db"
    rows: list[tuple[str, str, str, str, str, str]] = []
    for idx in range(12):
        numero = f"90000{idx:04d}"
        rows.append((numero, "ABERTA", f"desc {idx}a", "LOC1", "SET1", "2026-W01"))
        rows.append((numero, "ABERTA", f"desc {idx}b", "LOC1", "SET1", "2026-W01"))
    _create_test_db(db_path, rows=rows)
    monkeypatch.chdir(tmp_path)

    module = _load_module(
        Path(__file__).resolve().parents[1]
        / "scripts_manutencao"
        / "analyze_db_integrity.py",
        "analyze_db_integrity_duplicate_count_test",
    )
    result = module.analyze_database_integrity()

    assert result["has_duplicates"] is True
    assert result["duplicate_count"] == 12


def test_analyze_db_integrity_closes_connection_when_query_fails(tmp_path, monkeypatch):
    module = _load_module(
        Path(__file__).resolve().parents[1]
        / "scripts_manutencao"
        / "analyze_db_integrity.py",
        "analyze_db_integrity_close_test",
    )
    real_connect = sqlite3.connect
    connections = []

    class TrackingConnection(sqlite3.Connection):
        closed = False

        def close(self):
            self.closed = True
            super().close()

    def _connect(*args, **kwargs):
        connection = real_connect(*args, factory=TrackingConnection, **kwargs)
        connections.append(connection)
        return connection

    def _fail_query(_conn):
        raise sqlite3.DatabaseError("forced query failure")

    monkeypatch.setattr(module.sqlite3, "connect", _connect)
    monkeypatch.setattr(module, "_get_db_path", lambda: tmp_path / "failure.db")
    monkeypatch.setattr(module, "_query_core_metrics", _fail_query)

    with pytest.raises(sqlite3.DatabaseError, match="forced query failure"):
        module.verify_database_integrity()

    assert len(connections) == 1
    assert connections[0].closed is True


def test_check_status_closes_connection_when_query_fails(tmp_path, monkeypatch):
    module = _load_module(
        Path(__file__).resolve().parents[1] / "scripts_manutencao" / "check_status.py",
        "check_status_close_test",
    )
    real_connect = sqlite3.connect
    connections = []

    class TrackingConnection(sqlite3.Connection):
        closed = False

        def close(self):
            self.closed = True
            super().close()

    def _connect(*_args, **kwargs):
        connection = real_connect(
            tmp_path / "failure.db", factory=TrackingConnection, **kwargs
        )
        connections.append(connection)
        return connection

    monkeypatch.setattr(module.sqlite3, "connect", _connect)

    with pytest.raises(sqlite3.OperationalError, match="no such table"):
        module.main()

    assert len(connections) == 1
    assert connections[0].closed is True
