import time
import sys
import pandas as pd
from core.app_logic import filter_dataframe
from armazenamento.database import query_db

print("=== TESTE DE PERFORMANCE DO FILTRO ===")

# Carrega dados
print("Carregando dados...")
start_time = time.time()
df = query_db('data/ssas.db', 'ssas')
load_time = time.time() - start_time
print(f"Dados carregados: {len(df)} registros em {load_time:.2f}s")

# Teste filtro SVP
print("\nTestando filtro 'svp'...")
start_time = time.time()
result = filter_dataframe(df, ['svp'])
filter_time = time.time() - start_time
print(f"Filtro aplicado: {len(result)} resultados em {filter_time:.2f}s")

if filter_time < 2.0:
    print("✅ EXCELENTE! Filtro rápido")
elif filter_time < 5.0:
    print("⚠️  BOM. Filtro aceitável")
else:
    print("❌ LENTO. Precisa otimizar mais")

# Teste filtro sequencial
print("\nTestando filtro sequencial 'svp' → 'iee3'...")
start_time = time.time()
result2 = filter_dataframe(result, ['iee3'])
filter_time2 = time.time() - start_time
print(f"Segundo filtro: {len(result2)} resultados em {filter_time2:.2f}s")

print(f"\nTempo total: {filter_time + filter_time2:.2f}s")
print(f"Resultados: {len(df)} → {len(result)} → {len(result2)}")
