#!/usr/bin/env python3
"""Inspect Excel file headers and data for SSA 202207421."""

import pandas as pd

print("=" * 80)
print("INSPECTING: Consulta SSA - 03-11-2025_0851AM.xlsx")
print("=" * 80)

filepath = "docs_entrada/Consulta SSA - 03-11-2025_0851AM.xlsx"

# Read Excel WITHOUT any header processing
df_raw = pd.read_excel(filepath, header=None)

print("\nRAW DATA (first 10 rows, all columns):")
print(df_raw.head(10).to_string())

print("\n" + "=" * 80)
print("SHAPE:", df_raw.shape)
print("=" * 80)

# Now read with default header (row 0)
df_default = pd.read_excel(filepath)

print("\nDEFAULT READ (with header=0):")
print(f"Columns: {list(df_default.columns)}")
print("\nFirst 5 rows:")
print(df_default.head().to_string())

# Find row with SSA 202207421
print("\n" + "=" * 80)
print("SEARCHING FOR SSA 202207421")
print("=" * 80)

for col in df_default.columns:
    if df_default[col].astype(str).str.contains("202207421", na=False).any():
        row_idx = df_default[
            df_default[col].astype(str).str.contains("202207421", na=False)
        ].index[0]
        print(f"\nFound in column: {col}")
        print(f"Row index: {row_idx}")
        print("\nFull row data:")
        row_data = df_default.iloc[row_idx]
        for k, v in row_data.items():
            if pd.notna(v):
                print(f"  {k}: {v}")
        break

# Check if there's a "Data de Cadastro" column
print("\n" + "=" * 80)
print("CHECKING DATA COLUMNS")
print("=" * 80)

data_cols = [
    col
    for col in df_default.columns
    if "data" in col.lower() or "cadastro" in col.lower()
]
print(f"\nColumns with 'data' or 'cadastro': {data_cols}")

if not data_cols:
    print("\n[CRITICAL] NO date/cadastro column found!")

    # Try to find it in raw data
    print("\nSearching in raw data (first 3 rows):")
    for i in range(min(3, len(df_raw))):
        row = df_raw.iloc[i]
        for j, val in enumerate(row):
            if pd.notna(val) and isinstance(val, str):
                if "data" in val.lower() or "cadastro" in val.lower():
                    print(f"  Row {i}, Col {j}: {val}")
