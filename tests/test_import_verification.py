#!/usr/bin/env python3
# test_import_verification.py
"""
Teste abrangente da importação de arquivos e verificação da integridade dos dados.
"""

import sys
import os
import pandas as pd
import sqlite3
from datetime import datetime
import logging

sys.path.insert(0, '.')

from core.app_logic import import_files_to_database
from armazenamento.database import get_db_connection, query_db, verify_database_integrity
from extracao.extractor import extract_data_from_excel

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_import_all_files():
    """Testa a importação de todos os arquivos."""
    print("=== TESTE DE IMPORTAÇÃO COMPLETA ===")

    docs_dir = "docs_entrada"
    db_path = "data/ssas.db"

    # Verificar se há arquivos para importar
    if not os.path.exists(docs_dir):
        print(f"❌ Diretório {docs_dir} não encontrado")
        return False

    files = [f for f in os.listdir(docs_dir) if f.endswith('.xlsx')]
    print(f"📁 Encontrados {len(files)} arquivos Excel para importação")

    # Fazer backup do banco atual se existir
    if os.path.exists(db_path):
        backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"💾 Backup criado em: {backup_path}")

    # Executar importação
    print("🔄 Iniciando importação...")
    success = import_files_to_database(docs_dir, db_path, force_import=True)

    if success:
        print("✅ Importação concluída com sucesso")
        return True
    else:
        print("❌ Falha na importação")
        return False

def analyze_database_content():
    """Analisa o conteúdo do banco após importação."""
    print("\n=== ANÁLISE DO BANCO DE DADOS ===")

    db_path = "data/ssas.db"

    try:
        with get_db_connection(db_path) as conn:
            # Contar total de registros
            cursor = conn.execute("SELECT COUNT(*) FROM ssas")
            total_records = cursor.fetchone()[0]
            print(f"📊 Total de registros: {total_records}")

            # Contar SSAs únicas
            cursor = conn.execute("SELECT COUNT(DISTINCT numero_ssa) FROM ssas WHERE numero_ssa IS NOT NULL")
            unique_ssas = cursor.fetchone()[0]
            print(f"🔢 SSAs únicas: {unique_ssas}")

            # Verificar duplicatas
            cursor = conn.execute("""
                SELECT numero_ssa, COUNT(*) as count
                FROM ssas
                WHERE numero_ssa IS NOT NULL
                GROUP BY numero_ssa
                HAVING COUNT(*) > 1
                ORDER BY count DESC
                LIMIT 10
            """)
            duplicates = cursor.fetchall()

            if duplicates:
                print(f"⚠️  SSAs duplicadas encontradas: {len(duplicates)} diferentes")
                print("Top 10 SSAs com mais duplicatas:")
                for ssa, count in duplicates[:5]:
                    print(f"  SSA {ssa}: {count} registros")
            else:
                print("✅ Nenhuma SSA duplicada encontrada")

            # Verificar colunas principais
            cursor = conn.execute("PRAGMA table_info(ssas)")
            columns = [row[1] for row in cursor.fetchall()]
            print(f"📋 Colunas no banco: {len(columns)}")

            # Verificar dados mais recentes
            cursor = conn.execute("""
                SELECT data_cadastro, COUNT(*)
                FROM ssas
                WHERE data_cadastro IS NOT NULL
                GROUP BY data_cadastro
                ORDER BY data_cadastro DESC
                LIMIT 5
            """)
            recent_dates = cursor.fetchall()

            if recent_dates:
                print("📅 Datas mais recentes no banco:")
                for date, count in recent_dates:
                    print(f"  {date}: {count} registros")

            # Verificar situações
            cursor = conn.execute("""
                SELECT situacao, COUNT(*)
                FROM ssas
                WHERE situacao IS NOT NULL
                GROUP BY situacao
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """)
            situations = cursor.fetchall()

            if situations:
                print("📈 Distribuição por situação:")
                for situation, count in situations:
                    print(f"  {situation}: {count} registros")

    except Exception as e:
        print(f"❌ Erro ao analisar banco: {e}")
        return False

    return True

def test_upsert_logic():
    """Testa especificamente a lógica de upsert (atualização vs inserção)."""
    print("\n=== TESTE DA LÓGICA DE UPSERT ===")

    db_path = "data/ssas.db"

    try:
        # Pegar algumas SSAs existentes para testar
        with get_db_connection(db_path) as conn:
            cursor = conn.execute("""
                SELECT numero_ssa, data_cadastro, situacao
                FROM ssas
                WHERE numero_ssa IS NOT NULL
                ORDER BY data_cadastro DESC
                LIMIT 5
            """)
            sample_ssas = cursor.fetchall()

        if not sample_ssas:
            print("❌ Nenhuma SSA encontrada para teste")
            return False

        print(f"🔍 Testando com {len(sample_ssas)} SSAs de exemplo:")
        for ssa, date, situation in sample_ssas:
            print(f"  SSA {ssa}: {date} - {situation}")

        # Verificar comportamento ao processar o mesmo arquivo duas vezes
        print("\n🔄 Testando reprocessamento do último arquivo...")

        docs_dir = "docs_entrada"
        files = [f for f in os.listdir(docs_dir) if f.endswith('.xlsx')]
        if files:
            # Pegar o arquivo mais recente
            latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(docs_dir, f)))
            file_path = os.path.join(docs_dir, latest_file)

            print(f"📄 Reprocessando: {latest_file}")

            # Contar registros antes
            with get_db_connection(db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM ssas")
                count_before = cursor.fetchone()[0]

            # Extrair e importar novamente
            from armazenamento.database import insert_dataframe_with_smart_upsert
            from extracao.extractor import extract_data_from_excel

            df = extract_data_from_excel(file_path)
            if df is not None and not df.empty:
                success = insert_dataframe_with_smart_upsert(df, db_path)

                # Contar registros depois
                with get_db_connection(db_path) as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM ssas")
                    count_after = cursor.fetchone()[0]

                print(f"📊 Registros antes: {count_before}")
                print(f"📊 Registros depois: {count_after}")
                print(f"📊 Diferença: {count_after - count_before}")

                if count_after == count_before:
                    print("✅ Upsert funcionando corretamente - nenhum registro duplicado")
                elif count_after > count_before:
                    print(f"ℹ️  {count_after - count_before} novos registros adicionados")
                else:
                    print("⚠️  Registros foram removidos - comportamento inesperado")

                return success
            else:
                print("❌ Falha ao extrair dados do arquivo")
                return False
        else:
            print("❌ Nenhum arquivo encontrado para teste")
            return False

    except Exception as e:
        print(f"❌ Erro no teste de upsert: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_column_mapping():
    """Verifica se todas as colunas estão sendo mapeadas corretamente."""
    print("\n=== VERIFICAÇÃO DE MAPEAMENTO DE COLUNAS ===")

    # Verificar um arquivo de exemplo
    docs_dir = "docs_entrada"
    files = [f for f in os.listdir(docs_dir) if f.endswith('.xlsx')]

    if not files:
        print("❌ Nenhum arquivo encontrado")
        return False

    # Pegar o primeiro arquivo
    sample_file = os.path.join(docs_dir, files[0])
    print(f"📄 Analisando arquivo: {files[0]}")

    try:
        # Extrair dados do arquivo
        df = extract_data_from_excel(sample_file)

        if df is None or df.empty:
            print("❌ Falha ao extrair dados")
            return False

        print(f"📊 Dados extraídos: {len(df)} linhas, {len(df.columns)} colunas")
        print("📋 Colunas encontradas:")
        for i, col in enumerate(df.columns):
            sample_values = df[col].dropna().head(3).tolist()
            print(f"  {i+1:2}. {col}")
            if sample_values:
                print(f"      Exemplos: {sample_values}")

        # Verificar no banco de dados
        db_path = "data/ssas.db"
        with get_db_connection(db_path) as conn:
            cursor = conn.execute("PRAGMA table_info(ssas)")
            db_columns = [row[1] for row in cursor.fetchall()]

        print(f"\n📋 Colunas no banco: {len(db_columns)}")
        for i, col in enumerate(db_columns):
            print(f"  {i+1:2}. {col}")

        # Verificar correspondência
        missing_in_file = set(db_columns) - set(df.columns)
        missing_in_db = set(df.columns) - set(db_columns)

        if missing_in_file:
            print(f"\n⚠️  Colunas no banco mas não no arquivo: {missing_in_file}")

        if missing_in_db:
            print(f"\n⚠️  Colunas no arquivo mas não no banco: {missing_in_db}")

        if not missing_in_file and not missing_in_db:
            print("✅ Todas as colunas estão mapeadas corretamente")

        return True

    except Exception as e:
        print(f"❌ Erro na verificação de colunas: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Executa todos os testes."""
    print("🚀 INICIANDO VERIFICAÇÃO COMPLETA DA IMPORTAÇÃO")
    print("=" * 60)

    try:
        # 1. Verificar integridade do banco
        print("🔍 Verificando integridade do banco...")
        integrity_report = verify_database_integrity("data/ssas.db")
        if integrity_report['is_valid']:
            print("✅ Banco íntegro")
        else:
            print("⚠️  Problemas no banco:", integrity_report['issues'])

        # 2. Testar importação
        import_success = test_import_all_files()

        # 3. Analisar conteúdo
        if import_success:
            analyze_database_content()

        # 4. Testar lógica de upsert
        test_upsert_logic()

        # 5. Verificar mapeamento de colunas
        verify_column_mapping()

        print("\n" + "=" * 60)
        print("✅ VERIFICAÇÃO COMPLETA CONCLUÍDA")

    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
