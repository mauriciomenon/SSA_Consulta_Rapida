#!/usr/bin/env python3
"""
Script para testar as melhorias do sistema Streamlit.

Testa:
1. Cache de filtros do Streamlit
2. Funcionalidades de performance
3. Sistema de estatísticas
"""

import sys
import os
import pandas as pd
import time

# Adiciona o diretório raiz do projeto ao path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Mock do session_state do Streamlit
class MockSessionState:
    def __init__(self):
        self.filter_cache = {}
        self.cache_stats = {'hits': 0, 'misses': 0, 'evictions': 0}

# Mock básico do streamlit
class MockStreamlit:
    session_state = MockSessionState()

# Substitui o import do streamlit para testes
sys.modules['streamlit'] = MockStreamlit()

# Agora pode importar a classe do cache
from streamlit_app import StreamlitFilterCache


def create_test_dataframe(size=1000):
    """Cria DataFrame de teste."""
    import random
    random.seed(42)
    
    data = {
        'numero_ssa': [f"2025{i:05d}" for i in range(size)],
        'situacao': [random.choice(['ASE', 'ADI', 'APL', 'EXECUTADA', 'ABERTA']) for _ in range(size)],
        'setor_executor': [f"Setor {random.randint(1, 10)}" for _ in range(size)],
        'descricao_ssa': [f"Descrição {i}" for i in range(size)]
    }
    
    return pd.DataFrame(data)


def test_streamlit_cache():
    """Testa o cache do Streamlit."""
    print("🧪 Teste 1: Cache do Streamlit")
    
    cache = StreamlitFilterCache(max_size=5, ttl_seconds=10)
    df = create_test_dataframe(100)
    
    # Teste 1: Cache miss inicial
    result1 = cache.get(df.shape, "ASE", ["ASE"], ["Setor 1"], [])
    assert result1 is None, "Cache deveria estar vazio"
    
    # Teste 2: Armazenar no cache
    test_result = df[df['situacao'] == 'ASE'].head(10)
    cache.put(df.shape, "ASE", ["ASE"], ["Setor 1"], [], test_result)
    
    # Teste 3: Cache hit
    result2 = cache.get(df.shape, "ASE", ["ASE"], ["Setor 1"], [])
    assert result2 is not None, "Cache deveria ter resultado"
    assert len(result2) == len(test_result), "Resultado deve ter mesmo tamanho"
    
    # Teste 4: Estatísticas
    stats = cache.get_stats()
    assert stats['hits'] == 1, f"Deveria ter 1 hit, mas tem {stats['hits']}"
    assert stats['misses'] == 1, f"Deveria ter 1 miss, mas tem {stats['misses']}"
    
    print(f"   ✅ Estatísticas: {stats}")
    print("   ✅ Cache do Streamlit: OK\n")


def test_cache_ttl():
    """Testa TTL (Time To Live) do cache."""
    print("⏰ Teste 2: TTL do Cache")
    
    cache = StreamlitFilterCache(max_size=5, ttl_seconds=1)  # TTL curto para teste
    df = create_test_dataframe(50)
    
    # Adiciona item ao cache
    test_result = df.head(5)
    cache.put(df.shape, "test", [], [], [], test_result)
    
    # Verifica que está no cache
    result1 = cache.get(df.shape, "test", [], [], [])
    assert result1 is not None, "Item deveria estar no cache"
    
    # Espera TTL expirar
    print("   ⏳ Aguardando TTL expirar...")
    time.sleep(1.1)
    
    # Verifica que expirou
    result2 = cache.get(df.shape, "test", [], [], [])
    assert result2 is None, "Item deveria ter expirado do cache"
    
    print("   ✅ TTL funcionando corretamente\n")


def test_performance_simulation():
    """Simula cenário de performance real."""
    print("🚀 Teste 3: Simulação de Performance")
    
    cache = StreamlitFilterCache(max_size=20)
    df = create_test_dataframe(2000)
    
    # Filtros que usuário aplica frequentemente
    common_filters = [
        ("ASE", ["ASE"], [], []),
        ("EXECUTADA", ["EXECUTADA"], [], []),
        ("Setor 1", [], ["Setor 1"], []),
        ("ASE OR ADI", ["ASE", "ADI"], [], [])
    ]
    
    print("   🔄 Primeira execução (cache misses):")
    miss_times = []
    
    for search, situacoes, executores, emissores in common_filters:
        start = time.perf_counter()
        
        # Simula filtro (cache miss)
        result = cache.get(df.shape, search, situacoes, executores, emissores)
        if result is None:
            # Simula processamento
            time.sleep(0.05)  # 50ms
            filtered = df.head(100)  # Resultado simulado
            cache.put(df.shape, search, situacoes, executores, emissores, filtered)
        
        elapsed = time.perf_counter() - start
        miss_times.append(elapsed)
        print(f"     '{search}' → {elapsed*1000:.1f}ms")
    
    print("\n   ⚡ Segunda execução (cache hits):")
    hit_times = []
    
    for search, situacoes, executores, emissores in common_filters:
        start = time.perf_counter()
        
        result = cache.get(df.shape, search, situacoes, executores, emissores)
        
        elapsed = time.perf_counter() - start
        hit_times.append(elapsed)
        status = "HIT" if result is not None else "MISS"
        print(f"     '{search}' → {status} {elapsed*1000:.2f}ms")
    
    # Calcula speedup
    avg_miss = sum(miss_times) / len(miss_times)
    avg_hit = sum(hit_times) / len(hit_times)
    speedup = avg_miss / avg_hit if avg_hit > 0 else float('inf')
    
    stats = cache.get_stats()
    
    print(f"\n   📊 Resultados:")
    print(f"     • Tempo médio (miss): {avg_miss*1000:.1f}ms")
    print(f"     • Tempo médio (hit): {avg_hit*1000:.2f}ms") 
    print(f"     • Speedup: {speedup:.0f}x")
    print(f"     • Hit rate: {stats['hit_rate']:.1f}%")
    print("   ✅ Performance simulada com sucesso\n")


def test_cache_lru():
    """Testa política LRU (Least Recently Used)."""
    print("🔄 Teste 4: Política LRU")
    
    cache = StreamlitFilterCache(max_size=3)  # Cache pequeno
    df = create_test_dataframe(50)
    
    # Adiciona 3 itens (enche o cache)
    for i in range(3):
        test_df = df.head(10 + i)
        cache.put(df.shape, f"test{i}", [], [], [], test_df)
    
    # Verifica que todos estão no cache
    for i in range(3):
        result = cache.get(df.shape, f"test{i}", [], [], [])
        assert result is not None, f"test{i} deveria estar no cache"
    
    # Adiciona 4º item (deveria remover test0)
    cache.put(df.shape, "test3", [], [], [], df.head(5))
    
    # test0 deveria ter sido removido (LRU)
    result0 = cache.get(df.shape, "test0", [], [], [])
    result3 = cache.get(df.shape, "test3", [], [], [])
    
    assert result0 is None, "test0 deveria ter sido removido (LRU)"
    assert result3 is not None, "test3 deveria estar no cache"
    
    stats = cache.get_stats()
    assert stats['evictions'] > 0, "Deveria ter havido evictions"
    
    print(f"   ✅ LRU funcionando - {stats['evictions']} evictions registradas\n")


def main():
    """Executa todos os testes."""
    print("🎯 SSA Consulta Rápida - Teste das Melhorias Streamlit\n")
    
    try:
        test_streamlit_cache()
        test_cache_ttl()
        test_performance_simulation()
        test_cache_lru()
        
        print("📋 RESUMO DOS TESTES")
        print("=" * 50)
        print("✅ Todos os testes das melhorias Streamlit passaram!")
        print("🎯 Funcionalidades validadas:")
        print("   • Cache de filtros com TTL")
        print("   • Política LRU com eviction")
        print("   • Performance tracking")
        print("   • Estatísticas em tempo real")
        print("\n🚀 Interface Streamlit otimizada está pronta!")
        
    except Exception as e:
        print(f"❌ Erro durante os testes: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()