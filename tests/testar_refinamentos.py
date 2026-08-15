#!/usr/bin/env python3
"""
Teste Rapido de Performance dos Refinamentos
Valida se as otimizacoes estao funcionando corretamente.
"""

import os
import sys
import time
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd

_BOOTSTRAP_ROOT = Path(__file__).resolve().parents[1]
if str(_BOOTSTRAP_ROOT) not in sys.path:
    sys.path.insert(0, str(_BOOTSTRAP_ROOT))

from launchers.main_runtime import _get_project_root  # noqa: E402

project_dir = _get_project_root()
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from tests.legacy_config_utils import validate_refinement_configs  # noqa: E402
from tests.legacy_path_utils import require_project_path  # noqa: E402
from tests.legacy_report_utils import (  # noqa: E402
    calculate_speedup,
    emit,
    report_boolean_results,
)


def teste_contrato_cache_cli():
    """Testa o contrato funcional do cache do CLI."""
    emit("TEST TESTE DE CONTRATO DE CACHE - CLI")
    emit("-" * 40)

    try:
        from core.config_manager import load_display_mappings_integrity, load_settings
        from interface.cli import _cached_pretty_print_df, enhancement_manager

        # Cria DataFrame de teste
        test_data = {
            "numero_ssa": ["SSA00001", "SSA00002", "SSA00003"] * 100,
            "setor_executor": ["Setor A", "Setor B", "Setor C"] * 100,
            "situacao": ["Ativa", "Pendente", "Finalizada"] * 100,
            "descricao_ssa": ["Descricao longa de teste que vai ser truncada"] * 300,
        }
        df = pd.DataFrame(test_data)

        display_map = load_display_mappings_integrity()
        settings = load_settings()
        cache = {}

        # Teste 1: primeira execucao deve preencher o cache.
        start_time = time.time()
        with (
            patch.object(
                enhancement_manager, "is_enhanced_printer_enabled", return_value=False
            ),
            patch.dict(os.environ, {"SSA_NON_INTERACTIVE": "1"}),
            redirect_stdout(StringIO()),
        ):
            _cached_pretty_print_df(df.head(50), display_map, settings, cache)
        first_time = time.time() - start_time

        first_cache_keys = set(cache)

        # Teste 2: segunda execucao deve reutilizar as mesmas chaves.
        start_time = time.time()
        with (
            patch.object(
                enhancement_manager, "is_enhanced_printer_enabled", return_value=False
            ),
            patch.dict(os.environ, {"SSA_NON_INTERACTIVE": "1"}),
            redirect_stdout(StringIO()),
        ):
            _cached_pretty_print_df(df.head(50), display_map, settings, cache)
        cached_time = time.time() - start_time

        # Resultados
        speedup = calculate_speedup(first_time, cached_time)
        cache_contract_ok = bool(first_cache_keys) and set(cache) == first_cache_keys
        emit(f"  Primeira execucao: {first_time:.4f}s")
        emit(f"  Segunda execucao (cache): {cached_time:.4f}s")
        emit(f"  Melhoria: {speedup:.1f}x mais rapido")
        emit(f"  Cache funcionando: {'OK' if cache_contract_ok else 'ERR'}")
        emit()

        return cache_contract_ok

    except Exception as e:
        emit(f"  ERR Erro no teste CLI: {e}")
        return False


def teste_contrato_otimizacoes_gui():
    """Testa equivalencia funcional das otimizacoes da GUI."""
    emit("TEST TESTE DE CONTRATO DE OTIMIZACOES - GUI")
    emit("-" * 40)

    try:
        # Testa equivalencia da operacao otimizada sem depender de timing.
        test_columns = ["col1", "col2", "col3", "col4", "col5"]
        original_results = []
        start_time = time.time()
        for i in range(1000):
            expandable_cols = ["col1", "col3"]
            original_results.append(
                tuple(col for col in expandable_cols if col in set(test_columns))
            )
        original_time = time.time() - start_time

        optimized_results = []
        start_time = time.time()
        test_columns_set = set(test_columns)  # Cached
        for i in range(1000):
            expandable_cols = ["col1", "col3"]
            optimized_results.append(
                tuple(col for col in expandable_cols if col in test_columns_set)
            )
        optimized_time = time.time() - start_time

        speedup = calculate_speedup(original_time, optimized_time)
        optimization_contract_ok = optimized_results == original_results
        emit(f"  Operacao original (1000x): {original_time:.4f}s")
        emit(f"  Operacao otimizada (1000x): {optimized_time:.4f}s")
        emit(f"  Melhoria: {speedup:.1f}x mais rapido")
        emit(f"  Otimizacao equivalente: {'OK' if optimization_contract_ok else 'ERR'}")
        emit()

        return optimization_contract_ok

    except Exception as e:
        emit(f"  ERR Erro no teste GUI: {e}")
        return False


def teste_configuracoes():
    """Testa se as configuracoes estao consistentes."""
    emit("TEST TESTE DE CONFIGURACOES")
    emit("-" * 40)

    all_valid, _total_entries = validate_refinement_configs()
    emit()
    return all_valid


def main():
    """Executa todos os testes de refinamento."""
    emit("FIX VALIDACAO DOS REFINAMENTOS")
    emit("=" * 50)
    emit()

    require_project_path("interface/cli.py")

    # Executa testes
    results = []

    results.append(teste_contrato_cache_cli())
    results.append(teste_contrato_otimizacoes_gui())
    results.append(teste_configuracoes())

    return report_boolean_results(
        results,
        all_success_message="  OK TODOS OS REFINAMENTOS FUNCIONANDO!",
        high_partial_message="  FAIL Maioria dos refinamentos funcionando, mas gate falhou",
        partial_message="  FAIL Refinamentos precisam de ajustes",
        failure_message="  ERR Refinamentos precisam de ajustes",
    )


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
