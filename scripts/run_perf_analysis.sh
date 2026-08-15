#!/usr/bin/env bash
set -euo pipefail
python scripts/analyze_perf_history.py
echo '--- Weekly summary ---'
sed -n '1,120p' reports/perf_weekly_summary.json || true