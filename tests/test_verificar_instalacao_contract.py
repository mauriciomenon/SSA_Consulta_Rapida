"""Contrato textual de scripts_manutencao/verificar_instalacao.ps1.

O script nao roda em CI (PowerShell/Windows); este teste fixa a regra que
impede resetar um banco existente apontado por SSA_DB_PATH.
"""

from __future__ import annotations

from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts_manutencao" / "verificar_instalacao.ps1"


def _db_block() -> str:
    text = SCRIPT.read_text(encoding="utf-8")
    start = text.index('-Name "Criação do Banco"')
    return text[start : text.index("-SuccessMessage", start)]


def test_reset_db_uses_same_effective_target_as_main() -> None:
    block = _db_block()
    assert "$env:SSA_DB_PATH" in block
    target_line = block.index("$dbTarget =")
    assert block.index("Test-Path $dbTarget") > target_line
    assert block.index("python main.py --reset-db") > block.index("Test-Path $dbTarget")


def test_reset_db_errors_are_not_hidden() -> None:
    assert "--reset-db 2>$null" not in _db_block()
