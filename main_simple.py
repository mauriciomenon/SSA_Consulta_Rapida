#!/usr/bin/env python3
"""
Wrapper simples para a CLI minimalista.
Encaminha para `utils/main_simple.py` sem dependências pesadas.
"""

from utils.main_simple import simple_cli


def main() -> int:
    simple_cli()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
