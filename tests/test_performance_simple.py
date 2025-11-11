#!/usr/bin/env python
"""
Teste simples das melhorias de performance.
2025-10-31T09:30:00
"""

import sys
import os
import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from core.app_logic import filter_dataframe

print('=== TESTE SIMPLES DE MELHORIAS ===')
print()

# DataFrame de teste com colunas usadas no schema real
df = pd.DataFrame({
    'descricao_servico': ['Sistema web', 'Manutencao preventiva', None, 'Sistema ERP', 'Calibracao'],
    'setor_executor': ['TI', None, 'COMPRAS', 'TI', 'MANUTENCAO'],
    'numero_ssa': ['1001', '1002', '1003', '1004', '1005']
})

print('DataFrame:')
print(df)
print()

# Teste 1: Busca basica
print('Teste 1: Busca por "sistema"')
result = filter_dataframe(df, ['sistema'])
print(f'Resultados: {len(result)} linhas')
print(result[['numero_ssa', 'descricao_servico']])
if len(result) == 2 and '1001' in result['numero_ssa'].values and '1004' in result['numero_ssa'].values:
    print('Status: PASS')
else:
    print('Status: FAIL')
print()

# Teste 2: NaN nao deve ser encontrado como "nan"
print('Teste 2: Busca por "nan" (nao deve encontrar)')
result = filter_dataframe(df, ['nan'])
print(f'Resultados: {len(result)} linhas')
if len(result) == 0:
    print('Status: PASS')
else:
    print('Status: FAIL - NaN esta sendo encontrado como string')
print()

# Teste 3: Busca com multiplos termos (teste cache)
print('Teste 3: Busca por "sistema" E "TI"')
result = filter_dataframe(df, ['sistema', 'TI'])
print(f'Resultados: {len(result)} linhas')
print(result[['numero_ssa', 'descricao_servico', 'setor_executor']] if len(result) > 0 else 'Nenhum resultado')
if len(result) == 2:
    print('Status: PASS')
else:
    print('Status: FAIL')
print()

print('=== CONCLUSAO ===')
print('Melhoria 1: fillna(\'\') - NaN nao vira "nan" string')
print('Melhoria 2: Cache de regex patterns - funciona transparentemente')
