#!/usr/bin/env python3
"""Copy a finished Harbor job into bench/results/<task>/<label>/ and print one table row per task.

    python3 bench/collect.py bench/jobs/<job> <label>

Each row: fixed (all hidden tests pass), broke-others (previously passing tests now failing),
real run before first edit (a one-liner, test run or script executed while the marker was up),
guard blocks, turns, cost, minutes. Reads Harbor's result.json, verifier/report.json and the
Claude Code stream-json transcript; no third-party packages.
"""
import json, os, re, shutil, sys
from datetime import datetime

EXEC = re.compile(r"(?:^|&&|;|\|\|)\s*(?:PATH=\S+\s+)?(?:\S*/)?(?:python3?(?:\.\d+)?\s+(?:-c\s+'|-m\s|\S+\.py)|node\s+-[ep]|ruby\s+-e|curl\s|pytest|npm test|make\s|sqlite3\s|\./\S+)")


def events(path):
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.replace("[REDACTED]", "1")
        try:
            yield json.loads(line)
        except ValueError:
            continue


def summarize(transcript):
    calls, order, blocks, announce, final, turns = {}, [], 0, "", "", 0
    marker_up, real_before_edit, first_edit_seen = False, False, False
    for d in events(transcript):
        if d.get("type") == "assistant":
            turns += 1
            for c in d["message"]["content"]:
                if c.get("type") == "text" and not announce:
                    m = re.search(r"Rehearse: (\w+), because", c["text"])
                    announce = m.group(1) if m else ""
                if c.get("type") == "tool_use":
                    calls[c["id"]] = c
                    order.append(c)
        elif d.get("type") == "user":
            for c in d["message"].get("content", []):
                if isinstance(c, dict) and c.get("type") == "tool_result":
                    call = calls.get(c["tool_use_id"])
                    if not call:
                        continue
                    out = c["content"] if isinstance(c["content"], str) else " ".join(x.get("text", "") for x in c["content"] if isinstance(x, dict))
                    blocked = "rehearse: blocked" in out
                    blocks += blocked
                    if call["name"] == "Bash" and not blocked:
                        cmd = call["input"].get("command", "")
                        if re.search(r"touch\s+\S*\.rehearsal/active", cmd):
                            marker_up = True
                        if re.search(r"rm\s+(-\S+\s+)?\S*\.rehearsal", cmd):
                            marker_up = False
                        if marker_up and not first_edit_seen and EXEC.search(cmd):
                            real_before_edit = True
                    if call["name"] in {"Edit", "Write", "MultiEdit"} and not blocked:
                        first_edit_seen = True
                    if call["name"] == "Bash" and not blocked and re.search(r"(cat|tee)\s*>>?\s*\S+\.py|sed -i|patch\s", call["input"].get("command", "")):
                        first_edit_seen = True
        elif d.get("type") == "result":
            final = d.get("result", "")
    return dict(turns=turns, tool_calls=len(order), guard_blocks=blocks, announce=announce or "-", real_run_before_edit=real_before_edit, final=final)


def walk(o, acc):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("cost_usd", "started_at", "finished_at"):
                acc.setdefault(k, v)
            walk(v, acc)
    elif isinstance(o, list):
        for v in o:
            walk(v, acc)
    return acc


def main(job, label):
    rows = []
    for trial in sorted(os.listdir(job)):
        t = os.path.join(job, trial)
        if not os.path.isdir(t) or not os.path.isdir(os.path.join(t, "verifier")):
            continue
        tb = not os.path.exists(os.path.join(t, "verifier", "report.json"))  # Terminal-Bench: reward.txt, no FAIL_TO_PASS split
        if tb and not os.path.exists(os.path.join(t, "verifier", "reward.txt")):
            continue
        task = re.sub(r"__[^_]+$", "", trial)
        short = task.split("__")[1] if "__" in task else "tb2-" + task
        dest = os.path.join("bench", "results", short, label)
        os.makedirs(dest, exist_ok=True)
        shutil.copy(os.path.join(t, "agent", "claude-code.txt"), os.path.join(dest, "transcript.stream.jsonl"))
        for name in ("report.json", "reward.txt", "test-stdout.txt"):
            if os.path.exists(os.path.join(t, "verifier", name)):
                shutil.copy(os.path.join(t, "verifier", name), os.path.join(dest, name))
        shutil.copy(os.path.join(t, "result.json"), os.path.join(dest, "harbor-result.json"))
        if tb:
            reward = float(open(os.path.join(dest, "reward.txt")).read().strip() or 0)
            rep = {"resolved": reward >= 1.0}
            ts = {"PASS_TO_PASS": {"failure": []}, "FAIL_TO_PASS": {"failure": [] if reward >= 1.0 else ["reward=%s" % reward]}}
        else:
            rep = list(json.load(open(os.path.join(dest, "report.json"))).values())[0]
            ts = rep["tests_status"]
        meta = walk(json.load(open(os.path.join(dest, "harbor-result.json"))), {})
        f = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))
        mins = (f(meta["finished_at"]) - f(meta["started_at"])).total_seconds() / 60 if "finished_at" in meta else 0
        s = summarize(os.path.join(dest, "transcript.stream.jsonl"))
        row = dict(task=short, fixed=rep["resolved"], broke_others=len(ts["PASS_TO_PASS"]["failure"]),
                   hidden_tests_failing=len(ts["FAIL_TO_PASS"]["failure"]), announce=s["announce"],
                   real_run_before_edit=s["real_run_before_edit"], guard_blocks=s["guard_blocks"], turns=s["turns"],
                   cost_usd=round(meta.get("cost_usd", 0), 2), minutes=round(mins, 1))
        rows.append(row)
        with open(os.path.join(dest, "summary.json"), "w") as fh:
            json.dump(dict(row, final=s["final"]), fh, indent=1)
        with open(os.path.join(dest, "final-message.md"), "w") as fh:
            fh.write(s["final"])
    cols = ["task", "fixed", "broke_others", "hidden_tests_failing", "announce", "real_run_before_edit", "guard_blocks", "turns", "cost_usd", "minutes"]
    print("| " + " | ".join(cols) + " |")
    print("|" + "---|" * len(cols))
    for r in rows:
        print("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return rows


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
