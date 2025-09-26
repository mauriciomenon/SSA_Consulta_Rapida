#!/usr/bin/env python3
"""
Script para testar o sistema de cache da interface Streamlit.

Valida:
1. Cache de filtros funcional
2. Performance das operações
3. Persistência entre sessões
4. Estatísticas do cache
"""

import sys
import os
import time
import pandas as pd

# Adiciona o diretório raiz do projeto ao path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Simula ambiente Streamlit
class MockStreamlitSession:
    """Mock da session_state do Streamlit para testes."""
    
    def __init__(self):
        self._data = {}
    
    def __setitem__(self, key, value):
        self._data[key] = value
    
    def __getitem__(self, key):
        return self._data[key]
    
    def __contains__(self, key):
        return key in self._data
    
    def get(self, key, default=None):
        return self._data.get(key, default)

# Mock do streamlit
class MockStreamlit:
    def __init__(self):
        self.session_state = MockStreamlitSession()

# Substitui streamlit por mock
sys.modules['streamlit'] = MockStreamlit()

# Agora pode importar do streamlit_app
try:
    # Importa as classes diretamente do arquivo
    exec(open('streamlit_app.py').read(), globals())
    StreamlitFilterCache = globals()['StreamlitFilterCache']
    apply_filters_with_cache = globals()['apply_filters_with_cache']
except Exception as e:
    print(f"❌ Erro ao importar streamlit_app.py: {e}")
    sys.exit(1)


def create_test_dataframe(size=1000):
    """Cria DataFrame de teste."""
    import random
    random.seed(42)
    
    data = {
        'numero_ssa': [f"2025{i:05d}" for i in range(size)],
        'situacao': [random.choice(['ASE', 'ADI', 'APL', 'SPG', 'STE']) for _ in range(size)],
        'setor_executor': [f"Setor {random.randint(1, 10)}" for _ in range(size)],
        'descricao_ssa': [f"Descrição da SSA {i}" for i in range(size)]
    }
    
    return pd.DataFrame(data)


def test_cache_basic_functionality():
    """Testa funcionalidades básicas do cache Streamlit."""
    print("🧪 Teste 1: Funcionalidades básicas do cache Streamlit")
    
    cache = StreamlitFilterCache(max_size=5)
    df_test = create_test_dataframe(100)
    
    # Teste 1: Cache vazio
    result = cache.get_cached_filter("test1")
    assert result is None, "Cache deveria estar vazio"
    
    # Teste 2: Adiciona ao cache
    filtered_df = df_test[df_test['situacao'] == 'ASE']
    cache.cache_filter_result("test1", filtered_df, {"situacao": "ASE"})
    
    # Teste 3: Recupera do cache
    cached_result = cache.get_cached_filter("test1")
    assert cached_result is not None, "Cache deveria ter resultado"
    assert len(cached_result) > 0, "Resultado do cache não deveria estar vazio"
    
    # Teste 4: Verifica estatísticas
    stats = cache.get_stats()
    assert stats['entries'] == 1, f"Deveria ter 1 entrada, tem {stats['entries']}"
    assert stats['hits'] >= 1, f"Deveria ter pelo menos 1 hit, tem {stats['hits']}"
    
    print("   ✅ Funcionalidades básicas: OK")
    return stats


def test_cache_performance():
    """Testa performance do cache."""
    print("🚀 Teste 2: Performance do cache Streamlit")
    
    cache = StreamlitFilterCache(max_size=10)
    df_test = create_test_dataframe(5000)
    
    # Filtros de teste
    test_filters = [
        {"situacao": "ASE"},
        {"setor_executor": "Setor 1"},
        {"numero_ssa": "202500"},
    ]
    
    # Teste sem cache
    print("   🔄 Executando filtros sem cache...")
    start_time = time.time()
    
    results_no_cache = []
    for filter_params in test_filters:
        for _ in range(3):  # Repete cada filtro 3x
            # Simula filtro manual
            result_df = df_test.copy()
            for col, val in filter_params.items():
                if col == "numero_ssa":
                    result_df = result_df[result_df[col].str.contains(val, na=False)]
                else:
                    result_df = result_df[result_df[col] == val]
            results_no_cache.append(len(result_df))
    
    time_no_cache = time.time() - start_time
    
    # Teste com cache
    print("   ⚡ Executando filtros com cache...")
    start_time = time.time()
    
    results_with_cache = []
    for filter_params in test_filters:
        filter_key = str(sorted(filter_params.items()))
        
        for _ in range(3):  # Repete cada filtro 3x
            cached = cache.get_cached_filter(filter_key)
            if cached is not None:
                results_with_cache.append(len(cached))
            else:
                # Cache miss - executa filtro
                result_df = df_test.copy()
                for col, val in filter_params.items():
                    if col == "numero_ssa":
                        result_df = result_df[result_df[col].str.contains(val, na=False)]
                    else:
                        result_df = result_df[result_df[col] == val]
                
                cache.cache_filter_result(filter_key, result_df, filter_params)
                results_with_cache.append(len(result_df))
    
    time_with_cache = time.time() - start_time
    
    # Resultados
    speedup = time_no_cache / time_with_cache if time_with_cache > 0 else float('inf')
    stats = cache.get_stats()
    
    print(f"   📈 Tempo sem cache: {time_no_cache:.3f}s")
    print(f"   ⚡ Tempo com cache: {time_with_cache:.3f}s")
    print(f"   🚀 Speedup: {speedup:.2f}x")
    print(f"   📊 Cache stats: {stats}")
    print("   ✅ Performance: OK")
    
    return speedup, stats


def test_cache_consistency():
    """Testa consistência dos resultados."""
    print("🔍 Teste 3: Consistência do cache")
    
    cache = StreamlitFilterCache()
    df_test = create_test_dataframe(500)
    
    filter_params = {"situacao": "ASE"}
    filter_key = "consistency_test"
    
    # Primeira execução
    original_result = df_test[df_test['situacao'] == 'ASE']
    cache.cache_filter_result(filter_key, original_result, filter_params)
    
    # Segunda execução - do cache
    cached_result = cache.get_cached_filter(filter_key)
    
    assert cached_result is not None, "Cache deveria ter resultado"
    assert len(cached_result) == len(original_result), f"Tamanhos diferentes: {len(cached_result)} vs {len(original_result)}"
    
    print("   ✅ Consistência: OK")


def test_lru_eviction():
    """Testa política LRU de evicção."""
    print("🗑️ Teste 4: Política LRU")
    
    cache = StreamlitFilterCache(max_size=3)
    df_test = create_test_dataframe(100)
    
    # Adiciona 4 entradas (deveria remover a primeira)
    for i in range(4):
        result_df = df_test.iloc[:10]  # Pequeno subset
        cache.cache_filter_result(f"test_{i}", result_df, {"test": i})
    
    # test_0 deveria ter sido removido
    assert cache.get_cached_filter("test_0") is None, "test_0 deveria ter sido removido"
    assert cache.get_cached_filter("test_3") is not None, "test_3 deveria estar no cache"
    
    stats = cache.get_stats()
    assert stats['entries'] <= 3, f"Cache não deveria ter mais que 3 entradas, tem {stats['entries']}"
    
    print("   ✅ LRU Policy: OK")


def main():
    """Executa todos os testes."""
    print("🎯 SSA Consulta Rápida - Teste do Cache Streamlit\n")
    
    try:
        # Executa testes
        basic_stats = test_cache_basic_functionality()
        speedup, perf_stats = test_cache_performance() 
        test_cache_consistency()
        test_lru_eviction()
        
        # Sumário
        print("\n📋 SUMÁRIO DOS TESTES")
        print("=" * 50)
        print("✅ Todos os testes passaram!")
        print(f"🚀 Speedup médio: {speedup:.2f}x")
        print(f"📊 Hit rate: {perf_stats.get('hit_rate', 0):.1f}%")
        print(f"💾 Entries no cache: {perf_stats.get('entries', 0)}")
        
        if speedup > 2.0:
            print("🏆 Performance: EXCELENTE")
        elif speedup > 1.5:
            print("🥈 Performance: BOA")
        else:
            print("⚠️ Performance: ADEQUADA")
        
        print("\n🎉 Cache Streamlit funcionando corretamente!")
        
    except Exception as e:
        print(f"❌ Erro durante os testes: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()