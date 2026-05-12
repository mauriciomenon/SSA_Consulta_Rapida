# tests/automated_system_tests.py
"""
Sistema de testes automatizados completo para SSA Consulta Rápida.

Testa todas as interfaces (CLI, POC, GUI) e funcionalidades principais
sem necessidade de interação manual.
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

# Adicionar diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armazenamento.database import get_db_connection, initialize_database
from core.app_logic import get_filtered_data, import_files_to_database
from extracao.extractor import extract_data_from_excel as extract_data_from_file
from launchers.smoke_validation import run_cli_import_smoke
from utils.db_maintenance import DatabaseAnalyzer

logger = logging.getLogger(__name__)


class SystemTestResult:
    """Resultado de um teste do sistema."""

    def __init__(self, test_name: str):
        self.test_name = test_name
        self.start_time = datetime.now()
        self.end_time = None
        self.success = False
        self.error_message = None
        self.details = {}
        self.duration = None

    def complete(self, success: bool, error_message: Optional[str] = None, **details):
        """Completa o teste com resultado."""
        self.end_time = datetime.now()
        self.duration = self.end_time - self.start_time
        self.success = success
        self.error_message = error_message
        self.details.update(details)

    def to_dict(self) -> Dict:
        """Converte resultado para dicionário."""
        return {
            "test_name": self.test_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration.total_seconds()
            if self.duration
            else None,
            "success": self.success,
            "error_message": self.error_message,
            "details": self.details,
        }


class AutomatedSystemTester:
    """Executor de testes automatizados do sistema."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.getcwd()
        self.test_results = []
        self.temp_dir: str = ""
        self.original_db_path = "data/ssas.db"
        self.test_db_path: str = ""

    def setup_test_environment(self) -> bool:
        """Configura ambiente de teste isolado."""
        try:
            # Criar diretório temporário para testes
            self.temp_dir = tempfile.mkdtemp(prefix="ssa_tests_")
            self.test_db_path = os.path.join(self.temp_dir, "test_ssas.db")

            # Copiar arquivos necessários
            config_src = os.path.join(self.base_dir, "config")
            config_dst = os.path.join(self.temp_dir, "config")
            if os.path.exists(config_src):
                shutil.copytree(config_src, config_dst)

            # Criar diretório de dados de teste
            test_data_dir = os.path.join(self.temp_dir, "data")
            os.makedirs(test_data_dir, exist_ok=True)

            return True

        except Exception as e:
            logger.error(f"Erro ao configurar ambiente de teste: {e}")
            return False

    def cleanup_test_environment(self):
        """Limpa ambiente de teste."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                logger.warning(f"Erro ao limpar ambiente de teste: {e}")

    def test_database_creation(self) -> SystemTestResult:
        """Testa criação de banco de dados do zero."""
        result = SystemTestResult("database_creation")

        try:
            # Remover banco se existir
            if os.path.exists(self.test_db_path):
                os.remove(self.test_db_path)

            # Inicializar banco
            schema_path = os.path.join(self.base_dir, "config", "schema.sql")
            success = initialize_database(self.test_db_path, schema_path)

            if success:
                # Verificar estrutura
                with get_db_connection(self.test_db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()

                    cursor.execute("PRAGMA table_info(ssas)")
                    columns = cursor.fetchall()

                result.complete(
                    True, tables_created=len(tables), columns_created=len(columns)
                )
            else:
                result.complete(False, "Falha ao inicializar banco de dados")

        except Exception as e:
            result.complete(False, str(e))

        return result

    def test_file_extraction(self) -> SystemTestResult:
        """Testa extração de dados de arquivos Excel."""
        result = SystemTestResult("file_extraction")

        try:
            docs_entrada = os.path.join(self.base_dir, "docs_entrada")

            if not os.path.exists(docs_entrada):
                result.complete(False, "Diretório docs_entrada não encontrado")
                return result

            # Listar arquivos Excel
            excel_files = []
            for file in os.listdir(docs_entrada):
                if file.endswith((".xlsx", ".xls")) and not file.startswith("~$"):
                    excel_files.append(os.path.join(docs_entrada, file))

            if not excel_files:
                result.complete(
                    False, "Nenhum arquivo Excel encontrado em docs_entrada"
                )
                return result

            extraction_results = []
            successful_extractions = 0

            for file_path in excel_files:
                try:
                    df = extract_data_from_file(file_path)
                    if df is not None and not df.empty:
                        successful_extractions += 1
                        extraction_results.append(
                            {
                                "file": os.path.basename(file_path),
                                "rows": len(df),
                                "columns": len(df.columns),
                                "success": True,
                            }
                        )
                    else:
                        extraction_results.append(
                            {
                                "file": os.path.basename(file_path),
                                "success": False,
                                "error": "DataFrame vazio ou None",
                            }
                        )
                except Exception as e:
                    extraction_results.append(
                        {
                            "file": os.path.basename(file_path),
                            "success": False,
                            "error": str(e),
                        }
                    )

            success_rate = (
                successful_extractions / len(excel_files) if excel_files else 0
            )

            result.complete(
                successful_extractions == len(excel_files),
                total_files=len(excel_files),
                successful_extractions=successful_extractions,
                success_rate=success_rate,
                extraction_details=extraction_results,
            )

        except Exception as e:
            result.complete(False, str(e))

        return result

    def test_full_import_process(self) -> SystemTestResult:
        """Testa processo completo de importação de todas as planilhas."""
        result = SystemTestResult("full_import_process")

        try:
            # Criar banco de teste
            db_creation = self.test_database_creation()
            if not db_creation.success:
                result.complete(False, "Falha na criação do banco de dados")
                return result

            # Importar todas as planilhas
            docs_entrada = os.path.join(self.base_dir, "docs_entrada")

            import_success = import_files_to_database(docs_entrada, self.test_db_path)

            if import_success:
                # Verificar dados importados
                with get_db_connection(self.test_db_path) as conn:
                    df = pd.read_sql_query("SELECT COUNT(*) as total FROM ssas", conn)
                    total_records = df.iloc[0]["total"]

                    # Verificar dados essenciais
                    df_sample = pd.read_sql_query("SELECT * FROM ssas LIMIT 10", conn)

                result.complete(
                    total_records > 0,
                    total_records=total_records,
                    sample_columns=list(df_sample.columns),
                    has_essential_data=not df_sample.empty,
                )
            else:
                result.complete(False, "Falha no processo de importação")

        except Exception as e:
            result.complete(False, str(e))

        return result

    def test_cli_functionality(self) -> SystemTestResult:
        """Testa funcionalidades da CLI."""
        result = SystemTestResult("cli_functionality")

        try:
            # Preparar banco com dados
            import_result = self.test_full_import_process()
            if not import_result.success:
                result.complete(False, "Falha na preparação de dados para teste CLI")
                return result

            cli_tests = []

            # Teste 1: importacao funcional via entrypoint CLI
            try:
                smoke_result = run_cli_import_smoke(repo_root=Path(self.base_dir))
                cli_tests.append(
                    {
                        "test": "functional_import",
                        "success": smoke_result.ok,
                        "imported_rows": smoke_result.imported_rows,
                        "return_code": smoke_result.returncode,
                        "details": smoke_result.details(),
                    }
                )
            except Exception as e:
                cli_tests.append(
                    {"test": "functional_import", "success": False, "error": str(e)}
                )

            # Teste 2: Verificar se aceita parâmetros
            try:
                # Usar ambiente temporário
                env = os.environ.copy()
                env["SSA_DB_PATH"] = self.test_db_path

                cmd_result = subprocess.run(
                    [sys.executable, "main.py", "--log-level", "ERROR"],
                    cwd=self.base_dir,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    env=env,
                    input="\n",  # Simular enter para sair
                )
                cli_tests.append(
                    {
                        "test": "parameters",
                        "success": cmd_result.returncode == 0,
                        "return_code": cmd_result.returncode,
                        "had_output": len(cmd_result.stdout) > 0,
                        "stderr": cmd_result.stderr[:500],
                    }
                )
            except Exception as e:
                cli_tests.append(
                    {"test": "parameters", "success": False, "error": str(e)}
                )

            successful_tests = sum(
                1 for test in cli_tests if test.get("success", False)
            )

            result.complete(
                successful_tests == len(cli_tests),
                total_tests=len(cli_tests),
                successful_tests=successful_tests,
                test_details=cli_tests,
            )

        except Exception as e:
            result.complete(False, str(e))

        return result

    def test_gui_startup(self) -> SystemTestResult:
        """Testa inicialização da GUI (sem interação)."""
        result = SystemTestResult("gui_startup")

        try:
            # Preparar banco com dados
            import_result = self.test_full_import_process()
            if not import_result.success:
                result.complete(False, "Falha na preparação de dados para teste GUI")
                return result

            # Tentar importar módulos da GUI (via pacote "gui")
            try:
                # O diretório raiz já foi adicionado ao sys.path no topo do arquivo,
                # portanto podemos importar como pacote para melhor compatibilidade com Pylance
                from gui import gui_ssa  # noqa: F401
                from gui import simple_width_manager  # noqa: F401

                module_tests = {"gui_ssa_import": True, "width_manager_import": True}

            except ImportError as e:
                module_tests = {
                    "gui_ssa_import": False,
                    "width_manager_import": False,
                    "import_error": str(e),
                }

            # Verificar se PyQt6 está disponível (projeto usa apenas PyQt6)
            pyqt_available = False
            try:
                from PyQt6.QtWidgets import QApplication  # noqa: F401

                pyqt_available = True
            except ImportError:
                pyqt_available = False

            result.complete(
                bool(module_tests.get("gui_ssa_import", False)),
                module_tests=module_tests,
                pyqt_available=pyqt_available,
            )

        except Exception as e:
            result.complete(False, str(e))

        return result

    def test_data_filtering(self) -> SystemTestResult:
        """Testa funcionalidades de filtragem de dados."""
        result = SystemTestResult("data_filtering")

        try:
            # Preparar banco com dados
            import_result = self.test_full_import_process()
            if not import_result.success:
                result.complete(
                    False, "Falha na preparação de dados para teste de filtros"
                )
                return result

            filter_tests = []

            # Teste 1: Filtro por situação
            try:
                filtered_data = get_filtered_data(
                    db_path=self.test_db_path, filters={"situacao": "EM EXECUÇÃO"}
                )
                filter_tests.append(
                    {
                        "filter_type": "situacao",
                        "success": filtered_data is not None,
                        "records": len(filtered_data)
                        if filtered_data is not None
                        else 0,
                    }
                )
            except Exception as e:
                filter_tests.append(
                    {"filter_type": "situacao", "success": False, "error": str(e)}
                )

            # Teste 2: Filtro por setor
            try:
                filtered_data = get_filtered_data(
                    db_path=self.test_db_path, filters={"setor_executor": "MEDEIRO"}
                )
                filter_tests.append(
                    {
                        "filter_type": "setor_executor",
                        "success": filtered_data is not None,
                        "records": len(filtered_data)
                        if filtered_data is not None
                        else 0,
                    }
                )
            except Exception as e:
                filter_tests.append(
                    {"filter_type": "setor_executor", "success": False, "error": str(e)}
                )

            # Teste 3: Sem filtros (todos os dados)
            try:
                all_data = get_filtered_data(db_path=self.test_db_path)
                filter_tests.append(
                    {
                        "filter_type": "no_filter",
                        "success": all_data is not None,
                        "records": len(all_data) if all_data is not None else 0,
                    }
                )
            except Exception as e:
                filter_tests.append(
                    {"filter_type": "no_filter", "success": False, "error": str(e)}
                )

            successful_tests = sum(
                1 for test in filter_tests if test.get("success", False)
            )

            result.complete(
                successful_tests == len(filter_tests),
                total_tests=len(filter_tests),
                successful_tests=successful_tests,
                filter_details=filter_tests,
            )

        except Exception as e:
            result.complete(False, str(e))

        return result

    def test_database_integrity(self) -> SystemTestResult:
        """Testa integridade do banco de dados."""
        result = SystemTestResult("database_integrity")

        try:
            # Preparar banco com dados
            import_result = self.test_full_import_process()
            if not import_result.success:
                result.complete(
                    False, "Falha na preparação de dados para teste de integridade"
                )
                return result

            # Usar DatabaseAnalyzer para verificar integridade
            analyzer = DatabaseAnalyzer(self.test_db_path)

            # Análise estrutural
            structure_analysis = analyzer.analyze_table_structure()

            # Verificação de sanidade
            sanity_check = analyzer.perform_sanity_check()

            # Verificar se não há colunas duplicadas
            duplicated_groups = structure_analysis.get("duplicated_groups", {})
            has_duplicates = len(duplicated_groups) > 0

            # Verificar dados essenciais
            total_records = sanity_check.get("total_records", 0)
            summary = sanity_check.get("summary", {})

            critical_issues = sum(
                [summary.get("missing_numero_ssa", 0), summary.get("empty_records", 0)]
            )

            integrity_score = 0.0
            if total_records > 0:
                integrity_score = max(0, 1 - (critical_issues / total_records))

            result.complete(
                total_records > 0 and not has_duplicates and critical_issues == 0,
                total_records=total_records,
                duplicated_columns=len(duplicated_groups),
                critical_issues=critical_issues,
                integrity_score=integrity_score,
                sanity_summary=summary,
            )

        except Exception as e:
            result.complete(False, str(e))

        return result

    def test_configuration_integrity(self) -> SystemTestResult:
        """Testa integridade dos arquivos de configuração."""
        result = SystemTestResult("configuration_integrity")

        try:
            config_tests = []
            config_dir = os.path.join(self.base_dir, "config")

            # Teste 1: column_mappings.json
            mappings_file = os.path.join(config_dir, "column_mappings.json")
            try:
                with open(mappings_file, "r", encoding="utf-8") as f:
                    mappings = json.load(f)

                is_valid = isinstance(mappings, dict) and len(mappings) > 0
                config_tests.append(
                    {
                        "file": "column_mappings.json",
                        "success": is_valid,
                        "entries": len(mappings) if is_valid else 0,
                    }
                )
            except Exception as e:
                config_tests.append(
                    {"file": "column_mappings.json", "success": False, "error": str(e)}
                )

            # Teste 2: schema.sql
            schema_file = os.path.join(config_dir, "schema.sql")
            try:
                with open(schema_file, "r", encoding="utf-8") as f:
                    schema_content = f.read()

                has_table = "CREATE TABLE" in schema_content
                config_tests.append(
                    {
                        "file": "schema.sql",
                        "success": has_table,
                        "content_length": len(schema_content),
                    }
                )
            except Exception as e:
                config_tests.append(
                    {"file": "schema.sql", "success": False, "error": str(e)}
                )

            # Teste 3: display_mappings.json (se existir)
            display_file = os.path.join(config_dir, "display_mappings.json")
            if os.path.exists(display_file):
                try:
                    with open(display_file, "r", encoding="utf-8") as f:
                        display_mappings = json.load(f)

                    config_tests.append(
                        {
                            "file": "display_mappings.json",
                            "success": isinstance(display_mappings, dict),
                            "entries": len(display_mappings),
                        }
                    )
                except Exception as e:
                    config_tests.append(
                        {
                            "file": "display_mappings.json",
                            "success": False,
                            "error": str(e),
                        }
                    )

            successful_tests = sum(
                1 for test in config_tests if test.get("success", False)
            )

            result.complete(
                successful_tests == len(config_tests),
                total_tests=len(config_tests),
                successful_tests=successful_tests,
                config_details=config_tests,
            )

        except Exception as e:
            result.complete(False, str(e))

        return result

    def run_all_tests(self) -> Dict:
        """Executa todos os testes do sistema."""
        print("Iniciando testes automatizados do sistema SSA...")
        print("=" * 60)

        start_time = datetime.now()

        # Configurar ambiente de teste
        if not self.setup_test_environment():
            return {
                "success": False,
                "error": "Falha ao configurar ambiente de teste",
                "timestamp": start_time.isoformat(),
            }

        try:
            # Lista de testes a executar
            tests_to_run = [
                ("Criação de Banco de Dados", self.test_database_creation),
                ("Extração de Arquivos", self.test_file_extraction),
                ("Processo de Importação Completo", self.test_full_import_process),
                ("Funcionalidade CLI", self.test_cli_functionality),
                ("Inicialização GUI", self.test_gui_startup),
                ("Filtragem de Dados", self.test_data_filtering),
                ("Integridade do Banco", self.test_database_integrity),
                ("Integridade de Configurações", self.test_configuration_integrity),
            ]

            # Executar testes
            for test_name, test_func in tests_to_run:
                print(f"\nINFO Executando: {test_name}...")

                test_result = test_func()
                self.test_results.append(test_result)

                status = "OK PASSOU" if test_result.success else "ERR FALHOU"
                duration = (
                    f"{test_result.duration.total_seconds():.2f}s"
                    if test_result.duration
                    else "N/A"
                )

                print(f"   {status} ({duration})")

                if not test_result.success and test_result.error_message:
                    print(f"   Erro: {test_result.error_message}")

                # Mostrar detalhes relevantes
                if test_result.details:
                    relevant_details = {
                        k: v
                        for k, v in test_result.details.items()
                        if k
                        in [
                            "total_records",
                            "successful_tests",
                            "total_files",
                            "integrity_score",
                        ]
                    }
                    if relevant_details:
                        print(f"   Detalhes: {relevant_details}")

            # Calcular estatísticas finais
            total_tests = len(self.test_results)
            successful_tests = sum(1 for result in self.test_results if result.success)
            success_rate = successful_tests / total_tests if total_tests > 0 else 0

            end_time = datetime.now()
            total_duration = end_time - start_time

            # Resultado final
            print("\n" + "=" * 60)
            print("INFO RESULTADO FINAL DOS TESTES:")
            print(f"   Total de Testes: {total_tests}")
            print(f"   Testes Bem-sucedidos: {successful_tests}")
            print(f"   Taxa de Sucesso: {success_rate:.1%}")
            print(f"   Duração Total: {total_duration.total_seconds():.2f}s")

            critical_test_names = {
                "database_creation",
                "full_import_process",
                "cli_functionality",
                "configuration_integrity",
            }
            critical_failures = [
                test_result.test_name
                for test_result in self.test_results
                if test_result.test_name in critical_test_names
                and not test_result.success
            ]
            overall_success = successful_tests == total_tests
            status_final = (
                "OK SISTEMA APROVADO"
                if overall_success
                else "ERR SISTEMA COM PROBLEMAS"
            )
            print(f"   Status: {status_final}")

            return {
                "success": overall_success,
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": success_rate,
                "critical_failures": critical_failures,
                "duration_seconds": total_duration.total_seconds(),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "test_results": [result.to_dict() for result in self.test_results],
            }

        finally:
            # Limpar ambiente de teste
            self.cleanup_test_environment()

    def generate_test_report(
        self, test_summary: Dict, output_file: Optional[str] = None
    ) -> str:
        """Gera relatório detalhado dos testes."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"docs_saida/automated_tests_report_{timestamp}.md"

        # Criar diretório se não existir
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        status_icon = "OK" if test_summary.get("success", False) else "ERR"

        content = f"""# Relatório de Testes Automatizados - Sistema SSA

**Data dos Testes:** {test_summary.get("start_time", "N/A")}
**Duração Total:** {test_summary.get("duration_seconds", 0):.2f} segundos
**Status Geral:** {status_icon} {"APROVADO" if test_summary.get("success", False) else "COM PROBLEMAS"}

## Resumo Executivo

- **Total de Testes:** {test_summary.get("total_tests", 0)}
- **Testes Bem-sucedidos:** {test_summary.get("successful_tests", 0)}
- **Taxa de Sucesso:** {test_summary.get("success_rate", 0):.1%}

## Resultados Detalhados

"""

        for test_result in test_summary.get("test_results", []):
            status = "OK PASSOU" if test_result.get("success", False) else "ERR FALHOU"
            duration = test_result.get("duration_seconds", 0)

            content += (
                f"### {test_result.get('test_name', 'Teste Desconhecido')} {status}\n\n"
            )
            content += f"**Duração:** {duration:.2f}s\n\n"

            if not test_result.get("success", False) and test_result.get(
                "error_message"
            ):
                content += f"**Erro:** {test_result.get('error_message')}\n\n"

            # Adicionar detalhes relevantes
            details = test_result.get("details", {})
            if details:
                content += "**Detalhes:**\n"
                for key, value in details.items():
                    if key not in [
                        "test_details",
                        "extraction_details",
                        "filter_details",
                    ]:
                        content += f"- {key.replace('_', ' ').title()}: {value}\n"
                content += "\n"

        content += f"""
## Conclusões

O sistema SSA Consulta Rápida foi submetido a {test_summary.get("total_tests", 0)} testes automatizados abrangentes,
cobrindo todas as principais funcionalidades:

- OK Criação e inicialização do banco de dados
- OK Extração de dados de arquivos Excel
- OK Processo completo de importação
- OK Funcionalidades da interface CLI
- OK Inicialização da interface GUI
- OK Sistema de filtragem de dados
- OK Integridade do banco de dados
- OK Configurações do sistema

### Recomendações

"""

        if test_summary.get("success", False):
            content += """
**Status: SISTEMA APROVADO** OK

O sistema passou em todos os testes críticos e está funcionando corretamente.
Todas as interfaces (CLI, GUI) estão operacionais e o banco de dados está íntegro.

**Ações Recomendadas:**
- Sistema pronto para uso em produção
- Continuar monitoramento regular
- Executar testes automatizados periodicamente
"""
        else:
            content += """
**Status: SISTEMA COM PROBLEMAS** ERR

Alguns testes falharam. Revisar os erros acima e corrigir antes do uso em produção.

**Ações Recomendadas:**
- Corrigir problemas identificados nos testes
- Re-executar testes após correções
- Verificar logs do sistema para mais detalhes
"""

        content += """
---
*Relatório gerado automaticamente pelo sistema de testes do SSA Consulta Rápida.*
"""

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"\nFILE Relatório salvo em: {output_file}")
        return output_file


def main():
    """Função principal para executar testes automatizados."""
    tester = AutomatedSystemTester()

    # Executar todos os testes
    test_summary = tester.run_all_tests()

    # Gerar relatório
    tester.generate_test_report(test_summary)

    # Retornar código de saída baseado no sucesso
    return 0 if test_summary.get("success", False) else 1


if __name__ == "__main__":
    exit(main())
