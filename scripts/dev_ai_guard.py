#!/usr/bin/env python3
"""
Local pre/post PR guard runner for derivadas workflows.

Primary runner is TypeScript/Bun:
  - scripts/dev_ai_guard.ts

This Python file is a parity fallback and should remain aligned with the TS steps.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal


Mode = Literal["pre-pr", "post-pr"]


@dataclass(frozen=True)
class Step:
    name: str
    cmd: list[str]


@dataclass(frozen=True)
class StepResult:
    name: str
    command: str
    exit_code: int
    duration_ms: int
    stdout: str
    stderr: str


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Derivadas local pre/post PR guard (Python fallback)")
    parser.add_argument("--mode", choices=("pre-pr", "post-pr"), default="pre-pr")
    parser.add_argument("--db", dest="db_path", default="data/ssas.db")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-health", action="store_true")
    parser.add_argument("--skip-lint", action="store_true")
    parser.add_argument("--skip-sync-verify", action="store_true")
    parser.add_argument("--output-dir", default="local_ai_private")
    return parser.parse_args(argv)


def build_steps(options: argparse.Namespace) -> list[Step]:
    lint_targets = [
        "armazenamento/derivadas_schema.py",
        "armazenamento/derivadas_queries.py",
        "armazenamento/derivadas_sync.py",
        "scripts/derivadas_cli.py",
        "tests/test_derivadas_schema.py",
        "tests/test_derivadas_sync.py",
        "tests/test_derivadas_queries.py",
        "tests/test_derivadas_cli.py",
        "tests/test_derivadas_maintenance.py",
    ]

    derivadas_tests = [
        "tests/test_derivadas_schema.py",
        "tests/test_derivadas_sync.py",
        "tests/test_derivadas_queries.py",
        "tests/test_derivadas_cli.py",
        "tests/test_derivadas_maintenance.py",
    ]

    post_pr_tests = [
        "tests/test_derivadas_sync.py",
        "tests/test_derivadas_queries.py",
        "tests/test_derivadas_maintenance.py",
    ]

    steps: list[Step] = []
    if not options.skip_lint:
        steps.append(Step(name="py_compile", cmd=["python", "-m", "py_compile", *lint_targets]))
        steps.append(Step(name="ruff_check", cmd=["ruff", "check", *lint_targets]))

    if options.mode == "pre-pr":
        if not options.skip_tests:
            steps.append(Step(name="pytest_derivadas_suite", cmd=["pytest", "-q", *derivadas_tests]))
        if not options.skip_health:
            steps.append(
                Step(
                    name="schema_scan",
                    cmd=["python", "scripts/derivadas_cli.py", "--db", options.db_path, "--output", "json", "schema-scan"],
                )
            )
            steps.append(
                Step(
                    name="consistency_scan",
                    cmd=["python", "scripts/derivadas_cli.py", "--db", options.db_path, "--output", "json", "scan"],
                )
            )
            if not options.skip_sync_verify:
                steps.append(
                    Step(
                        name="sync_verify_only",
                        cmd=[
                            "python",
                            "scripts/derivadas_cli.py",
                            "--db",
                            options.db_path,
                            "--output",
                            "json",
                            "sync",
                            "--verify-only",
                        ],
                    )
                )
            steps.append(
                Step(
                    name="sync_stats",
                    cmd=["python", "scripts/derivadas_cli.py", "--db", options.db_path, "--output", "json", "stats"],
                )
            )
        return steps

    if not options.skip_tests:
        steps.append(Step(name="pytest_post_pr_smoke", cmd=["pytest", "-q", *post_pr_tests]))
    if not options.skip_health:
        steps.append(
            Step(
                name="schema_scan",
                cmd=["python", "scripts/derivadas_cli.py", "--db", options.db_path, "--output", "json", "schema-scan"],
            )
        )
        steps.append(
            Step(
                name="consistency_scan",
                cmd=["python", "scripts/derivadas_cli.py", "--db", options.db_path, "--output", "json", "scan"],
            )
        )
        steps.append(
            Step(
                name="maintenance_scan_only",
                cmd=[
                    "python",
                    "scripts/derivadas_cli.py",
                    "--db",
                    options.db_path,
                    "--output",
                    "json",
                    "maintenance",
                    "--min-interval-seconds",
                    "0",
                    "--no-auto-heal",
                ],
            )
        )
        steps.append(
            Step(
                name="sync_stats",
                cmd=["python", "scripts/derivadas_cli.py", "--db", options.db_path, "--output", "json", "stats"],
            )
        )
    return steps


def run_step(step: Step) -> StepResult:
    started_at = time.time()
    result = subprocess.run(
        step.cmd,
        cwd=os.getcwd(),
        text=True,
        capture_output=True,
        check=False,
    )
    duration_ms = int((time.time() - started_at) * 1000)
    return StepResult(
        name=step.name,
        command=" ".join(step.cmd),
        exit_code=int(result.returncode),
        duration_ms=duration_ms,
        stdout=result.stdout or "",
        stderr=result.stderr or "",
    )


def write_report(options: argparse.Namespace, results: list[StepResult]) -> str:
    report_dir = Path(os.getcwd()) / options.output_dir
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat().replace(":", "-").replace(".", "-")
    report_path = report_dir / f"dev_ai_guard_{options.mode}_{timestamp}_py.json"
    payload = {
        "mode": options.mode,
        "dbPath": options.db_path,
        "success": all(item.exit_code == 0 for item in results),
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "steps": [asdict(item) for item in results],
        "runner": "python-fallback",
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(report_path)


def main(argv: list[str] | None = None) -> int:
    options = parse_args(list(argv or sys.argv[1:]))
    steps = build_steps(options)

    print(f"Mode: {options.mode}")
    print(f"DB:   {options.db_path}")
    print(f"Steps planned: {len(steps)}")

    results: list[StepResult] = []
    for step in steps:
        print(f"\n==> {step.name}")
        print(f"$ {' '.join(step.cmd)}")
        outcome = run_step(step)
        results.append(outcome)
        if outcome.stdout.strip():
            print(outcome.stdout.strip())
        if outcome.stderr.strip():
            print(outcome.stderr.strip(), file=sys.stderr)
        if outcome.exit_code != 0:
            report = write_report(options, results)
            print(f"\nFAILED at step '{step.name}'. Report: {report}", file=sys.stderr)
            return 1

    report = write_report(options, results)
    print(f"\nAll steps passed. Report: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
