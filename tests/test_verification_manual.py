#!/usr/bin/env python3
# test_verification_manual.py
"""
Teste manual das funcionalidades de verificação do banco de dados.
"""

import os
import sys

sys.path.insert(0, ".")

import pandas as pd

from armazenamento.database import (
    validate_dataframe_before_insert,
    verify_database_integrity,
)


def test_existing_database():
    """Testa o banco de dados existente."""
    print("=== Testando Verificação de Integridade ===")

    db_path = "data/ssas.db"
    if os.path.exists(db_path):
        print(f"Verificando banco: {db_path}")
        report = verify_database_integrity(db_path)

        print("\nResultado da verificação:")
        print(f"  Válido: {report['is_valid']}")
        print(f"  Banco existe: {report['database_exists']}")
        print(f"  Banco acessível: {report['database_accessible']}")
        print(f"  Tabela existe: {report['table_exists']}")
        print(f"  Schema válido: {report['schema_valid']}")
        print(f"  Dados consistentes: {report['data_consistent']}")
        print(f"  Espaço suficiente: {report['disk_space_sufficient']}")
        print(f"  Permissões OK: {report['file_permissions_ok']}")

        if report["issues"]:
            print("\nProblemas encontrados:")
            for issue in report["issues"]:
                print(f"  - {issue}")

        if report["warnings"]:
            print("\nAvisos:")
            for warning in report["warnings"]:
                print(f"  - {warning}")
    else:
        print(f"Banco não encontrado: {db_path}")


def test_data_validation():
    """Testa validação de dados."""
    print("\n=== Testando Validação de Dados ===")

    # Teste com dados válidos
    df_valid = pd.DataFrame(
        {
            "numero_ssa": [202312345, 202398765],
            "situacao": ["Pendente", "Executada"],
            "data_cadastro": ["2023-12-01 10:00:00", "2023-12-02 15:30:00"],
            "descricao_ssa": ["Teste 1", "Teste 2"],
        }
    )

    print("Testando dados válidos:")
    report = validate_dataframe_before_insert(df_valid)
    print(f"  Válido: {report['is_valid']}")
    print(f"  Linhas: {report['row_count']}")
    print(f"  Problemas: {len(report['issues'])}")
    print(f"  Avisos: {len(report['warnings'])}")

    # Teste com dados inválidos
    df_invalid = pd.DataFrame(
        {
            "numero_ssa": [123, "invalid", None],
            "situacao": ["Pendente", "", None],
            "data_cadastro": ["invalid-date", "2023-99-99", "2023-12-01"],
        }
    )

    print("\nTestando dados inválidos:")
    report = validate_dataframe_before_insert(df_invalid)
    print(f"  Válido: {report['is_valid']}")
    print(f"  Linhas: {report['row_count']}")
    print(f"  Problemas: {len(report['issues'])}")
    print(f"  Avisos: {len(report['warnings'])}")

    if report["warnings"]:
        print("  Avisos encontrados:")
        for warning in report["warnings"]:
            print(f"    - {warning}")


if __name__ == "__main__":
    try:
        test_existing_database()
        test_data_validation()
        print("\n Testes concluídos com sucesso!")
    except Exception as e:
        print(f"\n Erro durante os testes: {e}")
        import traceback

        traceback.print_exc()
