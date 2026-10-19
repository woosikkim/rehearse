#!/usr/bin/env python3
"""rehearse: the single hook entry. Reads one Claude Code hook payload on stdin, dispatches on hook_event_name.

UserPromptSubmit: activation, `rehearse stop`, goal answers, confirmations, the stuck answers.
PreToolUse: the edit gate in the locked phases (project files and declared outputs); created files may not run
there; worker and director spawns get their prompt, model and the foreground flag.
PostToolUse(Failure): the log, REHEARSE-RESULT lines from bin/rehearse, the run counter, the Agent notes.
SubagentStop: the director's verdict, a worker's outcome. Stop: when the manager may stop.
Fails open: any error or malformed input exits 0 with no decision.
"""
import json
import os
import re
import traceback
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import findings as FD  # noqa: E402
import fingerprint as F  # noqa: E402
import log as L  # noqa: E402
import provenance as P  # noqa: E402
import state as S  # noqa: E402

EDIT_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
AFFIRMATIVE = {"yes", "y", "ok", "correct", "confirmed", "네", "예", "응", "맞아", "맞아요", "네 맞아요"}
ACTIVATE = re.compile(r"^(?:/rehearse(?::rehearse)?(?:\s+|$)|rehearse(?:\s*:\s*|\s+))(.*)$", re.I | re.S)
LONG_RUN = re.compile(r"(?:^|[\s;&|(])(?:\S*rehearse|\$\w+)\s+(?:ending|run|stage\s+step)\b")
BIN = os.path.join(os.path.dirname(HERE), "bin", "rehearse")
BASH_CAP_MS = 600000  # Claude Code's largest Bash timeout; rehearse ending/run get it so a slow baseline is not cut off
NEED_ENDING = "edits are locked: register and confirm an ending first"
DIRECTOR = ("rehearse:director",)  # agent_type is always namespaced (probes P16, P18d)
WORKER = ("rehearse:worker",)
WRAPPED = re.compile(r"<(?:task-notification|system-reminder)\b")  # harness messages that arrive as prompts
REPORT_LINES = ("fixed", "built, not verified against the real target", "not fixed")
PLUGIN_FILES = ("results.jsonl", "state.json", "commands.jsonl", "log.md")  # the run folder's own records
NOT_VERIFIED = re.compile(r"(?im)^[#*\s]*not verified\b")


def status_line(s, nxt=None):
    return "[rehearse] job %s, %s, phase %s · next: %s" % (s["run_id"], S.label(s), s["phase"], nxt or S.next_step(s))


def context(event, text):
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}


def refused(s, why, kind=None):
    """Count every refusal by kind for the Process section (the kind: the message's head, or as given).
    A job file from before 3.1.0 has no log: it stays missing ("not recorded"), never a count that began late."""
    with S.locked(s) as cur:
        if cur.get("refusals") is not None:
            cur["refusals"].append({"kind": kind or re.split(r"[;:.\n]", why)[0].strip()[:60], "at": S.now(cur)})


def deny(s, why, kind=None):
    refused(s, why, kind)
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                   "permissionDecisionReason": "rehearse: %s.\n%s" % (why, status_line(s))}}


def block(s, why, kind=None):
    refused(s, why, kind)
    return {"decision": "block", "reason": "rehearse: %s.\n%s" % (why, status_line(s))}


def option(name, default):
    # A saved plugin setting, else a plain variable, else the EVAL_ form (the only
    # kind of variable `claude plugin eval` lets through), else the default.
    return (os.environ.get("CLAUDE_PLUGIN_OPTION_" + name) or os.environ.get("REHEARSE_" + name)
            or os.environ.get("EVAL_REHEARSE_" + name) or default)


def attended():
    return option("CONFIRM_ENDING", "true").lower() not in ("false", "0", "no")


def instruction(name):
    try:
        with open(os.path.join(HERE, "instructions", name), encoding="utf-8") as f:
            return f.read().replace("${CLAUDE_PLUGIN_ROOT}", os.path.dirname(HERE)).rstrip()
    except OSError:
        return "[rehearse] instructions pending: %s" % name


def unattended_mark():
    return {"by": "unattended", "answer": None, "affirmative": True, "at": time.time()}


def nfail(results):
    return sum(1 for r in results or [] if not r.get("passed"))


# ---------- stages ----------

def stage_def(s):
    """The current stage's line in the plan; the final stage is the job ending over every output."""
    if S.final(s):
        return {"name": "end to end", "kind": "build", "line": "the job ending", "inputs": [],
                "outputs": [o for st in s["stages"] for o in st.get("outputs") or []]}
    return (s.get("stages") or [{}])[s["stage"] - 1] if s.get("stages") else {}


def declared(s):
    """Real paths of the declared outputs of every stage so far (every stage in the final stage)."""
    return {P.realpath(s["root"], o) for st in (s.get("stages") or [])[:s.get("stage") or 1]
            for o in st.get("outputs") or []}


def start_stage(cur, n):
    cur.update(S.fresh_stage(F.fingerprint(cur["root"]), S.now(cur)), stage=n)


def archive(cur):
    # .get: a job file from an earlier release may lack a newer stage field (strike_log, stuck_log since 3.1.0)
    cur["stages"][cur["stage"] - 1].update({k: cur.get(k) for k in S.STAGE_KEYS}, passed=True, reruns=[])


def advance(cur):
    """A director PASS: the next stage, the final stage, or the end of the job."""
    n, m = cur["stage"], len(cur["stages"])
    if S.final(cur) or m == 1:
        if m == 1:
            cur["stages"][0]["passed"] = True
        cur["phase"] = "done.passed"
        return "[rehearse] %s passed. The job is done: write report.md, then finish" % S.label(cur)
    archive(cur)
    start_stage(cur, n + 1)
    if n < m:
        cur["phase"] = "look"
        return ("[rehearse] stage %d passed. Next: stage %d's look. Before its worker starts you may rewrite the "
                "job ending with rehearse ending --job" % (n, n + 1))
    job = dict(cur["job_ending"], after=None)
    cur.update(ending=job, confirmation=cur.get("job_confirmation"), phase="build",
               fewest_failing=nfail((job.get("before") or {}).get("results")))
    return ("[rehearse] stage %d passed. Every stage has passed: the job ending is now the final stage, in build. "
            "Run it with rehearse run, add glue if needed, then start rehearse:director" % n)


def strike(cur, msgs, cause):
    cur["strikes"] += 1
    cur["pending_change"] = False
    if cur.get("strike_log") is not None:  # a stage begun before 3.1.0 has no log: it stays "not recorded"
        cur["strike_log"].append({"cause": cause, "at": S.now(cur)})
    if cur["strikes"] < int(float(option("MAX_STRIKES", "3"))):
        return
    if attended():
        cur.update(phase="stuck", stuck_at=S.now(cur))
        if cur.get("stuck_log") is not None:
            cur["stuck_log"].append({"at": S.now(cur), "answer": None})
        msgs.append("%s has %d strikes and is stuck: ask the user once (stop here, try again, or change the stage), "
                    "then record the answer with rehearse stuck" % (S.label(cur), cur["strikes"]))
    else:
        cur["phase"] = "done.not_fixed"
        msgs.append('%s has %d strikes. Write report.md starting with "not fixed": what is known and what '
                    'to try next' % (S.label(cur), cur["strikes"]))


def reopen(cur, why, **kw):
    """Edits locked again for the same stage (a relock or the user's "change"): a look step comes first."""
    cur.update(kw, phase="look", fp_phase_entry=F.fingerprint(cur["root"]), failing_runs=0, code_edits_since_run=0,
               direct_pending=False, reopen={"at": S.now(cur), "looks": 0, "why": why})


def relock(cur, msgs):
    n = cur["failing_runs"]
    reopen(cur, "relock")
    cur["relocks"].append({"at": S.now(cur)})
    cur["notes"].append("%s: edits relocked after %d failing runs" % (S.label(cur), n))
    msgs.append("%d failing runs in a row: edits are locked again. Stop and say what you learned; the next step is "
                "a look (a stage step into project code, or rehearse fetch)" % n)
    strike(cur, msgs, "relock")


def failing_run(cur, msgs):
    cur["failing_runs"] += 1
    if cur["failing_runs"] >= int(float(option("LOOP_BREAKER_ROUNDS", "2"))):
        relock(cur, msgs)


def look_step(cur):
    if cur.get("reopen"):
        cur["reopen"]["looks"] += 1


# ---------- UserPromptSubmit and answers ----------

def confirm_job(cur):
    if cur.get("confirm_return"):
        cur["confirm_return"] = None  # back to the stage it came from, nothing reset
    else:
        start_stage(cur, 1)
    cur["phase"] = "look"
    return "[rehearse] the user confirmed the job. Next: stage %d's look" % cur["stage"]


def confirm_answer(cur, a, low):
    ph = cur["phase"]
    yes = low in AFFIRMATIVE
    cur["job_confirmation" if ph == "job-confirm" else "confirmation"] = {
        "by": "user", "answer": a, "affirmative": yes, "at": S.now(cur)}
    if yes and ph == "job-confirm":
        return confirm_job(cur)
    if yes:
        cur["phase"] = "build"
        return "[rehearse] the user confirmed the ending; edits are open." + (
            " It already passes: start rehearse:director" if cur["start_director"] else "")
    if ph == "confirm":  # a "no": back to look for the same stage, where a worker may re-register the ending
        cur["prompts"].append(a)
        cur.update(phase="look", redo=(a.splitlines() or [""])[0])
        return "[rehearse] the user did not confirm the ending. Next: " + S.next_step(cur)
    return None


STUCK_NOTE = ("[rehearse] still stuck. The plugin does not read the decision from the user's words: read their answer, "
              "then record it with rehearse stuck --stop-here | --try-again | --change --confirmed (change only after "
              "their explicit yes to redoing the stage). A question from the user is not a decision: answer it, then "
              "ask again")


def answer(cur, text, add=True):
    """Apply the user's answer for the current phase; return the note for the agent, or None."""
    a = text.strip()
    low = a.lower().rstrip(".!")
    ph = cur["phase"]
    cur["user_answer_at"] = S.now(cur)  # rehearse stuck needs a user answer recorded after the question arose
    if ph in ("job-confirm", "confirm"):
        return confirm_answer(cur, a, low)
    if ph == "stuck":  # the decision comes from `rehearse stuck` (apply_stuck), never from matching these words
        cur["notes"].append("stuck answer: " + a)
        return STUCK_NOTE
    if add:
        cur["prompts"].append(a)
    return None


def on_prompt(p, sid):
    prompt = str(p.get("prompt") or "").strip()
    if WRAPPED.match(prompt):  # a background agent's completion, delivered as a user message: not the user
        return None
    m = ACTIVATE.match(prompt)
    rest = m.group(1).strip() if m else None
    is_stop = rest is not None and rest.lower() == "stop"
    if is_stop:  # also after done.passed without a report, or done.not_fixed: the manager may stop afterwards
        s = S.newest(sid)
        if not S.v3(s) or s.get("closed") or s["phase"] == "done.cancelled":
            return None
        with S.locked(s) as cur:
            cur["phase"] = "done.cancelled"
            cur["notes"].append("cancelled by user")
        return {"systemMessage": "rehearse stopped (job %s cancelled)" % s["run_id"]}
    s = S.current(sid)
    if rest is not None and rest.lower() in ("job", "status"):  # a status question, never a new job
        msg = S.job_text(s) if s else "no active rehearse job"
        return dict(context("UserPromptSubmit", msg), systemMessage=msg)
    if s and not s["phase"].startswith("done"):
        with S.locked(s) as cur:
            msg = answer(cur, prompt)
        return context("UserPromptSubmit", msg) if msg else None
    if rest is None:
        return None
    root = p.get("cwd") or os.getcwd()
    s = S.new_run(sid, root, prompt, F.fingerprint(root), attended())
    mode = ("attended: the user answers confirmations" if s["attended"] else "unattended: confirmations are off; "
            "nothing is asked, unasked goal items are recorded as assumed, endings are accepted at registration")
    text = instruction("manager.md") + "\n[rehearse] job %s activated\n%s\ncommand: rehearse (if not on PATH: %s)" % (
        s["run_id"], mode, BIN)
    return dict(context("UserPromptSubmit", text), systemMessage="rehearse is on — type `rehearse stop` to stop")


# ---------- PreToolUse ----------

def new_code_file(s, path):
    """A project code file present now and absent at the stage start, that no program produced. Decided from the
    stage-start snapshot and git alone: the snapshot lists every untracked or changed code file (in git) or every
    code file (outside git), so absence means new; a file's modification time is never read (the OS stamps it
    with a wall clock that can step back)."""
    if not F.is_code(path) or path in s["produced"] or F.kind(s["root"], path) != "code":
        return False
    rel = os.path.relpath(path, s["root"])
    if rel in s["fp_activation"]["files"]:
        return False
    if s["fp_activation"].get("git"):
        tracked = F._git(s["root"], "ls-files", "--error-unmatch", "--", rel)
        if tracked and tracked.returncode == 0:
            return False
    return os.path.isfile(path)


def updated(tin, text, model):
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedInput": dict(
        tin, prompt=text, model=model, run_in_background=False)}}  # the agent waits instead of polling (probe P16)


def about(s):
    """The current stage from the job file, for a worker's or the director's prompt."""
    st, e = stage_def(s), s.get("ending")
    goal = "; ".join("%s: %s (%s)" % (k, g["text"], g["source"]) for k, g in (s.get("goal") or {}).items())
    lines = ["- %s: %s (%s); plan line: %s" % (S.where(s), st.get("name"),
                                                          st.get("kind"), st.get("line")),
             "- inputs: %s; declared outputs: %s" % (", ".join(st.get("inputs") or []) or "none",
                                                     ", ".join(st.get("outputs") or []) or "none"),
             "- goal: %s" % (goal or "none recorded"),
             "- ending: %s" % (json.dumps({"cmd": e["cmd"], "expectations": e["expectations"]}, ensure_ascii=False)
                               if e else "none registered yet"),
             "- run folder: %s; job file copy: %s; project root: %s; command: %s" % (
                 s["run_folder"], S.mirror_path(s), s["root"], BIN)]
    if s.get("findings"):
        lines.append("- the director's findings to address: %s" % json.dumps(s["findings"], ensure_ascii=False))
    return "\n".join(lines)


def spawn_worker(s, tin):
    half = s["phase"]
    with S.locked(s) as cur:
        cur["workers"] += 1
        cur["worker"] = {"half": half, "at": S.now(cur), "relocks": len(cur["relocks"]), "reopen": bool(cur["reopen"])}
        cur["spawn"] = {"kind": "worker", "at": S.now(cur), "background": False, "stopped": False}
    kind = stage_def(cur).get("kind") or "build"
    text = "\n\n".join(["[rehearse] %s %s" % (S.label(cur), half), instruction("worker.md"),
                        instruction("%s-%s.md" % (kind, half)), "This stage (from the job file):\n" + about(cur),
                        "The manager adds:\n" + str(tin.get("prompt") or "")])
    return updated(tin, text, option("WORKER_MODEL", "sonnet"))


def spawn_director(s, tin):
    """Replace the director's prompt and model; snapshot code and declared outputs; enter judge."""
    with S.locked(s) as cur:
        fpath = FD.write(cur)
        cur["spawn_fingerprint"] = dict(F.fingerprint(cur["root"]), outputs={o: F._sig(o) for o in declared(cur)})
        cur["spawn_at"] = S.now(cur)
        cur.update(verdict_note=None, phase="judge", start_director=False,
                   spawn={"kind": "director", "at": S.now(cur), "background": False, "stopped": False})
    extra = "- ending record: %s (the \"ending\" key)\n- findings: %s\n%s" % (S.mirror_path(cur), fpath, about(cur))
    if S.final(cur):
        extra += "\nEvery stage ending; rerun each with `rehearse run --stage <n> --as-director` (a live source: " \
                 "check its structure, or against the saved fixture):\n" + "\n".join(
                     "- stage %d: %s" % (i, json.dumps((st.get("ending") or {}).get("cmd"), ensure_ascii=False))
                     for i, st in enumerate(cur["stages"], 1))
    return updated(tin, instruction("director.md") + "\n\nThis run:\n" + extra, option("DIRECTOR_MODEL", "opus"))


def on_pre(p, sid):
    s = S.current(sid)
    if not s or s["phase"].startswith("done"):
        return None
    tool = p.get("tool_name")
    tin = p.get("tool_input") if isinstance(p.get("tool_input"), dict) else {}
    cwd = p.get("cwd") or s["root"]
    if tool == "Agent":
        with S.locked(s) as cur:
            drain(cur, p.get("agent_type"))  # a spawn decision rests on every result so far
        s = S.current(sid)
        kind = tin.get("subagent_type")
        if kind in DIRECTOR and S.running(s) == "worker":
            return deny(s, "worker still running in the background; wait for its notification, then rehearse job")
        if kind in DIRECTOR and s["phase"] not in ("build", "judge"):
            return deny(s, "the director is started in build (or again in judge); the job is in %s%s" % (
                s["phase"], ": settle it with the user and record the answer with rehearse stuck; after try again, "
                            "an ending that already passes goes straight to the director" if s["phase"] == "stuck"
                else ""))
        if kind in DIRECTOR:
            return spawn_director(s, tin)
        if kind in WORKER:
            if s["phase"] not in ("look", "build"):
                return deny(s, "a worker is started only in look or build; the job is in %s" % s["phase"])
            return spawn_worker(s, tin)
        return None
    locked = s["phase"] in S.LOCKED
    outs = declared(s) if locked else set()
    # the plugin's own records in the run folder are written by the plugin only, in every phase, for any caller:
    # results.jsonl is what the hook reads, commands.jsonl is what citations cite, state.json is what bin reads
    # ponytail: edit tools and shell write targets only; a script opening the file for append is not seen
    own = {os.path.realpath(os.path.join(s["run_folder"], n)) for n in PLUGIN_FILES}
    if tool in EDIT_TOOLS:
        path = tin.get("file_path") or tin.get("notebook_path")
        if not path:
            return None
        real = P.realpath(cwd, path)
        if real in own:
            return deny(s, "%s is the plugin's own record; it is written by the plugin only" % path, "plugin record")
        if real in outs:
            return deny(s, "%s; %s is a declared output in the plan" % (NEED_ENDING, path))
        if locked and F.kind(s["root"], real):
            return deny(s, "%s; %s is project code" % (NEED_ENDING, path))
        if tool == "Write" and not os.path.exists(real):
            with S.locked(s) as cur:
                cur["created"].append(real)
        return None
    if tool != "Bash":
        return None
    segs = P.parse(str(tin.get("command") or ""), cwd)
    for seg in segs:
        for t in seg["targets"]:
            if t in own:
                return deny(s, "this command writes %s, the plugin's own record; it is written by the plugin only" % t,
                            "plugin record")
    if locked:
        for seg in segs:
            for t in seg["targets"]:
                if t in outs:
                    return deny(s, "%s; this command writes the declared output %s" % (NEED_ENDING, t))
                if F.kind(s["root"], t) == "code":
                    return deny(s, "%s; this command writes the code file %s" % (NEED_ENDING, t))
        made = set()  # outputs of earlier segments of this same command (cc -o prog x.c && ./prog)
        created = set(s["created"])
        for seg in segs:
            pp = seg["pp"]
            if pp and os.path.isabs(pp) and pp not in made and (pp in created or new_code_file(s, pp)):
                return deny(s, "%s was created during this stage; it may not run while edits are locked. Run "
                               "programs that existed when the stage started, or look through the stage" % pp,
                            "a created file may not run while edits are locked")
            made.update(seg["outputs"])
    targets = [t for seg in segs for t in seg["targets"]]
    outputs = [o for seg in segs for o in seg["outputs"]]
    if targets or outputs:
        with S.locked(s) as cur:
            cur["created"] += [t for t in targets if t not in cur["created"]]
            cur["produced"] += [o for o in outputs if o not in cur["produced"]]
    if LONG_RUN.search(str(tin.get("command") or "")):
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedInput": dict(tin, timeout=BASH_CAP_MS)}}
    return None


# ---------- PostToolUse ----------

def ending_marks(s):
    """Program positions and test runners whose direct run is a direct run of the ending."""
    e = s.get("ending") or {}
    pps, runners = set(), set()
    for cmd in (e.get("cmd"), e.get("tests_effective")):
        for seg in P.parse(cmd or "", s["root"]):
            if seg["runner"]:
                runners.add(seg["runner"])
            elif seg["pp"] and os.path.isabs(str(seg["pp"])) and cmd == e.get("cmd"):
                pps.add(seg["pp"])  # a bare name (grep, make) is not a mark: only a program given as a path
    return pps, runners


def scratch(root, real):
    """A scratch edit: a code file outside the project. Counted toward the ten-edit reminder, never refused."""
    return F.is_code(real) and not real.startswith(os.path.realpath(root) + os.sep)


def project_edit(cur, msgs):
    if cur["phase"] != "build":
        return
    cur["project_edits_since_run"] += 1
    if cur["direct_pending"]:  # a direct run of the ending, then another edit: that run was a failing run
        cur["direct_pending"] = False
        failing_run(cur, msgs)


def code_edit(cur, msgs):
    if cur["phase"] != "build":  # while looking, scratch work is the point
        return
    cur["code_edits_since_run"] += 1
    if cur["code_edits_since_run"] % 10 == 0:
        msgs.append("reminder: %d code edits with no run of the ending. Stop guessing: run rehearse run, or look at "
                    "what the code really does; a change that exists only in a copy is not a fix"
                    % cur["code_edits_since_run"])


def apply_plan(cur, res, msgs):
    n = res.get("change")
    why = S.plan_refused(cur, n)
    if why:
        msgs.append(why)
        return True
    if n:
        cur["stages"][n - 1] = res["stages"][0]
        msgs.append("stage %d changed in the plan" % n)
        return False
    cur.update(goal=res["goal"], assumptions=res["assumptions"], blockers=res["blockers"], stages=res["stages"],
               stages_from="request" if res.get("from_request") else "manager", job_ending=None,
               job_confirmation=None, confirm_return=None)
    if len(cur["stages"]) == 1:
        start_stage(cur, 1)
        cur["phase"] = "look"
        msgs.append("one-stage plan recorded: its stage ending is the job ending. Look at the stage yourself, then "
                    "rehearse ending")
    else:
        cur["phase"] = "goal"
        msgs.append("plan recorded (%d stages). Next: the job ending with rehearse ending --job" % len(cur["stages"]))
    return False


def set_job_ending(cur, e, msgs):
    keep = lambda x: {k: (x or {}).get(k) for k in ("cmd", "expectations")}  # noqa: E731
    same = cur["job_ending"] is not None and keep(cur["job_ending"]) == keep(e)
    from_look = cur["phase"] == "look"
    cur["job_ending"] = e
    if from_look and same:
        msgs.append("the job ending is unchanged; no confirmation needed. Next: stage %d's look" % cur["stage"])
        return False
    if not attended():
        cur["job_confirmation"] = unattended_mark()
        if not from_look:
            start_stage(cur, 1)
            cur["phase"] = "look"
        msgs.append("job ending registered and accepted (unattended run, not confirmed by a person)")
        return False
    if from_look:
        cur["confirm_return"] = cur["stage"]
    cur.update(phase="job-confirm", job_confirmation=None)
    msgs.append("job ending registered. Ask the user to confirm the job in one question: the goal, the assumptions, "
                "the blockers, the stages (from the %s), the models and the job ending" % cur.get("stages_from"))
    return False


def apply_ending(cur, res, msgs):
    job = bool(res.get("job")) and not S.final(cur)
    why = S.ending_refused(cur, job)
    if why:
        msgs.append(why)
        return True
    ro = cur.get("reopen")
    if not job and ro and not ro["looks"]:
        msgs.append(S.NO_LOOK)
        return True
    if not job:
        changed = F.code_change(cur["fp_phase_entry"], F.fingerprint(cur["root"]))
        if changed:
            msgs.append("code changed while edits were locked: %s; put them back, then register" % ", ".join(changed))
            return True
    already = bool(res.get("all_pass"))
    if already and (job or not ro):
        msgs.append("the ending shows nothing wrong: every expectation already passes. An ending must fail before "
                    "the work (a build fails because the program does not exist yet)")
        return True
    e = dict(res["ending"], before=res.get("before"), after=None, baseline=res.get("baseline"),
             tests_effective=(res.get("baseline") or {}).get("cmd"), registered_at=S.now(cur))
    cur["not_verified"] += [u for u in e.get("unchecked") or [] if u not in cur["not_verified"]]
    if job:
        return set_job_ending(cur, e, msgs)
    if ro and ro["why"] == "relock" and cur["relocks"]:
        cur["relocks"][-1]["looks"] = ro["looks"]
    cur.update(ending=e, fewest_failing=nfail((res.get("before") or {}).get("results")), failing_runs=0,
               pending_change=False, reopen=None, no_ending=0, start_director=already, redo=None)
    if S.final(cur):
        cur["job_ending"] = e
    if not attended():
        cur.update(confirmation=unattended_mark(), phase="build")
        msgs.append("ending registered and accepted (unattended run, not confirmed by a person); edits are open"
                    + ("; it already passes: start rehearse:director" if already else ""))
        return False
    cur["phase"] = "confirm"
    msgs.append("ending registered." + (" It already passes: the code was right and the old ending was wrong; show "
                                        "the user the look steps since edits were locked, and after the yes start "
                                        "rehearse:director." if already else "")
                + " Ask the user to confirm it in one plain sentence, with the command and the expected values beneath")
    if len(cur["stages"]) == 1:
        msgs.append("one-stage job: the same question lists the goal items and assumptions: %s; assumptions: %s" % (
            "; ".join("%s: %s" % (k, g["text"]) for k, g in (cur.get("goal") or {}).items()),
            "; ".join(cur.get("assumptions") or []) or "none"))
    return False


def apply_run(cur, res, msgs):
    director = res.get("as_director") and res.get("agent_type") in DIRECTOR
    rec = dict({k: res.get(k) for k in ("rc", "results", "all_pass")}, agent_type=res.get("agent_type"), at=S.now(cur))
    n = res.get("stage_rerun")
    if n:
        if not (director and S.final(cur) and 1 <= n <= len(cur["stages"])):
            msgs.append("rehearse run --stage is for the end-to-end director, in the final stage")
            return True
        cur["stages"][n - 1].setdefault("reruns", []).append(rec)
        return False
    if director:
        cur["director_runs"].append(rec)
        return False
    if not cur.get("ending"):
        return False
    cur["ending"]["after"] = {k: res.get(k) for k in ("rc", "stdout", "stderr", "results", "all_pass")}
    passing, failing, edits = bool(res.get("all_pass")), nfail(res.get("results")), cur["project_edits_since_run"]
    if cur["relocks"] and "next_run" not in cur["relocks"][-1]:
        cur["relocks"][-1]["next_run"] = {"passed": passing, "edits": edits}
    cur["runs"].append({"passing": passing, "failing": failing, "at": S.now(cur)})
    cur.update(project_edits_since_run=0, code_edits_since_run=0, direct_pending=False)
    if cur["phase"] == "look" and cur["reopen"] and passing:
        cur.update(phase="build", start_director=True, reopen=None, pending_change=False)
        msgs.append("the ending passes: edits are open; start rehearse:director")
    elif cur["phase"] != "build" or not edits:
        return False  # only a run after a project edit counts
    elif passing:
        cur["failing_runs"] = 0
    elif cur["fewest_failing"] is None or failing < cur["fewest_failing"]:
        cur.update(fewest_failing=failing, failing_runs=0)  # progress
    else:
        failing_run(cur, msgs)
    return False


def apply_stuck(cur, res, msgs):
    """The user's answer to the stuck question, recorded by the manager with `rehearse stuck`."""
    a = res.get("answer")
    if a != "stop here" and cur["phase"] != "stuck" and not (cur["phase"] == "look" and attended()):
        msgs.append("rehearse stuck is accepted in stuck, or in look after a blocked look worker; the job is in %s"
                    % cur["phase"])
        return True
    # structural: the user must have spoken (a prompt or a question answer) since the question arose: the stage
    # becoming stuck, or the last worker's stop (a blocked look), or the stage start
    stuck = cur["phase"] == "stuck"
    since = cur.get("stuck_at") or 0 if stuck else max((cur.get("worker") or {}).get("at") or 0, cur["started_at"])
    if not cur.get("user_answer_at") or cur["user_answer_at"] < since:
        msgs.append("no answer from the user is recorded since %s: ask them (a prompt, or AskUserQuestion), then "
                    "record what they chose" % ("the stage became stuck" if stuck else "the last worker stopped"))
        return True
    cur["notes"].append("stuck decision: %s" % a)
    log = cur.get("stuck_log")
    if log is None:
        pass  # a stage begun before 3.1.0: not recorded
    elif stuck and log and log[-1].get("answer") is None:
        log[-1]["answer"] = a
    else:
        log.append({"at": S.now(cur), "answer": a, "where": cur["phase"]})
    if a == "stop here":
        cur.update(stop_here=True, pending_change=False)
        msgs.append('the user chose to stop here; write report.md starting with "not fixed", then finish')
    elif a == "try again":
        cur["pending_change"] = False
        if cur["phase"] == "stuck":
            # a run that passed after the last verdict, with no edit since: the director next, not a build worker
            runs, verdicts = cur["runs"], cur["verdicts"]
            judged = verdicts[-1]["at"] if verdicts else 0
            cur.update(phase="build", strikes=0, failing_runs=0, start_director=bool(
                runs and runs[-1]["passing"] and runs[-1]["at"] > judged and not cur["project_edits_since_run"]))
        msgs.append("try again: next: " + S.next_step(cur))
    elif a == "change":
        reopen(cur, "change", strikes=0, pending_change=True)
        msgs.append("change: edits are locked for %s. %s Then look again (a stage step into project code, or "
                    "rehearse fetch) and register the ending again" % (S.label(cur), (
                        "Register the job ending again with rehearse ending." if S.final(cur) else
                        "rehearse plan --stage %d may rewrite the stage." % cur["stage"])))
    else:
        msgs.append("rehearse stuck: unknown answer %r" % a)
        return True
    return False


def apply_result(cur, res, msgs):
    kind = res.get("kind")
    if not res.get("ok") and kind in ("plan", "ending", "run", "stuck"):
        return False
    if kind == "plan":
        return apply_plan(cur, res, msgs)
    if kind == "ending":
        return apply_ending(cur, res, msgs)
    if kind == "run":
        return apply_run(cur, res, msgs)
    if kind == "stuck":
        return apply_stuck(cur, res, msgs)
    if kind == "fetch" and res.get("ok") and res.get("fixture"):
        cur["fixtures"].append(res["fixture"])
        look_step(cur)
    if kind == "stage-step" and res.get("project_files"):
        look_step(cur)
    return False


def drain(cur, agent_type, msgs=None):
    """Self-healing: apply every record the CLI wrote that no hook call has read yet (a PostToolUse that was
    missed, timed out or failed open), before any decision rests on it. Records carry no agent: the caller
    names the agent whose records they can be (its own stop, or none)."""
    recorded, cur["results_read"] = L.new_results(cur["run_folder"], cur.get("results_read", 0))
    out = [] if msgs is None else msgs
    for res in (r for r in recorded if r.get("run") == cur["run_id"]):
        res["agent_type"] = agent_type
        apply_result(cur, res, out)
    if msgs is None and out:
        cur["notes"].append("applied at a later hook call: " + " ".join(out))
    return recorded


def results(text):
    """Every REHEARSE-RESULT object in the output, in order (`$R plan ... && $R job` prints two)."""
    out = []
    for ln in text.splitlines():
        if ln.startswith("REHEARSE-RESULT "):
            try:
                res = json.loads(ln[len("REHEARSE-RESULT "):])
            except ValueError:
                continue
            if isinstance(res, dict):
                out.append(res)
    return out


def agent_note(s, tin, resp, event):
    """The note on a worker's or the director's tool result: what happened, the phase, the next step, the ending."""
    kind = tin.get("subagent_type")
    if kind not in WORKER + DIRECTOR:
        return None
    if isinstance(resp, dict) and (resp.get("status") == "async_launched" or resp.get("isAsync")):
        # interactive sessions run it in the background anyway (probes P19, P20): its stop comes later
        with S.locked(s) as cur:
            sp = cur.get("spawn")
            if sp and not sp.get("agent_id") and not sp["stopped"] and \
                    sp["kind"] == ("director" if kind in DIRECTOR else "worker"):
                sp.update(agent_id=resp.get("agentId"), background=True)
        who = "director" if kind in DIRECTOR else "%s worker" % S.label(s)
        return context(event, "[rehearse] %s launched in the background: end your turn now; when its notification "
                              "arrives, run `rehearse job` and do its next step." % who)
    if kind in DIRECTOR:
        head = s.get("verdict_note") or "[rehearse] no verdict was recorded"
    else:
        w = s.get("worker") or {}
        head = "[rehearse] %s %s worker: %s" % (S.label(s), w.get("half"), w.get("outcome") or "no stop recorded")
    e = s.get("ending")
    return context(event, "\n".join([
        head, "phase %s · next: %s" % (s["phase"], S.next_step(s)),
        "registered ending, from the job file: " + (json.dumps({"cmd": e["cmd"], "expectations": e["expectations"]},
                                                               ensure_ascii=False) if e else "none")]))


def note(event, msgs):
    return context(event, "\n".join("rehearse: " + m for m in msgs)) if msgs else None


def on_post(p, sid):
    s = S.current(sid)
    if not s:
        return None
    tool = p.get("tool_name")
    tin = p.get("tool_input") if isinstance(p.get("tool_input"), dict) else {}
    cwd = p.get("cwd") or s["root"]
    event = p.get("hook_event_name")
    judge = p.get("agent_type") in DIRECTOR
    msgs, refused = [], False
    if tool == "Agent":
        return agent_note(s, tin, p.get("tool_response"), event)
    if tool in EDIT_TOOLS:
        path = tin.get("file_path") or tin.get("notebook_path")
        real = P.realpath(cwd, path) if path else None
        k = real and (F.kind(s["root"], real) or ("output" if real in declared(s) else None))
        code = bool(real) and (k == "code" or scratch(s["root"], real)) and not judge
        if not k and not code:
            return None
        with S.locked(s) as cur:
            L.log_edit(cur["run_folder"], tool, path, cur["phase"])
            if k == "data":
                cur["config_edits"].append({"path": path, "phase": cur["phase"], "at": S.now(cur)})
            if k and not judge:
                project_edit(cur, msgs)
            if code:
                code_edit(cur, msgs)
        return note(event, msgs)
    if tool == "AskUserQuestion":
        resp = p.get("tool_response") if isinstance(p.get("tool_response"), dict) else {}
        answers = resp.get("answers") if isinstance(resp.get("answers"), dict) else {}
        vals = [str(a).strip() for a in answers.values() if str(a).strip()]
        if not vals:
            return None
        with S.locked(s) as cur:
            if cur["phase"] == "goal":
                cur["prompts"] += vals
                cur["user_answer_at"] = S.now(cur)
                return None
            msg = answer(cur, vals[0], add=False)
        return context(event, msg) if msg else None
    if tool != "Bash":
        return None
    cmd = str(tin.get("command") or "")
    out = L.output_text(p)
    segs = P.parse(cmd, cwd)
    with S.locked(s) as cur:
        # The CLI records every result in the run folder before printing it (results.jsonl); the hook reads that
        # record, so a filter on the output (head, tail -c, cut, a redirect) loses nothing. A printed line with an
        # id is only an echo (cat log.md); lines without one (an older CLI, a test) still count when the command
        # names rehearse (`R=/path/bin/rehearse; $R ending` names it through a variable).
        # ponytail: a record is taken by the next Bash hook of any agent; a manager command landing in the instant
        # between a background director's CLI exit and the director's own hook would take the director's record
        recorded, cur["results_read"] = L.new_results(cur["run_folder"], cur.get("results_read", 0))
        plain = any(seg["prog"] == "rehearse" or os.path.basename(seg["pp"] or "") == "rehearse" for seg in segs)
        named = plain or bool(re.search(r"(?<![\w-])rehearse(?![\w-])", cmd))
        found = recorded + ([r for r in results(out) if not r.get("id")] if named else [])
        L.log_command(cur["run_folder"], cmd, out, cur["phase"], [r.get("kind") for r in found], P.invocations(cmd))
        if plain or found:
            if not found:
                msgs.append("no result recorded for this rehearse command; run it again on its own, from the project")
            for res in (r for r in found if r.get("run") == cur["run_id"]):
                res["agent_type"] = p.get("agent_type")  # --as-director counts only for the director's own call
                refused = apply_result(cur, res, msgs) or refused
        elif cur["phase"] == "build" and not judge:
            pps, runners = ending_marks(cur)
            if any(seg["pp"] in pps or (seg["runner"] and seg["runner"] in runners) for seg in segs):
                cur.update(direct_pending=True, code_edits_since_run=0)
            targets = [t for seg in segs for t in seg["targets"]]
            outs = declared(cur)
            if any(F.kind(cur["root"], t) or t in outs for t in targets):
                project_edit(cur, msgs)
            # ponytail: shell writes count as code edits only inside the project; in-place edits of copies
            # outside it are counted only through the edit tools (2.0.1 also parsed sed -i there)
            if any(F.kind(cur["root"], t) == "code" for t in targets):
                code_edit(cur, msgs)
    if not msgs:
        return None
    return block(cur, "\n".join(msgs)) if refused else note(event, msgs)


# ---------- SubagentStop: the verdict, a worker's outcome ----------

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


def worker_stop(s):
    """Record what a worker's turn did: build passed / relocked / neither (a strike); look registered or not."""
    with S.locked(s) as cur:
        w, msgs = cur.get("worker"), []
        if not w or w.get("outcome"):
            return None
        drain(cur, "rehearse:worker", msgs)  # its own run may have been recorded without its hook call
        runs = [r for r in cur["runs"] if r["at"] >= w["at"]]
        registered = (cur.get("ending") or {}).get("registered_at", 0) >= w["at"]
        if w["half"] == "build":
            if len(cur["relocks"]) > w["relocks"]:
                out = "relocked"
            elif cur["phase"] == "build" and runs and runs[-1]["passing"]:
                out = "passed"
            else:
                out = "neither"
                strike(cur, msgs, "build worker stopped without a pass")
        elif registered:
            out = "re-registered, %s" % ("already passes" if cur["start_director"] else "fails") if w["reopen"] \
                else "ending registered"
        elif cur["phase"] == "build":
            out = "passed"  # a passing run of the old ending after a relock or change
        else:
            out = "no ending"
            cur["no_ending"] += 1
            if cur["no_ending"] >= 2:
                cur["no_ending"] = 0
                strike(cur, msgs, "two look workers without an ending")
        w["outcome"] = out + ("; " + " ".join(msgs) if msgs else "")
    return None


def on_subagent_stop(p, sid):
    s = S.current(sid)
    if not s:
        return None
    sp = s.get("spawn") or {}
    if sp.get("agent_id") and p.get("agent_id") != sp["agent_id"]:
        return None  # not the agent we launched (a stray stop fires right after a background launch)
    if p.get("agent_type") in WORKER + DIRECTOR and sp:
        with S.locked(s) as cur:
            cur["spawn"]["stopped"] = True
        s = S.current(sid)
    if p.get("agent_type") in WORKER:
        return worker_stop(s)
    if p.get("agent_type") not in DIRECTOR or not s.get("spawn_fingerprint"):
        return None
    v = last_json(str(p.get("last_assistant_message") or "")) or {}
    verdict = str(v.get("verdict") or "").upper()
    with S.locked(s) as cur:
        spawn, msgs = cur["spawn_fingerprint"], []
        drain(cur, p.get("agent_type"), msgs)  # the director's own runs, if their hook calls were missed
        changed = F.code_change(spawn, F.fingerprint(cur["root"]))
        changed += [os.path.relpath(o, cur["root"]) for o, sig in (spawn.get("outputs") or {}).items()
                    if F._sig(o) != sig]
        changed += [e["path"] for e in cur["config_edits"] if e["at"] >= cur.get("spawn_at", 0)]
        rec = {"agent_type": p.get("agent_type"), "agent_id": p.get("agent_id"), "verdict": verdict,
               "findings": v.get("findings"), "extra_inputs": v.get("extra_inputs"), "tests": v.get("tests"),
               "at": S.now(cur)}
        cur["spawn_fingerprint"] = None
        cur["verdicts"].append(rec)
        n = S.label(cur)
        if changed or cur["phase"] != "judge":
            rec["void"] = "project files changed while the director worked: %s" % (", ".join(changed) or "edited")
            if cur["phase"] == "judge":
                cur.update(phase="build", start_director=True)
            msg = "[rehearse] %s: the verdict is void: %s. Start rehearse:director again" % (n, rec["void"])
        elif verdict == "PASS":
            msg = advance(cur)
        elif verdict == "REWORK":
            cur.update(findings=v.get("findings"), phase="build", start_director=False)
            strike(cur, msgs, "REWORK")
            msg = "[rehearse] %s: the director asks for rework: %s" % (
                n, json.dumps(v.get("findings"), ensure_ascii=False))
        else:
            rec["void"] = "no JSON verdict in the director's final message"
            cur.update(phase="build", start_director=True)
            msg = "[rehearse] %s: the director gave no verdict. Start rehearse:director again" % n
        cur["verdict_note"] = " ".join([msg] + msgs)
    return None


# ---------- Stop ----------

def report(s):
    """(first line lowercased, has a "not verified" section), or (None, False) with no report."""
    try:
        with open(os.path.join(s["run_folder"], "report.md"), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None, False
    return (text.splitlines() or [""])[0].strip().lower(), bool(NOT_VERIFIED.search(text))


def verified(s):
    """Only runs of the top-level ending count: the job ending in the final stage, reset at every stage start."""
    after = (s.get("ending") or {}).get("after") or {}
    runs = s.get("director_runs") or []
    return bool(after.get("all_pass")) or bool(runs and runs[-1].get("all_pass"))


def on_stop(p, sid):
    s = S.newest(sid)
    if not S.v3(s) or s["phase"] == "done.cancelled" or s.get("closed"):
        return None
    with S.locked(s) as cur:
        if drain(cur, None):  # the manager's own results, if a hook call was missed: verified() reads them
            s = cur
    ph = s["phase"]
    first, nv = report(s)
    # An honest give-up ends the job where nobody can answer: unattended, or after the user chose "stop here".
    if (first or "").startswith("not fixed") and nv and (not attended() or s.get("stop_here")):
        with S.locked(s) as cur:
            cur["phase"] = "done.not_fixed"
            S.finish_report(cur)
        return None
    nxt = None
    if ph == "done.not_fixed" or s.get("stop_here"):
        if not (first or "").startswith("not fixed"):
            nxt = 'write report.md starting with "not fixed"'
    elif ph == "done.passed" and first is None:
        nxt = "write report.md, then finish"
    elif ph in ("build", "judge", "done.passed") and first is not None:
        if not first.startswith(REPORT_LINES):
            nxt = "write report.md starting with fixed / built, not verified against the real target / not fixed"
        elif first.startswith("fixed") and not verified(s):
            nxt = "say built, not verified against the real target"
    if nxt is None and first is not None and not nv and (ph.startswith("done") or s.get("stop_here")):
        nxt = 'add a "not verified" section to report.md ("none" if nothing is unverified)'
    if nxt is None and not ph.startswith("done") and not s.get("stop_here"):
        if ph in S.WAIT:
            nxt = None if attended() else S.next_step(s)  # unattended: nobody will answer
        elif S.running(s):
            # ponytail: an interrupted background agent never stops, so Stop stays allowed in this phase (fail open)
            return {"systemMessage": "rehearse: %s running in the background; the next step comes with its "
                                     "notification" % S.running(s)}
        elif ph == "look":
            nxt = S.next_step(s)
        else:
            nxt = "spawn rehearse:director"
            with S.locked(s) as cur:
                FD.write(cur)
    if nxt:
        refused(s, nxt, "stop blocked: " + re.split(r"[;:.\n]", nxt)[0].strip()[:40])
        return {"decision": "block", "reason": status_line(s, nxt)}
    with S.locked(s) as cur:
        if cur.get("stop_here") and ph != "done.not_fixed":
            cur["phase"] = "done.not_fixed"
        if ph == "done.passed":  # the job is over; later work in this session is not governed by it
            cur["closed"] = True
        if cur["phase"] in ("done.passed", "done.not_fixed") and first is not None:
            S.finish_report(cur)
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
        S.ensure_mirror(s)
    handler = {"UserPromptSubmit": on_prompt, "PreToolUse": on_pre, "PostToolUse": on_post,
               "PostToolUseFailure": on_post, "SubagentStop": on_subagent_stop, "Stop": on_stop}.get(p["hook_event_name"])
    out = handler(p, sid) if handler else None
    if out:
        print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # a hook bug must never block the user, but it must not pass in silence either
        log = os.path.join(os.path.dirname(S.sessions_root()), "hook-errors.log")
        try:
            os.makedirs(os.path.dirname(log), exist_ok=True)
            with open(log, "a", encoding="utf-8") as f:
                f.write("%s\n%s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), traceback.format_exc()))
        except OSError:
            pass
        print(json.dumps({"systemMessage": "rehearse: hook error; this check did not run; see %s" % log}))
    sys.exit(0)
