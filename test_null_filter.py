import pandas as pd
from interface.table_printer import format_cell_data

# Testa diversos tipos de valores null
print('=== Teste de Filtro de Valores Null ===')

test_cases = [
    ('nan', 'data'),
    ('NaN', 'data'),
    ('null', 'data'), 
    ('', 'data'),
    ('NULL', 'data'),
    ('test_value', 'data'),
    (None, 'data')
]

for value, column in test_cases:
    result = format_cell_data(value, column)
    print(f'{str(value):<12} -> "{result}"')
