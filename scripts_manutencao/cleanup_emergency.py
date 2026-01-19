import os
import sqlite3
from datetime import datetime


def emergency_cleanup():
    """Limpeza emergencial para remover duplicatas massivas"""

    print(" LIMPEZA EMERGENCIAL DO BANCO DE DADOS")
    print("=" * 60)

    # Backup adicional de segurança
    backup_name = (
        f"data/ssas_emergency_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    )
    os.system(f'copy "data\\ssas.db" "{backup_name}"')
    print(f"OK Backup criado: {backup_name}")

    conn = sqlite3.connect("data/ssas.db")
    cursor = conn.cursor()

    # 1. Verificar estado atual
    cursor.execute("SELECT COUNT(*) FROM ssas")
    total_before = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(DISTINCT numero_ssa) FROM ssas WHERE numero_ssa IS NOT NULL AND numero_ssa != ''"
    )
    unique_ssas = cursor.fetchone()[0]

    print(f"\nINFO ESTADO ATUAL:")
    print(f"   Total de registros: {total_before:,}")
    print(f"   SSAs únicas: {unique_ssas:,}")
    print(f"   Duplicatas: {total_before - unique_ssas:,}")

    # 2. Criar tabela temporária com dados únicos
    print(f"\nFIX INICIANDO LIMPEZA...")

    cursor.execute(
        """
    CREATE TABLE ssas_clean AS
    SELECT * FROM ssas
    WHERE id IN (
        SELECT MIN(id)
        FROM ssas
        WHERE numero_ssa IS NOT NULL AND numero_ssa != ''
        GROUP BY numero_ssa
    )
    """
    )

    # 3. Adicionar registros sem número de SSA (mas válidos)
    cursor.execute(
        """
    INSERT INTO ssas_clean
    SELECT * FROM ssas
    WHERE (numero_ssa IS NULL OR numero_ssa = '')
    AND (descricao_ssa IS NOT NULL AND descricao_ssa != '')
    AND id NOT IN (SELECT id FROM ssas_clean)
    """
    )

    # 4. Verificar resultado
    cursor.execute("SELECT COUNT(*) FROM ssas_clean")
    total_clean = cursor.fetchone()[0]

    print(f"   OK Tabela limpa criada: {total_clean:,} registros")
    print(f"   ️ Removidos: {total_before - total_clean:,} duplicatas")

    # 5. Substituir tabela original
    cursor.execute("DROP TABLE ssas")
    cursor.execute("ALTER TABLE ssas_clean RENAME TO ssas")

    # 6. Recriar índices
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_numero_ssa ON ssas(numero_ssa)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_situacao ON ssas(situacao)")

    # 7. Verificar resultado final
    cursor.execute("SELECT COUNT(*) FROM ssas")
    total_after = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM ssas WHERE numero_ssa IS NULL OR numero_ssa = ''"
    )
    empty_ssa = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM ssas WHERE semana_cadastro IS NULL OR semana_cadastro = '' OR semana_cadastro = '-'"
    )
    empty_week = cursor.fetchone()[0]

    conn.commit()
    conn.close()

    print(f"\nOK LIMPEZA CONCLUÍDA:")
    print(f"   Registros antes: {total_before:,}")
    print(f"   Registros depois: {total_after:,}")
    print(f"   Removidos: {total_before - total_after:,}")
    print(f"   SSAs sem número: {empty_ssa:,}")
    print(f"   SSAs sem semana: {empty_week:,}")

    # 8. Verificar integridade
    conn = sqlite3.connect("data/ssas.db")
    cursor = conn.cursor()

    cursor.execute(
        """
    SELECT numero_ssa, COUNT(*) as count
    FROM ssas
    WHERE numero_ssa IS NOT NULL AND numero_ssa != ''
    GROUP BY numero_ssa
    HAVING COUNT(*) > 1
    LIMIT 5
    """
    )

    remaining_dupes = cursor.fetchall()
    if remaining_dupes:
        print(f"\nWARN AINDA EXISTEM DUPLICATAS:")
        for ssa, count in remaining_dupes:
            print(f"   SSA {ssa}: {count} cópias")
    else:
        print(f"\nOK NENHUMA DUPLICATA RESTANTE")

    conn.close()

    return total_before, total_after


if __name__ == "__main__":
    before, after = emergency_cleanup()
    print(f"\n" + "=" * 60)
    print(f"DONE EMERGÊNCIA RESOLVIDA: {before - after:,} duplicatas removidas!")
    print(
        "FIX Próximo passo: Corrigir o código de importação para evitar futuras duplicatas."
    )
