#!/usr/bin/env python3
"""Fail fast when the local Snyk CLI installation is degraded."""

from __future__ import annotations

import shutil
import subprocess


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

    version_text = (version.stdout or "").strip()
    if not version_text:
        print("ERR snyk --version nao retornou versao.")
        return 3

    print(f"OK snyk preflight ok: {snyk_path} ({version_text})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
