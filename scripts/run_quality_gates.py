#!/usr/bin/env python3
"""run_quality_gates.py
Executa os quality gates principais do projeto (configs, smoke CLI, docs) e consolida resultados em um único JSON.

Suporte adicional:
    * --extra-config-dir <dir> pode ser passado múltiplas vezes. Cada diretório gera
        um gate separado (validate_configs_extra_1, validate_configs_extra_2, ...)
        permitindo identificar qual conjunto falhou sem ambiguidade.
    * --extra-doc adiciona arquivos markdown individuais a serem validados pelo check_docs.
    * A saída é uma única linha JSON para facilitar parsing em pipelines.

Saída JSON exemplo:
{
  "summary": {"overall_status": "ok"|"fail", "started_at": "...", "finished_at": "...", "duration_seconds": 1.23},
  "gates": {
     "validate_configs": {...},
     "smoke_cli": {...},
     "check_docs": {...}
  }
}
Exit codes:
 0 -> todos os gates sem falhas
 1 -> algum gate falhou (qualidade)
 2 -> erro interno de execução
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import argparse
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable

@dataclass
class GateResult:
    name: str
    status: str  # ok | fail | error
    exit_code: int
    duration_s: float
    details: Optional[dict] = None
    stdout_snippet: Optional[str] = None
    stderr_snippet: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        return data


def run_gate(
    cmd: List[str],
    name: str,
    parse_json: bool = True,
    max_snippet: int = 4000,
    timeout: int = 120,
) -> GateResult:
    start = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=timeout,
            check=False,
        )
        duration = time.time() - start
        details = None
        status = "ok"
        if parse_json and proc.stdout.strip():
            try:
                details = json.loads(proc.stdout)
            except json.JSONDecodeError:
                details = {"raw": proc.stdout.strip()[:max_snippet], "parse_error": True}
        if proc.returncode != 0:
            # Differentiating quality fail vs internal error is up to underlying gate
            status = "fail" if proc.returncode == 1 else "error"
        return GateResult(
            name=name,
            status=status,
            exit_code=proc.returncode,
            duration_s=round(duration, 3),
            details=details,
            stdout_snippet=proc.stdout[:max_snippet] if proc.stdout else None,
            stderr_snippet=proc.stderr[:max_snippet] if proc.stderr else None,
        )
    except Exception as e:  # noqa: BLE001
        duration = time.time() - start
        return GateResult(
            name=name,
            status="error",
            exit_code=2,
            duration_s=round(duration, 3),
            details={"exception": str(e)},
        )


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Executa e agrega quality gates (configs, smoke CLI, docs).")
    p.add_argument("--extra-doc", action="append", dest="extra_docs", help="Arquivo markdown adicional para validar (pode repetir)")
    p.add_argument("--extra-config-dir", action="append", dest="extra_cfg_dirs", help="Diretório extra de configs JSON (pode repetir)")
    p.add_argument("--skip", action="append", dest="skip_gates", choices=["validate_configs", "smoke_cli", "check_docs", "lint"], help="Gate a pular (pode repetir)")
    p.add_argument("--only", action="append", dest="only_gates", choices=["validate_configs", "smoke_cli", "check_docs", "lint"], help="Executa apenas os gates listados")
    p.add_argument("--no-fail-on-doc-issues", action="store_true", help="Não força falha se check_docs encontrar issues")
    p.add_argument("--timeout", type=int, default=120, help="Timeout (s) para cada gate individual")
    p.add_argument("--lint-stream", action="store_true", help="Mostra saída em tempo real do lint (sem captura)")
    p.add_argument("--include-lint", action="store_true", help="Inclui gate de lint (flake8/mypy). Off por padrão para smoke.")
    return p


def compose_gates(args: argparse.Namespace) -> List[tuple[str, List[str]]]:
    gates: List[tuple[str, List[str]]] = []
    # Gate principal de configs (diretório padrão implícito dentro do script validate_configs)
    gates.append(("validate_configs", [PYTHON, "scripts/validate_configs.py", "--json"]))
    # Diretórios extras – cada um vira um gate separado para granularidade
    if args.extra_cfg_dirs:
        for idx, cfg_dir in enumerate(args.extra_cfg_dirs, start=1):
            # Cada diretório extra precisa ser passado via --config-dir (validate_configs não aceita arg posicional)
            gates.append((f"validate_configs_extra_{idx}", [PYTHON, "scripts/validate_configs.py", "--json", "--config-dir", cfg_dir]))
    # Smoke CLI
    gates.append(("smoke_cli", [PYTHON, "scripts/smoke_cli.py", "--json"]))
    # Docs
    docs_cmd = [PYTHON, "scripts/check_docs.py", "--json"]
    if not args.no_fail_on_doc_issues:
        docs_cmd.append("--fail-on-issues")
    if args.extra_docs:
        docs_cmd.extend(["--paths", *args.extra_docs])
    gates.append(("check_docs", docs_cmd))
    # Lint opcional: desligado por padrão (caminho feliz/smoke não depende).
    if args.include_lint or (args.only_gates and "lint" in args.only_gates):
        gates.append(("lint", [PYTHON, "scripts/run_lint.py", "--strict"]))
    # Filtragem por --only / --skip
    if args.only_gates:
        only_set = set(args.only_gates)
        gates = [g for g in gates if g[0] in only_set]
    if args.skip_gates:
        skip_set = set(args.skip_gates)
        gates = [g for g in gates if g[0] not in skip_set]
    return gates


def main(argv: Optional[List[str]] = None) -> int:
    started = time.time()
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    gates_cmds = compose_gates(args)

    results: Dict[str, GateResult] = {}
    for name, cmd in gates_cmds:
        # Gate lint pode exibir saída em tempo real (--lint-stream) para facilitar debug.
        if name == "lint" and args.lint_stream:
            start = time.time()
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(REPO_ROOT),
                    timeout=args.timeout,
                    check=False,
                )
                duration = time.time() - start
                status = "ok"
                if proc.returncode != 0:
                    status = "fail" if proc.returncode == 1 else "error"
                results[name] = GateResult(
                    name=name,
                    status=status,
                    exit_code=proc.returncode,
                    duration_s=round(duration, 3),
                    details=None,
                )
            except Exception as e:  # noqa: BLE001
                duration = time.time() - start
                results[name] = GateResult(
                    name=name,
                    status="error",
                    exit_code=2,
                    duration_s=round(duration, 3),
                    details={"exception": str(e)},
                )
            continue
        # Demais gates ou lint sem stream utilizam execução com captura
        parse_json = name not in {"lint"}
        results[name] = run_gate(
            cmd,
            name=name,
            parse_json=parse_json,
            timeout=args.timeout,
        )

    # Determinação de severidade: fail > error > ok
    overall = "ok"
    for r in results.values():
        if r.status == "fail":  # prioridade máxima
            overall = "fail"
            break
        if r.status == "error" and overall == "ok":
            overall = "error"

    finished = time.time()
    # Estrutura principal esperada pelos testes:
    #  * test_quality_gates_smoke.py espera summary.overall_status == "ok"
    #  * test_quality_gates_fail_paths.py espera chaves top-level: overall_status e nomes dos gates
    # Para compatibilizar ambos adicionamos campos redundantes (flatten dos gates + overall_status root).
    gates_dict = {k: v.to_dict() for k, v in results.items()}
    payload = {
        "overall_status": overall,
        "summary": {
            "overall_status": overall,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(finished)),
            "duration_seconds": round(finished - started, 3),
            "executed_gates": list(results.keys()),
        },
        "gates": gates_dict,
        "args": {
            "extra_docs": args.extra_docs or [],
            "extra_cfg_dirs": args.extra_cfg_dirs or [],
            "skip_gates": args.skip_gates or [],
            "only_gates": args.only_gates or [],
        },
    }
    # Flatten (redundante) – garante que testes que buscam gate direto em root encontrem.
    for gate_name, gate_info in gates_dict.items():
        payload.setdefault(gate_name, gate_info)

    # Imprimir em linha única para facilitar parse linha-a-linha dos testes (que iteram linhas ao contrário).
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))

    if overall == "ok":
        return 0
    if overall == "fail":
        return 1
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
