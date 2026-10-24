"""E-25: docs e scripts versionados sem caminho absoluto pessoal.

docs/RECOVERY_BACKLOG.md fica de fora: e registro de incidente e o caminho e o fato registrado.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PERSONAL_PATH_RE = re.compile(r"/Users/menon|/home/menon|[A-Za-z]:[\\/]+Users[\\/]+(menon|mauri)", re.I)
EXEMPT = {"docs/RECOVERY_BACKLOG.md"}


def test_tracked_files_have_no_personal_absolute_paths() -> None:
    listed = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    ).stdout.split("\0")
    offenders = []
    for relative in filter(None, listed):
        if relative in EXEMPT or relative.startswith("tests/"):
            continue
        path = ROOT / relative
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if PERSONAL_PATH_RE.search(line):
                offenders.append(f"{relative}:{number}")
    assert offenders == []
