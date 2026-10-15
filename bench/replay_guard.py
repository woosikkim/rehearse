#!/usr/bin/env python3
"""Replay every Bash/Write command in bench/results transcripts through two guard versions and diff the decisions.

  python3 bench/replay_guard.py --old v0.6.3 --new HEAD [--fixture]
Only shape checks are replayed: the marker has mtime 0, so file-age rules are neutralised.
"""
import argparse, glob, importlib.util, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = tempfile.mkdtemp(prefix="replay_guard_")
MARKER = os.path.join(TMP, "active")
open(MARKER, "w").close()
os.utime(MARKER, (0, 0))


def load(ref):
    if ref == "worktree":  # the uncommitted hooks/guard.py on disk
        with open(os.path.join(ROOT, "hooks", "guard.py")) as f:
            src = f.read()
    else:
        src = subprocess.run(["git", "show", f"{ref}:hooks/guard.py"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    path = os.path.join(TMP, f"guard_{len(os.listdir(TMP))}.py")
    with open(path, "w") as f:
        f.write(src)
    spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # the transcripts' files do not exist here, so neutralise the age rule itself (0.7 renames it may_run)
    if hasattr(mod, "predates_marker"):
        mod.predates_marker = lambda *a, **k: True
    if hasattr(mod, "may_run"):
        mod.may_run = lambda *a, **k: True
    return mod


def decide(g, kind, item, errs):
    """Return (refused reason or '', executed, test) for one command; exceptions are counted, not raised."""
    def safe(fn):
        try:
            return fn()
        except Exception:
            errs[0] += 1
            return None
    if kind == "bash":
        reason = safe(lambda: g.check_shell(item, TMP, MARKER, full=True))
        return (reason or "", bool(safe(lambda: g.executed(item))), bool(safe(lambda: g.TEST_CMD.search(item))))
    return (safe(lambda: g.check_write(item, MARKER, False)) or "", False, False)


def commands():
    for path in sorted(glob.glob(os.path.join(ROOT, "bench/results/*/*/transcript.stream.jsonl"))):
        task = path.split(os.sep)[-3]
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    ev = json.loads(line.replace("[REDACTED]", "1"))
                except ValueError:
                    continue
                content = (ev.get("message") or {}).get("content") if ev.get("type") == "assistant" else None
                for b in content if isinstance(content, list) else []:
                    if b.get("type") != "tool_use" or not isinstance(b.get("input"), dict):
                        continue
                    if b.get("name") == "Bash" and isinstance(b["input"].get("command"), str):
                        yield task, "bash", b["input"]["command"]
                    elif b.get("name") in ("Write", "Edit", "MultiEdit"):
                        yield task, "write", b["input"]


def label(kind, item):
    s = item if kind == "bash" else "[%s] %s" % ("write", item.get("file_path") or item.get("path") or "")
    return s.replace("\n", " / ")[:120]


def table(title, rows):
    print(f"\n{title}: {len(rows)}")
    for task, cmd, o, n in rows:
        print(f"  {task} | {cmd} | old: {o[:80] or '-'} | new: {n[:80] or '-'}")


def fixture(old, new):
    bad = 0
    for ln in open(os.path.join(ROOT, "bench/replay_fixture.txt"), encoding="utf-8"):
        ln = ln.rstrip("\n")
        if not ln.strip() or ln.startswith("#"):
            continue
        if "# pending" in ln:
            print("SKIPPED", ln[:110])
            continue
        eo, en, cmd = ln.split("|", 2)
        for ref, g, exp in (("old", old, eo), ("new", new, en)):
            got = "refused" if decide(g, "bash", cmd, [0])[0] else "allowed"
            if got != exp:
                bad += 1
                print(f"MISMATCH {ref}: expected {exp}, got {got}: {cmd[:100]}")
    print("fixture:", "FAIL" if bad else "ok")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", default="HEAD")
    ap.add_argument("--new", default="HEAD")
    ap.add_argument("--fixture", action="store_true")
    a = ap.parse_args()
    old, new = load(a.old), load(a.new)
    if a.fixture:
        return fixture(old, new)
    eo, en = [0], [0]
    so, sn = [0, 0, 0], [0, 0, 0]  # checked, refused, executed
    refused, allowed = [], []
    for task, kind, item in commands():
        ro, xo, _ = decide(old, kind, item, eo)
        rn, xn, _ = decide(new, kind, item, en)
        so[0] += 1; sn[0] += 1; so[1] += bool(ro); sn[1] += bool(rn); so[2] += xo; sn[2] += xn
        if ro and not rn:
            allowed.append((task, label(kind, item), ro, rn))
        elif rn and not ro:
            refused.append((task, label(kind, item), ro, rn))
    for ref, s, e in ((a.old, so, eo), (a.new, sn, en)):
        print(f"{ref}: checked {s[0]}, refused {s[1]}, allowed {s[0] - s[1]}, executed {s[2]}, guard exceptions {e[0]}")
    table("newly refused under --new", refused)
    table("newly allowed under --new", allowed)
    return 0


sys.exit(main())
