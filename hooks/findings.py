"""Two shortcut findings on the diff since activation, handed to the director; they never refuse anything (plan 2.8)."""
import json
import os
import re

import fingerprint as F

TEST_PATH = re.compile(r"(^|/)(test_[^/]*\.py|[^/]*_test\.py|conftest\.py|[^/]*\.(test|spec)\.[^/]+)$"
                       r"|(^|/)(tests|testing|spec)/")
SKIP = re.compile(r"@skip|@pytest\.mark\.skip|unittest\.skip|xfail|\.only\(|test\.skip|xit\(|it\.skip|describe\.skip")


def added_lines(s, rel):
    """Lines added to rel since activation: git diff against HEAD, or the whole file when it is new."""
    path = os.path.join(s["root"], rel)
    if s["fp_activation"].get("git"):
        p = F._git(s["root"], "diff", "-U0", "HEAD", "--", rel)
        out = p.stdout.decode("utf-8", "replace") if p and p.returncode == 0 else ""
        if out:
            return [ln[1:] for ln in out.splitlines() if ln.startswith("+") and not ln.startswith("+++")]
        tracked = F._git(s["root"], "ls-files", "--error-unmatch", "--", rel)
        if tracked and tracked.returncode == 0:
            return []
    elif rel in s["fp_activation"]["files"]:
        return []  # ponytail: non-git keeps no old content, so only new files are scanned
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read(F.BIG).splitlines()
    except OSError:
        return []


def write(s):
    """Write <run folder>/findings.json and return its path."""
    changed = F.code_change(s["fp_activation"], F.fingerprint(s["root"]))
    tests = [{"path": r, "status": "changed" if os.path.exists(os.path.join(s["root"], r)) else "deleted"}
             for r in changed if TEST_PATH.search(r.replace(os.sep, "/"))]
    skips = [{"path": r, "line": ln.strip()} for r in changed for ln in added_lines(s, r) if SKIP.search(ln)]
    out = {"findings": [{"kind": "test files changed or deleted", "items": tests},
                        {"kind": "skip markers added", "items": skips}],
           "baseline": (s.get("ending") or {}).get("baseline") or "no baseline: none recorded"}
    path = os.path.join(s["run_folder"], "findings.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return path
