#!/usr/bin/env python3
"""LEGACY REFERENCE TEST (não executado em suite padrão)

Mantido apenas para contexto histórico de como era feito um teste manual de
import único baseado em arquivo Excel real. Substituído por
`tests/test_import_single_legacy_compat.py` que usa fixtures sintéticas e APIs
atuais (`insert_dataframe_to_db`). Este arquivo pode ser removido em limpeza futura.
"""
# @legacy
# Imports originais mantidos como comentário para referência histórica.
# import sys
# import pandas as pd
# from armazenamento.database import insert_data_in_database
# from extracao.extractor import extract_data_from_excel


def test_single_file():
    print("Iniciando teste...")
    try:
        # Pegar o primeiro arquivo Excel
        import os

        print("Importando os...")
        docs_path = "docs_entrada"
        print(f"Listando arquivos em {docs_path}...")
        excel_files = [f for f in os.listdir(docs_path) if f.endswith(".xlsx")]

        if not excel_files:
            print("Nenhum arquivo Excel encontrado")
            return

        test_file = os.path.join(docs_path, excel_files[0])
        print(f"Testando arquivo: {test_file}")

        # Extrair dados
        print("Importando extractor...")
        from extracao.extractor import extract_data_from_excel

        print("Extraindo dados...")
        df = extract_data_from_excel(test_file)

        if df is None or df.empty:
            print("Nenhum dado extraído")
            return

        print(f"Dados extraídos: {len(df)} registros")
        print(f"Colunas: {list(df.columns)}")

        # Inserir dados
        print("Importando database...")
        from armazenamento.database import insert_data_in_database

        print("Inserindo dados...")
        success = insert_data_in_database(df, "ssa_data.db", "ssa_table")

        if success:
            print("OK Inserção bem-sucedida!")

            # Verificar resultado
            import sqlite3

            with sqlite3.connect("ssa_data.db") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM ssa_table")
                count = cursor.fetchone()[0]
                print(f"Total de registros inseridos: {count}")
        else:
            print("ERR Falha na inserção")

    except Exception as e:
        print(f"Erro: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_single_file()
