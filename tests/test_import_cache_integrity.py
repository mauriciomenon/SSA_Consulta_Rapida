# tests/test_import_cache_integrity.py
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from armazenamento import database
from armazenamento.database_optimized import (
    disable_optimized_import,
    enable_optimized_import,
)
from core.app_logic import run_importer_logic
from extracao import extractor


def test_cache_not_updated_when_extraction_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    (docs_dir / "broken.xlsx").write_text("not an xlsx file", encoding="utf-8")

    data_dir = tmp_path / "data"

    # Path safety allowlist is computed at import-time. Ensure tmp_path is allowed
    # so this test is stable across platforms/pytest tempdir layouts.
    from utils import path_safety

    monkeypatch.setattr(
        path_safety,
        "ALLOWED_ROOTS",
        list(path_safety.ALLOWED_ROOTS) + [tmp_path],
    )

    updated = run_importer_logic(
        docs_dir=str(docs_dir),
        data_dir=str(data_dir),
        db_name="test.db",
        table_name="ssa_table",
        force_import=True,
    )

    assert updated is False
    assert not (data_dir / "file_cache.json").exists()


def test_force_import_orders_snapshot_files_by_embedded_datetime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs_dir = tmp_path / "docs_entrada"
    docs_dir.mkdir()
    newer = docs_dir / "Consulta SSA - 02-01-2026_1127AM.xlsx"
    older = docs_dir / "Consulta SSA - 30-12-2025_0309PM.xlsx"
    newer.write_bytes(b"fake")
    older.write_bytes(b"fake")
    data_dir = tmp_path / "data"

    from utils import path_safety

    monkeypatch.setattr(
        path_safety,
        "ALLOWED_ROOTS",
        list(path_safety.ALLOWED_ROOTS) + [tmp_path],
    )

    def fake_extract(file_path: str, should_cancel=None):  # noqa: ARG001
        setor = "STE" if Path(file_path).name == newer.name else "ADM"
        return pd.DataFrame(
            [
                {
                    "numero_ssa": "202600654",
                    "situacao": "ABERTA",
                    "data_cadastro": "01/01/2026",
                    "descricao_ssa": "ssa teste",
                    "setor_executor": setor,
                }
            ]
        )

    monkeypatch.setattr(extractor, "extract_data_from_excel", fake_extract)

    enable_optimized_import()
    try:
        updated = run_importer_logic(
            docs_dir=str(docs_dir),
            data_dir=str(data_dir),
            db_name="test.db",
            table_name="ssa_table",
            force_import=True,
        )
    finally:
        disable_optimized_import()

    assert updated is True

    with database.get_db_connection(str(data_dir / "test.db")) as conn:
        row = conn.execute(
            "SELECT numero_ssa, setor_executor, arquivo_origem FROM ssa_table WHERE numero_ssa = ?",
            ("202600654",),
        ).fetchone()

    assert row == ("202600654", "STE", newer.name)


def test_file_cache_name_is_unique_per_database_filename(tmp_path: Path) -> None:
    """Cada banco alternativo recebe cache proprio, sem colisao de stem.

    archive.db e archive.sqlite sao bancos distintos; SSAS.db e ssas.db
    tambem sao arquivos distintos em volumes case-sensitive (Linux).
    """
    from core.app_logic import _initialize_import_run_context

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    def cache_name(db_name: str) -> str:
        ctx = _initialize_import_run_context(
            docs_dir=str(docs_dir), data_dir=str(data_dir), db_name=db_name
        )
        return Path(ctx["cache_file"]).name

    assert cache_name("ssas.db") == "file_cache.json"
    assert cache_name("archive.db") == "file_cache.archive.db.json"
    assert cache_name("archive.sqlite") == "file_cache.archive.sqlite.json"
    # Case-sensitive: alias de caixa diferente nao reusa o cache canonico
    assert cache_name("SSAS.db") != "file_cache.json"
