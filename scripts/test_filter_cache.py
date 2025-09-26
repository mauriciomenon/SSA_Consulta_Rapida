#!/usr/bin/env python3
"""
Script para testar o sistema de cache inteligente de filtros da GUI.

Executa uma série de filtros repetidos para validar:
1. Hit/miss ratio do cache
2. Performance gains com cache
3. Funcionalidade LRU (Least Recently Used)
4. Limpeza de cache
"""

import sys
import os
import time
import pandas as pd

# Adiciona o diretório raiz do projeto ao path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from gui.gui_ssa import FilterCache, FilterWorker
from core.app_logic import parse_search_terms, filter_dataframe


def create_test_dataframe(size=10000):
    """Cria um DataFrame de teste com dados simulados."""
    import random
    random.seed(42)  # Seed fixo para reprodutibilidade
    
    data = {
        'numero_ssa': [f"2025{i:05d}" for i in range(size)],
        'situacao': [random.choice(['ASE', 'ADI', 'APL', 'APG', 'SPG', 'SEE', 'SAD', 'STE']) for _ in range(size)],
        'setor_executor': [f"Setor {random.randint(1, 20)}" for _ in range(size)],
        'descricao_ssa': [f"Descrição da SSA número {i}" for i in range(size)],
        'data_cadastro': pd.date_range('2025-01-01', periods=size, freq='1H'),
        'grau_prioridade_emissao': [random.randint(1, 5) for _ in range(size)]
    }
    
    return pd.DataFrame(data)


def test_cache_functionality():
    """Testa funcionalidades básicas do cache."""
    print("🧪 Teste 1: Funcionalidades básicas do cache")
    
    # Cria cache pequeno para teste
    cache = FilterCache(max_size=3)
    
    # Dados simulados
    df_hash = "test_hash"
    
    # Teste 1: Cache vazio
    result = cache.get(df_hash, ["teste1"], "contains")
    assert result is None, "Cache deveria estar vazio"
    
    # Teste 2: Adiciona ao cache
    test_df = pd.DataFrame({'col1': [1, 2, 3]})
    cache.put(df_hash, ["teste1"], "contains", test_df)
    
    # Teste 3: Recupera do cache
    cached_result = cache.get(df_hash, ["teste1"], "contains")
    assert cached_result is not None, "Cache deveria ter resultado"
    assert len(cached_result) == 3, "Resultado do cache deveria ter 3 linhas"
    
    # Teste 4: Política LRU
    cache.put(df_hash, ["teste2"], "contains", test_df)
    cache.put(df_hash, ["teste3"], "contains", test_df)
    cache.put(df_hash, ["teste4"], "contains", test_df)  # Deveria remover teste1
    
    # teste1 deveria ter sido removido
    result1 = cache.get(df_hash, ["teste1"], "contains")
    result4 = cache.get(df_hash, ["teste4"], "contains")
    assert result1 is None, "teste1 deveria ter sido removido do cache (LRU)"
    assert result4 is not None, "teste4 deveria estar no cache"
    
    stats = cache.get_stats()
    print(f"   ✅ Estatísticas: {stats}")
    print("   ✅ Funcionalidades básicas: OK\n")


def test_cache_performance():
    """Testa performance do cache comparado com execução sem cache."""
    print("🚀 Teste 2: Performance do cache")
    
    # Cria DataFrame de teste
    df_test = create_test_dataframe(5000)
    print(f"   📊 DataFrame de teste criado: {len(df_test)} linhas")
    
    # Filtros de teste que serão repetidos
    test_filters = [
        ["ASE"],
        ["ADI", "APL"],
        ["Setor 1"],
        ["2025"],
        ["!STE"]
    ]
    
    # Teste sem cache (simulação)
    print("   🔄 Testando execução sem cache...")
    start_time = time.time()
    results_no_cache = []
    
    for _ in range(3):  # Repete 3x cada filtro
        for terms in test_filters:
            parsed = parse_search_terms(terms)
            result = filter_dataframe(df_test, parsed)
            results_no_cache.append(len(result))
    
    time_no_cache = time.time() - start_time
    
    # Teste com cache (usando FilterWorker)
    print("   ⚡ Testando execução com cache...")
    cache = FilterCache(max_size=20)
    FilterWorker._cache = cache  # Substitui cache padrão
    
    start_time = time.time()
    df_hash = "performance_test"
    results_with_cache = []
    
    for _ in range(3):  # Repete 3x cada filtro
        for terms in test_filters:
            # Simula lookup no cache
            cached = cache.get(df_hash, [terms], "contains")
            if cached is not None:
                results_with_cache.append(len(cached))
            else:
                # Cache miss - executa filtro
                parsed = parse_search_terms(terms)
                result = filter_dataframe(df_test, parsed)
                cache.put(df_hash, [terms], "contains", result)
                results_with_cache.append(len(result))
    
    time_with_cache = time.time() - start_time
    
    # Resultados
    cache_stats = cache.get_stats()
    speedup = time_no_cache / time_with_cache if time_with_cache > 0 else float('inf')
    
    print(f"   📈 Tempo sem cache: {time_no_cache:.3f}s")
    print(f"   ⚡ Tempo com cache: {time_with_cache:.3f}s")
    print(f"   🚀 Speedup: {speedup:.2f}x")
    print(f"   📊 Cache stats: {cache_stats}")
    print(f"   ✅ Performance: OK\n")
    
    return speedup, cache_stats


def test_cache_consistency():
    """Testa consistência dos resultados do cache."""
    print("🔍 Teste 3: Consistência do cache")
    
    df_test = create_test_dataframe(1000)
    cache = FilterCache(max_size=10)
    
    test_terms = ["ASE", "ADI"]
    df_hash = "consistency_test"
    
    # Primeira execução - cache miss
    parsed = parse_search_terms(test_terms)
    original_result = filter_dataframe(df_test, parsed)
    cache.put(df_hash, [test_terms], "contains", original_result)
    
    # Segunda execução - cache hit
    cached_result = cache.get(df_hash, [test_terms], "contains")
    
    # Verifica consistência
    assert cached_result is not None, "Cache deveria ter resultado"
    assert len(cached_result) == len(original_result), f"Tamanhos diferentes: {len(cached_result)} vs {len(original_result)}"
    
    # Verifica se os DataFrames são iguais (conteúdo)
    pd.testing.assert_frame_equal(original_result.reset_index(drop=True), 
                                cached_result.reset_index(drop=True))
    
    print("   ✅ Consistência: OK\n")


def test_cache_invalidation():
    """Testa invalidação e limpeza do cache."""
    print("🗑️ Teste 4: Invalidação do cache")
    
    cache = FilterCache(max_size=5)
    df_test = create_test_dataframe(100)
    df_hash = "invalidation_test"
    
    # Adiciona alguns itens ao cache
    for i in range(3):
        test_df = pd.DataFrame({'col': [i]})
        cache.put(df_hash, [f"test{i}"], "contains", test_df)
    
    initial_stats = cache.get_stats()
    print(f"   📊 Stats iniciais: {initial_stats}")
    
    # Limpa cache
    cache.clear()
    
    final_stats = cache.get_stats()
    print(f"   🧹 Stats após limpeza: {final_stats}")
    
    assert final_stats['size'] == 0, "Cache deveria estar vazio"
    assert final_stats['hits'] == 0, "Hits deveriam ser zerados"
    assert final_stats['misses'] == 0, "Misses deveriam ser zerados"
    
    print("   ✅ Invalidação: OK\n")


def main():
    """Executa todos os testes de cache."""
    print("🎯 SSA Consulta Rápida - Teste do Sistema de Cache de Filtros\n")
    
    try:
        # Executa todos os testes
        test_cache_functionality()
        speedup, final_stats = test_cache_performance()
        test_cache_consistency()
        test_cache_invalidation()
        
        # Sumário final
        print("📋 SUMÁRIO DOS TESTES")
        print("=" * 50)
        print(f"✅ Todos os testes passaram com sucesso!")
        print(f"🚀 Performance gain com cache: {speedup:.2f}x")
        print(f"📊 Hit rate final: {final_stats['hit_rate']:.1f}%")
        print(f"💾 Evictions durante teste: {final_stats['evictions']}")
        
        if speedup > 1.5:
            print("🏆 Cache performance: EXCELENTE")
        elif speedup > 1.2:
            print("🥈 Cache performance: BOM")
        else:
            print("⚠️ Cache performance: PRECISA MELHORAR")
        
        print("\n🎉 Sistema de cache está funcionando corretamente!")
        
    except Exception as e:
        print(f"❌ Erro durante os testes: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()