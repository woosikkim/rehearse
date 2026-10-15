#!/usr/bin/env python3
"""Every module the plugin ships imports only the standard library.

    python3 tests/test_stdlib_only.py

Imports every .py under hooks/, stage/, tracer/ and the bin/rehearse script in a clean interpreter
(python3 -I -S: no user site, no site-packages, no PYTHON* variables) and fails if anything else got loaded.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIRS = [os.path.join(ROOT, d) for d in ("hooks", "stage", "bin", "tracer")]

CHILD = r'''
import importlib.machinery, importlib.util, os, sys, json
dirs = json.loads(sys.argv[1])
files = []
for d in dirs:
    if not os.path.isdir(d):
        continue
    sys.path.insert(0, d)
    for name in sorted(os.listdir(d)):
        path = os.path.join(d, name)
        if os.path.isfile(path) and (name.endswith(".py") or os.path.basename(d) == "bin"):
            files.append(path)
for i, path in enumerate(files):
    spec = importlib.util.spec_from_file_location("_shipped_%d" % i, path,
                                                  loader=importlib.machinery.SourceFileLoader("_shipped_%d" % i, path))
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass  # hooks/guard.py is a shim that exits on import
inside = tuple(os.path.realpath(d) + os.sep for d in dirs)
foreign = []
for name, mod in list(sys.modules.items()):
    f = getattr(mod, "__file__", None)
    if f and os.path.realpath(f).startswith(inside):
        continue
    if name == "__main__" or name.split(".")[0] in sys.stdlib_module_names:
        continue
    foreign.append("%s (%s)" % (name, f))
print(json.dumps({"files": len(files), "foreign": foreign}))
'''

if sys.version_info < (3, 10):
    print("stdlib: skipped, needs Python 3.10+ for sys.stdlib_module_names")
    sys.exit(0)
r = subprocess.run([sys.executable, "-I", "-S", "-c", CHILD, json.dumps(DIRS)],
                   capture_output=True, text=True, cwd=ROOT)
assert r.returncode == 0, r.stderr
out = json.loads(r.stdout.strip().splitlines()[-1])
assert out["files"] > 0, "no modules found"
assert not out["foreign"], "non-stdlib modules loaded: %s" % ", ".join(out["foreign"])
print("stdlib: all checks passed")
