#!/usr/bin/env python3
"""
Detector de Código Frankenstein
Identifica implementações misturadas, redundantes e inconsistentes no código.
"""

import json
import os
import re
import sys


def analisar_implementacoes_misturadas():
    """Identifica implementações conflitantes ou misturadas."""

    issues = []
    warnings = []
    frankenstein_code = []

    print(" ANÁLISE DE CÓDIGO FRANKENSTEIN")
    print("=" * 50)
    print()

    # 1. Analisar GUI - Implementações misturadas
    gui_path = os.path.join("gui", "gui_ssa.py")
    if os.path.exists(gui_path):
        with open(gui_path, "r", encoding="utf-8") as f:
            gui_content = f.read()

        print("INFO ANALISANDO GUI...")

        # Detectar múltiplas estratégias de largura
        width_strategies = {
            "best-fit": gui_content.count("best-fit"),
            "MIN_CHAR_SIZES": gui_content.count("MIN_CHAR_SIZES"),
            "column_widths": gui_content.count("column_widths"),
            "pixel_widths": gui_content.count("pixel_widths"),
            "_gui_column_pixel_widths": gui_content.count("_gui_column_pixel_widths"),
            "_saved_gui_column_widths": gui_content.count("_saved_gui_column_widths"),
        }

        active_strategies = [k for k, v in width_strategies.items() if v > 0]
        if len(active_strategies) > 3:
            frankenstein_code.append(
                f" GUI: {len(active_strategies)} estratégias de largura diferentes ({', '.join(active_strategies)})"
            )

        # Detectar múltiplos sistemas de cache
        cache_systems = {
            "_widths_computed_for_df_hash": gui_content.count(
                "_widths_computed_for_df_hash"
            ),
            "_formatted_df_cache": gui_content.count("_formatted_df_cache"),
            "_column_sets_cache": gui_content.count("_column_sets_cache"),
            "_cached_default_mode": gui_content.count("_cached_default_mode"),
        }

        cache_count = sum(1 for v in cache_systems.values() if v > 0)
        if cache_count > 2:
            frankenstein_code.append(
                f" GUI: {cache_count} sistemas de cache independentes"
            )

        # Detectar configurações misturadas
        config_sources = {
            "GUI_MAIN_PREFERENCES": gui_content.count("GUI_MAIN_PREFERENCES"),
            "load_display_mappings": gui_content.count("load_display_mappings"),
            "get_settings": gui_content.count("get_settings"),
            "settings.json": gui_content.count("settings.json"),
        }

        config_mix = sum(1 for v in config_sources.values() if v > 0)
        if config_mix > 2:
            frankenstein_code.append(
                f" GUI: {config_mix} fontes de configuração misturadas"
            )

    # 2. Analisar CLI - Implementações inconsistentes
    cli_path = os.path.join("interface", "cli.py")
    if os.path.exists(cli_path):
        with open(cli_path, "r", encoding="utf-8") as f:
            cli_content = f.read()

        print("INFO ANALISANDO CLI...")

        # Detectar handlers com assinaturas inconsistentes
        handler_patterns = re.findall(r"def (_handle_\w+)\(([^)]+)\):", cli_content)
        param_counts = {}
        for handler, params in handler_patterns:
            param_count = len([p.strip() for p in params.split(",") if p.strip()])
            param_counts[handler] = param_count

        if param_counts:
            min_params = min(param_counts.values())
            max_params = max(param_counts.values())
            if max_params - min_params > 2:
                frankenstein_code.append(
                    f" CLI: Handlers inconsistentes ({min_params}-{max_params} parâmetros)"
                )

        # Detectar imports desnecessários ou duplicados
        imports = re.findall(
            r"^(from .+ import .+|import .+)$", cli_content, re.MULTILINE
        )
        import_modules = set()
        duplicate_imports = []

        for imp in imports:
            if "from" in imp:
                module = imp.split("from")[1].split("import")[0].strip()
            else:
                module = imp.replace("import", "").strip().split(".")[0]

            if module in import_modules:
                duplicate_imports.append(module)
            import_modules.add(module)

        if duplicate_imports:
            frankenstein_code.append(
                f" CLI: Imports duplicados/redundantes ({len(duplicate_imports)})"
            )

    # 3. Analisar configurações - Estruturas inconsistentes
    config_files = [
        "config/gui_main_preferences.json",
        "config/display_mappings.json",
        "config/column_priority.json",
        "config/settings.json",
        "config/default_settings.json",
    ]

    print("INFO ANALISANDO CONFIGURAÇÕES...")

    config_structures = {}
    for config_file in config_files:
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                config_structures[config_file] = {
                    "keys": set(data.keys()) if isinstance(data, dict) else set(),
                    "type": type(data).__name__,
                    "size": len(data) if hasattr(data, "__len__") else 0,
                }
            except Exception:
                pass

    # Detectar chaves duplicadas entre arquivos
    all_keys = {}
    for file, info in config_structures.items():
        for key in info["keys"]:
            if key not in all_keys:
                all_keys[key] = []
            all_keys[key].append(file)

    duplicate_keys = {k: v for k, v in all_keys.items() if len(v) > 1}
    if duplicate_keys:
        frankenstein_code.append(
            f" CONFIG: {len(duplicate_keys)} chaves duplicadas entre arquivos"
        )

    return frankenstein_code, issues, warnings


def analisar_funcoes_redundantes():
    """Identifica funções duplicadas ou muito similares."""

    print("INFO ANALISANDO FUNÇÕES REDUNDANTES...")
    redundant_functions = []

    # Mapear todas as funções
    function_signatures = {}

    # Analisar arquivos Python principais
    python_files = [
        "gui/gui_ssa.py",
        "interface/cli.py",
        "core/app_logic.py",
        "utils/table_printer.py",
    ]

    for file_path in python_files:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extrair definições de função
            functions = re.findall(r"def (\w+)\([^)]*\):", content)

            for func in functions:
                if func not in function_signatures:
                    function_signatures[func] = []
                function_signatures[func].append(file_path)

    # Identificar funções duplicadas
    for func, files in function_signatures.items():
        if len(files) > 1:
            redundant_functions.append(f"RUN Função '{func}' em: {', '.join(files)}")

    return redundant_functions


def analisar_padroes_inconsistentes():
    """Identifica padrões de código inconsistentes."""

    print("INFO ANALISANDO PADRÕES INCONSISTENTES...")
    inconsistencies = []

    # Analisar nomenclatura de variáveis
    gui_path = "gui/gui_ssa.py"
    cli_path = "interface/cli.py"

    patterns = {
        "cache_vars": r"(\w*cache\w*|_\w*cache\w*)",
        "df_vars": r"(\w*df\w*|dataframe\w*)",
        "settings_vars": r"(\w*settings\w*|\w*config\w*)",
        "width_vars": r"(\w*width\w*|\w*largura\w*)",
    }

    for pattern_name, pattern in patterns.items():
        gui_vars = set()
        cli_vars = set()

        if os.path.exists(gui_path):
            with open(gui_path, "r", encoding="utf-8") as f:
                gui_content = f.read()
            gui_vars = set(re.findall(pattern, gui_content))

        if os.path.exists(cli_path):
            with open(cli_path, "r", encoding="utf-8") as f:
                cli_content = f.read()
            cli_vars = set(re.findall(pattern, cli_content))

        # Verificar inconsistências de nomenclatura
        if gui_vars and cli_vars:
            common_concept_different_names = []
            for gui_var in gui_vars:
                for cli_var in cli_vars:
                    # Se têm conceito similar mas nomes diferentes
                    if (
                        gui_var != cli_var
                        and len(gui_var) > 3
                        and len(cli_var) > 3
                        and (gui_var in cli_var or cli_var in gui_var)
                    ):
                        common_concept_different_names.append(f"{gui_var} vs {cli_var}")

            if common_concept_different_names:
                inconsistencies.append(
                    f" {pattern_name}: nomenclatura inconsistente ({len(common_concept_different_names)} casos)"
                )

    return inconsistencies


def analisar_arquitetura_mista():
    """Identifica mistura de padrões arquiteturais."""

    print("INFO ANALISANDO ARQUITETURA MISTA...")
    architectural_issues = []

    # Verificar se há mistura de padrões
    gui_path = "gui/gui_ssa.py"
    if os.path.exists(gui_path):
        with open(gui_path, "r", encoding="utf-8") as f:
            gui_content = f.read()

        # Detectar mistura de paradigmas
        paradigms = {
            "OOP": len(re.findall(r"class \w+", gui_content)),
            "Functional": len(re.findall(r"def \w+\(.*\) -> \w+", gui_content)),
            "Procedural": len(
                re.findall(r'def \w+\([^)]*\):\s*"""[^"]*"""', gui_content)
            ),
            "Global_vars": len(re.findall(r"^[A-Z_]+\s*=", gui_content, re.MULTILINE)),
        }

        active_paradigms = [k for k, v in paradigms.items() if v > 5]
        if len(active_paradigms) > 2:
            architectural_issues.append(
                f" Mistura de paradigmas: {', '.join(active_paradigms)}"
            )

        # Detectar dependências circulares potenciais
        imports = re.findall(r"from (\w+(?:\.\w+)*) import", gui_content)
        local_imports = [
            imp
            for imp in imports
            if not imp.startswith(("sys", "os", "json", "pd", "Qt"))
        ]

        if len(local_imports) > 10:
            architectural_issues.append(
                f"RUN Muitas dependências locais ({len(local_imports)})"
            )

    return architectural_issues


def sugerir_refatoracoes():
    """Sugere refatorações específicas para eliminar código frankenstein."""

    refactorings = [
        {
            "categoria": " Eliminação de Frankenstein",
            "sugestões": [
                "DONE Unificar estratégias de largura em uma única classe WidthManager",
                "DONE Consolidar sistemas de cache em CacheManager unificado",
                "DONE Criar ConfigurationManager central para todas as configurações",
                "DONE Padronizar assinaturas de handlers em interface comum",
            ],
        },
        {
            "categoria": "RUN Eliminação de Redundância",
            "sugestões": [
                " Criar classe base HandlerBase para handlers CLI",
                " Extrair funções comuns para módulo utils.common",
                " Unificar nomenclatura de variáveis entre GUI e CLI",
                " Consolidar imports duplicados em __init__.py",
            ],
        },
        {
            "categoria": " Melhoria Arquitetural",
            "sugestões": [
                " Implementar padrão Strategy para algoritmos de largura",
                " Aplicar padrão Observer para eventos de resize",
                " Usar padrão Factory para criação de handlers",
                " Implementar padrão Command para operações de filtro",
            ],
        },
        {
            "categoria": "CLEAN Limpeza de Código",
            "sugestões": [
                " Remover código morto e funções não utilizadas",
                " Eliminar imports desnecessários com autoflake",
                " Padronizar docstrings com formato consistente",
                " Aplicar formatação consistente com black/isort",
            ],
        },
    ]

    return refactorings


def main():
    """Executa análise completa de código frankenstein."""
    print(" DETECTOR DE CÓDIGO FRANKENSTEIN")
    print("=" * 55)
    print()

    # Muda para o diretório do projeto
    if os.path.basename(os.getcwd()) != "SSA_Consulta_Rapida":
        possible_paths = [".", "../SSA_Consulta_Rapida", "./SSA_Consulta_Rapida"]
        for path in possible_paths:
            if os.path.exists(os.path.join(path, "gui", "gui_ssa.py")):
                os.chdir(path)
                break

    # Executar análises
    frankenstein_code, issues, warnings = analisar_implementacoes_misturadas()
    redundant_functions = analisar_funcoes_redundantes()
    inconsistencies = analisar_padroes_inconsistentes()
    architectural_issues = analisar_arquitetura_mista()
    refactorings = sugerir_refatoracoes()

    print()
    print(" CÓDIGO FRANKENSTEIN DETECTADO:")
    if frankenstein_code:
        for item in frankenstein_code:
            print(f"  {item}")
    else:
        print("  OK Nenhum código frankenstein óbvio detectado")
    print()

    print("RUN FUNÇÕES REDUNDANTES:")
    if redundant_functions:
        for item in redundant_functions:
            print(f"  {item}")
    else:
        print("  OK Nenhuma redundância óbvia detectada")
    print()

    print(" PADRÕES INCONSISTENTES:")
    if inconsistencies:
        for item in inconsistencies:
            print(f"  {item}")
    else:
        print("  OK Padrões relativamente consistentes")
    print()

    print(" PROBLEMAS ARQUITETURAIS:")
    if architectural_issues:
        for item in architectural_issues:
            print(f"  {item}")
    else:
        print("  OK Arquitetura relativamente limpa")
    print()

    print("FIX REFATORAÇÕES SUGERIDAS:")
    for refactoring in refactorings:
        print(f"\nIN {refactoring['categoria']}:")
        for sugestao in refactoring["sugestões"]:
            print(f"  {sugestao}")

    print()
    print("=" * 55)

    # Resumo
    total_issues = (
        len(frankenstein_code)
        + len(redundant_functions)
        + len(inconsistencies)
        + len(architectural_issues)
    )

    if total_issues == 0:
        print("OK CÓDIGO RELATIVAMENTE LIMPO!")
        severity = "LIMPO"
    elif total_issues <= 5:
        print(f"WARN ALGUMAS MELHORIAS NECESSÁRIAS ({total_issues} pontos)")
        severity = "MELHORIAS"
    elif total_issues <= 10:
        print(f" CÓDIGO FRANKENSTEIN MODERADO ({total_issues} pontos)")
        severity = "FRANKENSTEIN"
    else:
        print(f" CÓDIGO FRANKENSTEIN SEVERO ({total_issues} pontos)")
        severity = "SEVERO"

    print(
        f"Recomendação: {'Refatoração necessária' if total_issues > 5 else 'Melhorias pontuais'}"
    )

    return severity


if __name__ == "__main__":
    severity = main()
    sys.exit(0 if severity in ["LIMPO", "MELHORIAS"] else 1)
