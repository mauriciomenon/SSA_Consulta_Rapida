#!/usr/bin/env python
import sys
sys.path.insert(0, '.')
import pandas as pd

test_data = {
    'numero_ssa': [1001, 1002, 1003, 1004, None],
    'descricao': ['Sistema web', 'Manutencao', None, 'Sistema ERP', 'Calibracao'],
    'setor': ['TI', None, 'COMPRAS', 'TI', 'MANUTENCAO']
}
df = pd.DataFrame(test_data)

print('DataFrame:')
print(df)
print()
print('Tipos:')
print(df.dtypes)
print()

# Simula logica de priority_columns
priority_columns = [
    'numero_ssa', 'situacao', 'setor_executor', 'setor_emissor',
    'descricao_ssa', 'descricao_execucao', 'descricao_servico', 'observacao',
    'prazo_limite_str', 'data_cadastro_str'
]

search_columns = [col for col in priority_columns if col in df.columns]
print(f'Colunas prioritarias encontradas: {search_columns}')

if not search_columns:
    search_columns = df.select_dtypes(include=['object']).columns.tolist()
    print(f'Fallback para todas object: {search_columns}')

# Simula o filter
available_search_cols = [col for col in search_columns if col in df.columns]
print(f'Colunas disponiveis: {available_search_cols}')

base_str_df = df[available_search_cols].select_dtypes(include=['object']).fillna('').astype(str)
print()
print('Base para busca:')
print(base_str_df)
print()

# Busca
result = base_str_df.apply(
    lambda col: col.str.contains('sistema', case=False, na=False, regex=False)
).any(axis=1)
print('Match por linha:')
print(result)
print()
print(f'Total matches: {result.sum()}')
