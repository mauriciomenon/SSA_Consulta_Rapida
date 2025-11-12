#!/usr/bin/env python3
"""Measure import times to identify startup bottlenecks."""
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def measure_import(module_name, globals_dict=None, fromlist=None):
    """Measure time to import a module."""
    start = time.perf_counter()
    try:
        if fromlist:
            __import__(module_name, globals_dict, None, fromlist)
        else:
            __import__(module_name)
        elapsed = (time.perf_counter() - start) * 1000
        print(f"{elapsed:8.2f}ms  {module_name}")
        return elapsed
    except Exception as e:
        print(f"   ERROR   {module_name}: {e}")
        return 0

print("=" * 60)
print("Import Time Measurement")
print("=" * 60)

total = 0

# Core Python stdlib
print("\n--- Standard Library ---")
total += measure_import("argparse")
total += measure_import("logging")
total += measure_import("sqlite3")
total += measure_import("json")
total += measure_import("pathlib")

# Scientific libraries
print("\n--- Scientific Libraries ---")
total += measure_import("pandas")
total += measure_import("numpy")
total += measure_import("openpyxl")

# GUI libraries
print("\n--- GUI Libraries (PyQt6) ---")
total += measure_import("PyQt6.QtWidgets", fromlist=["QApplication"])
total += measure_import("PyQt6.QtCore", fromlist=["Qt"])
total += measure_import("PyQt6.QtGui", fromlist=["QFont"])

# Project modules
print("\n--- Project Core Modules ---")
total += measure_import("core.app_logic")
total += measure_import("core.config_manager")
total += measure_import("armazenamento.database")
total += measure_import("utils.formatting")

# Project GUI modules
print("\n--- Project GUI Modules ---")
total += measure_import("gui.gui_ssa")
total += measure_import("gui.theme_manager")

print("\n" + "=" * 60)
print(f"Total measured time: {total:.2f}ms ({total/1000:.2f}s)")
print("=" * 60)
