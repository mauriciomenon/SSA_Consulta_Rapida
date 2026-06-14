from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def test_import_smoke_scripts_do_not_touch_default_database(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    default_db = Path("data/ssas.db")

    detailed = importlib.import_module("tests.run_import_detailed")
    modular = importlib.import_module("tests.run_modular_import")
    quick = importlib.import_module("tests.run_quick_import")

    if default_db.exists():
        pytest.fail("Import smoke script module import touched data/ssas.db")
    for module in (detailed, modular, quick):
        if not callable(module.main):
            pytest.fail(f"{module.__name__} does not expose callable main()")


def test_import_smoke_scripts_expose_main_entrypoints():
    detailed = importlib.import_module("tests.run_import_detailed")
    modular = importlib.import_module("tests.run_modular_import")
    quick = importlib.import_module("tests.run_quick_import")

    for module in (detailed, modular, quick):
        if not callable(module.main):
            pytest.fail(f"{module.__name__} does not expose callable main()")


def test_modular_import_smoke_rejects_empty_explicit_input(tmp_path):
    modular = importlib.import_module("tests.run_modular_import")
    docs_dir = tmp_path / "docs"
    data_dir = tmp_path / "data"
    docs_dir.mkdir()

    assert modular.main(["--docs-dir", str(docs_dir), "--data-dir", str(data_dir)]) == 1


def test_detailed_import_smoke_rejects_empty_explicit_input(tmp_path):
    detailed = importlib.import_module("tests.run_import_detailed")
    docs_dir = tmp_path / "docs"
    db_path = tmp_path / "data" / "ssas.db"
    docs_dir.mkdir()

    assert detailed.main(["--docs-dir", str(docs_dir), "--db-path", str(db_path)]) == 1


def test_modular_import_smoke_default_creates_real_xlsx(tmp_path, monkeypatch):
    modular = importlib.import_module("tests.run_modular_import")
    calls: list[dict[str, str]] = []

    def fake_run_importer_logic(**kwargs):
        calls.append(dict(kwargs))
        docs_dir = Path(str(kwargs["docs_dir"]))
        assert list(docs_dir.glob("*.xlsx"))
        data_dir = Path(str(kwargs["data_dir"]))
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / str(kwargs["db_name"])).write_text("ok", encoding="utf-8")
        return True

    monkeypatch.setattr(modular, "run_importer_logic", fake_run_importer_logic)
    monkeypatch.chdir(tmp_path)

    assert modular.main([]) == 0
    assert calls
    assert not Path("data/ssas.db").exists()


def test_detailed_import_smoke_fails_when_success_does_not_create_db(
    tmp_path, monkeypatch
):
    detailed = importlib.import_module("tests.run_import_detailed")

    def fake_run_importer_logic(**_kwargs):
        return True

    monkeypatch.setattr(
        "core.app_logic.run_importer_logic",
        fake_run_importer_logic,
    )
    monkeypatch.chdir(tmp_path)

    assert detailed.main([]) == 1
    assert not Path("data/ssas.db").exists()
