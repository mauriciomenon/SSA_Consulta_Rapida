#!/usr/bin/env python3
"""
Analisador de Contradições e Pontos de Refinamento
Identifica implementações conflitantes, código redundante e oportunidades de melhoria.
"""

import json
import os
import re
import sys


def analisar_contradictoes():
    """Identifica possíveis contradições e pontos de refinamento no código."""

    issues = []
    warnings = []
    improvements = []

    # 1. Analisar GUI
    gui_path = os.path.join("gui", "gui_ssa.py")
    if os.path.exists(gui_path):
        with open(gui_path, "r", encoding="utf-8") as f:
            gui_content = f.read()

        # Verificar implementações duplicadas
        if gui_content.count("_compute_gui_column_widths") > 3:
            count = gui_content.count("_compute_gui_column_widths")
            warnings.append(
                f"WARN  GUI: Muitas chamadas para _compute_gui_column_widths ({count})"
            )

        # Verificar cache inconsistente
        if (
            "_widths_computed_for_df_hash" in gui_content
            and "_gui_column_pixel_widths" in gui_content
        ):
            improvements.append(" GUI: Pode unificar sistemas de cache de larguras")

        # Verificar configurações misturadas
        if (
            "GUI_MAIN_PREFERENCES" in gui_content
            and "_cached_default_mode" in gui_content
        ):
            improvements.append(
                " GUI: Revisar uso misto de configurações globais e cache local"
            )

        # Verificar formatação duplicada
        if gui_content.count("format_dataframe_for_display") > 1:
            if "_formatted_df_cache" not in gui_content:
                issues.append(
                    "ERR GUI: format_dataframe_for_display chamado múltiplas vezes sem cache universal"
                )

    # 2. Analisar CLI
    cli_path = os.path.join("interface", "cli.py")
    if os.path.exists(cli_path):
        with open(cli_path, "r", encoding="utf-8") as f:
            cli_content = f.read()

        # Verificar importações desnecessárias
        imports = re.findall(r"^from .* import .*", cli_content, re.MULTILINE)
        if len(imports) > 15:
            warnings.append(
                f"WARN  CLI: Muitas importações ({len(imports)}) - pode ser otimizado"
            )

        # Verificar handlers inconsistentes
        cli_content.count("print_cache")
        handlers_without_cache = cli_content.count(
            "pretty_print_df("
        ) - cli_content.count("_cached_pretty_print_df")
        if handlers_without_cache > 0:
            issues.append(
                f"ERR CLI: {handlers_without_cache} handlers ainda usando pretty_print_df sem cache"
            )

        # Verificar parsing duplicado
        if cli_content.count("parse_search_terms") > 5:
            count = cli_content.count("parse_search_terms")
            warnings.append(
                f"WARN  CLI: Muitas chamadas parse_search_terms ({count}) - verificar cache"
            )

    # 3. Analisar configurações
    config_files = [
        "config/gui_main_preferences.json",
        "config/display_mappings.json",
        "config/column_priority.json",
    ]

    configs_data = {}
    for config_file in config_files:
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    configs_data[config_file] = json.load(f)
            except Exception:
                issues.append(f"ERR CONFIG: Erro ao ler {config_file}")

    # Verificar duplicação de configurações
    if (
        "config/gui_main_preferences.json" in configs_data
        and "config/display_mappings.json" in configs_data
    ):
        gui_display = configs_data["config/gui_main_preferences.json"].get(
            "display_mappings", {}
        )
        direct_display = configs_data["config/display_mappings.json"]
        if gui_display and direct_display:
            common_keys = set(gui_display.keys()) & set(direct_display.keys())
            if common_keys:
                issues.append(
                    f"ERR CONFIG: Duplicação em display_mappings ({len(common_keys)} chaves)"
                )

    # 4. Verificar consistência de larguras
    if "config/gui_main_preferences.json" in configs_data:
        gui_config = configs_data["config/gui_main_preferences.json"]
        column_widths = gui_config.get("column_widths", {})
        if column_widths:
            # Verificar larguras muito pequenas ou grandes
            for col, width in column_widths.items():
                if isinstance(width, (int, float)):
                    if width < 20:
                        warnings.append(
                            f"WARN  CONFIG: Largura muito pequena para '{col}': {width}px"
                        )
                    elif width > 500:
                        warnings.append(
                            f"WARN  CONFIG: Largura muito grande para '{col}': {width}px"
                        )

    # 5. Verificar algoritmos conflitantes
    if os.path.exists(gui_path):
        # Verificar se há múltiplas estratégias de cálculo de largura
        best_fit_mentions = gui_content.count("best-fit")
        gui_content.count("MIN_CHAR_SIZES")
        fixed_widths = gui_content.count("fixed_widths")

        if best_fit_mentions > 0 and fixed_widths > 0:
            improvements.append(
                " GUI: Múltiplas estratégias de largura (best-fit + fixed) - pode ser unificado"
            )

    return issues, warnings, improvements


def analisar_performance():
    """Analisa possíveis gargalos de performance restantes."""

    performance_issues = []

    # Verificar GUI
    gui_path = os.path.join("gui", "gui_ssa.py")
    if os.path.exists(gui_path):
        with open(gui_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Loops potencialmente custosos
        for_loops = len(re.findall(r"for .* in .*\.columns", content))
        if for_loops > 3:
            performance_issues.append(
                f" GUI: {for_loops} loops sobre colunas - pode ser otimizado"
            )

        # Operações DataFrame custosas
        sort_operations = content.count(".sort_values")
        if sort_operations > 2:
            performance_issues.append(
                f" GUI: {sort_operations} operações de sort - verificar necessidade"
            )

    # Verificar CLI
    cli_path = os.path.join("interface", "cli.py")
    if os.path.exists(cli_path):
        with open(cli_path, "r", encoding="utf-8") as f:
            content = f.read()

        # I/O desnecessário
        file_operations = content.count("open(") + content.count("load_")
        if file_operations > 10:
            performance_issues.append(
                f" CLI: {file_operations} operações de I/O - verificar cache"
            )

    return performance_issues


def sugerir_refinamentos():
    """Sugere refinamentos específicos baseados na análise."""

    refinements = []

    # Refinamentos de arquitetura
    refinements.append(
        {
            "categoria": "Arquitetura",
            "sugestões": [
                "  Unificar sistemas de cache em módulo dedicado",
                "  Centralizar configurações em manager único",
                "  Padronizar interface de handlers entre GUI e CLI",
            ],
        }
    )

    # Refinamentos de performance
    refinements.append(
        {
            "categoria": "Performance",
            "sugestões": [
                "PERF Implementar lazy loading para configurações pesadas",
                "PERF Adicionar throttling para eventos de resize",
                "PERF Otimizar loops sobre DataFrames grandes",
            ],
        }
    )

    # Refinamentos de código
    refinements.append(
        {
            "categoria": "Código",
            "sugestões": [
                "CLEAN Remover imports não utilizados",
                "CLEAN Consolidar funções similares entre GUI e CLI",
                "CLEAN Padronizar nomenclatura de variáveis de cache",
            ],
        }
    )

    # Refinamentos de configuração
    refinements.append(
        {
            "categoria": "Configuração",
            "sugestões": [
                "  Eliminar duplicações entre arquivos de config",
                "  Validar consistência de larguras de colunas",
                "  Implementar fallbacks robustos para configs",
            ],
        }
    )

    return refinements


def main():
    """Função principal do analisador."""
    print("INFO ANALISADOR DE CONTRADIÇÕES E REFINAMENTOS")
    print("=" * 55)
    print()

    # Mudar para diretório do projeto se necessário
    if os.path.basename(os.getcwd()) != "SSA_Consulta_Rapida":
        possible_paths = [".", "../SSA_Consulta_Rapida", "./SSA_Consulta_Rapida"]
        for path in possible_paths:
            if os.path.exists(os.path.join(path, "gui", "gui_ssa.py")):
                os.chdir(path)
                break

    # Executar análises
    issues, warnings, improvements = analisar_contradictoes()
    performance_issues = analisar_performance()
    refinements = sugerir_refinamentos()

    # Exibir resultados
    print("ERR PROBLEMAS IDENTIFICADOS:")
    if issues:
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  OK Nenhum problema crítico encontrado")
    print()

    print("WARN  AVISOS E ATENÇÕES:")
    if warnings:
        for warning in warnings:
            print(f"  {warning}")
    else:
        print("  OK Nenhum aviso significativo")
    print()

    print(" POSSÍVEIS GARGALOS DE PERFORMANCE:")
    if performance_issues:
        for perf in performance_issues:
            print(f"  {perf}")
    else:
        print("  OK Nenhum gargalo óbvio identificado")
    print()

    print(" OPORTUNIDADES DE MELHORIA:")
    if improvements:
        for improvement in improvements:
            print(f"  {improvement}")
    else:
        print("  OK Código bem otimizado")
    print()

    print("FIX  SUGESTÕES DE REFINAMENTO:")
    for refinement in refinements:
        print(f"\nIN {refinement['categoria']}:")
        for sugestao in refinement["sugestões"]:
            print(f"  {sugestao}")

    print()
    print("=" * 55)

    # Resumo
    total_issues = len(issues) + len(warnings) + len(performance_issues)
    if total_issues == 0:
        print("OK CÓDIGO EM EXCELENTE ESTADO PARA REFINAMENTOS!")
    elif total_issues <= 5:
        print(f"OK CÓDIGO EM BOM ESTADO ({total_issues} pontos para refinar)")
    else:
        print(f"WARN  CÓDIGO PRECISA DE ATENÇÃO ({total_issues} pontos identificados)")

    return total_issues == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
