#!/usr/bin/env python
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_TARGET = PROJECT_ROOT / "tests" / "test_search_filtering_logic.py"


if __name__ == "__main__":
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(TEST_TARGET)],
        cwd=PROJECT_ROOT,
        check=False,
    )
    raise SystemExit(result.returncode)
