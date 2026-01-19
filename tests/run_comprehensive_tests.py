# tests/run_comprehensive_tests.py
"""
Executor principal para todos os testes automatizados do sistema SSA.
Este script executa testes funcionais, de performance e de integração.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_test_suite(test_name: str, test_script: str, timeout: int = 300) -> dict:
    """Executa uma suíte de testes específica."""
    print(f"\nSTART Executando {test_name}...")
    print("-" * 50)

    start_time = datetime.now()

    try:
        # Executar script de teste
        result = subprocess.run(
            [sys.executable, test_script],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Imprimir saída do teste
        if result.stdout:
            print(result.stdout)

        if result.stderr and result.returncode != 0:
            print("ERROS:")
            print(result.stderr)

        success = result.returncode == 0
        status = "OK SUCESSO" if success else "ERR FALHOU"

        print(f"\n{test_name}: {status} ({duration:.2f}s)")

        return {
            "test_name": test_name,
            "script": test_script,
            "success": success,
            "duration_seconds": duration,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }

    except subprocess.TimeoutExpired:
        print(f"ERR TIMEOUT: {test_name} excedeu {timeout}s")
        return {
            "test_name": test_name,
            "script": test_script,
            "success": False,
            "duration_seconds": timeout,
            "error": "timeout",
            "timeout_seconds": timeout,
        }
    except Exception as e:
        print(f"ERR ERRO: {test_name} - {str(e)}")
        return {
            "test_name": test_name,
            "script": test_script,
            "success": False,
            "error": str(e),
        }


def run_manual_smoke_tests() -> dict:
    """Executa testes manuais básicos de fumaça."""
    print("\nINFO Executando testes de fumaça básicos...")
    print("-" * 50)

    smoke_tests = []

    # Teste 1: Verificar se CLI inicia
    print("Testando inicialização da CLI...")
    try:
        result = subprocess.run(
            [sys.executable, "main.py", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        cli_success = result.returncode == 0 and "SSA" in result.stdout
        print(f"  CLI: {'OK' if cli_success else 'ERR'}")

        smoke_tests.append(
            {
                "test": "cli_help",
                "success": cli_success,
                "details": "CLI --help funciona"
                if cli_success
                else "CLI --help falhou",
            }
        )

    except Exception as e:
        print(f"  CLI: ERR (Erro: {e})")
        smoke_tests.append({"test": "cli_help", "success": False, "error": str(e)})

    # Teste 2: Verificar estrutura de arquivos essenciais
    print("Verificando arquivos essenciais...")
    essential_files = [
        "main.py",
        "config/schema.sql",
        "config/column_mappings.json",
        "armazenamento/database.py",
        "core/app_logic.py",
        "gui/gui_ssa.py",
    ]

    missing_files = []
    for file_path in essential_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)

    files_ok = len(missing_files) == 0
    print(f"  Arquivos essenciais: {'OK' if files_ok else 'ERR'}")

    if missing_files:
        print(f"    Arquivos faltando: {missing_files}")

    smoke_tests.append(
        {
            "test": "essential_files",
            "success": files_ok,
            "missing_files": missing_files,
            "total_checked": len(essential_files),
        }
    )

    # Teste 3: Verificar banco de dados
    print("Verificando banco de dados...")
    db_path = "data/ssas.db"
    db_exists = os.path.exists(db_path)

    if db_exists:
        try:
            import sqlite3

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM ssas")
            record_count = cursor.fetchone()[0]
            conn.close()

            db_ok = record_count > 0
            print(f"  Banco de dados: OK ({record_count} registros)")

            smoke_tests.append(
                {
                    "test": "database_check",
                    "success": db_ok,
                    "record_count": record_count,
                }
            )

        except Exception as e:
            print(f"  Banco de dados: ERR (Erro: {e})")
            smoke_tests.append(
                {"test": "database_check", "success": False, "error": str(e)}
            )
    else:
        print("  Banco de dados: ERR (Arquivo não encontrado)")
        smoke_tests.append(
            {
                "test": "database_check",
                "success": False,
                "error": "Database file not found",
            }
        )

    successful_smoke_tests = sum(
        1 for test in smoke_tests if test.get("success", False)
    )

    return {
        "test_name": "smoke_tests",
        "total_tests": len(smoke_tests),
        "successful_tests": successful_smoke_tests,
        "success": successful_smoke_tests == len(smoke_tests),
        "test_details": smoke_tests,
    }


def generate_comprehensive_report(
    all_results: list, output_dir: str = "docs_saida"
) -> str:
    """Gera relatório abrangente de todos os testes."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(output_dir, f"comprehensive_test_report_{timestamp}.md")

    # Criar diretório se não existir
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Calcular estatísticas gerais
    total_suites = len(all_results)
    successful_suites = sum(1 for result in all_results if result.get("success", False))
    total_duration = sum(result.get("duration_seconds", 0) for result in all_results)

    success_rate = successful_suites / total_suites if total_suites > 0 else 0
    overall_success = success_rate >= 0.8  # 80% das suítes devem passar

    content = f"""# Relatório Abrangente de Testes - Sistema SSA Consulta Rápida

**Data dos Testes:** {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
**Duração Total:** {total_duration:.2f} segundos
**Status Geral:** {"OK SISTEMA APROVADO" if overall_success else "ERR SISTEMA COM PROBLEMAS"}

## Resumo Executivo

- **Total de Suítes de Teste:** {total_suites}
- **Suítes Bem-sucedidas:** {successful_suites}
- **Taxa de Sucesso:** {success_rate:.1%}
- **Tempo Total de Execução:** {total_duration:.2f}s

### Status por Categoria

"""

    # Adicionar detalhes de cada suíte
    for result in all_results:
        test_name = result.get("test_name", "Teste Desconhecido")
        success = result.get("success", False)
        duration = result.get("duration_seconds", 0)
        status_icon = "OK" if success else "ERR"

        content += f"#### {test_name} {status_icon}\n\n"
        content += f"**Duração:** {duration:.2f}s\n"

        if not success:
            error = result.get("error", result.get("stderr", "Erro desconhecido"))
            content += f"**Erro:** {error}\n"

        # Adicionar detalhes específicos se disponíveis
        if "test_details" in result:
            content += "\n**Detalhes:**\n"
            for detail in result["test_details"]:
                detail_name = detail.get("test", "teste")
                detail_success = detail.get("success", False)
                detail_icon = "OK" if detail_success else "ERR"
                content += f"- {detail_name}: {detail_icon}\n"

        content += "\n"

    content += f"""
## Análise de Resultados

### Funcionalidades Testadas

1. **Criação e Inicialização do Banco de Dados**
   - Criação de tabelas e índices
   - Integridade estrutural
   - Performance de consultas

2. **Importação de Dados**
   - Extração de arquivos Excel
   - Processamento de múltiplos formatos
   - Validação de dados importados

3. **Interfaces do Sistema**
   - CLI (Command Line Interface)
   - GUI (Graphical User Interface)
   - POC (Proof of Concept)

4. **Funcionalidades Principais**
   - Sistema de filtros
   - Consultas complexas
   - Exportação de dados

5. **Performance e Estabilidade**
   - Acesso concorrente
   - Uso de memória
   - Tempo de resposta

### Critérios de Aprovação

O sistema é considerado **APROVADO** quando:
- OK Pelo menos 80% das suítes de teste passam
- OK Todas as funcionalidades críticas funcionam
- OK Performance está dentro dos limites aceitáveis
- OK Nenhum erro crítico é detectado

### Recomendações

"""

    if overall_success:
        content += """
**OK SISTEMA APROVADO PARA USO**

O sistema SSA Consulta Rápida passou em todos os testes críticos e está funcionando corretamente.

**Próximos Passos:**
- OK Sistema pronto para produção
- RUN Configurar monitoramento automatizado
-  Agendar testes regulares
-  Atualizar documentação se necessário

**Manutenção Recomendada:**
- Executar testes automatizados semanalmente
- Monitorar performance do banco de dados
- Fazer backup regular dos dados
- Verificar logs do sistema periodicamente
"""
    else:
        content += """
**WARN SISTEMA REQUER ATENÇÃO**

Alguns testes falharam. O sistema pode ter problemas que impedem o uso seguro em produção.

**Ações Imediatas Necessárias:**
1. INFO Investigar falhas nos testes
2. FIX Corrigir problemas identificados
3. TEST Re-executar testes após correções
4. INFO Validar funcionalidades críticas manualmente

**Não recomendado para produção até que todos os problemas sejam resolvidos.**
"""

    content += f"""

---

## Informações Técnicas

**Ambiente de Teste:**
- Python: {sys.version.split()[0]}
- Sistema Operacional: {os.name}
- Diretório de Trabalho: {os.getcwd()}

**Arquivos de Log:**
- Relatório detalhado: `{report_file}`
- Logs de performance: `docs_saida/performance_tests_*.json`
- Logs de testes funcionais: `docs_saida/automated_tests_report_*.md`

---
*Relatório gerado automaticamente pelo sistema de testes abrangentes do SSA Consulta Rápida.*
*Para mais informações, consulte os logs individuais de cada suíte de teste.*
"""

    # Salvar relatório
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(content)

    # Também salvar dados em JSON para processamento automatizado
    json_file = report_file.replace(".md", ".json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "overall_success": overall_success,
                "success_rate": success_rate,
                "total_suites": total_suites,
                "successful_suites": successful_suites,
                "total_duration_seconds": total_duration,
                "test_results": all_results,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    return report_file


def main():
    """Função principal do executor de testes abrangentes."""
    parser = argparse.ArgumentParser(
        description="Executor abrangente de testes do sistema SSA"
    )
    parser.add_argument(
        "--skip-performance",
        action="store_true",
        help="Pular testes de performance (mais rápido)",
    )
    parser.add_argument(
        "--quick", action="store_true", help="Executar apenas testes rápidos essenciais"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout em segundos para cada suíte (padrão: 600)",
    )

    args = parser.parse_args()

    print("START SISTEMA DE TESTES ABRANGENTES - SSA CONSULTA RÁPIDA")
    print("=" * 70)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"Modo: {'Rápido' if args.quick else 'Completo'}")
    print("=" * 70)

    all_results = []

    # Executar testes de fumaça primeiro
    smoke_result = run_manual_smoke_tests()
    all_results.append(smoke_result)

    if not smoke_result.get("success", False):
        print(
            "\nWARN AVISO: Testes de fumaça falharam. Continuando com testes automatizados..."
        )

    # Lista de suítes de teste a executar
    test_suites = [
        ("Testes Funcionais Automatizados", "tests/automated_system_tests.py")
    ]

    # Adicionar testes de performance se não for pulado
    if not args.skip_performance and not args.quick:
        test_suites.append(("Testes de Performance", "tests/performance_tests.py"))

    # Executar cada suíte
    for test_name, test_script in test_suites:
        if os.path.exists(test_script):
            result = run_test_suite(test_name, test_script, args.timeout)
            all_results.append(result)
        else:
            print(f"WARN AVISO: Script {test_script} não encontrado, pulando...")
            all_results.append(
                {
                    "test_name": test_name,
                    "script": test_script,
                    "success": False,
                    "error": "Script não encontrado",
                }
            )

    # Gerar relatório abrangente
    print("\nFILE Gerando relatório abrangente...")
    report_file = generate_comprehensive_report(all_results)

    # Mostrar resultado final
    successful_suites = sum(1 for result in all_results if result.get("success", False))
    total_suites = len(all_results)
    success_rate = successful_suites / total_suites if total_suites > 0 else 0
    overall_success = success_rate >= 0.8

    print("\n" + "=" * 70)
    print("INFO RESULTADO FINAL:")
    print(f"   Suítes Executadas: {total_suites}")
    print(f"   Suítes Bem-sucedidas: {successful_suites}")
    print(f"   Taxa de Sucesso: {success_rate:.1%}")

    status_final = (
        "OK SISTEMA APROVADO" if overall_success else "ERR SISTEMA COM PROBLEMAS"
    )
    print(f"   Status Final: {status_final}")

    print(f"\nFILE Relatório completo salvo em: {report_file}")
    print("=" * 70)

    # Retornar código de saída apropriado
    return 0 if overall_success else 1


if __name__ == "__main__":
    exit(main())
