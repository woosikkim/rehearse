#!/usr/bin/env python3
"""rehearse: the single hook entry. Reads one Claude Code hook payload on stdin, dispatches on hook_event_name.

UserPromptSubmit: activation, `rehearse stop`, the confirmation answer, later prompts.
PreToolUse: the edit gate in observe, confirm and rework-observe; created files may not run there.
PostToolUse(Failure): the log, REHEARSE-RESULT lines from bin/rehearse, edit rounds and the loop breaker.
PreToolUse(Agent), SubagentStop: the director's prompt, model and verdict. Stop: when a run may end.
Fails open: any error or malformed input exits 0 with no decision.
"""
import json
import os
import re
import signal
import sys
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ending as E  # noqa: E402
import findings as FD  # noqa: E402
import fingerprint as F  # noqa: E402
import log as L  # noqa: E402
import provenance as P  # noqa: E402
import state as S  # noqa: E402

LOCKED = ("observe", "confirm", "rework-observe")
EDIT_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
AFFIRMATIVE = {"yes", "y", "ok", "correct", "confirmed", "네", "예", "응", "맞아", "맞아요", "네 맞아요"}
ACTIVATE = re.compile(r"^(?:/rehearse(?::rehearse)?(?:\s+|$)|rehearse(?:\s*:\s*|\s+))(.*)$", re.I | re.S)
LOOP_ROUNDS = 2
NEED_ENDING = "register and confirm an ending first"
NEED_LOOK = ("edits are locked after two failing rounds with no direct look; look directly (a stage step that "
             "calls project code, or rehearse fetch to a known host) or make rehearse run pass")
URL = re.compile(r"https?://([^/\s'\"<>:]+)")
DIRECTOR = ("rehearse:director", "director")
REPORT_LINES = ("fixed", "built, not verified against the real target", "not fixed")


def status_line(s):
    return "[rehearse] run %s, phase %s" % (s["run_id"], s["phase"])


def context(event, text):
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}


def deny(s, why):
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                   "permissionDecisionReason": "rehearse: %s.\n%s" % (why, status_line(s))}}


def block(s, why):
    return {"decision": "block", "reason": "rehearse: %s.\n%s" % (why, status_line(s))}


# ---------- UserPromptSubmit ----------

def instructions(mode, run_id):
    path = os.path.join(HERE, "instructions", "%s.md" % (mode or "rehearse"))
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read().replace("${CLAUDE_PLUGIN_ROOT}", os.path.dirname(HERE))
    except OSError:
        text = "[rehearse] instructions pending"
    return text.rstrip() + "\n[rehearse] run %s activated" % run_id


def on_prompt(p, sid):
    prompt = str(p.get("prompt") or "").strip()
    m = ACTIVATE.match(prompt)
    rest = m.group(1).strip() if m else None
    is_stop = rest is not None and rest.lower() == "stop"
    s = S.current(sid)
    if s and not s["phase"].startswith("done"):
        with S.locked(s) as cur:
            if is_stop:
                cur["phase"] = "done.cancelled"
                cur["notes"].append("cancelled by user")
            elif cur["phase"] == "confirm":
                yes = prompt.lower().rstrip(".!") in AFFIRMATIVE
                cur["confirmation"] = {"by": "user", "answer": prompt, "affirmative": yes, "at": time.time()}
                if prompt.lower().startswith("stop here"):
                    cur["stop_here"] = True
                if yes:
                    cur["phase"] = "work"
            else:
                cur["prompts"].append(prompt)
        if is_stop:
            return {"systemMessage": "rehearse stopped (run %s cancelled)" % s["run_id"]}
        if cur["phase"] == "work" and s["phase"] == "confirm":
            return context("UserPromptSubmit", "[rehearse] the user confirmed the ending; edits are open.")
        return None
    if rest is None or is_stop:
        return None
    word = re.match(r"(fix|build)\b", rest, re.I)
    mode = word.group(1).lower() if word else None
    root = p.get("cwd") or os.getcwd()
    s = S.new_run(sid, root, mode, prompt, F.fingerprint(root))
    return dict(context("UserPromptSubmit", instructions(mode, s["run_id"])),
                systemMessage="rehearse is on — type `rehearse stop` to stop")


# ---------- PreToolUse ----------

def new_code_file(s, path):
    """A project code file present now and absent at activation, that no program produced."""
    if not F.is_code(path) or path in s["produced"] or F.kind(s["root"], path) != "code":
        return False
    rel = os.path.relpath(path, s["root"])
    if rel in s["fp_activation"]["files"]:
        return False
    if s["fp_activation"].get("git"):
        tracked = F._git(s["root"], "ls-files", "--error-unmatch", "--", rel)
        if tracked and tracked.returncode == 0:
            return False
    return os.path.isfile(path) and os.path.getmtime(path) >= s["created_at"] - 1


def option(name, default):
    return os.environ.get("CLAUDE_PLUGIN_OPTION_" + name) or os.environ.get("REHEARSE_" + name) or default


def attended():
    return option("CONFIRM_ENDING", "true").lower() not in ("false", "0", "no")


def updated(tin, name, extra):
    try:
        with open(os.path.join(HERE, "instructions", name), encoding="utf-8") as f:
            text = f.read().rstrip()
    except OSError:
        return None
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedInput": dict(
        tin, prompt=text + "\n\nThis run:\n" + extra, model=option("DIRECTOR_MODEL", "opus"))}}


def spawn_review(s, tin):
    """Unattended confirm: the director reviews the ending against the request."""
    with S.locked(s) as cur:
        cur["review_spawned"] = True
    return updated(tin, "director-review.md", "- state file (request, prompts, ending): %s\n" % s["path"])


def spawn_director(s, tin):
    """Replace the director's prompt and model; take the spawn fingerprint and enter judge."""
    if not os.path.exists(os.path.join(HERE, "instructions", "director.md")):
        return None
    with S.locked(s) as cur:
        fpath = FD.write(cur)
        cur["spawn_fingerprint"] = F.fingerprint(cur["root"])
        cur["spawn_at"] = time.time()
        cur["spawn_from"] = cur["phase"]
        cur["phase"] = "judge"
    return updated(tin, "director.md", "- run folder: %s\n- ending record: %s (the \"ending\" key)\n- findings: %s\n"
                   "- project root: %s\n" % (cur["run_folder"], cur["path"], fpath, cur["root"]))


def on_pre(p, sid):
    s = S.current(sid)
    if not s or s["phase"].startswith("done"):
        return None
    tool = p.get("tool_name")
    tin = p.get("tool_input") if isinstance(p.get("tool_input"), dict) else {}
    cwd = p.get("cwd") or s["root"]
    if tool == "Agent":
        if tin.get("subagent_type") in DIRECTOR and s["phase"] in ("work", "rework-observe", "judge"):
            return spawn_director(s, tin)
        if tin.get("subagent_type") in DIRECTOR and s["phase"] == "confirm" and not attended():
            return spawn_review(s, tin)
        return None
    if p.get("agent_type") in DIRECTOR and tool in EDIT_TOOLS:
        path = tin.get("file_path") or tin.get("notebook_path")
        if path and F.kind(s["root"], P.realpath(cwd, path)):
            return deny(s, "the director judges and cannot edit project code; %s is project code" % path)
    why = NEED_LOOK if s["phase"] == "rework-observe" else NEED_ENDING
    if tool in EDIT_TOOLS:
        path = tin.get("file_path") or tin.get("notebook_path")
        if not path:
            return None
        real = P.realpath(cwd, path)
        if s["phase"] in LOCKED and F.kind(s["root"], real):
            return deny(s, "%s; %s is project code" % (why, path))
        if tool == "Write" and not os.path.exists(real):
            with S.locked(s) as cur:
                cur["created"].append(real)
        return None
    if tool != "Bash":
        return None
    segs = P.parse(str(tin.get("command") or ""), cwd)
    if s["phase"] in LOCKED:
        for seg in segs:
            for t in seg["targets"]:
                if F.kind(s["root"], t) == "code":
                    return deny(s, "%s; this command writes the code file %s" % (why, t))
        made = set()  # outputs of earlier segments of this same command (cc -o prog x.c && ./prog)
        created = set(s["created"])
        for seg in segs:
            pp = seg["pp"]
            if pp and os.path.isabs(pp) and pp not in made and (pp in created or new_code_file(s, pp)):
                return deny(s, "%s was created during this run; it may not run while edits are locked. Run "
                               "programs that existed at activation, or look through the stage" % pp)
            made.update(seg["outputs"])
    targets = [t for seg in segs for t in seg["targets"]]
    outputs = [o for seg in segs for o in seg["outputs"]]
    if targets or outputs:
        with S.locked(s) as cur:
            cur["created"] += [t for t in targets if t not in cur["created"]]
            cur["produced"] += [o for o in outputs if o not in cur["produced"]]
    return None


# ---------- PostToolUse ----------

def ending_marks(s):
    """Program positions and test runners whose direct run closes an edit round."""
    e = s.get("ending") or {}
    pps, runners = set(), set()
    for cmd in (e.get("cmd"), e.get("tests_effective")):
        for seg in P.parse(cmd or "", s["root"]):
            if seg["runner"]:
                runners.add(seg["runner"])
            elif seg["pp"] and cmd == e.get("cmd"):
                pps.add(seg["pp"])
    return pps, runners


def known_host(s, host=None):
    """With host: is it named in the request, the ending command or a project file. Without: is any host known."""
    texts = [s.get("request") or ""] + s.get("prompts", []) + [(s.get("ending") or {}).get("cmd") or ""]
    def hit(text):
        return (host in text) if host else bool(URL.search(text))
    if any(hit(t) for t in texts):
        return True
    for rel in F.project_files(s["root"]):
        try:
            with open(os.path.join(s["root"], rel), encoding="utf-8", errors="replace") as f:
                if hit(f.read(F.BIG)):
                    return True
        except OSError:
            continue
    return False


def runs_python(s):
    segs = P.parse((s.get("ending") or {}).get("cmd") or "", s["root"])
    return any(P.base_name(seg["prog"]) == "python" or seg["runner"] in ("pytest", "unittest")
               or str(seg["pp"]).endswith(".py") for seg in segs)


def leave_locked(cur, base):
    """The exit check: the code files that changed since base, or [] (and the phase moves on)."""
    return F.code_change(base, F.fingerprint(cur["root"]))


def unlock_rework(cur, msgs, why):
    changed = leave_locked(cur, cur["fp_phase_entry"])
    if changed:
        msgs.append("code changed during Observe: %s; put them back, then try again" % ", ".join(changed))
        return
    cur["phase"] = "work"
    cur["failing_rounds"] = 0
    msgs.append("edits are open again (%s)" % why)


def close_round(cur, passing, by, msgs):
    cur["round_open"] = False
    cur["rounds"].append({"passing": passing, "by": by, "at": time.time()})
    cur["failing_rounds"] = 0 if passing else cur["failing_rounds"] + 1
    if cur["failing_rounds"] < LOOP_ROUNDS:
        return
    if runs_python(cur) or known_host(cur):
        cur["phase"] = "rework-observe"
        cur["fp_phase_entry"] = F.fingerprint(cur["root"])
        msgs.append("%d failing rounds with no direct look: edits are locked. Look at what the code really does "
                    "(a stage step that calls project code, or rehearse fetch to a known host), or make "
                    "rehearse run pass" % cur["failing_rounds"])
    else:
        if "loop breaker not enforced: no stage for this language" not in cur["notes"]:
            cur["notes"].append("loop breaker not enforced: no stage for this language")
        msgs.append("reminder: %d failing rounds with no direct look. Stop guessing; look at what the code "
                    "really does before the next edit" % cur["failing_rounds"])


def direct_look(cur, msgs):
    cur["direct_looks"] += 1
    cur["failing_rounds"] = 0
    if cur["phase"] == "rework-observe":
        unlock_rework(cur, msgs, "direct look")


def apply_result(cur, res, msgs):
    kind = res.get("kind")
    if kind == "ending" and res.get("ok"):
        if cur["phase"] not in ("observe", "confirm"):
            msgs.append("an ending is registered in observe or confirm, not in %s" % cur["phase"])
            return True
        changed = leave_locked(cur, cur["fp_activation"])
        if changed:
            msgs.append("code changed during Observe: %s; put them back, then register" % ", ".join(changed))
            return True
        if res.get("all_pass"):
            msgs.append("the ending shows nothing wrong: every expectation already passes against the code as it "
                        "was at activation. An ending must fail before the fix (a build fails because the program "
                        "does not exist yet)")
            return True
        e = dict(res["ending"], before=res.get("before"), after=None, baseline=res.get("baseline"),
                 tests_effective=(res.get("baseline") or {}).get("cmd"))
        cur["ending"] = e
        cur["phase"] = "confirm"
        cur["uncovered"] = []
        msgs.append("ending registered. Ask the user to confirm it in one plain sentence, with the command and "
                    "the expected values beneath")
        return False
    if kind == "run" and res.get("ok") and res.get("as_director"):
        cur.setdefault("director_runs", []).append(dict({k: res.get(k) for k in ("rc", "results", "all_pass")},
                                                        agent_type=res.get("agent_type"), at=time.time()))
        return False
    if kind == "run" and res.get("ok") and cur.get("ending"):
        cur["ending"]["after"] = {k: res.get(k) for k in ("rc", "stdout", "stderr", "results", "all_pass")}
        passing = bool(res.get("all_pass"))
        if cur["phase"] == "work" and cur["round_open"]:
            close_round(cur, passing, "rehearse run", msgs)
        elif passing:
            cur["failing_rounds"] = 0
            if cur["phase"] == "rework-observe":
                unlock_rework(cur, msgs, "rehearse run passed")
        return False
    if kind == "fetch" and res.get("ok") and res.get("fixture"):
        cur["fixtures"].append(res["fixture"])
        if cur["phase"] in ("work", "rework-observe") and res.get("host") and known_host(cur, res["host"]):
            direct_look(cur, msgs)
        return False
    if kind == "stage-step":
        files = [P.realpath(cur["root"], f) for f in res.get("project_files") or []]
        if any(F.kind(cur["root"], f) for f in files) and cur["phase"] in ("work", "rework-observe"):
            direct_look(cur, msgs)
    return False


def last_result(text):
    lines = [ln for ln in text.splitlines() if ln.startswith("REHEARSE-RESULT ")]
    if not lines:
        return None
    try:
        res = json.loads(lines[-1][len("REHEARSE-RESULT "):])
        return res if isinstance(res, dict) else None
    except ValueError:
        return None


def on_post(p, sid):
    s = S.current(sid)
    if not s:
        return None
    tool = p.get("tool_name")
    tin = p.get("tool_input") if isinstance(p.get("tool_input"), dict) else {}
    cwd = p.get("cwd") or s["root"]
    msgs, refused = [], False
    if tool in EDIT_TOOLS:
        path = tin.get("file_path") or tin.get("notebook_path")
        k = F.kind(s["root"], P.realpath(cwd, path)) if path else None
        if not k:
            return None
        with S.locked(s) as cur:
            L.log_edit(cur["run_folder"], tool, path, cur["phase"])
            if k == "data":
                cur["config_edits"].append({"path": path, "phase": cur["phase"], "at": time.time()})
            if cur["phase"] in ("judge", "done.passed"):
                cur["phase"] = "work"
                cur["notes"].append("PASS voided: %s edited afterwards" % path)
                msgs.append("project code changed after the verdict; back to work")
            if cur["phase"] == "work":
                cur["round_open"] = True
        return context("PostToolUse", "\n".join("rehearse: " + m for m in msgs)) if msgs else None
    if tool == "AskUserQuestion":
        resp = p.get("tool_response") if isinstance(p.get("tool_response"), dict) else {}
        answers = resp.get("answers") if isinstance(resp.get("answers"), dict) else {}
        first = str(next(iter(answers.values()), "")).strip()
        if s["phase"] == "confirm" and first:
            yes = first.lower().rstrip(".!") in AFFIRMATIVE
            with S.locked(s) as cur:
                cur["confirmation"] = {"by": "user", "answer": first, "affirmative": yes, "at": time.time()}
                if yes:
                    cur["phase"] = "work"
            if yes:
                return context("PostToolUse", "[rehearse] the user confirmed the ending; edits are open.")
        if any(str(a).strip().lower().startswith("stop here") for a in answers.values()):
            with S.locked(s) as cur:
                cur["stop_here"] = True
            return context("PostToolUse", "rehearse: the user chose to stop here; write report.md starting with "
                                          "\"not fixed\", then finish")
        return None
    if tool != "Bash":
        return None
    cmd = str(tin.get("command") or "")
    out = L.output_text(p)
    segs = P.parse(cmd, cwd)
    with S.locked(s) as cur:
        L.log_command(cur["run_folder"], cmd, out, cur["phase"])
        if any(seg["prog"] == "rehearse" for seg in segs):
            res = last_result(out)
            if res is None:
                msgs.append("result line missing; rerun without a pipe")
            elif res.get("run") == cur["run_id"]:
                if res.get("as_director"):
                    res["agent_type"] = p.get("agent_type") or "director"
                refused = apply_result(cur, res, msgs)
        elif cur["phase"] == "work":
            pps, runners = ending_marks(cur)
            if cur["round_open"] and any(seg["pp"] in pps or (seg["runner"] and seg["runner"] in runners)
                                         for seg in segs):
                close_round(cur, False, "direct run", msgs)
            elif any(F.kind(cur["root"], t) for seg in segs for t in seg["targets"]):
                cur["round_open"] = True
    if not msgs:
        return None
    return block(cur, "\n".join(msgs)) if refused else context("PostToolUse", "\n".join("rehearse: " + m for m in msgs))


# ---------- SubagentStop: the verdict ----------

def last_json(text, key="verdict"):
    """The last JSON object in text carrying key, or None."""
    dec = json.JSONDecoder()
    for i in range(len(text) - 1, -1, -1):
        if text[i] == "{":
            try:
                obj, _ = dec.raw_decode(text, i)
            except ValueError:
                continue
            if isinstance(obj, dict) and key in obj:
                return obj
    return None


def on_review(s, text):
    v = last_json(text, "review") or {}
    review = str(v.get("review") or "").lower()
    with S.locked(s) as cur:
        cur["review_spawned"] = False
        if review == "confirmed":
            cur["confirmation"] = {"by": "director", "answer": "confirmed", "affirmative": True, "at": time.time()}
            cur["uncovered"] = []
            cur["phase"] = "work"
            msg = "the director confirmed the ending; edits are open"
        else:
            cur["uncovered"] = [str(u) for u in v.get("uncovered") or []] or ["no JSON review in the final message"]
            msg = ("uncovered: %s. Register the uncovered requirements with rehearse ending, then spawn the review "
                   "again" % "; ".join(cur["uncovered"]))
    return {"systemMessage": "rehearse: " + msg}


def on_subagent_stop(p, sid):
    s = S.current(sid)
    if s and p.get("agent_type") in DIRECTOR and s["phase"] == "confirm" and s.get("review_spawned"):
        return on_review(s, str(p.get("last_assistant_message") or ""))
    if not s or p.get("agent_type") not in DIRECTOR or not s.get("spawn_fingerprint"):
        return None
    v = last_json(str(p.get("last_assistant_message") or "")) or {}
    verdict = str(v.get("verdict") or "").upper()
    with S.locked(s) as cur:
        back = "rework-observe" if cur.get("spawn_from") == "rework-observe" else "work"
        changed = F.code_change(cur["spawn_fingerprint"], F.fingerprint(cur["root"]))
        changed += [e["path"] for e in cur["config_edits"] if e["at"] >= cur.get("spawn_at", 0)]
        rec = {"agent_type": p.get("agent_type"), "agent_id": p.get("agent_id"), "verdict": verdict,
               "findings": v.get("findings"), "extra_inputs": v.get("extra_inputs"), "tests": v.get("tests"),
               "at": time.time()}
        cur["spawn_fingerprint"] = None
        if changed or cur["phase"] != "judge":
            rec["void"] = "project code changed while the director worked: %s" % (", ".join(changed) or "edited")
            cur["phase"] = back if cur["phase"] == "judge" else cur["phase"]
            msg = "the verdict is void: %s. Spawn rehearse:director again" % rec["void"]
        elif verdict == "PASS":
            cur["phase"] = "done.passed"
            cur["pass_fingerprint"] = F.fingerprint(cur["root"])
            msg = "the director passed the change. Write report.md, then finish"
        elif verdict == "REWORK":
            cur["rejections"] += 1
            cur["findings"] = v.get("findings")
            if cur["rejections"] >= int(option("MAX_REJECTIONS", "3")):
                cur["phase"] = "done.not_fixed"
                cur["report_pending"] = True
                msg = ("the director rejected the change %d times. Write report.md starting with \"not fixed\": "
                       "what is known and what to try next" % cur["rejections"])
            else:
                cur["phase"] = back
                msg = "the director asks for rework: %s" % json.dumps(v.get("findings"), ensure_ascii=False)
        else:
            rec["void"] = "no JSON verdict in the director's final message"
            cur["phase"] = back
            msg = "the director gave no verdict. Spawn rehearse:director again"
        cur["verdicts"].append(rec)
    return {"systemMessage": "rehearse: " + msg}


def void_pass(s):
    """A code change after PASS, seen at any hook call, returns the phase to work."""
    if s["phase"] != "done.passed" or not s.get("pass_fingerprint"):
        return
    changed = F.code_change(s.get("pass_fingerprint"), F.fingerprint(s["root"]))
    if changed:
        with S.locked(s) as cur:
            cur["phase"] = "work"
            cur["notes"].append("PASS voided: %s changed afterwards" % ", ".join(changed))


# ---------- Stop ----------

def newest(sid):
    """The session's newest run in any phase (S.current hides ended runs)."""
    d = S.session_dir(sid)
    try:
        names = sorted((n for n in os.listdir(d) if n.endswith(".json")), reverse=True)
    except OSError:
        return None
    return S.load(os.path.join(d, names[0])) if names else None


def report_line(s):
    try:
        with open(os.path.join(s["run_folder"], "report.md"), encoding="utf-8") as f:
            return f.readline().strip().lower()
    except OSError:
        return None


def verified(s):
    after = (s.get("ending") or {}).get("after") or {}
    runs = s.get("director_runs") or []
    return bool(after.get("all_pass")) or bool(runs and runs[-1].get("all_pass"))


def kill_stage(s):
    """The stage writes its pid to <run folder>/stage.pid (stage/client.py)."""
    try:
        with open(os.path.join(s["run_folder"], "stage.pid"), encoding="utf-8") as f:
            os.kill(int(f.read().split()[0]), signal.SIGTERM)
    except (OSError, ValueError, IndexError):
        pass


def on_stop(p, sid):
    s = newest(sid)
    if not s or s["phase"] == "done.cancelled":
        return None
    first = report_line(s)
    ph = s["phase"]
    nxt = None
    if ph == "done.not_fixed" or s.get("stop_here"):
        if not (first or "").startswith("not fixed"):
            nxt = 'write report.md starting with "not fixed"'
    elif ph in ("work", "judge", "done.passed") and first is not None:
        if not first.startswith(REPORT_LINES):
            nxt = "write report.md starting with fixed / built, not verified against the real target / not fixed"
        elif first.startswith("fixed") and not verified(s):
            nxt = "say built, not verified against the real target"
    if nxt is None and ph not in ("done.passed", "done.not_fixed") and not s.get("stop_here"):
        if ph == "observe":
            nxt = "register an ending with rehearse ending"
        elif ph == "confirm" and s.get("uncovered"):
            nxt = ("register the uncovered requirements with rehearse ending, then spawn the review again (uncovered: "
                   "%s)" % "; ".join(s["uncovered"]))
        elif ph == "confirm":
            nxt = None if attended() else "spawn rehearse:director to review the ending"
        else:
            nxt = "spawn rehearse:director"
            with S.locked(s) as cur:
                FD.write(cur)
    if nxt:
        return {"decision": "block", "reason": "%s · next: %s" % (status_line(s), nxt)}
    if s.get("stop_here") and ph != "done.not_fixed":
        with S.locked(s) as cur:
            cur["phase"] = "done.not_fixed"
    kill_stage(s)
    return None


def main():
    try:
        p = json.loads(sys.stdin.read())
    except ValueError:
        return
    if not isinstance(p, dict) or not p.get("hook_event_name"):
        return
    sid = str(p.get("session_id") or "no-session")
    s = S.current(sid)
    if s:
        void_pass(s)
    handler = {"UserPromptSubmit": on_prompt, "PreToolUse": on_pre, "PostToolUse": on_post,
               "PostToolUseFailure": on_post, "SubagentStop": on_subagent_stop, "Stop": on_stop}.get(p["hook_event_name"])
    out = handler(p, sid) if handler else None
    if out:
        print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # a hook bug must never block the user
        pass
    sys.exit(0)
