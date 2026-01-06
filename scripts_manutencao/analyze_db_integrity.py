import sqlite3
import pandas as pd

def analyze_database_integrity():
    """Analisa a integridade do banco e identifica problemas"""

    conn = sqlite3.connect('data/ssas.db')

    print("INFO ANÁLISE DE INTEGRIDADE DO BANCO DE DADOS")
    print("=" * 60)

    # 1. Estatísticas básicas
    total_records = pd.read_sql_query("SELECT COUNT(*) as total FROM ssas", conn).iloc[0]['total']
    print(f"\nINFO Total de registros: {total_records:,}")

    # 2. Verificar duplicatas por numero_ssa
    duplicates_query = """
    SELECT numero_ssa, COUNT(*) as count
    FROM ssas
    WHERE numero_ssa IS NOT NULL AND numero_ssa != ''
    GROUP BY numero_ssa
    HAVING COUNT(*) > 1
    ORDER BY count DESC
    LIMIT 10
    """

    duplicates = pd.read_sql_query(duplicates_query, conn)
    if len(duplicates) > 0:
        print(f"\nERR DUPLICATAS ENCONTRADAS:")
        print(f"   {len(duplicates)} números de SSA duplicados")
        print("   Top 10 mais duplicados:")
        for _, row in duplicates.head().iterrows():
            print(f"     SSA {row['numero_ssa']}: {row['count']} cópias")

        total_duplicated = pd.read_sql_query("""
            SELECT SUM(count-1) as total_extra FROM (
                SELECT numero_ssa, COUNT(*) as count
                FROM ssas
                WHERE numero_ssa IS NOT NULL AND numero_ssa != ''
                GROUP BY numero_ssa
                HAVING COUNT(*) > 1
            )
        """, conn).iloc[0]['total_extra']
        print(f"   ️ Total de registros duplicados para remoção: {total_duplicated:,}")
    else:
        print("\nOK Nenhuma duplicata encontrada por numero_ssa")

    # 3. Verificar campos vazios críticos
    print(f"\nINFO VERIFICAÇÃO DE CAMPOS OBRIGATÓRIOS:")

    critical_fields = [
        'numero_ssa', 'situacao_ssa', 'descricao_da_ssa',
        'local_de_execucao', 'executor', 'semana_de_cadastro'
    ]

    for field in critical_fields:
        empty_count = pd.read_sql_query(f"""
            SELECT COUNT(*) as count
            FROM ssas
            WHERE {field} IS NULL OR {field} = '' OR {field} = '-'
        """, conn).iloc[0]['count']

        if empty_count > 0:
            percentage = (empty_count / total_records) * 100
            print(f"   ERR {field}: {empty_count:,} vazios ({percentage:.1f}%)")
        else:
            print(f"   OK {field}: Todos preenchidos")

    # 4. Verificar registros completamente vazios
    empty_records = pd.read_sql_query("""
        SELECT COUNT(*) as count FROM ssas
        WHERE (numero_ssa IS NULL OR numero_ssa = '')
        AND (situacao_ssa IS NULL OR situacao_ssa = '')
        AND (descricao_da_ssa IS NULL OR descricao_da_ssa = '')
    """, conn).iloc[0]['count']

    if empty_records > 0:
        print(f"\n️ REGISTROS VAZIOS: {empty_records:,} registros sem dados essenciais")

    # 5. Análise de qualidade por data de importação (se existir campo)
    try:
        import_dates = pd.read_sql_query("""
            SELECT DATE(data_importacao) as date, COUNT(*) as count
            FROM ssas
            WHERE data_importacao IS NOT NULL
            GROUP BY DATE(data_importacao)
            ORDER BY date DESC
            LIMIT 5
        """, conn)

        if len(import_dates) > 0:
            print(f"\n IMPORTAÇÕES RECENTES:")
            for _, row in import_dates.iterrows():
                print(f"   {row['date']}: {row['count']:,} registros")
    except:
        print(f"\nWARN Campo data_importacao não encontrado")

    conn.close()

    # 6. Recomendações
    print(f"\nFIX RECOMENDAÇÕES:")
    if len(duplicates) > 0:
        print(f"   1. Remover {total_duplicated:,} registros duplicados")
    print(f"   2. Implementar verificação de duplicatas antes da inserção")
    print(f"   3. Validar campos obrigatórios na importação")
    print(f"   4. Adicionar índices únicos para prevenir duplicatas futuras")

    return {
        'total_records': total_records,
        'has_duplicates': len(duplicates) > 0,
        'duplicate_count': total_duplicated if len(duplicates) > 0 else 0,
        'empty_fields': empty_count > 0
    }

if __name__ == "__main__":
    result = analyze_database_integrity()
    print(f"\n" + "=" * 60)
    print("OK Análise concluída!")
