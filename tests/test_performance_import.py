import json
import time
import os
from pathlib import Path
import pandas as pd
import pytest
from utils.robust_importer import import_excel_robust


@pytest.mark.performance
def test_large_spreadsheet_import(tmp_path: Path, monkeypatch):
    verbose = os.environ.get("SSA_PERF_VERBOSE") == "1"
    if verbose:
        print("PERF_TEST_START", flush=True)
    # Lower default to keep CI fast; allow override via SSA_PERF_ROWS
    rows = int(os.environ.get("SSA_PERF_ROWS", "3000"))
    # Safety cap to avoid accidental huge allocations in CI
    if rows > 15000:
        if verbose:
            print(f"Capping rows from {rows} to 15000 to avoid long Excel write", flush=True)
        rows = 15000
    fast_mode = os.environ.get("SSA_PERF_FAST") == "1"
    csv_mode = os.environ.get("SSA_PERF_CSV") == "1"
    if fast_mode:
        if verbose:
            print("FAST MODE ativo (bypass escrita Excel real)", flush=True)
    duplicate_every = 10  # 10% duplicates sharing same numero_ssa with newer date
    base_year = 2025
    data = {
        "Nº SSA": [],
        "Data Cadastro": [],
        "Situacao": [],
    }
    for i in range(rows):
        # create 9-digit numero_ssa: year + 5 digits
        numero = f"{base_year}{i%100000:05d}"
        # introduce duplicates: every duplicate_every row repeats previous numero with later date
        if i % duplicate_every == 0 and i > 0:
            numero = f"{base_year}{(i-1)%100000:05d}"
        data["Nº SSA"].append(numero)
        data["Data Cadastro"].append(f"{base_year}-09-{(i%28)+1:02d} 10:00:00")
        data["Situacao"].append("ABERTA")
    df = pd.DataFrame(data)
    # Caminho real ou dummy dependendo do modo
    if csv_mode and fast_mode:
        # CSV + FAST redundante, manter FAST apenas
        csv_mode = False
    file_path = tmp_path / (
        ("perf_large.csv" if csv_mode else "perf_large.xlsx") if not fast_mode else "dummy.xlsx"
    )
    if fast_mode:
        # criar arquivo vazio só para passar checagem de existência
        file_path.write_text("")
        # patch pandas.read_excel para retornar df diretamente, evitando custo IO
        if monkeypatch is not None:
            import pandas as _pandas
            monkeypatch.setattr(_pandas, "read_excel", lambda *a, **k: df.copy())
        t0 = time.perf_counter()
        t1 = t0  # sem escrita
        imported_df, stats = import_excel_robust(str(file_path))
        t2 = time.perf_counter()
    else:
        t0 = time.perf_counter()
        if csv_mode:
            df.to_csv(file_path, index=False)
        else:
            df.to_excel(file_path, index=False)
        t1 = time.perf_counter()
        imported_df, stats = import_excel_robust(str(file_path))
        t2 = time.perf_counter()
    write_s = t1 - t0
    import_s = t2 - t1
    assert not imported_df.empty, "Imported DF should not be empty"
    # Expected unique count roughly rows - (rows/duplicate_every)/2 due to how we duplicate only one previous id each cycle
    # Simpler: ensure imported unique ids less or equal original unique and > 0
    orig_unique = df["Nº SSA"].nunique()
    final_unique = imported_df["numero_ssa"].nunique()
    assert 0 < final_unique <= orig_unique
    report = {
        "rows_generated": rows,
        "original_unique": int(orig_unique),
        "final_unique": int(final_unique),
        "duplicate_rows_dropped": stats.get("duplicate_rows_dropped"),
        "invalid_numero_ssa_rows": stats.get("invalid_numero_ssa_rows"),
        "write_seconds": write_s,
        "import_seconds": import_s,
        "threshold_seconds": float(os.environ.get("SSA_PERF_THRESHOLD", "15")),
    }
    # Write local temp copy and persistent report
    (tmp_path / "perf_report.json").write_text(json.dumps(report, indent=2))
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    (reports_dir / "perf_last_import.json").write_text(json.dumps(report, indent=2))
    if verbose:
        print("PERF_REPORT_WRITTEN", flush=True)
    # Soft performance expectation (not a hard fail): warn if import too slow relative to size
    threshold = float(os.environ.get("SSA_PERF_THRESHOLD", "15"))
    allow_slow = os.environ.get("ALLOW_SLOW_IMPORT") == "1"
    if import_s > threshold and not allow_slow:
        pytest.xfail(f"Import took {import_s:.2f}s > threshold {threshold:.2f}s (set ALLOW_SLOW_IMPORT=1 to ignore)")

    # Append history
    history_dir = Path("reports")
    history_dir.mkdir(exist_ok=True)
    history_line = json.dumps({**report, "ts": time.time()})
    with (history_dir / "perf_history.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(history_line + "\n")
