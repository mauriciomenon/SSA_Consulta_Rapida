#!/usr/bin/env python
import sys
sys.path.insert(0, '.')
from core.app_logic import filter_dataframe
import pandas as pd

# DataFrame igual ao teste
test_data = {
    'numero_ssa': [1001, 1002, 1003, 1004, None],
    'descricao': ['Sistema web', 'Manutencao', None, 'Sistema ERP', 'Calibracao'],
    'setor': ['TI', None, 'COMPRAS', 'TI', 'MANUTENCAO']
}
df = pd.DataFrame(test_data)

print('DataFrame:')
print(df)
print()

# Teste com colunas especificadas
print('Teste 1: Especificando coluna descricao')
result = filter_dataframe(df, ['sistema'], search_columns=['descricao'])
print(f'Buscando: ["sistema"] em coluna descricao')
print(f'Resultados: {len(result)} linhas')
print(result[['numero_ssa', 'descricao']])
print()

# Teste sem especificar colunas (padrao)
print('Teste 2: Sem especificar colunas (padrao)')
result = filter_dataframe(df, ['sistema'])
print(f'Buscando: ["sistema"] em colunas padrao')
print(f'Resultados: {len(result)} linhas')
print(result[['numero_ssa', 'descricao']])
