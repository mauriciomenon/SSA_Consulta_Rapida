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
