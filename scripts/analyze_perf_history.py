#!/usr/bin/env python3
"""Analisa histórico de performance (perf_history.jsonl) e gera:
 - reports/perf_weekly_summary.json
 - reports/perf_history_plot.png (se matplotlib disponível)
"""
from __future__ import annotations
import json, time, os, statistics, math
from pathlib import Path

try:
    import matplotlib.pyplot as plt  # type: ignore
except Exception:  # pragma: no cover
    plt = None

HISTORY = Path("reports/perf_history.jsonl")
OUT_WEEKLY = Path("reports/perf_weekly_summary.json")
OUT_PNG = Path("reports/perf_history_plot.png")

def load_lines():
    if not HISTORY.exists():
        return []
    lines = []
    with HISTORY.open() as fh:
        for line in fh:
            line=line.strip()
            if not line:
                continue
            try:
                obj=json.loads(line)
                lines.append(obj)
            except Exception:
                pass
    return lines

def week_key(ts: float):
    return time.strftime("%Y-W%W", time.gmtime(ts))

def aggregate_weekly(rows):
    buckets = {}
    for r in rows:
        wk = week_key(r.get("ts", 0))
        buckets.setdefault(wk, []).append(r)
    summary = []
    for wk, items in sorted(buckets.items()):
        imports = [i.get("import_seconds", 0) for i in items]
        rows_count = [i.get("rows_generated", 0) for i in items]
        uniq = [i.get("final_unique", 0) for i in items]
        summary.append({
            "week": wk,
            "runs": len(items),
            "avg_import_s": statistics.mean(imports) if imports else 0,
            "p95_import_s": percentile(imports, 95) if imports else 0,
            "min_import_s": min(imports) if imports else 0,
            "max_import_s": max(imports) if imports else 0,
            "avg_rows": statistics.mean(rows_count) if rows_count else 0,
            "avg_final_unique": statistics.mean(uniq) if uniq else 0,
        })
    return summary

def percentile(values, pct):
    if not values:
        return 0
    vals = sorted(values)
    k = (len(vals)-1) * (pct/100)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return vals[int(k)]
    d0 = vals[f] * (c-k)
    d1 = vals[c] * (k-f)
    return d0 + d1

def plot(values):  # pragma: no cover
    if not plt:
        return False
    if not values:
        return False
    xs = [v.get("ts") for v in values]
    ys = [v.get("import_seconds") for v in values]
    plt.figure(figsize=(8,4))
    plt.plot(xs, ys, marker='o', linewidth=1)
    plt.title("Import Time Over Runs")
    plt.xlabel("timestamp")
    plt.ylabel("import_seconds")
    plt.tight_layout()
    plt.savefig(OUT_PNG)
    return True

def main():
    rows = load_lines()
    weekly = aggregate_weekly(rows)
    OUT_WEEKLY.write_text(json.dumps(weekly, indent=2))
    plotted = plot(rows)
    print(f"WEEKLY_SUMMARY_WRITTEN {OUT_WEEKLY} plotted={plotted}")
    if plotted:
        print(f"PLOT {OUT_PNG}")

if __name__ == "__main__":
    main()
