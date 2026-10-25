"""BL-44: regras de camada de scripts_manutencao/analyze_code_quality.py valem na suite.

shared/ nao importa camadas do app (core, gui, utils...) e armazenamento/ nao importa
core, gui, interface, extracao nem exportacao.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _analyzer():
    spec = importlib.util.spec_from_file_location(
        "analyze_code_quality", ROOT / "scripts_manutencao" / "analyze_code_quality.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_shared_does_not_import_app_layers() -> None:
    assert _analyzer().check_shared_purity() == []


def test_armazenamento_does_not_import_upper_layers() -> None:
    assert _analyzer().check_armazenamento_independence() == []
