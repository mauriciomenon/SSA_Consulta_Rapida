#!/usr/bin/env python3
"""
Script rápido para verificar status do banco após --rescan
"""

import sqlite3
from contextlib import closing


def main():
    print("=== VERIFICAÇÃO FINAL PÓS-RESCAN ===")

    with closing(sqlite3.connect("data/ssas.db")) as conn:
        c = conn.cursor()

        # Contar registros totais
        total = c.execute("SELECT COUNT(*) FROM ssas").fetchone()[0]

        # Contar registros únicos
        unique = c.execute("SELECT COUNT(DISTINCT numero_ssa) FROM ssas").fetchone()[0]

        print(f"INFO Total de registros no banco: {total}")
        print(f"INFO Registros únicos por numero_ssa: {unique}")

        # Verificar duplicatas
        duplicates = c.execute("""
            SELECT numero_ssa, COUNT(*)
            FROM ssas
            GROUP BY numero_ssa
            HAVING COUNT(*) > 1
        """).fetchall()

        print(f"WARN  Duplicatas encontradas: {len(duplicates)}")

        if duplicates:
            print("ERR AINDA EXISTEM DUPLICATAS!")
            print("Primeiras 5 duplicatas:")
            for ssa, count in duplicates[:5]:
                print(f"  {ssa}: {count} registros")
        else:
            print("OK NENHUMA DUPLICATA ENCONTRADA!")
            print("OK SISTEMA FUNCIONANDO CORRETAMENTE!")

        # Status final
        if total == unique:
            print(f"\n STATUS: SUCESSO - {total} registros únicos mantidos")
        else:
            print(f"\n STATUS: PROBLEMA - {total - unique} duplicatas ainda existem")


if __name__ == "__main__":
    main()
