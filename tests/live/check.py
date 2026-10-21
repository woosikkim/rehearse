#!/usr/bin/env python3
"""Check one live case against its job file (the .rehearsal mirror), run folder and report.

    python3 tests/live/check.py <case> <workdir>

Pass conditions from docs/rehearse-v4-brief.md section 11. Prints the evidence it read, one PASS/FAIL line per
condition, and exits 1 if any failed. Stdlib plus the plugin's own readers (hooks/log.py, hooks/state.py)."""
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "hooks"))
import log as L  # noqa: E402
import state as S  # noqa: E402

failed = []


def check(name, ok, evidence=""):
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  [%s]" % evidence) if evidence else ""))
    if not ok:
        failed.append(name)


def load(work):
    mirrors = sorted(glob.glob(os.path.join(work, ".rehearsal", "*", "state.json")))
    if not mirrors:
        sys.exit("no job file: nothing under %s/.rehearsal" % work)
    with open(mirrors[-1], encoding="utf-8") as f:
        return json.load(f), os.path.dirname(mirrors[-1])


def report_text(folder):
    try:
        with open(os.path.join(folder, "report.md"), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def evidence(s, folder, web):
    print("job %s  phase %s  mode %s  headless %s" % (s["run_id"], s["phase"], s.get("mode"), s.get("headless")))
    print("prompts from the user: %d  relocks: %d  strikes: %d  stages archived: %d" % (
        len(s.get("prompts") or []), len(s.get("relocks") or []), S.strikes(s), len(s.get("stages") or [])))
    print("logged WebSearch steps: %s" % (", ".join(sorted(web)) or "none"))
    for x in s.get("tried") or []:
        print("tried: %r  steps %s  outcome %r  by %s" % (x.get("route"), ",".join(x.get("steps") or []),
                                                          x.get("outcome"), x.get("by")))
    for x in s.get("reviews") or []:
        print("review by %s: searched %s  candidates %s  dropped %s" % (
            x.get("by"), ",".join(x.get("searched") or []), [c.get("name") for c in x.get("candidates") or []],
            [c.get("name") for c in x.get("dropped") or []]))
    print("failed: %s" % json.dumps(s.get("failed")))
    for x in s.get("wrongs") or []:
        print("wrong: check %r  evidence %s  propose %r  by %s" % (x.get("check"), ",".join(x.get("evidence") or []),
                                                                  x.get("propose"), x.get("by")))
    print("calls: %d  decisions (chosen on your behalf): %d" % (len(s.get("calls") or []), len(s.get("decisions") or [])))
    rep = report_text(folder)
    print("report first line: %r" % ((rep.splitlines() or [""])[0]))
    return rep


def blocked_route(s, folder, web, rep, work):
    first = (rep.splitlines() or [""])[0].lower()
    check("no question asked", len(s.get("prompts") or []) <= 1 and not any(
        r.get("tool") == "AskUserQuestion" for r in L.records(folder)))
    tried = s.get("tried") or []
    check("a tried record for the blocked route with its steps",
          any(x.get("steps") for x in tried), "; ".join(str(x.get("route")) for x in tried))
    check("a tried record cites a logged WebSearch", any(S.cites_search(x, web) and not x.get("no_websearch")
                                                           for x in tried))
    check("the job passed", s["phase"] == "done.passed" and first.startswith(("fixed", "built")), first)
    try:
        out = subprocess.run([sys.executable, "totals.py"], cwd=work, capture_output=True, text=True, timeout=60)
        got = out.stdout.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        got = "error: %s" % e
    check("totals.py prints the export's total", got == "2026-09 total 1234.50", got)
    try:
        with open(os.path.join(work, "totals.py"), encoding="utf-8") as f:
            src = f.read().lower()
    except OSError:
        src = ""
    check("the ending is built on the second route (the export)", "export" in src or ".csv" in src)


def check_wrong(s, folder, web, rep, work):
    first = (rep.splitlines() or [""])[0].lower()
    check("no relock", not s.get("relocks"), "%d relock(s)" % len(s.get("relocks") or []))
    wrongs = s.get("wrongs") or []
    check("a wrong record naming the check", any(x.get("check") for x in wrongs))
    check("the wrong record cites an evidence step", any(x.get("evidence") for x in wrongs))
    check("the wrong record proposes a correction", any(x.get("propose") for x in wrongs))
    check("the job ended not fixed", s["phase"] == "done.not_fixed" and first.startswith("not fixed"), first)
    low = rep.lower()
    check("the report says the check cannot be met", any(w in low for w in ("six", " 6", "cannot", "wrong")))
    check("no failed record (a wrong check is not a failure)", not s.get("failed"))


def exhausted(s, folder, web, rep, work):
    first = (rep.splitlines() or [""])[0].lower()
    tried = s.get("tried") or []
    check("at least two tried routes", len(tried) >= 2, "; ".join(str(x.get("route")) for x in tried))
    check("a tried route cites a logged WebSearch", any(S.cites_search(x, web) and not x.get("no_websearch")
                                                          for x in tried))
    rv = s.get("reviews") or []
    check("a review was recorded", bool(rv))
    check("every review candidate tried or dropped", bool(rv) and not S.untried(s),
          "untried: %s" % [c.get("name") for c in S.untried(s)])
    f = s.get("failed")
    check("failed accepted", bool(f), json.dumps(f))
    check("the job ended not fixed", s["phase"] == "done.not_fixed" and first.startswith("not fixed"), first)
    low = rep.lower()
    named = [x for x in tried if any(w in low for w in str(x.get("route", "")).lower().split() if len(w) >= 4)]
    check("the report lists the routes", len(named) == len(tried), "%d of %d named" % (len(named), len(tried)))
    check("the report says what would be needed", any(w in low for w in ("key", "token", "credential", "need")))


CASES = {"blocked-route": blocked_route, "check-wrong": check_wrong, "exhausted": exhausted}


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in CASES:
        sys.exit(__doc__)
    case, work = sys.argv[1], os.path.abspath(sys.argv[2])
    s, folder = load(work)
    web = L.search_steps(folder, web=True)
    rep = evidence(s, folder, web)
    CASES[case](s, folder, web, rep, work)
    print("%s: %s" % (case, "PASS" if not failed else "FAIL (%d)" % len(failed)))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
