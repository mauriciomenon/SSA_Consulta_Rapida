#!/usr/bin/env python
import sys
sys.path.insert(0, '.')
from core.app_logic import filter_dataframe
import pandas as pd

df = pd.DataFrame({
    'descricao': ['Sistema web', 'Manutencao', 'Sistema ERP']
})

print('DataFrame:')
print(df)
print()

print('Teste filter_dataframe:')
result = filter_dataframe(df, ['sistema'])
print(f'Buscando: ["sistema"]')
print(f'Resultados: {len(result)} linhas')
print(result)
