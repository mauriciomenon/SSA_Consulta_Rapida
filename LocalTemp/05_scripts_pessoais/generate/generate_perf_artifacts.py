#!/usr/bin/env python3
"""Gera artefatos de performance sem depender do pytest.

Uso:
  SSA_PERF_ROWS=5000 SSA_PERF_FAST=1 SSA_PERF_VERBOSE=1 python scripts/generate_perf_artifacts.py
Opções env:
  SSA_PERF_ROWS     Quantidade de linhas sintéticas (default 3000, cap 15000)
  SSA_PERF_FAST     Se '1', evita escrita Excel/CSV real e monkeypatch read_excel
  SSA_PERF_CSV      Se '1', usa CSV ao invés de XLSX (ignorado em FAST)
  SSA_PERF_VERBOSE  Se '1', imprime detalhes
  SSA_PERF_THRESHOLD Limite de segundos para import (default 15)

Saídas:
  reports/perf_last_import.json
  reports/perf_history.jsonl (acréscimo de linha)
"""
from __future__ import annotations
import os, json, time
from pathlib import Path
import pandas as pd
from utils.robust_importer import import_excel_robust

verbose = os.environ.get("SSA_PERF_VERBOSE") == "1"
rows = int(os.environ.get("SSA_PERF_ROWS", "3000"))
if rows > 15000:
    if verbose:
        print(f"[perf] Cap rows {rows} -> 15000")
    rows = 15000
fast = os.environ.get("SSA_PERF_FAST") == "1"
csv_mode = os.environ.get("SSA_PERF_CSV") == "1"
if fast and csv_mode:
    csv_mode = False  # redundante
if verbose:
    print(f"[perf] rows={rows} fast={fast} csv={csv_mode}")

base_year = 2025
data = {"Nº SSA": [], "Data Cadastro": [], "Situacao": []}
for i in range(rows):
    numero = f"{base_year}{i%100000:05d}"
    if i % 10 == 0 and i > 0:
        numero = f"{base_year}{(i-1)%100000:05d}"
    data["Nº SSA"].append(numero)
    data["Data Cadastro"].append(f"{base_year}-09-{(i%28)+1:02d} 10:00:00")
    data["Situacao"].append("ABERTA")

import pandas as _p

df = pd.DataFrame(data)

reports_dir = Path("reports")
reports_dir.mkdir(exist_ok=True)

def run():
    if fast:
        dummy = Path("perf_dummy.xlsx")
        dummy.write_text("")
        orig = _p.read_excel
        _p.read_excel = lambda *a, **k: df.copy()
        t0 = time.perf_counter(); t1 = t0
        imported, stats = import_excel_robust(str(dummy))
        t2 = time.perf_counter()
        _p.read_excel = orig
    else:
        suffix = ".csv" if csv_mode else ".xlsx"
        tmp = Path("perf_data" + suffix)
        t0 = time.perf_counter()
        if csv_mode:
            df.to_csv(tmp, index=False)
        else:
            df.to_excel(tmp, index=False)
        t1 = time.perf_counter()
        imported, stats = import_excel_robust(str(tmp))
        t2 = time.perf_counter()
    write_s = t1 - t0
    import_s = t2 - t1
    report = {
        "rows_generated": rows,
        "original_unique": int(df['Nº SSA'].nunique()),
        "final_unique": int(imported['numero_ssa'].nunique()),
        "duplicate_rows_dropped": stats.get('duplicate_rows_dropped'),
        "invalid_numero_ssa_rows": stats.get('invalid_numero_ssa_rows'),
        "write_seconds": write_s,
        "import_seconds": import_s,
        "threshold_seconds": float(os.environ.get("SSA_PERF_THRESHOLD", "15")),
    }
    (reports_dir / "perf_last_import.json").write_text(json.dumps(report, indent=2))
    with (reports_dir / "perf_history.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({**report, "ts": time.time()}) + "\n")
    if verbose:
        print("[perf] report=", json.dumps(report, indent=2))

if __name__ == "__main__":
    run()
    if verbose:
        print("[perf] artifacts written in 'reports/'")
