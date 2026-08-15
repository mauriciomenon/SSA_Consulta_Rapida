#!/usr/bin/env bash
set -euo pipefail
if [ $# -lt 1 ]; then
  echo "Usage: $0 <command> [args...]" >&2
  exit 1
fi
export PYTHONUNBUFFERED=1
LOG_FILE="capture_$(date +%Y%m%d_%H%M%S).log"
echo "[run_with_capture] Logging to $LOG_FILE" >&2
"$@" 2>&1 | tee "$LOG_FILE"
echo "[run_with_capture] --- Tail of log ---" >&2
tail -n 50 "$LOG_FILE" >&2
echo "[run_with_capture] Complete" >&2
