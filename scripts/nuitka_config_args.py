"""Imprime os argumentos --include-data-file do Nuitka para a config versionada.

BL-11: o pacote leva so o que esta no git em config/ (mesma regra do PyInstaller
em launchers/build_multiplatform.py). Arquivos locais (gui_main_preferences.json,
filtros salvos, estado do Streamlit, .bak) ficam fora; sem eles o app usa os
padroes do codigo. Saida: uma linha, argumentos separados por espaco.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def tracked_config_files(repo_root: Path = REPO_ROOT) -> list[str]:
    """Arquivos versionados de config/ que vao no pacote (sem codigo Python)."""
    result = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "-z", "--", "config"],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    files = []
    for relative in sorted(filter(None, result.stdout.split("\0"))):
        path = Path(relative)
        if path.suffix.lower() in {".py", ".pyc"} or "__pycache__" in path.parts:
            continue
        if not (repo_root / path).is_file():
            continue
        if any(ch.isspace() for ch in relative):
            raise ValueError(f"nome com espaco nao suportado no build: {relative}")
        files.append(path.as_posix())
    if not files:
        raise ValueError("nenhum arquivo versionado em config/")
    return files


def main() -> int:
    args = [f"--include-data-file={name}={name}" for name in tracked_config_files()]
    print(" ".join(args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
