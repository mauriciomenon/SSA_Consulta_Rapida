#!/usr/bin/env python3
"""
Configurações de teste globais.

- Força o Qt a usar modo offscreen para evitar dependência de display nas GUIs.
"""

import os


def pytest_sessionstart(session):  # noqa: D401
    """Executa no início da sessão de testes."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

