#!/usr/bin/env python3
"""
VERIFICAÇÃO URGENTE DO BANCO DE DADOS
"""

import sqlite3

from armazenamento.identifier_utils import quote_identifier


def verificar_urgente():
    print(" VERIFICAÇÃO URGENTE DO BANCO")
    print("=" * 50)

    conn = sqlite3.connect("data/ssas.db")

    # 1. Estrutura da tabela
    print("\nINFO ESTRUTURA DA TABELA:")
    colunas = conn.execute("PRAGMA table_info(ssas)").fetchall()
    for col in colunas:
        print(f"  {col[1]} ({col[2]})")

    # 2. Amostra dos dados
    print("\nINFO AMOSTRA DOS DADOS:")
    try:
        rows = conn.execute(
            "SELECT numero_ssa, situacao, semana_cadastro, descricao_ssa FROM ssas LIMIT 5"
        ).fetchall()
        for r in rows:
            desc = (r[3][:30] + "...") if r[3] else "NULL"
            print(f"  SSA: {r[0]}, Sit: {r[1]}, Sem: {r[2]}, Desc: {desc}")
    except Exception as e:
        print(f"  ERRO: {e}")

    # 3. Verificar se numero_ssa está NULL
    print("\nINFO VERIFICAÇÃO DE NULOS:")
    try:
        nulls = conn.execute(
            "SELECT COUNT(*) FROM ssas WHERE numero_ssa IS NULL OR numero_ssa = ''"
        ).fetchone()[0]
        total = conn.execute("SELECT COUNT(*) FROM ssas").fetchone()[0]
        print(f"  Total registros: {total}")
        print(f"  Registros com numero_ssa NULL/vazio: {nulls}")
        print(f"  Registros com numero_ssa válido: {total - nulls}")
    except Exception as e:
        print(f"  ERRO: {e}")

    # 4. Verificar campos específicos que estão faltando
    print("\nINFO CAMPOS ESPECÍFICOS:")
    campos_importantes = [
        "numero_ssa",
        "semana_cadastro",
        "semana_programada",
        "data_cadastro",
    ]
    for campo in campos_importantes:
        try:
            # Verifica se a coluna existe
            existe = any(col[1] == campo for col in colunas)
            if existe:
                quoted_campo = quote_identifier(campo)
                sample = conn.execute(
                    f"SELECT {quoted_campo} FROM ssas "
                    f"WHERE {quoted_campo} IS NOT NULL AND {quoted_campo} != '' LIMIT 1"
                ).fetchone()
                print(
                    f"  {campo}: {'OK EXISTE' if sample else 'ERR VAZIO'} - Sample: {sample[0] if sample else 'N/A'}"
                )
            else:
                print(f"  {campo}: ERR NÃO EXISTE NA TABELA")
        except Exception as e:
            print(f"  {campo}: ERR ERRO - {e}")

    conn.close()


if __name__ == "__main__":
    verificar_urgente()
