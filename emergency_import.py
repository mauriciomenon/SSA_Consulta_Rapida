#!/usr/bin/env python3
"""
Wrapper simples para importação de emergência (sem pandas).
Encaminha para `utils/emergency_import.py` que usa apenas SQLite.
"""

from utils.emergency_import import emergency_import


def main() -> int:
    print("Importação de emergência iniciada...")
    ok = emergency_import()
    if ok:
        print("✓ Banco de dados criado com dados de teste")
        print("✓ Agora você pode testar o main_simple.py e a GUI")
        return 0
    else:
        print("✗ Falha na criação do banco de dados")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
