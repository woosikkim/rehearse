"""One job file per activation, written only by hooks, under flock.

$CLAUDE_PLUGIN_DATA/sessions/<session_id>/<run_id>.json (else ~/.claude/rehearse/sessions/...) is the state every
decision reads. Each save also writes a copy to <root>/.rehearsal/<run_id>/state.json, which is all that
bin/rehearse (no plugin variables; possibly a sandboxed shell that cannot see the data folder) and the director
read. An edited or deleted copy changes no decision; a missing copy is written again on the next hook call.
"""
import collections
import contextlib
import datetime
import fcntl
import json
import os
import re
import secrets
import time

ENDED = ("done.cancelled", "done.not_fixed")
LOCKED = ("goal", "job-confirm", "look", "confirm", "wait")  # edits of project files and declared outputs refused
WAIT = ("goal", "job-confirm", "confirm", "wait")  # where a manager may stop when someone can answer: it waits
NO_LOOK = ("no look step since edits were locked again: take one (a stage step into project code, or rehearse "
           "fetch; file://<path> for a draft or CSV), then register")
GOAL_ITEMS = ("purpose", "deliverable", "done", "out_of_scope")
NEXT = {"judge": "wait for the director's verdict",
        "wait": "give the solution-ready report and ask the user once (give what is needed / these checks are wrong / "
                "redo this stage / stop here, which ends the whole rehearse job), then record the answer: rehearse "
                "wait --resume --says '<words>' | --correct --says '<words>' | --change --confirmed | --stop-here",
        "done.passed": "write report.md, then finish",
        "done.not_fixed": 'write report.md starting with "not fixed"',
        "done.cancelled": "the job is cancelled"}


def fresh_stage(fp, at=None):
    """The current-stage fields, reset at every stage start (brief section 8); archived into stages[n] on PASS."""
    return {"ending": None, "confirmation": None, "created": [], "produced": [], "fp_activation": fp,
            "fp_phase_entry": fp, "director_runs": [], "findings": None, "verdicts": [], "spawn_fingerprint": None,
            "config_edits": [], "started_at": at or time.time(), "runs": [], "failing_runs": 0, "fewest_failing": None,
            "direct_pending": False, "project_edits_since_run": 0, "code_edits_since_run": 0, "relocks": [],
            "strikes": 0, "pending_change": False, "reopen": None, "redo": None, "worker": None,
            "spawn": None, "workers": 0, "start_director": False, "strike_log": [], "wait_log": [], "wrongs": [],
            "corrections": [], "tried": [], "reviews": [], "review_due": None, "failed": None, "reviewer": None}


STAGE_KEYS = tuple(fresh_stage(None))


def now(cur):
    """A stamp for ordering inside the job file: never earlier than the last one, even when the wall clock steps
    back between two hook processes (a WSL2 resync). A step back is noted once, for the Process section."""
    t = time.time()
    last = cur.get("clock") or 0
    if t < last - 0.05:
        cur.setdefault("notes", []).append("clock stepped back %.3f s between hook calls" % (last - t))
    t = max(t, last + 1e-6)
    cur["clock"] = t
    return t


def cites_search(x, web):
    """True if a tried record (steps) or a review (searched) cites a logged WebSearch step, or carries a recorded
    reason why none was available (--no-websearch)."""
    return bool(set(x.get("steps") or x.get("searched") or []) & web) or bool(x.get("no_websearch"))


def tried_names(s):
    return {str(x.get("route", "")).strip().lower() for x in s.get("tried") or []}


def latest_review(s, since=0):
    rv = [r for r in s.get("reviews") or [] if r.get("at", 0) >= since]
    return rv[-1] if rv else None


def untried(s):
    """The latest review's candidates that no tried record names and no drop explains."""
    rv = latest_review(s)
    if not rv:
        return []
    done = tried_names(s) | {str(x.get("name", "")).strip().lower() for x in rv.get("dropped") or []}
    return [c for c in rv.get("candidates") or [] if str(c.get("name", "")).strip().lower() not in done]


def passed(s):
    return sum(1 for st in s.get("stages") or [] if st.get("passed"))


def final(s):
    """The end-to-end stage that runs the job ending after the last planned stage passed."""
    return bool(s.get("stages")) and (s.get("stage") or 0) > len(s["stages"])


def label(s):
    """How messages name the current stage: the job ending runs as a final stage after the planned ones."""
    return "final stage (job ending)" if final(s) else "stage %s" % s.get("stage")


def where(s):
    n = len(s.get("stages") or [])
    if final(s):
        return "final stage (job ending), %d of %d stages passed" % (passed(s), n)
    return "stage %s of %d (%d passed)" % (s.get("stage"), n, passed(s))


def running(s):
    """"director" or "worker" while a background spawn of this stage has not stopped, else None."""
    sp = s.get("spawn") or {}
    return sp.get("kind") if sp.get("background") and not sp.get("stopped") else None


def next_step(s):
    """What to do next, from the job file alone (no plugin variables: bin/rehearse calls this in a sandboxed shell)."""
    ph = s.get("phase")
    if ph in ("judge", "look", "build") and running(s):
        return "wait for the %s's notification, then rehearse job" % running(s)
    if ph == "goal":
        if not s.get("stages"):
            if headless(s):  # nobody to ask
                return "record the four goal items (assumed where the request is silent), then rehearse plan"
            return "ask the goal questions the request leaves open, then rehearse plan"
        return "register the job ending with rehearse ending --job"
    if ph == "job-confirm":
        return "have the job confirmed: ask the user"
    if ph in ("look", "build") and s.get("review_due"):
        rv = latest_review(s, s["review_due"]["at"])
        if not rv:
            return ("a worker stopped without %s: review its log (rehearse review ...; in a one-stage job start "
                    "rehearse:reviewer), then a new worker gets the candidates, or rehearse failed"
                    % ("an ending" if ph == "look" else "a pass"))
        if untried(s):
            return "start a new rehearse:worker with the review's candidates: %s" % ", ".join(
                c["name"] for c in untried(s))
        return "the review found no untried candidate: rehearse failed --needs '<the one thing>' or --exhausted"
    if ph == "look":
        if s.get("redo") is not None:
            return "start a look worker to re-register the ending; the user said: %s" % s["redo"]
        if (s.get("reopen") or {}).get("why") == "correct":
            return ("register the ending again with the checks corrected to the user's words (rehearse ending; no "
                    "look step needed), then have it confirmed")
        if s.get("reopen") and not s["reopen"]["looks"]:
            return "look again (a stage step into project code, or rehearse fetch), then rehearse ending"
        return "look at %s (start rehearse:worker; a one-stage job: yourself), then rehearse ending" % label(s)
    if ph == "confirm":
        return "have the %s ending confirmed: ask the user" % label(s)
    if ph == "build":
        if s.get("start_director"):
            return "start rehearse:director" + (" again" if s.get("verdicts") else "")
        return "build %s (start rehearse:worker), rehearse run until it passes, then start rehearse:director" % label(s)
    return NEXT.get(ph, "see the instructions")


def failing(s):
    """The requirements the last run of the ending failed: the registration run, until a later `rehearse run`."""
    e = s.get("ending") or {}
    last = e.get("after") or e.get("before") or {}
    return [r for r in last.get("results") or [] if not r.get("passed")]


def failing_checks(s):
    """The checks the last run failed, in one line, so the wait question can name them."""
    bad = failing(s)
    if not bad:
        return "failing checks: none recorded"
    return "failing checks: " + "; ".join("%s (%s %s)" % (r.get("requirement"), r.get("check"), r.get("value")) for r in bad)


def question_since(s):
    """The stamp after which the user must have answered for a wait decision: the wait began, or (stop here, from
    any question) the last worker's stop or the stage start."""
    if s.get("phase") == "wait":
        return s.get("wait_at") or 0
    return max((s.get("worker") or {}).get("at") or 0, s.get("started_at") or 0)


def said(s, text, since=0):
    """True if the user said `text` word for word in an answer recorded at or after `since` (the same rule a goal
    item's "answer" source gets): the record holds the user's words, never the manager's paraphrase."""
    text = (text or "").strip()
    return bool(text) and any(text in w.get("text", "") for w in s.get("user_words") or [] if w.get("at", 0) >= since)


def job_text(s):
    """What `rehearse job` prints, and what the hook answers when the user types it as a prompt."""
    stages = s.get("stages") or []
    lines = ["job %s: phase %s, %s, strikes %d, failing runs %d" % (
        s["run_id"], s["phase"], where(s), s.get("strikes", 0), s.get("failing_runs", 0))]
    if s["phase"] == "wait":
        lines.append(failing_checks(s))
    lines += ["  stage %d %s (%s)%s: %s" % (i, st.get("name"), st.get("kind"), ", passed" if st.get("passed") else "",
                                           st.get("line")) for i, st in enumerate(stages, 1)]
    sp = s.get("spawn") or {}
    if running(s):
        lines.append("%s running since %s" % (running(s), time.strftime("%H:%M:%S", time.localtime(sp["at"]))))
    elif sp.get("stopped"):  # a background agent's result reaches the manager only here
        last = s.get("verdict_note") if sp["kind"] == "director" else (s.get("worker") or {}).get("outcome")
        lines.append("last: %s" % (last or "no result recorded"))
    lines += ["next: " + next_step(s), "not verified: " + ("; ".join(s.get("not_verified") or []) or "none recorded")]
    return "\n".join(lines + [""] + process_lines(s))


def one_line(x, n=120):
    text = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)
    return (text.strip().splitlines() or [""])[0][:n]


def process_lines(s):
    """The Process section (owner's proposal P4b): counts from the job file and the run folder's records, computed
    by the plugin, never written by a model. It changes nothing by itself; a rule change stays a human proposal."""
    folder = s["run_folder"]

    def lines(name):  # the stage server loads this module by path, so hooks/log.py is read here directly
        try:
            with open(os.path.join(folder, name), encoding="utf-8") as f:
                return [ln for ln in f if ln.strip()]
        except OSError:
            return []
    def parsed(name):
        out = []
        for ln in lines(name):
            try:
                out.append(json.loads(ln))
            except ValueError:
                continue
        return out
    steps = [r for r in parsed("commands.jsonl") if "step" in r]
    records = parsed("results.jsonl")
    # Commands that should have written a result against results recorded. Since 3.1.0 the hook counts each
    # step's rehearse invocations exactly ("rehearse") and every record carries "at"; steps and records from
    # earlier releases are counted by text and shown apart, since results were then read from the output.
    exact = [r for r in steps if "rehearse" in r]
    ran = sum(int(r.get("rehearse") or 0) for r in exact)
    rec = sum(1 for r in records if "at" in r)
    by_text = sum(len(re.findall(r"(?:^|[\s;&|(])(?:\S*rehearse|\$\w+)\s+(?:plan|ending|run|fetch|job|status|wait|wrong|"
                                 r"stage|tried|review|failed)\b", r.get("cmd") or "")) for r in steps if "rehearse" not in r)
    commands = "- rehearse commands: %d; results recorded: %d; without a record: %d" % (ran, rec, max(ran - rec, 0))
    if rec > ran:  # a script (python3 - <<EOF ...) that calls rehearse in a loop is not countable from its text
        commands += "; results from commands inside scripts, not counted: %d" % (rec - ran)
    if len(exact) < len(steps):
        commands += (" (since 3.1.0; earlier: %d commands by text, %d results recorded by 3.0.1, results read from "
                     "the output before the record file not counted)" % (by_text, len(records) - rec))
    # every stage so far: the archived ones carry their own fields, the current one is the top level
    rows = [("stage %d" % i, st) for i, st in enumerate(s.get("stages") or [], 1) if "verdicts" in st]  # archived
    rows.append((label(s), s))
    old = "not recorded (job predates 3.1.0)"
    counts = lambda c: ", ".join("%s %d" % kv for kv in c.most_common()) if c else "none"  # noqa: E731

    def logged(key, text):
        """A missing log is unknown, never zero: a stage begun before 3.1.0 says so beside the stages that have it."""
        have = [(lab, st) for lab, st in rows if st.get(key) is not None]
        missing = [lab for lab, st in rows if st.get(key) is None]
        if not have:
            return old
        return text(have) + ("; not recorded for %s (job predates 3.1.0)" % ", ".join(missing) if missing else "")
    strikes = logged("strike_log", lambda have: "%d (%s)" % (
        sum(len(st["strike_log"]) for _, st in have),
        counts(collections.Counter(e.get("cause") for _, st in have for e in st["strike_log"]))))
    rows = [(lab, dict(st, wait_log=st["stuck_log"]) if st.get("wait_log") is None and st.get("stuck_log") is not None
             else st) for lab, st in rows]  # a stage from 3.1.0 to 3.2.0 kept this log under the stuck phase's name
    waits = logged("wait_log", lambda have: "%d (%s)" % (
        sum(len(st["wait_log"]) for _, st in have),
        ", ".join(e.get("answer") or "unanswered" for _, st in have for e in st["wait_log"]) or "none"))
    reworks = ["  - %s: %s" % (lab, one_line((v.get("findings") or ["no reason given"])[0]))
               for lab, st in rows for v in st.get("verdicts") or [] if v.get("verdict") == "REWORK" and not v.get("void")]
    relocks = sum(len(st.get("relocks") or []) for _, st in rows)
    refusals = old if s.get("refusals") is None else counts(collections.Counter(r.get("kind") for r in s["refusals"]))
    free = sum(1 for n in s.get("notes") or [] if str(n).startswith("wait answer: "))
    wrongs = sum(len(st.get("wrongs") or []) for _, st in rows)
    no_web = sum(1 for _, st in rows for x in (st.get("tried") or []) + (st.get("reviews") or []) if x.get("no_websearch"))
    loops = "- routes tried: " + logged("tried", lambda have: "%d; reviews: %d; candidates dropped: %d; failed: %s" % (
        sum(len(st["tried"]) for _, st in have), sum(len(st.get("reviews") or []) for _, st in have),
        sum(len(r.get("dropped") or []) for _, st in have for r in st.get("reviews") or []),
        "; ".join("%s: %s" % (lab, "needs " + st["failed"]["needs"] if st["failed"].get("needs") else "exhausted")
                  for lab, st in have if st.get("failed")) or "none")).replace("3.1.0", "4.0.0")
    loops += "; without a web search, reason recorded: %d" % no_web
    fixes = ["  - %s, %s: %s -> %s (the user: %s)" % (c.get("stage"), c.get("requirement"), c.get("before") or "none",
                                                      c.get("after") or "dropped", one_line(c.get("user") or ""))
             for _, st in rows for c in st.get("corrections") or []]
    return ["## Process (computed by the plugin from the job file; it changes nothing by itself)",
            commands,
            "- strikes: " + strikes,
            "- REWORK reasons (%d):%s" % (len(reworks), "\n" + "\n".join(reworks) if reworks else " none"),
            "- refusals: " + refusals,
            "- waits: %s; free-text answers while waiting: %d; checks reported wrong: %d" % (waits, free, wrongs),
            "- corrected checks (%d):%s" % (len(fixes), "\n" + "\n".join(fixes) if fixes else " none"),
            loops,
            "- relocks: %d" % relocks]


def finish_report(s):
    """Append the Process section to report.md once, when the job ends."""
    path = os.path.join(s["run_folder"], "report.md")
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return
    if "## Process" in text:
        return
    with open(path, "a", encoding="utf-8") as f:
        f.write(("\n" if text.endswith("\n") else "\n\n") + "\n".join(process_lines(s)) + "\n")


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


STAMP = "%Y%m%dT%H%M%S%fZ"


def _stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime(STAMP)


def mode(s):
    """"ask" or "auto"; a 3.x job file (an `attended` flag) reads as ask or auto plus headless."""
    return s.get("mode") or ("auto" if s.get("attended") is False else "ask")


def auto(s):
    return mode(s) == "auto"


def headless(s):
    """Nobody can answer (evals, scripts): goal items are assumed, confirmations accepted, a wait ends as not fixed."""
    return bool(s.get("headless")) or s.get("attended") is False


def mode_text(s):
    if headless(s):
        return ("auto, headless: nobody can answer; record unasked goal items as assumed, endings are accepted at "
                "registration, and anything that would wait for the user ends the job as not fixed")
    if auto(s):
        return ("auto: ask the goal items and confirm the plan, the stages and the job ending up front; after that "
                "ask nothing: stage endings and judgment calls are accepted as registered and recorded")
    return "ask: the user confirms the goal, the plan and each ending"


def new_run(session_id, root, request, fp, mode="ask", headless=False, task=None):
    """A new job in goal. The key stays run_id: stage/client.py and the hook's result matching read it."""
    ts = _stamp()
    try:  # newest() and find_for_cwd() sort by this prefix: it must sort after every earlier job of the session,
        names = sorted(n for n in os.listdir(session_dir(session_id)) if n.endswith(".json"))  # whatever the clock did
    except OSError:
        names = []
    if names and ts <= names[-1].split("-")[0]:
        last = datetime.datetime.strptime(names[-1].split("-")[0], STAMP).replace(tzinfo=datetime.timezone.utc)
        ts = (last + datetime.timedelta(microseconds=1)).strftime(STAMP)
    run_id = ts + "-" + secrets.token_hex(3)
    root = os.path.realpath(root)
    folder = os.path.join(root, ".rehearsal", run_id)
    os.makedirs(os.path.join(folder, "fixtures"), exist_ok=True)
    os.makedirs(session_dir(session_id), exist_ok=True)
    s = dict(fresh_stage(fp), run_id=run_id, session_id=session_id,
             path=os.path.join(session_dir(session_id), run_id + ".json"), phase="goal", stage=1, root=root,
             mode=mode, headless=headless, task=task,  # decided at activation; later checks read the job file
             run_folder=folder, request=request, prompts=[], goal=None, assumptions=[], blockers=[], stages=[],
             stages_from=None, job_ending=None, job_confirmation=None, confirm_return=None, not_verified=[],
             fixtures=[], notes=[], results_read=0, refusals=[], user_words=[], created_at=time.time(),
             updated_at=time.time())
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
