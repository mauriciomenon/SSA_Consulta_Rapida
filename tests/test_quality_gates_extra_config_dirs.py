#!/usr/bin/env python3
"""Teste para múltiplos --extra-config-dir em run_quality_gates.

Objetivo:
  * Criar dois diretórios temporários de configs válidos mínimos.
  * Executar agregador com --extra-config-dir apontando para ambos.
  * Verificar que surgem gates: validate_configs_extra_1 e validate_configs_extra_2.
  * Assegurar overall_status == "ok" e exit codes/gate statuses também ok.

Critério de "config válida mínima": usar apenas um version.json simples
que passa nas regras de validate_configs.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

VALID_VERSION_JSON = '{"version_short": "1.0", "version_long": "Versao 1.0 inicial"}'


@pytest.mark.integration
def test_quality_gates_multiple_extra_config_dirs(tmp_path):
    extra1 = tmp_path / "cfg1"
    extra2 = tmp_path / "cfg2"
    extra1.mkdir()
    extra2.mkdir()
    (extra1 / "version.json").write_text(VALID_VERSION_JSON, encoding="utf-8")
    (extra2 / "version.json").write_text(VALID_VERSION_JSON, encoding="utf-8")

    # Não usamos --only validate_configs porque isso filtraria *apenas* o gate base,
    # removendo os extras. Em vez disso, executamos todos e usamos --skip para pular
    # gates não relacionados (smoke_cli, check_docs) mantendo validate_configs + extras.
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "run_quality_gates.py"),
        "--extra-config-dir", str(extra1),
        "--extra-config-dir", str(extra2),
        "--skip", "smoke_cli",
        "--skip", "check_docs",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    assert proc.returncode == 0, f"Agregador deveria retornar 0. stdout={proc.stdout} stderr={proc.stderr}"

    parsed = None
    for line in reversed([ln for ln in proc.stdout.splitlines() if ln.strip()]):
        try:
            parsed = json.loads(line)
            break
        except Exception:
            continue
    assert parsed, f"Saída não contém JSON parseável. STDOUT:\n{proc.stdout}"

    assert parsed.get("overall_status") == "ok", f"overall_status != ok :: {parsed.get('overall_status')}"

    gates = parsed.get("gates", {})
    assert "validate_configs" in gates, "Gate base validate_configs ausente"
    assert "validate_configs_extra_1" in gates, "Gate validate_configs_extra_1 ausente"
    assert "validate_configs_extra_2" in gates, "Gate validate_configs_extra_2 ausente"

    for gname in ("validate_configs", "validate_configs_extra_1", "validate_configs_extra_2"):
        ginfo = gates.get(gname, {})
        assert ginfo.get("status") == "ok", f"Gate {gname} não ok: {ginfo}"
        assert ginfo.get("exit_code") == 0, f"Gate {gname} exit_code != 0: {ginfo}"
