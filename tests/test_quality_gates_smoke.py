#!/usr/bin/env python3
"""Teste smoke (caminho feliz) do agregador de quality gates.

Executa `run_quality_gates.py` sem parâmetros adicionais e valida:
  * Exit code == 0
  * JSON parseável
  * summary.overall_status == "ok"
  * Campos essenciais presentes para cada gate esperado

Se algum gate estiver falhando legitimamente o teste mostrará
stdout/stderr para diagnóstico. Marcado como `integration` por
executar subprocessos e percorrer múltiplas camadas (scripts + configs).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

EXPECTED_GATES = {"validate_configs", "smoke_cli", "check_docs"}


@pytest.mark.integration
@pytest.mark.smoke
def test_quality_gates_smoke_ok():
    cmd = [sys.executable, str(SCRIPTS_DIR / "run_quality_gates.py")]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    assert proc.returncode == 0, (
        "Agregador deveria retornar 0 no caminho feliz.\n"
        f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    )
    # Extrair último bloco JSON (stdout pode conter apenas JSON, mas ser resiliente)
    parsed = None
    for line in reversed([ln for ln in proc.stdout.splitlines() if ln.strip()]):
        try:
            parsed = json.loads(line)
            break
        except Exception:
            continue
    assert parsed is not None, f"Saída não contém JSON parseável. STDOUT:\n{proc.stdout}"
    summary = parsed.get("summary", {})
    assert summary.get("overall_status") == "ok", f"overall_status != ok :: {summary}"
    gates = parsed.get("gates", {})
    missing = EXPECTED_GATES - set(gates.keys())
    assert not missing, f"Gates esperados ausentes: {missing}"
    # Checagens básicas de cada gate
    for name, info in gates.items():
        assert info.get("status") in {"ok", "fail", "error"}, f"Status inválido gate {name}: {info}"
        assert isinstance(info.get("duration_s"), (int, float)), f"duration_s ausente/inválido em {name}"
        assert "exit_code" in info, f"exit_code ausente em {name}"

