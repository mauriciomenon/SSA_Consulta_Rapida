#!/usr/bin/env python3
"""Fail fast when the local Snyk CLI installation is degraded."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def _find_expected_constants_file(snyk_path: str) -> Path | None:
    resolved = Path(snyk_path).resolve()
    for parent in resolved.parents:
        candidate = (
            parent
            / "libexec"
            / "lib"
            / "node_modules"
            / "snyk"
            / "pysrc"
            / "constants.py"
        )
        if candidate.exists():
            return candidate
    for parent in resolved.parents:
        candidate = parent / "pysrc" / "constants.py"
        if candidate.exists():
            return candidate
    return None


def main() -> int:
    snyk_path = shutil.which("snyk")
    if not snyk_path:
        print("ERR snyk CLI nao encontrado no PATH.")
        return 2

    version = subprocess.run(
        ["snyk", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    if version.returncode != 0:
        stderr = (version.stderr or "").strip()
        stdout = (version.stdout or "").strip()
        print("ERR snyk --version falhou.")
        if stdout:
            print(stdout)
        if stderr:
            print(stderr)
        return 2

    constants_file = _find_expected_constants_file(snyk_path)
    if constants_file is None:
        print("ERR instalacao local do snyk parece degradada.")
        print("INFO arquivo esperado ausente: pysrc/constants.py")
        print("INFO reinstale o CLI por metodo suportado antes de usar scans Python.")
        return 3

    print(f"OK snyk preflight ok: {constants_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
