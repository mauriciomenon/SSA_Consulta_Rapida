#!/usr/bin/env python3
"""
Teste simples de performance da função filter_dataframe otimizada.
"""
import sys
import os
import pandas as pd
import time

# Garantir que raiz do projeto esteja no sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.app_logic import filter_dataframe, parse_search_terms

def test_filter_performance():
    """Testa performance do filtro otimizado vs. não otimizado."""
    print("🧪 Testando performance da função filter_dataframe otimizada...")
    
    # Criar DataFrame de teste
    data = {
        'numero_ssa': ['2025001', '2025002', '2025003'] * 1000,
        'situacao': ['EM EXECUÇÃO', 'APROVADA', 'SUSPENSA'] * 1000,
        'setor_executor': ['MEDEIRO', 'SVPENG', 'SUPTEL'] * 1000,
        'descricao_servico': ['Manutenção preventiva', 'Análise técnica', 'Inspeção'] * 1000,
        'coluna_nao_usada1': ['dados'] * 3000,
        'coluna_nao_usada2': ['mais dados'] * 3000,
        'coluna_nao_usada3': ['ainda mais dados'] * 3000,
        'coluna_nao_usada4': ['dados desnecessários'] * 3000,
        'coluna_nao_usada5': ['texto longo aqui'] * 3000,
    }
    
    df = pd.DataFrame(data)
    print(f"📊 DataFrame criado: {len(df)} linhas, {len(df.columns)} colunas")
    
    # Termos de teste
    search_terms = parse_search_terms(['MEDEIRO', 'EXECUÇÃO'])
    
    # Teste 1: Busca otimizada (colunas específicas)
    print("\n🚀 Teste 1: Busca otimizada (colunas prioritárias)")
    start_time = time.time()
    result_optimized = filter_dataframe(df, search_terms, search_columns=['numero_ssa', 'situacao', 'setor_executor'])
    optimized_time = time.time() - start_time
    print(f"   ⏱️  Tempo: {optimized_time:.4f}s")
    print(f"   📊 Resultados: {len(result_optimized)} linhas")
    
    # Teste 2: Busca padrão (todas as colunas de texto)  
    print("\n🐌 Teste 2: Busca em todas as colunas (método antigo)")
    start_time = time.time()
    # Simular busca em todas as colunas passando todas as colunas de texto
    all_text_cols = df.select_dtypes(include=['object']).columns.tolist()
    result_all_cols = filter_dataframe(df, search_terms, search_columns=all_text_cols)
    all_cols_time = time.time() - start_time
    print(f"   ⏱️  Tempo: {all_cols_time:.4f}s") 
    print(f"   📊 Resultados: {len(result_all_cols)} linhas")
    
    # Comparação
    if optimized_time > 0:
        speedup = all_cols_time / optimized_time
        print(f"\n📈 RESULTADO:")
        print(f"   🚀 Busca otimizada: {speedup:.2f}x mais rápida")
        print(f"   💾 Economia de tempo: {(all_cols_time - optimized_time) * 1000:.1f}ms")
        
        if speedup > 1.5:
            print("   ✅ Otimização bem-sucedida!")
        else:
            print("   ⚠️  Melhoria marginal - considere outras otimizações")
    
    print(f"\n✅ Teste concluído")

if __name__ == "__main__":
    test_filter_performance()