#!/usr/bin/env python3
"""
Versão simplificada temporária do main.py - sem pandas
"""

import os
import sqlite3


def simple_cli():
    """CLI simplificado sem pandas"""
    db_path = "data/ssas.db"

    if not os.path.exists(db_path):
        print(
            "ERR Banco de dados não encontrado. Execute emergency_import.py primeiro."
        )
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Conta total de registros
        total = cursor.execute("SELECT COUNT(*) FROM ssa_table").fetchone()[0]
        print("Pesquisa Rápida de SSAs 3.0.7")
        print(f"Base de dados: {total} registros")
        print()

        while True:
            query = input(
                f"[{total} SSAs] Buscar termos separados por vírgula ou comando: "
            ).strip()

            if query.lower() in ["exit", "quit", "sair"]:
                print("Saindo...")
                break

            if not query:
                continue

            # Busca simples
            try:
                if query.isdigit():
                    # Busca por número SSA
                    results = cursor.execute(
                        "SELECT numero_ssa, situacao, descricao_ssa, setor_executor FROM ssa_table WHERE numero_ssa = ?",
                        (int(query),),
                    ).fetchall()
                else:
                    # Busca por texto na descrição
                    results = cursor.execute(
                        "SELECT numero_ssa, situacao, descricao_ssa, setor_executor FROM ssa_table WHERE descricao_ssa LIKE ?",
                        (f"%{query}%",),
                    ).fetchall()

                if results:
                    print(f"\n{len(results)} resultado(s) encontrado(s):")
                    print("-" * 80)
                    for row in results:
                        print(
                            f"SSA: {row[0]} | Situação: {row[1]} | Executor: {row[3]}"
                        )
                        print(f"Descrição: {row[2]}")
                        print("-" * 80)
                else:
                    print(
                        "Nenhum resultado encontrado para o filtro. Tente outros termos."
                    )

            except Exception as e:
                print(f"Erro na consulta: {e}")

            print()

    finally:
        conn.close()


if __name__ == "__main__":
    simple_cli()
