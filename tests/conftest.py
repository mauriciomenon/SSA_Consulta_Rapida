# ruff: noqa: E402
from __future__ import annotations

import logging
import os
import tempfile

# Force unbuffered stdout/stderr for visibility in CI / tooling
os.environ.setdefault("PYTHONUNBUFFERED", "1")

# Basic logging config if not already configured
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )

logging.getLogger(__name__).info(
    "conftest initialized (unbuffered=%s)", os.environ.get("PYTHONUNBUFFERED")
)
#!/usr/bin/env python3
"""Configurações de teste globais e fixtures compartilhadas.

Inclui:
    * Força Qt em modo offscreen (evita dependência de display)
    * Fixtures de banco de dados temporário com schema
    * DataFrames sintéticos para importação e upsert
    * Casos de normalização de numero_ssa
"""
import shutil
from contextlib import suppress
from pathlib import Path
from typing import Iterator

import pandas as pd
import pytest

from tests._helpers.db_utils import create_temp_db

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GUI_FILTER_LOGIC_TEST = "tests/test_gui_filter_logic.py"
_TEST_SSA_CONFIG_DIR: Path | None = None
_TRACKED_GUI_PREFS_PATH = PROJECT_ROOT / "config" / "gui_main_preferences.json"
_TRACKED_GUI_PREFS_BYTES: bytes | None = None


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    items.sort(
        key=lambda item: 0 if item.path.as_posix().endswith(GUI_FILTER_LOGIC_TEST) else 1
    )


def pytest_sessionstart(session):  # noqa: D401
    """Executa no início da sessão de testes."""
    global _TEST_SSA_CONFIG_DIR, _TRACKED_GUI_PREFS_BYTES
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    # Forçar modo não interativo para o table_printer (evita inputs que podem causar bloqueios/tempos ociosos)
    os.environ.setdefault("SSA_NON_INTERACTIVE", "1")
    # Desabilitar prompts de atualização do oh-my-zsh / zsh interativo em subprocessos
    os.environ.setdefault("DISABLE_AUTO_UPDATE", "true")
    os.environ.setdefault("DISABLE_UPDATE_PROMPT", "true")
    # Evitar que ferramentas tentem paginar (ex: pydoc, help, etc.)
    os.environ.setdefault("PAGER", "cat")
    if _TRACKED_GUI_PREFS_PATH.exists():
        _TRACKED_GUI_PREFS_BYTES = _TRACKED_GUI_PREFS_PATH.read_bytes()
    _TEST_SSA_CONFIG_DIR = Path(tempfile.mkdtemp(prefix="ssa_test_config_"))
    shutil.copytree(PROJECT_ROOT / "config", _TEST_SSA_CONFIG_DIR, dirs_exist_ok=True)
    # Keep tests independent from the developer's local, gitignored GUI layout.
    (_TEST_SSA_CONFIG_DIR / "gui_main_preferences.json").unlink(missing_ok=True)
    os.environ["SSA_CONFIG_DIR"] = str(_TEST_SSA_CONFIG_DIR)


def pytest_sessionfinish(session, exitstatus):  # noqa: D401
    """Executa no fim da sessão de testes."""
    _ = session, exitstatus
    if (
        _TRACKED_GUI_PREFS_BYTES is not None
        and _TRACKED_GUI_PREFS_PATH.exists()
        and _TRACKED_GUI_PREFS_PATH.read_bytes() != _TRACKED_GUI_PREFS_BYTES
    ):
        logging.getLogger(__name__).error(
            "Tracked GUI preferences changed during tests: %s",
            _TRACKED_GUI_PREFS_PATH,
        )
    if _TEST_SSA_CONFIG_DIR is None:
        return
    with suppress(Exception):
        shutil.rmtree(_TEST_SSA_CONFIG_DIR, ignore_errors=True)


@pytest.fixture(scope="function")
def temp_db() -> Iterator[str]:
    """Fornece caminho para DB SQLite temporário com schema aplicado."""
    db_path, tmp_dir = create_temp_db()
    try:
        yield db_path
    finally:  # limpeza best-effort
        with suppress(Exception):
            shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture()
def sample_import_dataframe() -> pd.DataFrame:
    """DataFrame sintético mínimo representando lote de importação."""
    data = {
        "numero_ssa": ["202512345", "202512346", None],
        "situacao": ["ABERTA", "EM ANDAMENTO", "FECHADA"],
        "data_cadastro": ["01/01/2025 10:00", "02/01/2025 11:30", ""],
        "descricao_ssa": ["Teste A", "Teste B", "Teste C"],
        "setor_executor": ["SETOR1", "SETOR2", "SETOR3"],
    }
    return pd.DataFrame(data)


@pytest.fixture()
def sample_upsert_batches() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Dois lotes para teste de upsert (lote2 atualiza um registro)."""
    batch1 = {
        "numero_ssa": ["202512345", "202512346"],
        "situacao": ["ABERTA", "ABERTA"],
        "data_cadastro": ["2025-01-01 10:00:00", "2025-01-01 10:05:00"],
        "descricao_ssa": ["Orig A", "Orig B"],
    }
    batch2 = {
        "numero_ssa": ["202512345", "202512347"],  # primeiro atualiza, segundo novo
        "situacao": ["EM ANDAMENTO", "ABERTA"],
        "data_cadastro": ["2025-01-02 09:00:00", "2025-01-01 12:00:00"],
        "descricao_ssa": ["Upd A", "Orig C"],
    }
    return pd.DataFrame(batch1), pd.DataFrame(batch2)


@pytest.fixture()
def normalization_cases() -> list[tuple[str | int | None, str | None]]:
    return [
        (None, None),
        ("", None),
        ("00000", None),
        ("123", None),
        ("202512345", "202512345"),
        ("202512345678", None),
        ("2101234", None),
        ("2601234", None),
    ]
