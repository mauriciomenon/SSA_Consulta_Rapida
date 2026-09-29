#!/usr/bin/env python3
"""
Verificação rápida de integridade do banco após importação
"""

import sqlite3
import sys
from contextlib import closing

TABLE_NAME = "ssa_table"
COUNT_TOTAL_SQL = "SELECT COUNT(*) FROM ssa_table"
COUNT_DISTINCT_SQL = "SELECT COUNT(DISTINCT numero_ssa) FROM ssa_table"
COUNT_NULL_NUMERO_SQL = "SELECT COUNT(*) FROM ssa_table WHERE numero_ssa IS NULL"
COUNT_EMPTY_DESC_SQL = (
    "SELECT COUNT(*) FROM ssa_table WHERE descricao_ssa IS NULL OR descricao_ssa = ''"
)
SAMPLE_ROWS_SQL = "SELECT numero_ssa, situacao, descricao_ssa FROM ssa_table LIMIT 5"
STATUS_TOP_SQL = (
    "SELECT situacao, COUNT(*) FROM ssa_table "
    "GROUP BY situacao ORDER BY COUNT(*) DESC LIMIT 10"
)


def verificar_integridade():
    print("INFO VERIFICAÇÃO DE INTEGRIDADE PÓS-IMPORTAÇÃO")
    print("=" * 60)

    try:
        with closing(sqlite3.connect("data/ssas.db")) as conn:
            cursor = conn.cursor()

            # Verificações básicas
            total = cursor.execute(COUNT_TOTAL_SQL).fetchone()[0]
            unicos = cursor.execute(COUNT_DISTINCT_SQL).fetchone()[0]
            nulls_ssa = cursor.execute(COUNT_NULL_NUMERO_SQL).fetchone()[0]
            vazios_desc = cursor.execute(COUNT_EMPTY_DESC_SQL).fetchone()[0]

            print(f"INFO Total de registros: {total}")
            print(f" Registros únicos por numero_ssa: {unicos}")
            print(f"ERR Registros com numero_ssa NULL: {nulls_ssa}")
            print(f"ERR Registros sem descrição: {vazios_desc}")

            # Amostra de dados
            print("\nINFO AMOSTRA DOS DADOS:")
            amostras = cursor.execute(SAMPLE_ROWS_SQL).fetchall()
            for ssa, situacao, desc in amostras:
                desc_preview = (
                    (desc[:50] + "...")
                    if desc and len(desc) > 50
                    else (desc or "N/A")
                )
                print(f"  SSA {ssa}: {situacao} - {desc_preview}")

            # Verificar situações
            print("\nSTAT SITUAÇÕES ENCONTRADAS:")
            situacoes = cursor.execute(STATUS_TOP_SQL).fetchall()
            for sit, count in situacoes:
                print(f"  {sit}: {count} registros")

        # Status geral
        duplicatas = total - unicos
        print("\nOK RESULTADO GERAL:")
        print(
            f"  - Zero duplicatas: {'OK SIM' if duplicatas == 0 else 'ERR NÃO - ' + str(duplicatas) + ' duplicatas'}"
        )
        print(
            f"  - Dados válidos: {'OK SIM' if nulls_ssa == 0 else 'WARN ' + str(nulls_ssa) + ' registros sem numero_ssa'}"
        )
        print(f"  - Importação: {'OK SUCESSO' if total > 0 else 'ERR FALHOU'}")

        return total > 0 and duplicatas == 0

    except Exception as e:
        print(f"ERR ERRO na verificação: {e}")
        return False


if __name__ == "__main__":
    sucesso = verificar_integridade()
    sys.exit(0 if sucesso else 1)
