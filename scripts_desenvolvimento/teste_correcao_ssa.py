import sys
import os
sys.path.append(os.getcwd())

from armazenamento.database import normalize_numero_ssa

print("=== TESTE DA CORREÇÃO SSA ===")

# Casos de teste
casos = [
    "2513402",    # 7 dígitos começando com 25 -> deve virar 202513402
    "2100033",    # 7 dígitos começando com 21 -> deve virar 202100033  
    "2413586",    # 7 dígitos começando com 24 -> deve virar 202413586
    "13586",      # 5 dígitos -> deve virar 000013586
    "202513402",  # 9 dígitos -> deve manter 202513402
]

print("Testando normalização:")
for caso in casos:
    resultado = normalize_numero_ssa(caso)
    print(f"  {caso} ({len(caso)} dígitos) -> {resultado} ({len(resultado) if resultado else 0} dígitos)")

print("\nEsperado para 2513402: 202513402")
resultado_teste = normalize_numero_ssa("2513402")
if resultado_teste == "202513402":
    print("✅ CORREÇÃO FUNCIONOU!")
else:
    print(f"❌ ERRO: Resultado foi {resultado_teste}")
