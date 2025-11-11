#!/usr/bin/env python
import pandas as pd

test_data = {
    'numero_ssa': [1001, 1002, 1003, 1004, None],
    'descricao': ['Sistema web', 'Manutencao', None, 'Sistema ERP', 'Calibracao'],
}
df = pd.DataFrame(test_data)

print('DataFrame original:')
print(df)
print(df.dtypes)
print()

# Simula o que o codigo faz
base = df[['numero_ssa', 'descricao']].select_dtypes(include=['object'])
print('Apos select_dtypes(object):')
print(base)
print(base.dtypes)
print()

base2 = base.fillna('').astype(str)
print('Apos fillna + astype(str):')
print(base2)
print()

# Testa busca
result = base2.apply(lambda col: col.str.contains('sistema', case=False, na=False, regex=False)).any(axis=1)
print('Resultado busca por sistema (any axis=1):')
for idx, val in result.items():
    print(f'  Linha {idx}: {val} - {base2.loc[idx].tolist()}')
