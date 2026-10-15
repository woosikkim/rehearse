"""One state file per activation, written only by hooks, under flock.

$CLAUDE_PLUGIN_DATA/sessions/<session_id>/<run_id>.json, else ~/.claude/rehearse/sessions/<session_id>/.
The run folder <root>/.rehearsal/<run_id>/ holds a one-line `state-path` so bin/rehearse, which does not
see the plugin's variables, can find the state and read it.
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


def _save(s):
    tmp = s["path"] + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=1)
    os.replace(tmp, s["path"])


def current(session_id):
    """The session's newest run unless it has ended (cancelled or not fixed); None otherwise. Read-only."""
    d = session_dir(session_id)
    try:
        names = sorted((n for n in os.listdir(d) if n.endswith(".json")), reverse=True)
    except OSError:
        return None
    s = load(os.path.join(d, names[0])) if names else None
    return s if s and s.get("phase") not in ENDED else None


def find_for_cwd(cwd):
    """For bin/rehearse: the newest live run whose run folder is in cwd or an ancestor. Read-only."""
    d = os.path.realpath(cwd)
    while True:
        rd = os.path.join(d, ".rehearsal")
        if os.path.isdir(rd):
            for run in sorted(os.listdir(rd), reverse=True):
                try:
                    with open(os.path.join(rd, run, "state-path"), encoding="utf-8") as f:
                        s = load(f.read().strip())
                except OSError:
                    continue
                if s and s.get("phase") not in ENDED:
                    return s
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def new_run(session_id, root, mode, request, fp):
    now = datetime.datetime.now(datetime.timezone.utc)
    run_id = now.strftime("%Y%m%dT%H%M%S%fZ") + "-" + secrets.token_hex(3)
    root = os.path.realpath(root)
    folder = os.path.join(root, ".rehearsal", run_id)
    os.makedirs(os.path.join(folder, "fixtures"), exist_ok=True)
    os.makedirs(session_dir(session_id), exist_ok=True)
    s = {"run_id": run_id, "session_id": session_id, "path": os.path.join(session_dir(session_id), run_id + ".json"),
         "mode": mode, "phase": "observe", "root": root, "run_folder": folder, "request": request, "prompts": [],
         "ending": None, "confirmation": None, "rounds": [], "round_open": False, "failing_rounds": 0,
         "direct_looks": 0, "rejections": 0, "verdicts": [], "spawn_fingerprint": None,
         "fp_activation": fp, "fp_phase_entry": fp, "created": [], "produced": [], "config_edits": [],
         "fixtures": [], "notes": [], "created_at": time.time(), "updated_at": time.time()}
    _save(s)
    with open(os.path.join(folder, "state-path"), "w", encoding="utf-8") as f:
        f.write(s["path"] + "\n")
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
