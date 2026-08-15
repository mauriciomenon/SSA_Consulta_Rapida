from __future__ import annotations

import shutil

import pytest

from tests._helpers import db_utils


def test_db_utils_reject_invalid_sql_identifiers(temp_db):
    with pytest.raises(ValueError, match="Invalid SQL identifier"):
        db_utils.fetch_all(temp_db, "ssa_chamados; drop table ssa_chamados")

    with pytest.raises(ValueError, match="Invalid SQL identifier"):
        db_utils.insert_raw_rows(
            temp_db,
            "ssa_chamados",
            ["numero_ssa", "bad-column"],
            [("202600001", "x")],
        )


def test_insert_raw_rows_streams_iterable_without_materializing(tmp_path):
    schema = tmp_path / "schema.sql"
    schema.write_text(
        "CREATE TABLE items (numero_ssa TEXT);\n",
        encoding="utf-8",
    )
    db_path, tmp_dir = db_utils.create_temp_db(schema)
    consumed = []

    def _rows():
        for value in ("202600001", "202600002"):
            consumed.append(value)
            yield (value,)

    try:
        db_utils.insert_raw_rows(db_path, "items", ["numero_ssa"], _rows())

        rows = db_utils.fetch_all(db_path, "items")
        assert consumed == ["202600001", "202600002"]
        assert [row[0] for row in rows] == ["202600001", "202600002"]
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_create_temp_db_cleans_directory_when_schema_is_missing(tmp_path, monkeypatch):
    missing_schema = tmp_path / "missing.sql"
    created_dir = tmp_path / "created-db-dir"

    def _mkdtemp(prefix):
        assert prefix == "ssa_db_test_"
        created_dir.mkdir()
        return str(created_dir)

    monkeypatch.setattr(db_utils.tempfile, "mkdtemp", _mkdtemp)

    with pytest.raises(FileNotFoundError):
        db_utils.create_temp_db(missing_schema)

    assert not created_dir.exists()
