#!/usr/bin/env python3
"""Smoke test simples para a CLI.

Objetivo: validar rapidamente que o entrypoint de CLI inicia sem falhas graves
(tipos de import / path) e expõe --help ou marcador de versão. Não substitui
testes funcionais.

Saída / Convenções:
  * Código 0: sucesso
  * Código 1: falha
  * Com --json: imprime objeto JSON com campos summary / output / exit_code

Estratégia:
  1. Executa entrypoint via módulo launchers.cli_entry com variável SSA_SMOKE_TEST=1
     para caminho rápido (evita interface interativa bloqueante).
  2. Caso falhe, tenta fallback executando `python launchers/cli_entry.py --help`.
  3. Valida presença de marcador "SMOKE_CLI_OK" ou palavra-chave conhecida ("CONSULTA RÁPIDA", "Ajuda").

Uso:
  python scripts/smoke_cli.py
  python scripts/smoke_cli.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parent.parent


def run_smoke() -> dict:
    env = os.environ.copy()
    env["SSA_SMOKE_TEST"] = "1"
    cmd = [sys.executable, "-m", "launchers.cli_entry"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT, env=env, timeout=25)
        output = (proc.stdout + proc.stderr).strip()
        if proc.returncode == 0 and "SMOKE_CLI_OK" in output:
            return {"ok": True, "mode": "fast", "output": output, "returncode": proc.returncode}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "mode": "fast-exception", "output": str(exc), "returncode": 1}

    # Fallback: tentar help direto do script (pode abrir UI interativa se não protegido)
    try:
        cmd2 = [sys.executable, "launchers/cli_entry.py", "--help"]
        proc2 = subprocess.run(cmd2, capture_output=True, text=True, cwd=REPO_ROOT, timeout=25)
        output2 = (proc2.stdout + proc2.stderr).strip()
        markers = ["Ajuda", "CONSULTA", "Entry point", "SSA"]
        marker_hit = any(m.lower() in output2.lower() for m in markers)
        return {
            "ok": proc2.returncode == 0 and marker_hit,
            "mode": "help-fallback",
            "output": output2,
            "returncode": proc2.returncode,
            "marker_hit": marker_hit,
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "mode": "help-exception", "output": str(exc), "returncode": 1}


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Smoke test da CLI")
    p.add_argument("--json", action="store_true", help="Saída em JSON")
    return p.parse_args(argv)


def main(argv: List[str]) -> int:  # pragma: no cover - simples
    args = parse_args(argv)
    result = run_smoke()
    if args.json:
        print(json.dumps({"summary": result, "exit_code": 0 if result.get("ok") else 1}, ensure_ascii=False, indent=2))
    else:
        status = "OK" if result.get("ok") else "FAIL"
        print(f"[SMOKE_CLI] Status: {status} | mode={result.get('mode')} | returncode={result.get('returncode')}")
        # Limita tamanho do output para visual rápido
        out_preview = result.get("output", "")[:800]
        if out_preview:
            print("--- Output (preview) ---")
            print(out_preview)
            print("-------------------------")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
