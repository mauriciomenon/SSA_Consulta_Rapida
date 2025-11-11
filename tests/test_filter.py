import sys
sys.path.insert(0, '.')

import pandas as pd
from core.app_logic import parse_search_terms, filter_dataframe

# Create test dataframe
df = pd.DataFrame({'col1': ['svp', 'test', 'svp test', 'SP', 's/p', 'sp']})
print('Test DataFrame:')
print(df)
print()

# Parse and filter
terms = parse_search_terms(['svp'])
print(f'Parsed terms: {terms}')
print()

filtered = filter_dataframe(df, terms, ['col1'])
print('Filtered result:')
print(filtered)
print()

# Test if 'svp' matches
for idx, row in df.iterrows():
    val = str(row['col1']).lower()
    if 'svp' in val:
        print(f"Row {idx}: '{row['col1']}' matches 'svp'")
