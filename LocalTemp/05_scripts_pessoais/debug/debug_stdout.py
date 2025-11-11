#!/usr/bin/env python3
"""Quick utility to verify stdout visibility in current environment."""
import sys, time, os
print("DEBUG_STDOUT: start", flush=True)
print(f"PYTHONUNBUFFERED={os.environ.get('PYTHONUNBUFFERED')}")
for i in range(3):
    print(f"line {i}")
    sys.stdout.flush()
    time.sleep(0.1)
print("DEBUG_STDOUT: done", flush=True)
