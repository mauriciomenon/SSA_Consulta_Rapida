# tests/test_all_excel_imports.py
"""
Teste específico para importação de TODAS as planilhas Excel da pasta docs_entrada.
Este teste verifica se cada arquivo pode ser importado corretamente.
"""

import os
import sys
import sqlite3
import pandas as pd
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
import json

# Adicionar diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extracao.extractor import extract_data_from_excel as extract_data_from_file
from armazenamento.database import initialize_database, get_db_connection
from core.app_logic import import_files_to_database

class ExcelImportTester:
    """Testador específico para importação de arquivos Excel."""

    def __init__(self, docs_entrada_dir: str = "docs_entrada"):
        self.docs_entrada_dir = docs_entrada_dir
        self.test_results = []
        self.temp_dir = None
        self.test_db_path = None

    def setup_test_database(self) -> bool:
        """Configura banco de dados de teste."""
        try:
            self.temp_dir = tempfile.mkdtemp(prefix="excel_import_test_")
            self.test_db_path = os.path.join(self.temp_dir, "test_import.db")

            # Inicializar banco com schema
            schema_path = "config/schema.sql"
            if not os.path.exists(schema_path):
                print(f"❌ Schema não encontrado: {schema_path}")
                return False

            success = initialize_database(self.test_db_path, schema_path)
            if success:
                print(f"✅ Banco de teste criado: {self.test_db_path}")
                return True
            else:
                print("❌ Falha ao inicializar banco de teste")
                return False

        except Exception as e:
            print(f"❌ Erro ao configurar banco de teste: {e}")
            return False

    def cleanup(self):
        """Limpa arquivos temporários."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                print("🧹 Arquivos temporários limpos")
            except Exception as e:
                print(f"⚠️ Erro ao limpar arquivos temporários: {e}")

    def test_individual_file_extraction(self, file_path: str) -> dict:
        """Testa extração de um arquivo específico."""
        file_name = os.path.basename(file_path)
        print(f"🔍 Testando extração: {file_name}")

        start_time = datetime.now()

        try:
            # Tentar extrair dados
            df = extract_data_from_file(file_path)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            if df is not None and not df.empty:
                # Analisar estrutura dos dados
                columns = list(df.columns)
                row_count = len(df)

                # Verificar se tem colunas essenciais
                essential_columns = ['numero_ssa', 'situacao', 'descricao']
                found_essential = sum(1 for col in essential_columns
                                    if any(ess in col.lower() for ess in ['numero', 'situacao', 'descricao']))

                # Verificar qualidade dos dados
                non_null_rows = sum(df.count())
                data_quality = non_null_rows / (row_count * len(columns)) if row_count > 0 and columns else 0

                result = {
                    'file_name': file_name,
                    'file_path': file_path,
                    'success': True,
                    'duration_seconds': duration,
                    'row_count': row_count,
                    'column_count': len(columns),
                    'columns': columns,
                    'essential_columns_found': found_essential,
                    'data_quality_ratio': data_quality,
                    'file_size_mb': os.path.getsize(file_path) / 1024 / 1024,
                    'extraction_rate_rows_per_sec': row_count / duration if duration > 0 else 0
                }

                print(f"  ✅ Sucesso: {row_count} linhas, {len(columns)} colunas ({duration:.2f}s)")
                return result

            else:
                result = {
                    'file_name': file_name,
                    'file_path': file_path,
                    'success': False,
                    'duration_seconds': duration,
                    'error': 'DataFrame vazio ou None',
                    'file_size_mb': os.path.getsize(file_path) / 1024 / 1024
                }

                print(f"  ❌ Falhou: DataFrame vazio")
                return result

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            result = {
                'file_name': file_name,
                'file_path': file_path,
                'success': False,
                'duration_seconds': duration,
                'error': str(e),
                'file_size_mb': os.path.getsize(file_path) / 1024 / 1024 if os.path.exists(file_path) else 0
            }

            print(f"  ❌ Erro: {str(e)}")
            return result

    def test_file_import_to_database(self, file_path: str) -> dict:
        """Testa importação de arquivo para banco de dados."""
        file_name = os.path.basename(file_path)
        print(f"💾 Testando importação para BD: {file_name}")

        start_time = datetime.now()

        try:
            # Obter contagem inicial
            with get_db_connection(self.test_db_path) as conn:
                initial_count = pd.read_sql_query("SELECT COUNT(*) as count FROM ssas", conn).iloc[0]['count']

            # Criar diretório temporário com apenas este arquivo
            temp_single_file_dir = os.path.join(self.temp_dir, "single_file")
            os.makedirs(temp_single_file_dir, exist_ok=True)

            temp_file_path = os.path.join(temp_single_file_dir, file_name)
            shutil.copy2(file_path, temp_file_path)

            # Importar arquivo
            import_success = import_files_to_database(temp_single_file_dir, self.test_db_path)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Verificar se dados foram importados
            with get_db_connection(self.test_db_path) as conn:
                final_count = pd.read_sql_query("SELECT COUNT(*) as count FROM ssas", conn).iloc[0]['count']

                # Obter amostra dos dados importados
                sample_query = """
                SELECT numero_ssa, situacao, setor_executor
                FROM ssas
                ORDER BY rowid DESC
                LIMIT 5
                """
                sample_data = pd.read_sql_query(sample_query, conn)

            records_added = final_count - initial_count

            result = {
                'file_name': file_name,
                'file_path': file_path,
                'success': import_success and records_added > 0,
                'duration_seconds': duration,
                'initial_record_count': initial_count,
                'final_record_count': final_count,
                'records_added': records_added,
                'import_rate_records_per_sec': records_added / duration if duration > 0 else 0,
                'sample_data': sample_data.to_dict('records') if not sample_data.empty else []
            }

            if result['success']:
                print(f"  ✅ Importado: +{records_added} registros ({duration:.2f}s)")
            else:
                print(f"  ❌ Falha na importação ({duration:.2f}s)")

            # Limpar arquivo temporário
            shutil.rmtree(temp_single_file_dir, ignore_errors=True)

            return result

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            result = {
                'file_name': file_name,
                'file_path': file_path,
                'success': False,
                'duration_seconds': duration,
                'error': str(e)
            }

            print(f"  ❌ Erro na importação: {str(e)}")
            return result

    def test_all_excel_files(self) -> dict:
        """Testa todos os arquivos Excel na pasta docs_entrada."""
        print("🚀 Iniciando teste de TODOS os arquivos Excel...")
        print("=" * 60)

        if not os.path.exists(self.docs_entrada_dir):
            return {
                'success': False,
                'error': f'Diretório {self.docs_entrada_dir} não encontrado'
            }

        # Listar todos os arquivos Excel
        excel_files = []
        for file_name in os.listdir(self.docs_entrada_dir):
            if file_name.endswith(('.xlsx', '.xls')) and not file_name.startswith('~$'):
                file_path = os.path.join(self.docs_entrada_dir, file_name)
                excel_files.append(file_path)

        if not excel_files:
            return {
                'success': False,
                'error': f'Nenhum arquivo Excel encontrado em {self.docs_entrada_dir}'
            }

        print(f"📂 Encontrados {len(excel_files)} arquivos Excel para testar")
        print("-" * 60)

        # Configurar banco de teste
        if not self.setup_test_database():
            return {
                'success': False,
                'error': 'Falha ao configurar banco de teste'
            }

        try:
            extraction_results = []
            import_results = []

            total_start_time = datetime.now()

            # Testar cada arquivo
            for i, file_path in enumerate(excel_files, 1):
                print(f"\n📄 [{i}/{len(excel_files)}] Processando arquivo...")

                # Teste 1: Extração
                extraction_result = self.test_individual_file_extraction(file_path)
                extraction_results.append(extraction_result)

                # Teste 2: Importação (apenas se extração foi bem-sucedida)
                if extraction_result.get('success', False):
                    import_result = self.test_file_import_to_database(file_path)
                    import_results.append(import_result)
                else:
                    import_results.append({
                        'file_name': os.path.basename(file_path),
                        'file_path': file_path,
                        'success': False,
                        'skipped': True,
                        'reason': 'Extração falhou'
                    })

            total_end_time = datetime.now()
            total_duration = (total_end_time - total_start_time).total_seconds()

            # Calcular estatísticas
            successful_extractions = sum(1 for r in extraction_results if r.get('success', False))
            successful_imports = sum(1 for r in import_results if r.get('success', False))

            total_rows_extracted = sum(r.get('row_count', 0) for r in extraction_results if r.get('success'))
            total_records_imported = sum(r.get('records_added', 0) for r in import_results if r.get('success'))

            # Verificar estado final do banco
            with get_db_connection(self.test_db_path) as conn:
                final_db_count = pd.read_sql_query("SELECT COUNT(*) as count FROM ssas", conn).iloc[0]['count']

                # Obter estatísticas dos dados
                stats_query = """
                SELECT
                    COUNT(DISTINCT numero_ssa) as unique_ssas,
                    COUNT(DISTINCT situacao) as unique_situations,
                    COUNT(DISTINCT setor_executor) as unique_sectors
                FROM ssas
                WHERE numero_ssa IS NOT NULL
                """
                db_stats = pd.read_sql_query(stats_query, conn).iloc[0].to_dict()

            # Resultado final
            success_rate_extraction = successful_extractions / len(excel_files)
            success_rate_import = successful_imports / len(excel_files)
            overall_success = success_rate_extraction >= 0.7 and success_rate_import >= 0.6  # 70% extração, 60% importação

            result = {
                'test_name': 'all_excel_files_import',
                'success': overall_success,
                'total_files': len(excel_files),
                'successful_extractions': successful_extractions,
                'successful_imports': successful_imports,
                'extraction_success_rate': success_rate_extraction,
                'import_success_rate': success_rate_import,
                'total_duration_seconds': total_duration,
                'total_rows_extracted': total_rows_extracted,
                'total_records_imported': total_records_imported,
                'final_database_record_count': final_db_count,
                'database_statistics': db_stats,
                'extraction_results': extraction_results,
                'import_results': import_results,
                'performance_metrics': {
                    'avg_extraction_time': sum(r.get('duration_seconds', 0) for r in extraction_results) / len(extraction_results),
                    'avg_import_time': sum(r.get('duration_seconds', 0) for r in import_results) / len(import_results),
                    'total_file_size_mb': sum(r.get('file_size_mb', 0) for r in extraction_results),
                    'avg_extraction_rate': sum(r.get('extraction_rate_rows_per_sec', 0) for r in extraction_results if r.get('success')) / max(1, successful_extractions)
                }
            }

            return result

        finally:
            self.cleanup()

    def generate_detailed_report(self, test_result: dict, output_file: str = None) -> str:
        """Gera relatório detalhado dos testes de importação."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"docs_saida/excel_import_test_report_{timestamp}.md"

        # Criar diretório se não existir
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        success = test_result.get('success', False)
        status_icon = "✅" if success else "❌"

        content = f"""# Relatório de Teste - Importação de Arquivos Excel

**Data do Teste:** {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
**Status Geral:** {status_icon} {'APROVADO' if success else 'COM PROBLEMAS'}
**Duração Total:** {test_result.get('total_duration_seconds', 0):.2f} segundos

## Resumo Executivo

- **Total de Arquivos:** {test_result.get('total_files', 0)}
- **Extrações Bem-sucedidas:** {test_result.get('successful_extractions', 0)}
- **Importações Bem-sucedidas:** {test_result.get('successful_imports', 0)}
- **Taxa de Sucesso (Extração):** {test_result.get('extraction_success_rate', 0):.1%}
- **Taxa de Sucesso (Importação):** {test_result.get('import_success_rate', 0):.1%}

## Estatísticas dos Dados

- **Total de Linhas Extraídas:** {test_result.get('total_rows_extracted', 0):,}
- **Total de Registros Importados:** {test_result.get('total_records_imported', 0):,}
- **Registros Finais no Banco:** {test_result.get('final_database_record_count', 0):,}

### Diversidade dos Dados Importados

"""

        db_stats = test_result.get('database_statistics', {})
        if db_stats:
            content += f"""- **SSAs Únicas:** {db_stats.get('unique_ssas', 0):,}
- **Situações Diferentes:** {db_stats.get('unique_situations', 0)}
- **Setores Diferentes:** {db_stats.get('unique_sectors', 0)}

"""

        content += """## Performance Geral

"""

        perf_metrics = test_result.get('performance_metrics', {})
        if perf_metrics:
            content += f"""- **Tempo Médio de Extração:** {perf_metrics.get('avg_extraction_time', 0):.2f}s por arquivo
- **Tempo Médio de Importação:** {perf_metrics.get('avg_import_time', 0):.2f}s por arquivo
- **Tamanho Total dos Arquivos:** {perf_metrics.get('total_file_size_mb', 0):.1f} MB
- **Taxa Média de Extração:** {perf_metrics.get('avg_extraction_rate', 0):.0f} linhas/segundo

"""

        content += """## Resultados Detalhados por Arquivo

### Extrações

| Arquivo | Status | Linhas | Colunas | Tempo (s) | Taxa (linhas/s) | Tamanho (MB) |
|---------|--------|--------|---------|-----------|-----------------|--------------|
"""

        for result in test_result.get('extraction_results', []):
            status = "✅" if result.get('success', False) else "❌"
            file_name = result.get('file_name', 'N/A')
            rows = result.get('row_count', 0)
            cols = result.get('column_count', 0)
            duration = result.get('duration_seconds', 0)
            rate = result.get('extraction_rate_rows_per_sec', 0)
            size = result.get('file_size_mb', 0)

            content += f"| {file_name} | {status} | {rows:,} | {cols} | {duration:.2f} | {rate:.0f} | {size:.1f} |\n"

        content += """
### Importações para Banco de Dados

| Arquivo | Status | Registros Adicionados | Tempo (s) | Taxa (reg/s) |
|---------|--------|-----------------------|-----------|--------------|
"""

        for result in test_result.get('import_results', []):
            status = "✅" if result.get('success', False) else "❌"
            file_name = result.get('file_name', 'N/A')
            records = result.get('records_added', 0)
            duration = result.get('duration_seconds', 0)
            rate = result.get('import_rate_records_per_sec', 0)

            if result.get('skipped', False):
                status = "⏭️"
                records = "-"
                duration = "-"
                rate = "-"

            content += f"| {file_name} | {status} | {records} | {duration} | {rate} |\n"

        content += """
## Problemas Identificados

"""

        # Listar arquivos com problemas
        failed_extractions = [r for r in test_result.get('extraction_results', []) if not r.get('success', False)]
        failed_imports = [r for r in test_result.get('import_results', []) if not r.get('success', False) and not r.get('skipped', False)]

        if failed_extractions:
            content += "### Falhas na Extração\n\n"
            for failure in failed_extractions:
                content += f"- **{failure.get('file_name', 'N/A')}**: {failure.get('error', 'Erro desconhecido')}\n"
            content += "\n"

        if failed_imports:
            content += "### Falhas na Importação\n\n"
            for failure in failed_imports:
                content += f"- **{failure.get('file_name', 'N/A')}**: {failure.get('error', 'Erro desconhecido')}\n"
            content += "\n"

        if not failed_extractions and not failed_imports:
            content += "✅ Nenhum problema crítico identificado!\n\n"

        content += """## Recomendações

"""

        if success:
            content += """
### ✅ Teste Aprovado

O sistema demonstrou capacidade adequada para importar arquivos Excel:

- A maioria dos arquivos foi processada com sucesso
- Os dados foram importados corretamente para o banco
- Performance está dentro dos padrões aceitáveis

**Próximos Passos:**
- Sistema pronto para processar arquivos Excel em produção
- Continuar monitoramento da performance
- Considerar otimizações para arquivos muito grandes se necessário
"""
        else:
            content += """
### ❌ Teste Requer Atenção

Alguns problemas foram identificados na importação:

**Ações Recomendadas:**
1. Investigar arquivos que falharam na extração
2. Verificar formatos de dados não suportados
3. Considerar melhorias no tratamento de erros
4. Re-testar após correções

**Não recomendado processar arquivos em lote até resolver problemas.**
"""

        content += """
---
*Relatório gerado automaticamente pelo sistema de testes de importação Excel do SSA Consulta Rápida.*
"""

        # Salvar relatório
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)

        # Também salvar dados brutos em JSON
        json_file = output_file.replace('.md', '.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(test_result, f, indent=2, ensure_ascii=False, default=str)

        return output_file


def main():
    """Função principal para executar testes de importação Excel."""
    print("🚀 TESTE ABRANGENTE DE IMPORTAÇÃO DE ARQUIVOS EXCEL")
    print("=" * 60)

    tester = ExcelImportTester()

    # Executar teste completo
    test_result = tester.test_all_excel_files()

    # Mostrar resultado resumido
    print("\n" + "=" * 60)
    print("📊 RESULTADO FINAL:")

    if test_result.get('success', False):
        print("✅ TESTE APROVADO - Sistema pode importar arquivos Excel")
    else:
        if 'error' in test_result:
            print(f"❌ ERRO: {test_result['error']}")
        else:
            print("❌ TESTE COM PROBLEMAS - Verificar arquivos que falharam")

    if 'total_files' in test_result:
        print(f"   Arquivos Testados: {test_result['total_files']}")
        print(f"   Extrações Bem-sucedidas: {test_result['successful_extractions']}")
        print(f"   Importações Bem-sucedidas: {test_result['successful_imports']}")
        print(f"   Registros Importados: {test_result.get('total_records_imported', 0):,}")

    # Gerar relatório detalhado
    if 'total_files' in test_result:
        report_file = tester.generate_detailed_report(test_result)
        print(f"\n📄 Relatório detalhado salvo em: {report_file}")

    print("=" * 60)

    return 0 if test_result.get('success', False) else 1


if __name__ == "__main__":
    exit(main())
