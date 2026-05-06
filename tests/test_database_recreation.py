# tests/test_database_recreation.py
"""
Teste específico para recriação completa do banco de dados.
Testa backup, limpeza, recriação e restauração de dados.
"""

import json
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

# Adicionar diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armazenamento.database import initialize_database
from core.app_logic import import_files_to_database
from tests._helpers.fake_analyzer import fake_database_analyzer_type
from utils.db_maintenance import DatabaseAnalyzer


class DatabaseRecreationTester:
    """Testador para recriação completa do banco de dados."""

    def __init__(self, original_db_path: str = "data/ssas.db"):
        self.original_db_path = original_db_path
        self.test_dir: str = ""
        self.backup_path: str = ""
        self.new_db_path: str = ""
        self.test_results = []

    def setup_test_environment(self) -> bool:
        """Configura ambiente isolado para testes."""
        try:
            self.test_dir = tempfile.mkdtemp(prefix="db_recreation_test_")
            self.backup_path = os.path.join(self.test_dir, "backup_ssas.db")
            self.new_db_path = os.path.join(self.test_dir, "new_ssas.db")

            print(f"DIR Ambiente de teste criado: {self.test_dir}")
            return True

        except Exception as e:
            print(f"ERR Erro ao configurar ambiente: {e}")
            return False

    def cleanup(self):
        """Limpa ambiente de teste."""
        if self.test_dir and os.path.exists(self.test_dir):
            try:
                shutil.rmtree(self.test_dir)
                print("CLEAN Ambiente de teste limpo")
            except Exception as e:
                print(f"WARN Erro ao limpar ambiente: {e}")

    def test_backup_creation(self) -> dict:
        """Testa criação de backup do banco original."""
        print(" Testando criação de backup...")

        start_time = datetime.now()

        try:
            if not os.path.exists(self.original_db_path):
                return {
                    "test_name": "backup_creation",
                    "success": False,
                    "error": "Banco original não encontrado",
                    "original_db_path": self.original_db_path,
                }

            # Copiar banco para backup
            shutil.copy2(self.original_db_path, self.backup_path)

            # Verificar integridade do backup
            with sqlite3.connect(self.backup_path) as conn:
                cursor = conn.cursor()

                # Verificar estrutura
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()

                # Contar registros
                cursor.execute("SELECT COUNT(*) FROM ssas")
                record_count = cursor.fetchone()[0]

                # Verificar integridade
                cursor.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()[0]

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Comparar tamanhos
            original_size = os.path.getsize(self.original_db_path)
            backup_size = os.path.getsize(self.backup_path)

            success = (
                len(tables) > 0
                and record_count > 0
                and integrity_result == "ok"
                and abs(original_size - backup_size) < 1024  # Diferença menor que 1KB
            )

            result = {
                "test_name": "backup_creation",
                "success": success,
                "duration_seconds": duration,
                "original_size_mb": original_size / 1024 / 1024,
                "backup_size_mb": backup_size / 1024 / 1024,
                "record_count": record_count,
                "table_count": len(tables),
                "integrity_check": integrity_result,
                "backup_path": self.backup_path,
            }

            if success:
                print(
                    f"  OK Backup criado: {record_count:,} registros ({duration:.2f}s)"
                )
            else:
                print("  ERR Falha na criação do backup")

            return result

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            result = {
                "test_name": "backup_creation",
                "success": False,
                "duration_seconds": duration,
                "error": str(e),
            }

            print(f"  ERR Erro na criação do backup: {e}")
            return result

    def test_clean_database_creation(self) -> dict:
        """Testa criação de novo banco limpo."""
        print("🆕 Testando criação de banco limpo...")

        start_time = datetime.now()

        try:
            # Verificar se arquivo de schema existe
            schema_path = "config/schema.sql"
            if not os.path.exists(schema_path):
                return {
                    "test_name": "clean_database_creation",
                    "success": False,
                    "error": f"Schema não encontrado: {schema_path}",
                }

            # Criar novo banco
            success = initialize_database(self.new_db_path, schema_path)

            if not success:
                return {
                    "test_name": "clean_database_creation",
                    "success": False,
                    "error": "initialize_database retornou False",
                }

            # Verificar estrutura do novo banco
            with sqlite3.connect(self.new_db_path) as conn:
                cursor = conn.cursor()

                # Verificar tabelas
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]

                # Verificar estrutura da tabela principal
                cursor.execute("PRAGMA table_info(ssas)")
                columns = cursor.fetchall()

                # Verificar índices
                cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
                indexes = cursor.fetchall()

                # Verificar se está vazio
                cursor.execute("SELECT COUNT(*) FROM ssas")
                record_count = cursor.fetchone()[0]

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Verificar se estrutura está correta
            has_ssas_table = "ssas" in tables
            has_columns = len(columns) > 0
            is_empty = record_count == 0

            success = has_ssas_table and has_columns and is_empty

            result = {
                "test_name": "clean_database_creation",
                "success": success,
                "duration_seconds": duration,
                "tables_created": tables,
                "column_count": len(columns),
                "index_count": len(indexes),
                "initial_record_count": record_count,
                "database_size_kb": os.path.getsize(self.new_db_path) / 1024,
            }

            if success:
                print(
                    f"  OK Banco limpo criado: {len(columns)} colunas ({duration:.2f}s)"
                )
            else:
                print("  ERR Falha na criação do banco limpo")

            return result

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            result = {
                "test_name": "clean_database_creation",
                "success": False,
                "duration_seconds": duration,
                "error": str(e),
            }

            print(f"  ERR Erro na criação do banco limpo: {e}")
            return result

    def test_data_reimport(self) -> dict:
        """Testa reimportação de dados do backup."""
        print("IN Testando reimportação de dados...")

        start_time = datetime.now()

        try:
            # Primeiro, extrair dados do backup para análise
            with sqlite3.connect(self.backup_path) as backup_conn:
                # Obter contagem original
                cursor = backup_conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM ssas")
                original_record_count = cursor.fetchone()[0]

                # Obter amostra de dados
                cursor.execute("""
                    SELECT numero_ssa, situacao, setor_executor
                    FROM ssas
                    LIMIT 10
                """)
                sample_original = cursor.fetchall()

            # Simular reimportação usando dados dos arquivos Excel
            docs_entrada = "docs_entrada"
            if os.path.exists(docs_entrada):
                # Importar dados dos arquivos
                import_success = import_files_to_database(
                    docs_entrada, self.new_db_path
                )

                if not import_success:
                    return {
                        "test_name": "data_reimport",
                        "success": False,
                        "error": "Falha na função import_files_to_database",
                    }
            else:
                # Se não há arquivos, copiar dados diretamente do backup
                print("  IN Copiando dados diretamente do backup...")

                with sqlite3.connect(self.backup_path) as backup_conn:
                    with sqlite3.connect(self.new_db_path) as new_conn:
                        # Copiar dados da tabela ssas
                        backup_conn.execute(
                            "ATTACH DATABASE ? AS new_db", (self.new_db_path,)
                        )
                        backup_conn.execute(
                            "INSERT INTO new_db.ssas SELECT * FROM main.ssas"
                        )
                        backup_conn.execute("DETACH DATABASE new_db")

            # Verificar dados reimportados
            with sqlite3.connect(self.new_db_path) as new_conn:
                cursor = new_conn.cursor()

                # Contar registros
                cursor.execute("SELECT COUNT(*) FROM ssas")
                new_record_count = cursor.fetchone()[0]

                # Obter amostra de dados reimportados
                cursor.execute("""
                    SELECT numero_ssa, situacao, setor_executor
                    FROM ssas
                    LIMIT 10
                """)
                sample_new = cursor.fetchall()

                # Verificar integridade
                cursor.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()[0]

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Calcular taxa de recuperação
            recovery_rate = (
                new_record_count / original_record_count
                if original_record_count > 0
                else 0
            )

            success = (
                new_record_count > 0
                and new_record_count == original_record_count
                and integrity_result == "ok"
            )

            result = {
                "test_name": "data_reimport",
                "success": success,
                "duration_seconds": duration,
                "original_record_count": original_record_count,
                "new_record_count": new_record_count,
                "recovery_rate": recovery_rate,
                "integrity_check": integrity_result,
                "sample_original": sample_original,
                "sample_new": sample_new,
                "import_rate_records_per_sec": new_record_count / duration
                if duration > 0
                else 0,
            }

            if success:
                print(
                    f"  OK Dados reimportados: {new_record_count:,} registros ({recovery_rate:.1%} recuperação)"
                )
            else:
                print(f"  ERR Falha na reimportação: {recovery_rate:.1%} recuperação")

            return result

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            result = {
                "test_name": "data_reimport",
                "success": False,
                "duration_seconds": duration,
                "error": str(e),
            }

            print(f"  ERR Erro na reimportação: {e}")
            return result

    def test_database_integrity_after_recreation(self) -> dict:
        """Testa integridade do banco após recriação."""
        print("INFO Testando integridade após recriação...")

        start_time = datetime.now()

        try:
            # Usar DatabaseAnalyzer para verificação completa
            analyzer = DatabaseAnalyzer(self.new_db_path)

            # Análise estrutural
            structure_analysis = analyzer.analyze_table_structure()

            # Verificação de sanidade
            sanity_check = analyzer.perform_sanity_check()

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Extrair métricas importantes
            total_records = sanity_check.get("total_records", 0)
            summary = sanity_check.get("summary", {})
            structure_info = structure_analysis.get("structure_info", {})

            # Calcular score de integridade
            critical_issues = sum(
                [summary.get("missing_numero_ssa", 0), summary.get("empty_records", 0)]
            )

            integrity_score = 0.0
            if total_records > 0:
                integrity_score = max(0, 1 - (critical_issues / total_records))

            # Verificar se não há colunas duplicadas
            duplicated_groups = structure_analysis.get("duplicated_groups", {})
            has_duplicates = len(duplicated_groups) > 0

            success = (
                total_records > 0
                and critical_issues == 0
                and not has_duplicates
                and structure_info.get("column_count", 0) > 0
            )

            result = {
                "test_name": "database_integrity_after_recreation",
                "success": success,
                "duration_seconds": duration,
                "total_records": total_records,
                "integrity_score": integrity_score,
                "critical_issues": critical_issues,
                "has_duplicates": has_duplicates,
                "column_count": structure_info.get("column_count", 0),
                "duplicated_groups_count": len(duplicated_groups),
                "sanity_summary": summary,
                "structure_analysis": structure_analysis,
            }

            if success:
                print(f"  OK Integridade verificada: score {integrity_score:.1%}")
            else:
                print("  ERR Problemas de integridade detectados")

            return result

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            result = {
                "test_name": "database_integrity_after_recreation",
                "success": False,
                "duration_seconds": duration,
                "error": str(e),
            }

            print(f"  ERR Erro na verificação de integridade: {e}")
            return result

    def test_performance_comparison(self) -> dict:
        """Compara performance entre banco original e recriado."""
        print("PERF Testando performance comparativa...")

        start_time = datetime.now()

        try:
            test_queries = [
                ("SELECT COUNT(*) FROM ssas", "count_all"),
                ("SELECT DISTINCT situacao FROM ssas", "distinct_situacao"),
                (
                    "SELECT * FROM ssas WHERE situacao = 'EM EXECUÇÃO' LIMIT 100",
                    "filtered_select",
                ),
            ]

            original_times = []
            new_times = []

            # Testar banco original
            if os.path.exists(self.original_db_path):
                with sqlite3.connect(self.original_db_path) as conn:
                    for query, query_name in test_queries:
                        query_start = datetime.now()
                        cursor = conn.cursor()
                        cursor.execute(query)
                        cursor.fetchall()
                        query_end = datetime.now()
                        original_times.append((query_end - query_start).total_seconds())

            # Testar banco recriado
            with sqlite3.connect(self.new_db_path) as conn:
                for query, query_name in test_queries:
                    query_start = datetime.now()
                    cursor = conn.cursor()
                    cursor.execute(query)
                    cursor.fetchall()
                    query_end = datetime.now()
                    new_times.append((query_end - query_start).total_seconds())

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Calcular métricas de performance
            avg_original_time = (
                sum(original_times) / len(original_times) if original_times else 0
            )
            avg_new_time = sum(new_times) / len(new_times) if new_times else 0

            performance_ratio = (
                avg_original_time / avg_new_time if avg_new_time > 0 else 1
            )

            performance_acceptable = performance_ratio >= 0.9

            result = {
                "test_name": "performance_comparison",
                "success": performance_acceptable,
                "duration_seconds": duration,
                "original_avg_time": avg_original_time,
                "new_avg_time": avg_new_time,
                "performance_ratio": performance_ratio,
                "original_query_times": original_times,
                "new_query_times": new_times,
                "performance_acceptable": performance_acceptable,
            }

            if performance_acceptable:
                print(f"  OK Performance aceitável: {performance_ratio:.2f}x")
            else:
                print(f"  WARN Performance degradada: {performance_ratio:.2f}x")

            return result

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            result = {
                "test_name": "performance_comparison",
                "success": False,
                "duration_seconds": duration,
                "error": str(e),
            }

            print(f"  ERR Erro na comparação de performance: {e}")
            return result

    def run_complete_recreation_test(self) -> dict:
        """Executa teste completo de recriação do banco."""
        print("START TESTE COMPLETO DE RECRIAÇÃO DO BANCO DE DADOS")
        print("=" * 60)

        if not self.setup_test_environment():
            return {"success": False, "error": "Falha ao configurar ambiente de teste"}

        try:
            total_start_time = datetime.now()

            # Lista de testes a executar em ordem
            tests = [
                self.test_backup_creation,
                self.test_clean_database_creation,
                self.test_data_reimport,
                self.test_database_integrity_after_recreation,
                self.test_performance_comparison,
            ]

            test_results = []

            # Executar cada teste
            for test_func in tests:
                print()  # Linha em branco
                result = test_func()
                test_results.append(result)

                # Se um teste crítico falhar, parar
                if not result.get("success", False) and test_func.__name__ in [
                    "test_backup_creation",
                    "test_clean_database_creation",
                ]:
                    print(f"\nERR Teste crítico falhou: {test_func.__name__}")
                    break

            total_end_time = datetime.now()
            total_duration = (total_end_time - total_start_time).total_seconds()

            # Calcular resultado final
            successful_tests = sum(
                1 for result in test_results if result.get("success", False)
            )
            total_tests = len(test_results)
            success_rate = successful_tests / total_tests if total_tests > 0 else 0

            overall_success = successful_tests == total_tests

            final_result = {
                "test_name": "complete_database_recreation",
                "success": overall_success,
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": success_rate,
                "total_duration_seconds": total_duration,
                "test_results": test_results,
                "timestamp": datetime.now().isoformat(),
            }

            # Mostrar resultado final
            print("\n" + "=" * 60)
            print("INFO RESULTADO FINAL DA RECRIAÇÃO:")
            print(f"   Testes Executados: {total_tests}")
            print(f"   Testes Bem-sucedidos: {successful_tests}")
            print(f"   Taxa de Sucesso: {success_rate:.1%}")
            print(f"   Duração Total: {total_duration:.2f}s")

            status = (
                "OK RECRIAÇÃO APROVADA"
                if overall_success
                else "ERR RECRIAÇÃO COM PROBLEMAS"
            )
            print(f"   Status: {status}")

            return final_result

        finally:
            self.cleanup()

    def generate_recreation_report(
        self, test_result: dict, output_file: Optional[str] = None
    ) -> str:
        """Gera relatório detalhado do teste de recriação."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"docs_saida/database_recreation_report_{timestamp}.md"

        # Criar diretório se não existir
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        success = test_result.get("success", False)
        status_icon = "OK" if success else "ERR"

        content = f"""# Relatório de Teste - Recriação Completa do Banco de Dados

**Data do Teste:** {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
**Status Geral:** {status_icon} {"APROVADO" if success else "COM PROBLEMAS"}
**Duração Total:** {test_result.get("total_duration_seconds", 0):.2f} segundos

## Resumo Executivo

- **Total de Testes:** {test_result.get("total_tests", 0)}
- **Testes Bem-sucedidos:** {test_result.get("successful_tests", 0)}
- **Taxa de Sucesso:** {test_result.get("success_rate", 0):.1%}

## Processo de Recriação Testado

1. **Backup do Banco Original** INFO
2. **Criação de Banco Limpo** 🆕
3. **Reimportação de Dados** IN
4. **Verificação de Integridade** INFO
5. **Comparação de Performance** PERF

## Resultados Detalhados

"""

        for result in test_result.get("test_results", []):
            test_name = result.get("test_name", "Teste Desconhecido")
            success = result.get("success", False)
            duration = result.get("duration_seconds", 0)
            status_icon = "OK" if success else "ERR"

            content += f"### {test_name.replace('_', ' ').title()} {status_icon}\n\n"
            content += f"**Duração:** {duration:.2f}s\n\n"

            # Adicionar detalhes específicos por tipo de teste
            if test_name == "backup_creation":
                if success:
                    content += f"- **Registros no Backup:** {result.get('record_count', 0):,}\n"
                    content += f"- **Tamanho do Backup:** {result.get('backup_size_mb', 0):.1f} MB\n"
                    content += (
                        f"- **Integridade:** {result.get('integrity_check', 'N/A')}\n"
                    )
                else:
                    content += (
                        f"- **Erro:** {result.get('error', 'Erro desconhecido')}\n"
                    )

            elif test_name == "clean_database_creation":
                if success:
                    content += (
                        f"- **Colunas Criadas:** {result.get('column_count', 0)}\n"
                    )
                    content += (
                        f"- **Índices Criados:** {result.get('index_count', 0)}\n"
                    )
                    content += f"- **Tamanho Inicial:** {result.get('database_size_kb', 0):.1f} KB\n"
                else:
                    content += (
                        f"- **Erro:** {result.get('error', 'Erro desconhecido')}\n"
                    )

            elif test_name == "data_reimport":
                if success:
                    content += f"- **Registros Originais:** {result.get('original_record_count', 0):,}\n"
                    content += f"- **Registros Reimportados:** {result.get('new_record_count', 0):,}\n"
                    content += f"- **Taxa de Recuperação:** {result.get('recovery_rate', 0):.1%}\n"
                    content += f"- **Taxa de Importação:** {result.get('import_rate_records_per_sec', 0):.0f} registros/s\n"
                else:
                    content += (
                        f"- **Erro:** {result.get('error', 'Erro desconhecido')}\n"
                    )

            elif test_name == "database_integrity_after_recreation":
                if success:
                    content += f"- **Score de Integridade:** {result.get('integrity_score', 0):.1%}\n"
                    content += f"- **Total de Registros:** {result.get('total_records', 0):,}\n"
                    content += f"- **Problemas Críticos:** {result.get('critical_issues', 0)}\n"
                    content += f"- **Colunas Duplicadas:** {'Não' if not result.get('has_duplicates', False) else 'Sim'}\n"
                else:
                    content += (
                        f"- **Erro:** {result.get('error', 'Erro desconhecido')}\n"
                    )

            elif test_name == "performance_comparison":
                if success:
                    content += f"- **Tempo Médio Original:** {result.get('original_avg_time', 0):.3f}s\n"
                    content += f"- **Tempo Médio Novo:** {result.get('new_avg_time', 0):.3f}s\n"
                    content += f"- **Ratio de Performance:** {result.get('performance_ratio', 0):.2f}x\n"
                    content += f"- **Performance Aceitável:** {'Sim' if result.get('performance_acceptable', False) else 'Não'}\n"
                else:
                    content += (
                        f"- **Erro:** {result.get('error', 'Erro desconhecido')}\n"
                    )

            content += "\n"

        content += """## Análise e Recomendações

"""

        if success:
            content += """### OK Recriação Aprovada

O processo de recriação do banco de dados foi bem-sucedido:

- **Backup criado com segurança** OK
- **Novo banco inicializado corretamente** OK
- **Dados reimportados com alta fidelidade** OK
- **Integridade mantida** OK
- **Performance aceitável** OK

**Recomendações:**
- O sistema pode ser usado para recriação em produção
- Manter processo de backup regular
- Monitorar performance após recriação
- Documentar procedimento para equipe

**Processo Recomendado para Produção:**
1. Fazer backup completo do banco atual
2. Parar sistema temporariamente
3. Recriar banco com schema otimizado
4. Reimportar dados dos arquivos Excel mais recentes
5. Verificar integridade e performance
6. Reativar sistema
"""
        else:
            content += """### ERR Recriação Requer Atenção

Alguns problemas foram identificados no processo:

**Ações Necessárias:**
1. INFO Investigar falhas específicas nos testes
2. FIX Corrigir problemas identificados
3. TEST Re-executar testes após correções
4. INFO Validar processo manualmente

**WARN NÃO recomendado executar recriação em produção até resolver todos os problemas.**

**Checklist de Verificação:**
- [ ] Backup está sendo criado corretamente?
- [ ] Schema está atualizado e correto?
- [ ] Processo de importação está funcionando?
- [ ] Dados estão sendo preservados?
- [ ] Performance está aceitável?
"""

        content += """
---

## Informações Técnicas

**Banco Original:** `data/ssas.db`
**Schema Usado:** `config/schema.sql`
**Arquivos de Dados:** `docs_entrada/*.xlsx`

**Criterios de Aprovacao:**
- Todos os testes obrigatorios devem passar
- Recuperacao de dados deve preservar 100% dos registros
- Integridade nao pode ter issues criticos
- Performance deve manter performance_ratio minimo de 0.9

---
*Relatório gerado automaticamente pelo sistema de testes de recriação do SSA Consulta Rápida.*
"""

        # Salvar relatório
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)

        # Salvar dados em JSON
        json_file = output_file.replace(".md", ".json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(test_result, f, indent=2, ensure_ascii=False, default=str)

        return output_file


def _recreation_result(test_name: str, success: bool) -> dict:
    return {"test_name": test_name, "success": success}


def test_run_complete_recreation_requires_every_step_to_pass(monkeypatch) -> None:
    tester = DatabaseRecreationTester()
    monkeypatch.setattr(tester, "setup_test_environment", lambda: True)
    monkeypatch.setattr(tester, "cleanup", lambda: None)
    monkeypatch.setattr(
        tester,
        "test_backup_creation",
        lambda: _recreation_result("backup_creation", True),
    )
    monkeypatch.setattr(
        tester,
        "test_clean_database_creation",
        lambda: _recreation_result("clean_database_creation", True),
    )
    monkeypatch.setattr(
        tester,
        "test_data_reimport",
        lambda: _recreation_result("data_reimport", True),
    )
    monkeypatch.setattr(
        tester,
        "test_database_integrity_after_recreation",
        lambda: _recreation_result("database_integrity_after_recreation", True),
    )
    monkeypatch.setattr(
        tester,
        "test_performance_comparison",
        lambda: _recreation_result("performance_comparison", False),
    )

    result = tester.run_complete_recreation_test()

    assert result["success"] is False
    assert result["total_tests"] == 5
    assert result["successful_tests"] == 4
    assert result["success_rate"] == 0.8


def test_data_reimport_requires_full_record_recovery(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    docs_entrada = tmp_path / "docs_entrada"
    docs_entrada.mkdir()
    backup_path = tmp_path / "backup_ssas.db"
    new_db_path = tmp_path / "new_ssas.db"

    for db_path in (backup_path, new_db_path):
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE ssas (
                    numero_ssa TEXT,
                    situacao TEXT,
                    setor_executor TEXT
                )
                """
            )

    with sqlite3.connect(backup_path) as conn:
        conn.executemany(
            "INSERT INTO ssas VALUES (?, ?, ?)",
            [(str(index), "ABERTA", "SETOR") for index in range(10)],
        )

    def _partial_import(_docs_entrada: str, target_db_path: str) -> bool:
        with sqlite3.connect(target_db_path) as conn:
            conn.executemany(
                "INSERT INTO ssas VALUES (?, ?, ?)",
                [(str(index), "ABERTA", "SETOR") for index in range(8)],
            )
        return True

    monkeypatch.setattr(sys.modules[__name__], "import_files_to_database", _partial_import)

    tester = DatabaseRecreationTester()
    tester.backup_path = str(backup_path)
    tester.new_db_path = str(new_db_path)

    result = tester.test_data_reimport()

    assert result["success"] is False
    assert result["original_record_count"] == 10
    assert result["new_record_count"] == 8
    assert result["recovery_rate"] == 0.8


def test_recreation_report_documents_strict_approval_criteria(tmp_path) -> None:
    tester = DatabaseRecreationTester()
    report_path = tmp_path / "report.md"

    tester.generate_recreation_report(
        {
            "success": True,
            "test_results": [],
            "total_tests": 0,
            "successful_tests": 0,
            "success_rate": 0,
        },
        str(report_path),
    )

    content = report_path.read_text(encoding="utf-8")

    assert "Todos os testes obrigatorios devem passar" in content
    assert "100% dos registros" in content
    assert "performance_ratio minimo de 0.9" in content


def test_performance_comparison_rejects_half_speed_recreation(
    monkeypatch,
    tmp_path,
) -> None:
    original_db_path = tmp_path / "original.db"
    new_db_path = tmp_path / "new.db"
    for db_path in (original_db_path, new_db_path):
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE ssas (
                    numero_ssa TEXT,
                    situacao TEXT,
                    setor_executor TEXT
                )
                """
            )
            conn.execute("INSERT INTO ssas VALUES ('1', 'ABERTA', 'SETOR')")

    class FakeDateTime:
        values = iter(
            [
                datetime(2026, 1, 1, 0, 0, 0),
                datetime(2026, 1, 1, 0, 0, 1),
                datetime(2026, 1, 1, 0, 0, 2),
                datetime(2026, 1, 1, 0, 0, 3),
                datetime(2026, 1, 1, 0, 0, 4),
                datetime(2026, 1, 1, 0, 0, 5),
                datetime(2026, 1, 1, 0, 0, 6),
                datetime(2026, 1, 1, 0, 0, 7),
                datetime(2026, 1, 1, 0, 0, 9),
                datetime(2026, 1, 1, 0, 0, 10),
                datetime(2026, 1, 1, 0, 0, 12),
                datetime(2026, 1, 1, 0, 0, 13),
                datetime(2026, 1, 1, 0, 0, 15),
                datetime(2026, 1, 1, 0, 0, 16),
            ]
        )

        @classmethod
        def now(cls):
            return next(cls.values)

    monkeypatch.setattr(sys.modules[__name__], "datetime", FakeDateTime)

    tester = DatabaseRecreationTester(str(original_db_path))
    tester.new_db_path = str(new_db_path)

    result = tester.test_performance_comparison()

    assert result["success"] is False
    assert result["performance_ratio"] == 0.5


def test_recreation_integrity_requires_zero_critical_issues(
    monkeypatch,
    tmp_path,
) -> None:
    tester = DatabaseRecreationTester()
    tester.new_db_path = str(tmp_path / "new_ssas.db")

    monkeypatch.setattr(
        sys.modules[__name__],
        "DatabaseAnalyzer",
        fake_database_analyzer_type(
            structure={
                "duplicated_groups": {},
                "structure_info": {"column_count": 3},
            },
            sanity={
                "total_records": 10,
                "summary": {"missing_numero_ssa": 1, "empty_records": 0},
            },
        ),
    )

    result = tester.test_database_integrity_after_recreation()

    assert result["success"] is False
    assert result["critical_issues"] == 1


def test_recreation_integrity_reports_zero_score_for_empty_database(
    monkeypatch,
    tmp_path,
) -> None:
    tester = DatabaseRecreationTester()
    tester.new_db_path = str(tmp_path / "new_ssas.db")

    monkeypatch.setattr(
        sys.modules[__name__],
        "DatabaseAnalyzer",
        fake_database_analyzer_type(
            structure={
                "duplicated_groups": {},
                "structure_info": {"column_count": 3},
            },
            sanity={"total_records": 0, "summary": {}},
        ),
    )

    result = tester.test_database_integrity_after_recreation()

    assert result["success"] is False
    assert result["integrity_score"] == 0.0


def main():
    """Função principal para executar teste de recriação."""
    print("START TESTE DE RECRIAÇÃO COMPLETA DO BANCO DE DADOS")
    print("=" * 70)

    tester = DatabaseRecreationTester()

    # Executar teste completo
    test_result = tester.run_complete_recreation_test()

    # Gerar relatório
    report_file = tester.generate_recreation_report(test_result)

    print(f"\nFILE Relatório detalhado salvo em: {report_file}")
    print("=" * 70)

    return 0 if test_result.get("success", False) else 1


if __name__ == "__main__":
    exit(main())
