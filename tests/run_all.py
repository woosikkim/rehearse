#!/usr/bin/env python3
"""Run every rehearse test script that exists and exit non-zero if any fails.

    python3 tests/run_all.py

Stdlib only. Scripts are run in this order when present: the v2 scripts first,
then the 0.7 guard test while it still exists.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = ["test_hooks.py", "test_stage.py", "test_director_checks.py", "test_stdlib_only.py", "test_guard.py"]

failed = []
for name in SCRIPTS:
    path = os.path.join(HERE, name)
    if not os.path.exists(path):
        continue
    r = subprocess.run([sys.executable, path], capture_output=True, text=True)
    tail = (r.stdout + r.stderr).strip().splitlines()
    if r.returncode != 0:
        # Print only on failure: the ralph verify gate fingerprints every output line,
        # so a passing run must stay silent.
        failed.append(name)
        print(f"{name}: FAILED")
        print("\n".join(tail[-15:]))
sys.exit(1 if failed else 0)
