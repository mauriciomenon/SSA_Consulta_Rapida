import pandas as pd

print("=== DEBUG SIMPLES ===")

# Simular o problema
test_values = ["202513402", "202513586", "202100033"]

print("1. Valores originais:")
for val in test_values:
    print(f"   '{val}' -> len: {len(val)}")

print("\n2. Após pd.to_numeric:")
for val in test_values:
    numeric = pd.to_numeric(val, errors='coerce')
    print(f"   '{val}' -> {numeric} (tipo: {type(numeric)})")

print("\n3. Convertido para string novamente:")
for val in test_values:
    numeric = pd.to_numeric(val, errors='coerce')
    back_to_str = str(numeric)
    print(f"   '{val}' -> {numeric} -> '{back_to_str}' (len: {len(back_to_str)})")

print("\nProblema identificado: conversão numérica preserva valor mas pode afetar formato!")
