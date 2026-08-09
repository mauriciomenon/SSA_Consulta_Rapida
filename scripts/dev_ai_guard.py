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
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

Mode = Literal["pre-pr", "post-pr"]
TablePresence = Literal["present", "absent", "unknown"]

DEFAULT_STEP_TIMEOUT_SECONDS = int(
    os.environ.get("SSA_DEV_GUARD_STEP_TIMEOUT_SECONDS", "900")
)
PYTHON_EXE = sys.executable


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
    parser = argparse.ArgumentParser(
        description="Derivadas local pre/post PR guard (Python fallback)"
    )
    parser.add_argument("--mode", choices=("pre-pr", "post-pr"), default="pre-pr")
    parser.add_argument("--db", dest="db_path", default="data/ssas.db")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-health", action="store_true")
    parser.add_argument("--skip-lint", action="store_true")
    parser.add_argument("--skip-sync-verify", action="store_true")
    parser.add_argument("--output-dir", default="local_ai_private")
    return parser.parse_args(argv)


def sqlite_table_presence(db_path: str, table_name: str) -> TablePresence:
    if not db_path or not table_name:
        return "unknown"
    if not os.path.exists(db_path):
        return "unknown"
    try:
        with closing(sqlite3.connect(db_path)) as conn:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
                (table_name,),
            ).fetchone()
            return "present" if row is not None else "absent"
    except sqlite3.Error as exc:
        print(
            f"Warning: unable to verify table presence ({table_name}) in {db_path}: {exc}",
            file=sys.stderr,
        )
        return "unknown"


def _as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value


def build_steps(
    options: argparse.Namespace, *, include_sync_verify: bool
) -> list[Step]:
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
        steps.append(
            Step(name="py_compile", cmd=[PYTHON_EXE, "-m", "py_compile", *lint_targets])
        )
        steps.append(
            Step(
                name="ruff_check",
                cmd=[PYTHON_EXE, "-m", "ruff", "check", *lint_targets],
            )
        )

    if options.mode == "pre-pr":
        if not options.skip_tests:
            steps.append(
                Step(
                    name="pytest_derivadas_suite",
                    cmd=[PYTHON_EXE, "-m", "pytest", "-q", *derivadas_tests],
                )
            )
        if not options.skip_health:
            steps.append(
                Step(
                    name="schema_scan",
                    cmd=[
                        PYTHON_EXE,
                        "scripts/derivadas_cli.py",
                        "--db",
                        options.db_path,
                        "--output",
                        "json",
                        "schema-scan",
                    ],
                )
            )
            steps.append(
                Step(
                    name="consistency_scan",
                    cmd=[
                        PYTHON_EXE,
                        "scripts/derivadas_cli.py",
                        "--db",
                        options.db_path,
                        "--output",
                        "json",
                        "scan",
                    ],
                )
            )
            if include_sync_verify:
                steps.append(
                    Step(
                        name="sync_verify_only",
                        cmd=[
                            PYTHON_EXE,
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
                    cmd=[
                        PYTHON_EXE,
                        "scripts/derivadas_cli.py",
                        "--db",
                        options.db_path,
                        "--output",
                        "json",
                        "stats",
                    ],
                )
            )
        return steps

    if not options.skip_tests:
        steps.append(
            Step(
                name="pytest_post_pr_smoke",
                cmd=[PYTHON_EXE, "-m", "pytest", "-q", *post_pr_tests],
            )
        )
    if not options.skip_health:
        steps.append(
            Step(
                name="schema_scan",
                cmd=[
                    PYTHON_EXE,
                    "scripts/derivadas_cli.py",
                    "--db",
                    options.db_path,
                    "--output",
                    "json",
                    "schema-scan",
                ],
            )
        )
        steps.append(
            Step(
                name="consistency_scan",
                cmd=[
                    PYTHON_EXE,
                    "scripts/derivadas_cli.py",
                    "--db",
                    options.db_path,
                    "--output",
                    "json",
                    "scan",
                ],
            )
        )
        steps.append(
            Step(
                name="maintenance_scan_only",
                cmd=[
                    PYTHON_EXE,
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
                cmd=[
                    PYTHON_EXE,
                    "scripts/derivadas_cli.py",
                    "--db",
                    options.db_path,
                    "--output",
                    "json",
                    "stats",
                ],
            )
        )
    return steps


def run_step(step: Step) -> StepResult:
    started_at = time.time()
    try:
        result = subprocess.run(
            step.cmd,
            cwd=os.getcwd(),
            text=True,
            capture_output=True,
            check=False,
            timeout=DEFAULT_STEP_TIMEOUT_SECONDS,
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
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.time() - started_at) * 1000)
        stdout = _as_text(exc.stdout)
        stderr = _as_text(exc.stderr)
        if not stderr:
            stderr = f"Timeout after {DEFAULT_STEP_TIMEOUT_SECONDS}s"
        return StepResult(
            name=step.name,
            command=" ".join(step.cmd),
            exit_code=124,
            duration_ms=duration_ms,
            stdout=stdout,
            stderr=stderr,
        )


def write_report(options: argparse.Namespace, results: list[StepResult]) -> str:
    report_dir = Path(os.getcwd()) / options.output_dir
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = (
        dt.datetime.now(dt.timezone.utc).isoformat().replace(":", "-").replace(".", "-")
    )
    report_path = report_dir / f"dev_ai_guard_{options.mode}_{timestamp}_py.json"
    payload = {
        "mode": options.mode,
        "dbPath": options.db_path,
        "success": all(item.exit_code == 0 for item in results),
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "steps": [asdict(item) for item in results],
        "runner": "python-fallback",
    }
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return str(report_path)


def main(argv: list[str] | None = None) -> int:
    options = parse_args(list(argv or sys.argv[1:]))
    table_presence = sqlite_table_presence(options.db_path, "ssa_table")
    auto_skipped_sync_verify = (
        options.mode == "pre-pr"
        and not options.skip_health
        and not options.skip_sync_verify
        and table_presence == "absent"
    )
    if auto_skipped_sync_verify:
        print(
            "Notice: skipping sync_verify_only because table 'ssa_table' is missing in DB."
        )
    if (
        options.mode == "pre-pr"
        and not options.skip_health
        and not options.skip_sync_verify
        and table_presence == "unknown"
    ):
        print(
            "Notice: table presence check returned unknown; keeping sync_verify_only enabled."
        )

    include_sync_verify = not auto_skipped_sync_verify and not options.skip_sync_verify
    steps = build_steps(options, include_sync_verify=include_sync_verify)

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
