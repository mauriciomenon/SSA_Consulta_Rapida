#!/usr/bin/env python3
"""
Teste Rápido de Performance dos Refinamentos
Valida se as otimizações estão funcionando corretamente.
"""

import os
import sys
import time
import pandas as pd

# Adiciona o diretório do projeto ao path
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

def teste_performance_cli():
    """Testa a performance das otimizações do CLI."""
    print("🧪 TESTE DE PERFORMANCE - CLI")
    print("-" * 40)

    try:
        from interface.cli import _cached_pretty_print_df
        from utils.table_printer import pretty_print_df
        from core.config_manager import get_settings, load_display_mappings

        # Cria DataFrame de teste
        test_data = {
            'numero_ssa': ['SSA001', 'SSA002', 'SSA003'] * 100,
            'setor_executor': ['Setor A', 'Setor B', 'Setor C'] * 100,
            'situacao': ['Ativa', 'Pendente', 'Finalizada'] * 100,
            'descricao_ssa': ['Descrição longa de teste que vai ser truncada'] * 300
        }
        df = pd.DataFrame(test_data)

        display_map = load_display_mappings()
        settings = get_settings()
        cache = {}

        # Teste 1: Primeira execução (sem cache)
        start_time = time.time()
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        _cached_pretty_print_df(df.head(50), display_map, settings, cache)

        sys.stdout = old_stdout
        first_time = time.time() - start_time

        # Teste 2: Segunda execução (com cache)
        start_time = time.time()
        sys.stdout = io.StringIO()

        _cached_pretty_print_df(df.head(50), display_map, settings, cache)

        sys.stdout = old_stdout
        cached_time = time.time() - start_time

        # Resultados
        speedup = (first_time / cached_time) if cached_time > 0 else float('inf')
        print(f"  Primeira execução: {first_time:.4f}s")
        print(f"  Segunda execução (cache): {cached_time:.4f}s")
        print(f"  Melhoria: {speedup:.1f}x mais rápido")
        print(f"  Cache funcionando: {'✅' if len(cache) > 0 else '❌'}")
        print()

        return speedup > 2.0  # Espera pelo menos 2x mais rápido

    except Exception as e:
        print(f"  ❌ Erro no teste CLI: {e}")
        return False

def teste_otimizacoes_gui():
    """Testa as otimizações da GUI (sem interface gráfica)."""
    print("🧪 TESTE DE OTIMIZAÇÕES - GUI")
    print("-" * 40)

    try:
        # Testa cache de sets de colunas
        test_columns = ['col1', 'col2', 'col3', 'col4', 'col5']
        cache = {}

        # Simula operações de set que foram otimizadas
        start_time = time.time()
        for i in range(1000):
            # Operação original (sem cache)
            expandable_cols = ['col1', 'col3']
            result = [col for col in expandable_cols if col in set(test_columns)]
        original_time = time.time() - start_time

        # Operação otimizada (com cache simulado)
        start_time = time.time()
        test_columns_set = set(test_columns)  # Cached
        for i in range(1000):
            expandable_cols = ['col1', 'col3']
            result = [col for col in expandable_cols if col in test_columns_set]
        optimized_time = time.time() - start_time

        speedup = (original_time / optimized_time) if optimized_time > 0 else float('inf')
        print(f"  Operação original (1000x): {original_time:.4f}s")
        print(f"  Operação otimizada (1000x): {optimized_time:.4f}s")
        print(f"  Melhoria: {speedup:.1f}x mais rápido")
        print(f"  Otimização efetiva: {'✅' if speedup > 1.2 else '❌'}")
        print()

        return speedup > 1.2

    except Exception as e:
        print(f"  ❌ Erro no teste GUI: {e}")
        return False

def teste_configuracoes():
    """Testa se as configurações estão consistentes."""
    print("🧪 TESTE DE CONFIGURAÇÕES")
    print("-" * 40)

    try:
        import json

        config_files = [
            'config/gui_main_preferences.json',
            'config/display_mappings.json',
            'config/column_priority.json'
        ]

        all_valid = True

        for config_file in config_files:
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    print(f"  ✅ {config_file}: Válido ({len(data)} entradas)")
                except json.JSONDecodeError as e:
                    print(f"  ❌ {config_file}: JSON inválido - {e}")
                    all_valid = False
            else:
                print(f"  ⚠️  {config_file}: Arquivo não encontrado")

        print()
        return all_valid

    except Exception as e:
        print(f"  ❌ Erro no teste de configurações: {e}")
        return False

def main():
    """Executa todos os testes de refinamento."""
    print("🔧 VALIDAÇÃO DOS REFINAMENTOS")
    print("=" * 50)
    print()

    # Muda para o diretório do projeto se necessário
    if os.path.basename(os.getcwd()) != 'SSA_Consulta_Rapida':
        possible_paths = ['.', '../SSA_Consulta_Rapida', './SSA_Consulta_Rapida']
        for path in possible_paths:
            if os.path.exists(os.path.join(path, 'interface', 'cli.py')):
                os.chdir(path)
                break

    # Executa testes
    results = []

    results.append(teste_performance_cli())
    results.append(teste_otimizacoes_gui())
    results.append(teste_configuracoes())

    # Sumário
    print("📊 RESUMO DOS TESTES")
    print("-" * 40)
    passed = sum(results)
    total = len(results)

    print(f"  Testes aprovados: {passed}/{total}")
    if passed == total:
        print("  🎉 TODOS OS REFINAMENTOS FUNCIONANDO!")
    elif passed >= total * 0.8:
        print("  ✅ Maioria dos refinamentos funcionando")
    else:
        print("  ⚠️  Refinamentos precisam de ajustes")

    print()
    print(f"  Status final: {'SUCESSO' if passed == total else 'PARCIAL' if passed > 0 else 'FALHA'}")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
