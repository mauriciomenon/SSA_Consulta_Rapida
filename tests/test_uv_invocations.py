"""BL-12: hooks e docs versionados chamam uv como o AGENTS manda (uv run --no-sync)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Historicos e descricao exata de script (build_nuitka_clean.bat usa --python 3.13).
HISTORICAL_OR_DESCRIPTIVE = {
    "CHANGELOG.md",
    "docs_saida/CHANGELOG_IMPLEMENTACOES.md",
    "docs/SOLUCOES_AMBIENTE_BUILD.md",
}


def test_lefthook_commands_use_no_sync() -> None:
    text = (ROOT / "lefthook.yml").read_text(encoding="utf-8")
    runs = re.findall(r"^\s*run:\s*(.+)$", text, re.M)
    assert runs, "lefthook.yml sem comandos"
    for command in runs:
        if command.startswith("uv run"):
            assert command.startswith("uv run --no-sync "), command


def test_versioned_docs_do_not_pin_python_in_uv_run() -> None:
    listed = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", "*.md"],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    ).stdout.split("\0")
    offenders = []
    for relative in filter(None, listed):
        if relative in HISTORICAL_OR_DESCRIPTIVE:
            continue
        for number, line in enumerate(
            (ROOT / relative).read_text(encoding="utf-8").splitlines(), start=1
        ):
            if re.search(r"uv (run|pip install) --python 3\.13", line):
                offenders.append(f"{relative}:{number}")
    assert offenders == []
