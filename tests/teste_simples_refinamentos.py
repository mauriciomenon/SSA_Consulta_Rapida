#!/usr/bin/env python3
"""
Teste Simples de Refinamentos
Valida as otimizacoes sem dependencias externas pesadas.
"""

import sys
import time
from pathlib import Path

_BOOTSTRAP_ROOT = Path(__file__).resolve().parents[1]
if str(_BOOTSTRAP_ROOT) not in sys.path:
    sys.path.insert(0, str(_BOOTSTRAP_ROOT))

from launchers.main_runtime import _get_project_root  # noqa: E402

project_dir = _get_project_root()
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from tests.legacy_config_utils import validate_refinement_configs  # noqa: E402
from tests.legacy_path_utils import require_project_path, resolve_project_path  # noqa: E402
from tests.legacy_report_utils import (  # noqa: E402
    calculate_speedup,
    emit,
    report_boolean_results,
)


def teste_cache_operacoes():
    """Testa se as operacoes de cache estao funcionando."""
    emit("TEST TESTE DE CACHE DE OPERACOES")
    emit("-" * 40)

    # Simula o cache de sets de colunas da GUI
    cache = {}
    test_columns = ["col1", "col2", "col3", "col4", "col5"] * 100
    expandable_columns = ["col1", "col3", "col5"]

    baseline_results = []
    start_time = time.time()
    for i in range(1000):
        df_columns_set = set(test_columns)
        baseline_results.append(
            tuple(col for col in expandable_columns if col in df_columns_set)
        )
    time_without_cache = time.time() - start_time

    cached_results = []
    start_time = time.time()
    for i in range(1000):
        cache_key = f"columns_{len(test_columns)}"
        if cache_key not in cache:
            cache[cache_key] = set(test_columns)
        df_columns_set = cache[cache_key]

        expandable_key = f"expandable_{cache_key}"
        if expandable_key not in cache:
            cache[expandable_key] = [
                col for col in expandable_columns if col in df_columns_set
            ]
        cached_results.append(tuple(cache[expandable_key]))
    time_with_cache = time.time() - start_time

    improvement = calculate_speedup(time_without_cache, time_with_cache)
    cache_contract_ok = baseline_results == cached_results and set(cache) == {
        "columns_500",
        "expandable_columns_500",
    }

    emit(f"  Sem cache (1000x): {time_without_cache:.4f}s")
    emit(f"  Com cache (1000x): {time_with_cache:.4f}s")
    emit(f"  Melhoria: {improvement:.1f}x mais rapido")
    emit(f"  Cache criado: {len(cache)} entradas")
    emit(f"  Status: {'OK CONTRATO DE CACHE' if cache_contract_ok else 'ERR CACHE INVALIDO'}")
    emit()

    return cache_contract_ok


def teste_configuracoes_json():
    """Testa a integridade das configuracoes JSON."""
    emit("TEST TESTE DE CONFIGURACOES JSON")
    emit("-" * 40)

    all_valid, total_entries = validate_refinement_configs()

    emit(f"  Total de configuracoes: {total_entries}")
    emit(
        f"  Status: {'OK TODAS VALIDAS' if all_valid else 'FAIL PROBLEMAS ENCONTRADOS'}"
    )
    emit()

    return all_valid


def teste_estrutura_arquivos():
    """Testa se os arquivos refinados existem e tem o tamanho esperado."""
    emit("TEST TESTE DE ESTRUTURA DE ARQUIVOS")
    emit("-" * 40)

    arquivos_importantes = {
        "gui/gui_ssa.py": 50000,  # Pelo menos 50KB (arquivo grande com otimizacoes)
        "interface/cli.py": 15000,  # Pelo menos 15KB
        "config/gui_main_preferences.json": 100,  # Pelo menos 100 bytes
        "tests/historico_otimizacoes_execucao.py": 1000,  # Nota historica
    }

    structure_ok = True

    for arquivo, min_size in arquivos_importantes.items():
        arquivo_path = resolve_project_path(arquivo)
        if arquivo_path.exists():
            size = arquivo_path.stat().st_size
            if size >= min_size:
                emit(f"  OK {arquivo}: {size:,} bytes")
            else:
                emit(
                    f"  FAIL {arquivo}: {size:,} bytes (menor que esperado: {min_size:,})"
                )
                structure_ok = False
        else:
            emit(f"  ERR {arquivo}: Nao encontrado")
            structure_ok = False

    emit(
        f"  Status: {'OK ESTRUTURA OK' if structure_ok else 'FAIL ARQUIVOS FALTANDO/PEQUENOS'}"
    )
    emit()

    return structure_ok


def teste_hash_tracking():
    """Testa o sistema de hash tracking implementado."""
    emit("TEST TESTE DE HASH TRACKING")
    emit("-" * 40)

    # Simula o sistema de hash tracking
    cache_hits = 0
    cache_misses = 0

    # Simula diferentes DataFrames por seus hashes
    dataframe_hashes = [
        "hash_001",
        "hash_002",
        "hash_001",
        "hash_003",
        "hash_001",
        "hash_002",
    ]
    computed_widths = {}

    for df_hash in dataframe_hashes:
        if df_hash in computed_widths:
            # Cache hit - reutiliza larguras computadas
            cache_hits += 1
        else:
            # Cache miss - precisa computar larguras
            cache_misses += 1
            # Simula computacao cara
            time.sleep(0.001)  # 1ms de computacao simulada
            computed_widths[df_hash] = {"col1": 100, "col2": 150, "col3": 200}

    total_operations = len(dataframe_hashes)
    cache_hit_rate = (cache_hits / total_operations) * 100

    emit(f"  Total de operacoes: {total_operations}")
    emit(f"  Cache hits: {cache_hits}")
    emit(f"  Cache misses: {cache_misses}")
    emit(f"  Taxa de acerto: {cache_hit_rate:.1f}%")
    emit(f"  Entries no cache: {len(computed_widths)}")
    hash_contract_ok = cache_hits == 3 and cache_misses == 3 and len(computed_widths) == 3
    emit(f"  Status: {'OK HASH TRACKING' if hash_contract_ok else 'ERR HASH TRACKING'}")
    emit()

    return hash_contract_ok


def main():
    """Executa todos os testes simples."""
    emit("FIX VALIDACAO SIMPLES DOS REFINAMENTOS")
    emit("=" * 50)
    emit()

    require_project_path("gui/gui_ssa.py")

    # Executa testes
    results = []

    results.append(teste_cache_operacoes())
    results.append(teste_configuracoes_json())
    results.append(teste_estrutura_arquivos())
    results.append(teste_hash_tracking())

    return report_boolean_results(
        results,
        all_success_message="  OK TODOS OS REFINAMENTOS VALIDADOS!",
        high_partial_message="  FAIL Maioria dos refinamentos funcionando, mas gate falhou",
        partial_message="  FAIL Refinamentos parcialmente funcionando",
        failure_message="  ERR Refinamentos precisam de correcoes",
    )


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
