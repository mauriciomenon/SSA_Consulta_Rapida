#!/usr/bin/env python3
"""Functional smoke test for the CLI entrypoint.

This smoke intentionally imports a synthetic XLSX file through the normal CLI
entrypoint with `--force-rescan` and verifies the row in SQLite. It is a gate
for import behavior, not a help/version check.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from armazenamento.identifier_utils import quote_identifier  # noqa: E402
from shared.db_names import CANONICAL_SSA_TABLE  # noqa: E402

APP_RUNTIME_NAME = "SSA_Consulta_Rapida"
SAMPLE_NUMBER = "202699001"
SAMPLE_FILE_NAME = "SSA_Smoke_01-01-2026_0100AM.xlsx"
SMOKE_TABLE_NAME = CANONICAL_SSA_TABLE


def _runtime_root(smoke_dir: Path) -> Path:
    if sys.platform == "darwin":
        return smoke_dir / "home" / "Library" / "Application Support" / APP_RUNTIME_NAME
    if sys.platform.startswith("win"):
        return smoke_dir / "appdata" / APP_RUNTIME_NAME
    return smoke_dir / "xdg" / APP_RUNTIME_NAME


def _write_smoke_workbook(sample_path: Path) -> None:
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "Numero SSA": SAMPLE_NUMBER,
                "Situacao": "ABERTA",
                "Setor Executor": "SMOKE",
                "Emitida Em": "01/01/2026",
                "Descricao": "Smoke import CLI",
            }
        ]
    ).to_excel(sample_path, index=False)


def _copy_runtime_config(runtime_root: Path) -> Path:
    config_source = REPO_ROOT / "config"
    config_target = runtime_root / "config"
    config_target.mkdir(parents=True, exist_ok=True)
    for source in config_source.iterdir():
        if source.is_file():
            target = config_target / source.name
            target.write_bytes(source.read_bytes())
    (runtime_root / "data").mkdir(parents=True, exist_ok=True)
    return config_target


def _run_cli_entry(
    smoke_dir: Path,
    runtime_root: Path,
    runtime_config: Path,
    db_path: Path,
    table_name: str,
    executable: Path | None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("SSA_BUNDLED_ROOT", None)
    env.pop("SSA_SMOKE_TEST", None)
    env["SSA_CONFIG_DIR"] = str(runtime_config)
    env["SSA_DB_PATH"] = str(db_path)
    env["SSA_RUNTIME_ROOT"] = str(runtime_root)
    env["SSA_TABLE_NAME"] = table_name
    command = [sys.executable, "-m", "launchers.cli_entry", "--force-rescan"]
    if executable is None:
        env["PYTHONPATH"] = os.pathsep.join(
            [str(REPO_ROOT), env["PYTHONPATH"]]
            if env.get("PYTHONPATH")
            else [str(REPO_ROOT)]
        )
    else:
        command = [str(executable), "--force-rescan"]
    env["HOME"] = str(smoke_dir / "home")
    env["APPDATA"] = str(smoke_dir / "appdata")
    env["LOCALAPPDATA"] = str(smoke_dir / "localappdata")
    env["XDG_DATA_HOME"] = str(smoke_dir / "xdg")
    for key in ("home", "appdata", "localappdata", "xdg"):
        (smoke_dir / key).mkdir(parents=True, exist_ok=True)

    return subprocess.run(
        command,
        input="q\n",
        capture_output=True,
        text=True,
        cwd=smoke_dir,
        env=env,
        timeout=90,
        check=False,
    )


def _count_imported_rows(db_path: Path, table_name: str) -> int:
    if not db_path.is_file():
        raise RuntimeError(f"db ausente: {db_path}")
    if table_name != SMOKE_TABLE_NAME:
        raise RuntimeError(f"tabela invalida: {table_name}")
    quoted_table_name = quote_identifier(table_name)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            f"SELECT COUNT(*) FROM {quoted_table_name} WHERE CAST(numero_ssa AS TEXT) = ?",  # nosec B608
            (SAMPLE_NUMBER,),
        ).fetchone()
    return int(row[0] if row else 0)


def _cleanup_smoke_dir(smoke_dir: Path) -> str | None:
    for attempt in range(3):
        try:
            shutil.rmtree(smoke_dir)
            return None
        except FileNotFoundError:
            return None
        except OSError as exc:
            cleanup_warning = f"{type(exc).__name__}: {exc}"
            if attempt < 2:
                time.sleep(0.25)
    return cleanup_warning


def run_smoke(executable: Path | None = None) -> dict[str, Any]:
    if executable is not None and not executable.is_file():
        return {
            "ok": False,
            "mode": "functional-import",
            "returncode": 1,
            "error": f"executavel ausente: {executable}",
        }

    raw_tmp = tempfile.mkdtemp(prefix="ssa_cli_smoke_")
    smoke_dir = Path(raw_tmp)
    result: dict[str, Any] | None = None
    try:
        runtime_root = _runtime_root(smoke_dir)
        sample_path = runtime_root / "docs_entrada" / SAMPLE_FILE_NAME
        db_path = runtime_root / "data" / "ssas.db"
        table_name = SMOKE_TABLE_NAME

        runtime_config = _copy_runtime_config(runtime_root)
        _write_smoke_workbook(sample_path)

        try:
            proc = _run_cli_entry(
                smoke_dir,
                runtime_root,
                runtime_config,
                db_path,
                table_name,
                executable,
            )
        except subprocess.TimeoutExpired as exc:
            result = {
                "ok": False,
                "mode": "functional-import",
                "returncode": 124,
                "runtime_root": str(runtime_root),
                "error": f"timeout: {exc}",
            }
            return result
        except OSError as exc:
            result = {
                "ok": False,
                "mode": "functional-import",
                "returncode": 1,
                "runtime_root": str(runtime_root),
                "error": f"{type(exc).__name__}: {exc}",
            }
            return result
        output = (proc.stdout + proc.stderr).strip()
        if proc.returncode != 0:
            result = {
                "ok": False,
                "mode": "functional-import",
                "output": output,
                "returncode": proc.returncode,
                "runtime_root": str(runtime_root),
            }
            return result
        if "Importacao concluida" not in output:
            result = {
                "ok": False,
                "mode": "functional-import",
                "output": output,
                "returncode": proc.returncode,
                "runtime_root": str(runtime_root),
                "error": "stdout nao confirmou importacao",
            }
            return result

        rows = _count_imported_rows(db_path, table_name)
        result = {
            "ok": rows >= 1,
            "mode": "functional-import",
            "output": output,
            "returncode": proc.returncode,
            "runtime_root": str(runtime_root),
            "db_path": str(db_path),
            "imported_rows": rows,
            "executable": str(executable) if executable is not None else None,
        }
        return result
    finally:
        cleanup_warning = _cleanup_smoke_dir(smoke_dir)
        if cleanup_warning is not None and result is not None:
            result["cleanup_warning"] = cleanup_warning


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test funcional da CLI")
    parser.add_argument("--json", action="store_true", help="Saida em JSON")
    parser.add_argument(
        "--executable",
        type=Path,
        default=None,
        help="Executavel de release a validar; se omitido, usa launchers.cli_entry.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    result = run_smoke(args.executable)
    exit_code = 0 if result.get("ok") else 1
    if args.json:
        print(
            json.dumps(
                {"summary": result, "exit_code": exit_code},
                ensure_ascii=True,
                indent=2,
            )
        )
    else:
        status = "OK" if result.get("ok") else "FAIL"
        print(
            "[SMOKE_CLI] "
            f"Status: {status} | mode={result.get('mode')} | "
            f"returncode={result.get('returncode')} | "
            f"imported_rows={result.get('imported_rows', 0)}"
        )
        output = str(result.get("output", ""))[:1200]
        if output:
            print("--- Output (preview) ---")
            print(output)
            print("-------------------------")
        cleanup_warning = result.get("cleanup_warning")
        if cleanup_warning:
            print(f"[SMOKE_CLI] Aviso cleanup: {cleanup_warning}")
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
