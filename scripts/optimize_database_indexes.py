#!/usr/bin/env python3
"""Verificar e otimizar índices do banco de dados SQLite."""

import os
import sqlite3
from contextlib import closing


def check_database_indexes():
    """Verifica os índices existentes no banco de dados."""
    db_path = "data/ssas.db"

    if not os.path.exists(db_path):
        print("ERR Banco de dados não encontrado em:", db_path)
        return

    print("INFO Verificando índices no banco de dados...")
    print("=" * 50)

    with closing(sqlite3.connect(db_path)) as conn:
        # Verificar índices existentes
        cursor = conn.execute("""
            SELECT name, sql 
            FROM sqlite_master 
            WHERE type='index' AND sql IS NOT NULL
            ORDER BY name
        """)

        indexes = cursor.fetchall()

        if indexes:
            print("INFO Índices existentes:")
            for name, sql in indexes:
                print(f"   {name}")
        else:
            print("WARN  Nenhum índice customizado encontrado")

        # Verificar tabelas
        cursor = conn.execute("""
            SELECT name 
            FROM sqlite_master 
            WHERE type='table'
            ORDER BY name
        """)

        tables = [row[0] for row in cursor.fetchall()]
        print(f"\nINFO Tabelas disponíveis: {', '.join(tables)}")

        # Verificar contagem de registros
        if "ssas" in tables:
            cursor = conn.execute("SELECT COUNT(*) FROM ssas")
            count = cursor.fetchone()[0]
            print(f"STAT Total de registros na tabela 'ssas': {count:,}")

        if "ssa_table" in tables:
            cursor = conn.execute("SELECT COUNT(*) FROM ssa_table")
            count = cursor.fetchone()[0]
            print(f"STAT Total de registros na tabela 'ssa_table': {count:,}")


def add_performance_indexes():
    """Adiciona índices adicionais para melhor performance."""
    db_path = "data/ssas.db"

    if not os.path.exists(db_path):
        print("ERR Banco de dados não encontrado")
        return

    print("\nSTART Adicionando índices de performance...")

    # Índices adicionais baseados na análise de uso (na tabela base ssa_table)
    additional_indexes = [
        # Índices para filtros frequentes
        (
            "idx_descricao_ssa",
            "CREATE INDEX IF NOT EXISTS idx_descricao_ssa ON ssa_table (descricao_ssa)",
        ),
        (
            "idx_descricao_execucao",
            "CREATE INDEX IF NOT EXISTS idx_descricao_execucao ON ssa_table (descricao_execucao)",
        ),
        (
            "idx_prazo_limite",
            "CREATE INDEX IF NOT EXISTS idx_prazo_limite ON ssa_table (prazo_limite)",
        ),
        # Índices compostos para queries complexas (já existem alguns)
        (
            "idx_situacao_setor_executor_new",
            "CREATE INDEX IF NOT EXISTS idx_situacao_setor_executor_new ON ssa_table (situacao, setor_executor)",
        ),
        (
            "idx_setor_emissor_situacao_new",
            "CREATE INDEX IF NOT EXISTS idx_setor_emissor_situacao_new ON ssa_table (setor_emissor, situacao)",
        ),
        # Índice para busca de texto (queries LIKE no filtro otimizado)
        (
            "idx_numero_ssa_text_search",
            "CREATE INDEX IF NOT EXISTS idx_numero_ssa_text_search ON ssa_table (numero_ssa COLLATE NOCASE)",
        ),
    ]

    created_count = 0
    with closing(sqlite3.connect(db_path)) as conn:
        for index_name, sql in additional_indexes:
            try:
                conn.execute(sql)
                print(f"  OK Criado/verificado: {index_name}")
                created_count += 1
            except Exception as e:
                print(f"  ERR Erro ao criar {index_name}: {e}")

        # Commit das mudanças
        conn.commit()

    print(f"\nOK Processo concluído: {created_count} índices processados")


def analyze_query_performance():
    """Analisa performance de queries comuns."""
    db_path = "data/ssas.db"

    if not os.path.exists(db_path):
        print("ERR Banco de dados não encontrado")
        return

    print("\nINFO Analisando performance de queries...")

    test_queries = [
        (
            "Busca por número SSA",
            "SELECT numero_ssa FROM ssas WHERE numero_ssa = '2025001' LIMIT 1",
        ),
        (
            "Filtro por situação",
            "SELECT COUNT(*) FROM ssas WHERE situacao = 'EM EXECUÇÃO'",
        ),
        (
            "Filtro por setor executor",
            "SELECT COUNT(*) FROM ssas WHERE setor_executor = 'MEDEIRO'",
        ),
        (
            "Query composta",
            "SELECT COUNT(*) FROM ssas WHERE situacao = 'EM EXECUÇÃO' AND setor_executor = 'MEDEIRO'",
        ),
    ]

    with closing(sqlite3.connect(db_path)) as conn:
        # Habilitar análise de query
        conn.execute("PRAGMA query_planner = ON")

        for desc, query in test_queries:
            try:
                # Usar EXPLAIN QUERY PLAN
                explain_query = f"EXPLAIN QUERY PLAN {query}"
                cursor = conn.execute(explain_query)
                plan = cursor.fetchall()

                print(f"\nINFO {desc}:")
                for row in plan:
                    # SQLite EXPLAIN QUERY PLAN retorna: selectid, order, from, detail
                    print(f"   {row[3]}")

            except Exception as e:
                print(f"   ERR Erro: {e}")


if __name__ == "__main__":
    check_database_indexes()
    add_performance_indexes()
    analyze_query_performance()
