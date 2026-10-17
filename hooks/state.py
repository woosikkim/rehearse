"""One job file per activation, written only by hooks, under flock.

$CLAUDE_PLUGIN_DATA/sessions/<session_id>/<run_id>.json (else ~/.claude/rehearse/sessions/...) is the state every
decision reads. Each save also writes a copy to <root>/.rehearsal/<run_id>/state.json, which is all that
bin/rehearse (no plugin variables; possibly a sandboxed shell that cannot see the data folder) and the director
read. An edited or deleted copy changes no decision; a missing copy is written again on the next hook call.
"""
import contextlib
import datetime
import fcntl
import json
import os
import re
import secrets
import time

ENDED = ("done.cancelled", "done.not_fixed")
LOCKED = ("goal", "job-confirm", "look", "confirm", "stuck")  # edits of project files and declared outputs refused
WAIT = ("goal", "job-confirm", "confirm", "stuck")  # where an attended manager may stop: it waits for the user
NO_LOOK = ("no look step since edits were locked again: take one (a stage step into project code, or rehearse "
           "fetch; file://<path> for a draft or CSV), then register")
GOAL_ITEMS = ("purpose", "deliverable", "done", "out_of_scope")
NEXT = {"judge": "wait for the director's verdict",
        "stuck": "ask the user once: stop here, try again, or change the stage",
        "done.passed": "write report.md, then finish",
        "done.not_fixed": 'write report.md starting with "not fixed"',
        "done.cancelled": "the job is cancelled"}


def fresh_stage(fp):
    """The current-stage fields, reset at every stage start (brief section 8); archived into stages[n] on PASS."""
    return {"ending": None, "confirmation": None, "created": [], "produced": [], "fp_activation": fp,
            "fp_phase_entry": fp, "director_runs": [], "findings": None, "verdicts": [], "spawn_fingerprint": None,
            "config_edits": [], "started_at": time.time(), "runs": [], "failing_runs": 0, "fewest_failing": None,
            "direct_pending": False, "project_edits_since_run": 0, "code_edits_since_run": 0, "relocks": [],
            "strikes": 0, "pending_change": False, "reopen": None, "redo": None, "no_ending": 0, "worker": None,
            "spawn": None, "workers": 0, "start_director": False}


STAGE_KEYS = tuple(fresh_stage(None))


def passed(s):
    return sum(1 for st in s.get("stages") or [] if st.get("passed"))


def final(s):
    """The end-to-end stage that runs the job ending after the last planned stage passed."""
    return bool(s.get("stages")) and (s.get("stage") or 0) > len(s["stages"])


def running(s):
    """"director" or "worker" while a background spawn of this stage has not stopped, else None."""
    sp = s.get("spawn") or {}
    return sp.get("kind") if sp.get("background") and not sp.get("stopped") else None


def next_step(s):
    """What to do next, from the job file alone (no plugin variables: bin/rehearse calls this in a sandboxed shell)."""
    ph, n = s.get("phase"), s.get("stage")
    if ph in ("judge", "look", "build") and running(s):
        return "wait for the %s's notification, then rehearse job" % running(s)
    if ph == "goal":
        if not s.get("stages"):
            if s.get("attended") is False:  # nobody to ask
                return "record the four goal items (assumed where the request is silent), then rehearse plan"
            return "ask the goal questions the request leaves open, then rehearse plan"
        return "register the job ending with rehearse ending --job"
    if ph == "job-confirm":
        return "have the job confirmed: ask the user"
    if ph == "look":
        if s.get("redo") is not None:
            return "start a look worker to re-register the ending; the user said: %s" % s["redo"]
        if s.get("reopen") and not s["reopen"]["looks"]:
            return "look again (a stage step into project code, or rehearse fetch), then rehearse ending"
        return "look at stage %s (start rehearse:worker; a one-stage job: yourself), then rehearse ending" % n
    if ph == "confirm":
        return "have the stage %s ending confirmed: ask the user" % n
    if ph == "build":
        if s.get("start_director"):
            return "start rehearse:director" + (" again" if s.get("verdicts") else "")
        return "build stage %s (start rehearse:worker), rehearse run until it passes, then start rehearse:director" % n
    return NEXT.get(ph, "see the instructions")


def job_text(s):
    """What `rehearse job` prints, and what the hook answers when the user types it as a prompt."""
    stages = s.get("stages") or []
    lines = ["job %s: phase %s, stage %s of %d (%d passed), strikes %d, failing runs %d" % (
        s["run_id"], s["phase"], s.get("stage"), len(stages), passed(s), s.get("strikes", 0),
        s.get("failing_runs", 0))]
    lines += ["  stage %d %s (%s)%s: %s" % (i, st.get("name"), st.get("kind"), ", passed" if st.get("passed") else "",
                                           st.get("line")) for i, st in enumerate(stages, 1)]
    sp = s.get("spawn") or {}
    if running(s):
        lines.append("%s running since %s" % (running(s), time.strftime("%H:%M:%S", time.localtime(sp["at"]))))
    elif sp.get("stopped"):  # a background agent's result reaches the manager only here
        last = s.get("verdict_note") if sp["kind"] == "director" else (s.get("worker") or {}).get("outcome")
        lines.append("last: %s" % (last or "no result recorded"))
    lines += ["next: " + next_step(s), "not verified: " + ("; ".join(s.get("not_verified") or []) or "none recorded")]
    return "\n".join(lines)


def plan_refused(s, n=None):
    """Why `rehearse plan` (n None) or `rehearse plan --stage n` is refused now, or None."""
    ph, done, stages = s.get("phase"), passed(s), s.get("stages") or []
    if n is None:
        if ph == "goal" or (ph == "job-confirm" and not done):
            return None
        return ("plain rehearse plan is accepted in goal, and in job-confirm until a stage has passed; the job is in "
                "%s with %d stage(s) passed" % (ph, done))
    if not 1 <= n <= len(stages):
        return "there is no stage %d in the plan" % n
    if final(s):
        return "in the final stage, change means registering the job ending again; plan --stage is refused"
    if ph == "job-confirm" and not stages[n - 1].get("passed"):
        return None
    if ph == "look" and s.get("pending_change") and n == s.get("stage"):
        return None
    return ("plan --stage %d is accepted in job-confirm for a stage not yet passed, or in look for the current "
            "stage after the user chose change" % n)


def ending_refused(s, job=False):
    """Why `rehearse ending [--job]` is refused now, or None. In the final stage both kinds replace both endings."""
    ph = s.get("phase")
    if not s.get("stages"):
        return "register the plan first with rehearse plan"
    if job and not final(s):
        if len(s["stages"]) == 1:
            return "a one-stage job has no job ending: its stage ending is the job ending"
        if ph in ("goal", "job-confirm"):
            return None
        if ph == "look" and passed(s) and not (s.get("workers") or s.get("ending") or s.get("reopen")):
            return None
        return ("the job ending is registered in goal, in job-confirm, or in look right after a stage passed, "
                "before a worker starts or a stage ending exists")
    if ph in ("look", "confirm"):
        return None
    return "a stage ending is registered in look; the job is in %s" % ph


def v3(s):
    """A v3 job file. A 2.0.1 run file (no "stages") still on disk is ignored: its phases mean other things."""
    return bool(s) and "stages" in s


def live(s):
    """A job still governs the session until it is cancelled, not fixed, or closed (its final Stop was allowed)."""
    return v3(s) and s.get("phase") not in ENDED and not s.get("closed")


def sessions_root():
    data = os.environ.get("CLAUDE_PLUGIN_DATA")
    return os.path.join(data, "sessions") if data else os.path.expanduser("~/.claude/rehearse/sessions")


def session_dir(session_id):
    return os.path.join(sessions_root(), re.sub(r"[^\w.-]", "_", str(session_id)) or "_")


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            s = json.load(f)
        return s if isinstance(s, dict) else None
    except (OSError, ValueError):
        return None


def mirror_path(s):
    return os.path.join(s["run_folder"], "state.json")


def _write(path, s):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=1)
    os.replace(path + ".tmp", path)


def _save(s):
    _write(s["path"], s)
    _write(mirror_path(s), s)


def ensure_mirror(s):
    if not os.path.exists(mirror_path(s)):
        _write(mirror_path(s), s)


def newest(session_id):
    """The session's newest run in any phase. Read-only."""
    d = session_dir(session_id)
    try:
        names = sorted((n for n in os.listdir(d) if n.endswith(".json")), reverse=True)
    except OSError:
        return None
    return load(os.path.join(d, names[0])) if names else None


def current(session_id):
    """The session's newest run unless it has ended (cancelled or not fixed); None otherwise. Read-only."""
    s = newest(session_id)
    return s if live(s) else None


def find_for_cwd(cwd):
    """For bin/rehearse: the newest live run whose run folder is in cwd or an ancestor, from the copy. Read-only."""
    d = os.path.realpath(cwd)
    while True:
        rd = os.path.join(d, ".rehearsal")
        if os.path.isdir(rd):
            for run in sorted(os.listdir(rd), reverse=True):
                s = load(os.path.join(rd, run, "state.json"))
                if live(s):
                    return s
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def new_run(session_id, root, request, fp, attended=True):
    """A new job in goal. The key stays run_id: stage/client.py and the hook's result matching read it."""
    now = datetime.datetime.now(datetime.timezone.utc)
    run_id = now.strftime("%Y%m%dT%H%M%S%fZ") + "-" + secrets.token_hex(3)
    root = os.path.realpath(root)
    folder = os.path.join(root, ".rehearsal", run_id)
    os.makedirs(os.path.join(folder, "fixtures"), exist_ok=True)
    os.makedirs(session_dir(session_id), exist_ok=True)
    s = dict(fresh_stage(fp), run_id=run_id, session_id=session_id,
             path=os.path.join(session_dir(session_id), run_id + ".json"), phase="goal", stage=1, root=root,
             attended=attended,  # the mode at activation, for next_step (bin/rehearse sees no plugin settings)
             run_folder=folder, request=request, prompts=[], goal=None, assumptions=[], blockers=[], stages=[],
             stages_from=None, job_ending=None, job_confirmation=None, confirm_return=None, not_verified=[],
             fixtures=[], notes=[], created_at=time.time(), updated_at=time.time())
    _save(s)
    return s


@contextlib.contextmanager
def locked(s):
    """Reload the state under its lock, let the caller change it, write it back."""
    with open(s["path"] + ".lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        cur = load(s["path"]) or s
        yield cur
        cur["updated_at"] = time.time()
        _save(cur)
