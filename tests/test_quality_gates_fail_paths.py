#!/usr/bin/env python3
"""Testes dos quality gates em cenários de falha controlada.

Cria ambiente temporário simulando:
  * Documento markdown vazio (violação para check_docs)
  * Config JSON inválido (violação para validate_configs)
Verifica que o agregador reporta overall_status != ok e inclui detalhes.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"


@pytest.mark.integration
def test_quality_gates_failures(tmp_path):
    # Arrange: criar doc vazio e config inválido
    bad_doc = tmp_path / "BAD_DOC.md"
    bad_doc.write_text("\n")
    bad_cfg_dir = tmp_path / "bad_config"
    bad_cfg_dir.mkdir()
    (bad_cfg_dir / "invalid.json").write_text("{ invalid json")  # sintaxe quebrada

    # Executa scripts individualmente para garantir falha
    check_docs_cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "check_docs.py"),
        "--paths",
        str(bad_doc),
        "--fail-on-issues",
    ]
    validate_cfg_cmd = [sys.executable, str(SCRIPTS_DIR / "validate_configs.py"), str(bad_cfg_dir)]

    r1 = subprocess.run(check_docs_cmd, capture_output=True, text=True)
    r2 = subprocess.run(validate_cfg_cmd, capture_output=True, text=True)

    assert r1.returncode != 0, f"check_docs deveria falhar: stdout={r1.stdout} stderr={r1.stderr}"
    assert r2.returncode != 0, f"validate_configs deveria falhar: stdout={r2.stdout} stderr={r2.stderr}"

    # Agora roda agregador (espera overall_status != ok)
    aggregator_cmd = [sys.executable, str(SCRIPTS_DIR / "run_quality_gates.py"), "--extra-doc", str(bad_doc), "--extra-config-dir", str(bad_cfg_dir)]
    r3 = subprocess.run(aggregator_cmd, capture_output=True, text=True)

    assert r3.returncode != 0, f"Agregador deveria retornar código !=0 para falhas. stdout={r3.stdout} stderr={r3.stderr}"

    # Tentar parsear JSON final (stdout ou stderr) - assumir stdout
    # Procurar última linha que pareça JSON
    output_lines = [line_txt for line_txt in r3.stdout.splitlines() if line_txt.strip()]
    parsed = None
    for line in reversed(output_lines):
        try:
            parsed = json.loads(line)
            break
        except Exception:
            continue
    assert parsed is not None, f"Não foi possível parsear JSON do agregador. Saída: {r3.stdout}"
    assert parsed.get("overall_status") in {"fail", "error"}
    # Deve conter chaves dos gates
    for gate in ("check_docs", "validate_configs"):
        assert gate in parsed, f"Gate {gate} ausente no summary"


@pytest.mark.integration
def test_check_docs_ignores_opencode_node_modules(tmp_path):
    docs_root = tmp_path / "docs_ok"
    docs_root.mkdir()
    (docs_root / "GOOD.md").write_text(
        "# Guia\n\nConteudo valido.\n\nLinha extra.\n\nOutra linha.\n",
        encoding="utf-8",
    )

    ignored_bad_doc = tmp_path / ".opencode" / "node_modules" / "pkg" / "BAD.md"
    ignored_bad_doc.parent.mkdir(parents=True)
    ignored_bad_doc.write_text("\n", encoding="utf-8")

    cmd = [sys.executable, str(SCRIPTS_DIR / "check_docs.py"), "--paths", str(tmp_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)

    assert proc.returncode == 0, (
        "check_docs nao deveria falhar por markdown dentro de .opencode/node_modules.\n"
        f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    )
