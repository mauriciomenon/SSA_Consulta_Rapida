#!/usr/bin/env python3
"""Find SSA 202207421 in Excel files and check data_cadastro column."""

import os
import sys

import pandas as pd

# Add root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("=" * 80)
print("SEARCHING FOR SSA 202207421")
print("=" * 80)

target_ssa = "202207421"
docs_dir = "docs_entrada"

files = [f for f in os.listdir(docs_dir) if f.endswith(".xlsx")]
print(f"\nSearching in {len(files)} Excel files...")

found_in = []

for i, filename in enumerate(files, 1):
    filepath = os.path.join(docs_dir, filename)

    if i % 10 == 0:
        print(f"  Processed {i}/{len(files)} files...")

    try:
        # Read Excel
        df = pd.read_excel(filepath, sheet_name=0)

        # Search for SSA in all columns
        for col in df.columns:
            if df[col].astype(str).str.contains(target_ssa, na=False).any():
                # Found!
                row_idx = df[
                    df[col].astype(str).str.contains(target_ssa, na=False)
                ].index[0]
                row_data = df.iloc[row_idx]

                found_in.append(
                    {
                        "file": filename,
                        "row": row_idx + 2,  # Excel row (1-indexed + header)
                        "column": col,
                        "data": row_data.to_dict(),
                    }
                )

                print(f"\n[FOUND] File: {filename}")
                print(f"  Row: {row_idx + 2} (Excel)")
                print(f"  Column: {col}")

                # Check data_cadastro
                if "Data de Cadastro" in df.columns:
                    data_cad = row_data.get("Data de Cadastro", "N/A")
                    print(f"  Data de Cadastro: {data_cad}")
                    print(f"  Type: {type(data_cad)}")
                    print(f"  Is NaT/NaN: {pd.isna(data_cad)}")

                # Print all columns for this row
                print("\n  All columns in this row:")
                for k, v in row_data.items():
                    if pd.notna(v):
                        print(f"    {k}: {v} (type: {type(v).__name__})")

                break

    except Exception as e:
        if i % 10 == 0:
            print(f"    Error in {filename}: {e}")

print("\n" + "=" * 80)
print(f"SUMMARY: Found in {len(found_in)} file(s)")
print("=" * 80)

if not found_in:
    print("\n[WARNING] SSA 202207421 NOT FOUND in any file!")
else:
    for item in found_in:
        print(f"\nFile: {item['file']}")
        print(f"Row: {item['row']}")
        print(f"Column: {item['column']}")
