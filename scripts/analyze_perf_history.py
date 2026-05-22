#!/usr/bin/env python3
"""Analisa histórico de performance (perf_history.jsonl) e gera:
- reports/perf_weekly_summary.json
- reports/perf_history_plot.png (se matplotlib disponível)
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

try:
    import matplotlib.pyplot as plt  # type: ignore
except Exception:  # pragma: no cover
    plt = None

HISTORY = Path("reports/perf_history.jsonl")
OUT_WEEKLY = Path("reports/perf_weekly_summary.json")
OUT_PNG = Path("reports/perf_history_plot.png")


def iter_history():
    if not HISTORY.exists():
        return
    invalid_count = 0
    with HISTORY.open() as fh:
        for line_number, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                yield obj
            except json.JSONDecodeError as exc:
                invalid_count += 1
                print(f"Invalid JSON in {HISTORY}:{line_number}: {exc}", file=sys.stderr)
    if invalid_count:
        print(
            f"WARNING: ignored {invalid_count} invalid JSON line(s) in {HISTORY}",
            file=sys.stderr,
        )


def week_key(ts: float):
    return time.strftime("%Y-W%W", time.gmtime(ts))


def aggregate_weekly(rows):
    buckets = {}
    for r in rows:
        wk = week_key(r.get("ts", 0))
        buckets.setdefault(wk, []).append(r)
    summary = []
    for wk, items in sorted(buckets.items()):
        imports = []
        rows_count = []
        uniq = []
        for item in items:
            for raw_value, target in (
                (item.get("import_seconds"), imports),
                (item.get("rows_generated"), rows_count),
                (item.get("final_unique"), uniq),
            ):
                if raw_value is None:
                    continue
                try:
                    value = float(raw_value)
                except (TypeError, ValueError):
                    continue
                if np.isfinite(value):
                    target.append(value)
        if imports:
            avg_import_s = float(np.mean(imports))
            p95_import_s = percentile(imports, 95)
            min_import_s = min(imports)
            max_import_s = max(imports)
        else:
            avg_import_s = 0
            p95_import_s = 0
            min_import_s = 0
            max_import_s = 0
        avg_rows = float(np.mean(rows_count)) if rows_count else 0
        avg_final_unique = float(np.mean(uniq)) if uniq else 0
        summary.append(
            {
                "week": wk,
                "runs": len(items),
                "avg_import_s": avg_import_s,
                "p95_import_s": p95_import_s,
                "min_import_s": min_import_s,
                "max_import_s": max_import_s,
                "avg_rows": avg_rows,
                "avg_final_unique": avg_final_unique,
            }
        )
    return summary


def percentile(values, pct):
    if not values:
        return 0
    return float(np.percentile(values, pct))


def plot(values):  # pragma: no cover
    if not plt:
        return False
    if not values:
        return False
    points = [
        (row.get("ts"), row.get("import_seconds"))
        for row in values
        if row.get("ts") is not None and row.get("import_seconds") is not None
    ]
    if not points:
        return False
    xs = [datetime.fromtimestamp(float(point[0]), tz=timezone.utc) for point in points]
    ys = [point[1] for point in points]
    plt.figure(figsize=(8, 4))
    try:
        plt.plot(xs, ys, marker="o", linewidth=1)
        plt.title("Import Time Over Runs")
        plt.xlabel("timestamp")
        plt.ylabel("import_seconds")
        plt.tight_layout()
        plt.savefig(OUT_PNG)
    finally:
        plt.close()
    return True


def main():
    history = list(iter_history())
    weekly = aggregate_weekly(history)
    OUT_WEEKLY.write_text(json.dumps(weekly, indent=2))
    plotted = plot(history)
    print(f"WEEKLY_SUMMARY_WRITTEN {OUT_WEEKLY} plotted={plotted}")
    if plotted:
        print(f"PLOT {OUT_PNG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
