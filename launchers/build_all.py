#!/usr/bin/env python3
"""
Compatibilidade para build completo.

Historicamente este arquivo foi usado para disparar o fluxo legado de build.
Hoje o fluxo oficial esta em launchers/build_multiplatform.py.
"""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    target = Path(__file__).with_name("build_multiplatform.py")
    if not target.exists():
        print(f"ERRO: arquivo alvo nao encontrado: {target}")
        return 1

    print(
        "ATENCAO: build_all.py e compatibilidade legada. "
        "Usar launchers/build_multiplatform.py para fluxo principal."
    )
    result = subprocess.run(
        [sys.executable, str(target), *sys.argv[1:]],
        check=False,
        timeout=1800,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
