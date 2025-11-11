#!/usr/bin/env python
"""
Teste das melhorias de performance.
2025-10-31T09:10:00
"""

import sys
import os
import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from core.app_logic import filter_dataframe, parse_search_terms

print('=== TESTE DE MELHORIAS DE PERFORMANCE ===')
print()

# Criar DataFrame de teste com NaN
test_data = {
    'numero_ssa': [1001, 1002, 1003, 1004, None],
    'descricao': ['Sistema web', 'Manutencao', None, 'Sistema ERP', 'Calibracao'],
    'setor': ['TI', None, 'COMPRAS', 'TI', 'MANUTENCAO']
}
df = pd.DataFrame(test_data)

print('DataFrame de teste:')
print(df)
print()

# Teste 1: Busca com NaN presente
print('Teste 1: Busca com NaN no DataFrame')
result = filter_dataframe(df, ['sistema'])
print(f'Termos: ["sistema"]')
print(f'Resultados: {len(result)} linhas')
print(f'Numeros SSA: {result["numero_ssa"].tolist()}')
print(f'Esperado: [1001, 1004]')
if result['numero_ssa'].tolist() == [1001.0, 1004.0]:
    print('Status: PASS')
else:
    print('Status: FAIL')
print()

# Teste 2: Busca nao deve encontrar 'nan' como string
print('Teste 2: Busca por "nan" nao deve retornar registros vazios')
result = filter_dataframe(df, ['nan'])
print(f'Termos: ["nan"]')
print(f'Resultados: {len(result)} linhas')
print(f'Esperado: 0 linhas (NaN nao deve ser encontrado como "nan")')
if len(result) == 0:
    print('Status: PASS')
else:
    print('Status: FAIL')
print()

# Teste 3: Busca com prefixo
print('Teste 3: Busca com modo prefix')
result = filter_dataframe(df, ['^Sistema'])
print(f'Termos: ["^Sistema"]')
print(f'Resultados: {len(result)} linhas')
print(f'Numeros SSA: {result["numero_ssa"].tolist()}')
print(f'Esperado: [1001, 1004]')
if result['numero_ssa'].tolist() == [1001.0, 1004.0]:
    print('Status: PASS')
else:
    print('Status: FAIL')
print()

# Teste 4: Busca com multiplos termos (cache deve funcionar)
print('Teste 4: Busca com multiplos termos (teste de cache)')
result = filter_dataframe(df, ['sistema', 'TI'])
print(f'Termos: ["sistema", "TI"]')
print(f'Resultados: {len(result)} linhas')
print(f'Esperado: 2 linhas (ambos termos presentes)')
if len(result) == 2:
    print('Status: PASS')
else:
    print('Status: FAIL')
print()

# Teste 5: Busca com termos duplicados (cache deve evitar reprocessamento)
print('Teste 5: Termos duplicados (cache reutilizado)')
terms_parsed = parse_search_terms(['sistema', 'sistema'])
print(f'Termos parseados: {len(terms_parsed)}')
result = filter_dataframe(df, terms_parsed)
print(f'Resultados: {len(result)} linhas')
print(f'Esperado: 2 linhas (cache deve funcionar)')
if len(result) == 2:
    print('Status: PASS')
else:
    print('Status: FAIL')
print()

print('=== TODOS TESTES CONCLUIDOS ===')
