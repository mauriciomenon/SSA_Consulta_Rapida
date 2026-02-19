# ruff: noqa: E402
from __future__ import annotations

import os
import logging

# Force unbuffered stdout/stderr for visibility in CI / tooling
os.environ.setdefault("PYTHONUNBUFFERED", "1")

# Basic logging config if not already configured
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

logging.getLogger(__name__).info("conftest initialized (unbuffered=%s)", os.environ.get("PYTHONUNBUFFERED"))
#!/usr/bin/env python3
"""Configurações de teste globais e fixtures compartilhadas.

Inclui:
    * Força Qt em modo offscreen (evita dependência de display)
    * Fixtures de banco de dados temporário com schema
    * DataFrames sintéticos para importação e upsert
    * Casos de normalização de numero_ssa
"""
import shutil
from pathlib import Path
from typing import Iterator
from contextlib import suppress

import pandas as pd
import pytest

from tests._helpers.db_utils import create_temp_db

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def pytest_sessionstart(session):  # noqa: D401
    """Executa no início da sessão de testes."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    # Forçar modo não interativo para o table_printer (evita inputs que podem causar bloqueios/tempos ociosos)
    os.environ.setdefault("SSA_NON_INTERACTIVE", "1")
    # Desabilitar prompts de atualização do oh-my-zsh / zsh interativo em subprocessos
    os.environ.setdefault("DISABLE_AUTO_UPDATE", "true")
    os.environ.setdefault("DISABLE_UPDATE_PROMPT", "true")
    # Evitar que ferramentas tentem paginar (ex: pydoc, help, etc.)
    os.environ.setdefault("PAGER", "cat")


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
        ("123", "202500123"),
        ("202512345", "202512345"),
        ("202512345678", "202512345"),
        ("2101234", "202101234"),  # caso especial 7 dígitos iniciando 21
    ]
