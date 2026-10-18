"""`rehearse stage start [--python <path>] | step '<code>' | stop`: run stage/server.py for the current run.

No process outlives a Bash call: `<run folder>/stage.json` holds the interpreter and the accepted steps with what
each printed the first time, and every step replays them in a fresh interpreter before running the new one. The
output says how many were replayed, which ones came out differently, and when a step opens a network connection.
"""
import json
import os
import secrets
import shutil
import subprocess
import sys

SERVER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "server.py")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(SERVER)), "hooks"))
import log as L  # noqa: E402

NOT_RUNNING = "stage not running; rehearse stage start"
TIMEOUT = float(os.environ.get("REHEARSE_RUN_TIMEOUT", "600"))
FOLDER = None  # set by bin/rehearse: the run folder, where every result is recorded before it is printed


def result(run, kind, **kw):
    res = dict(run=run, kind=kind, **kw, id=secrets.token_hex(4))
    if FOLDER:
        try:
            L.record_result(FOLDER, res)
        except OSError as x:
            print("could not record the result in the run folder (%s): run this again on its own" % x)
    print("REHEARSE-RESULT " + json.dumps(res, ensure_ascii=False))


def stage_file(s):
    return os.path.join(s["run_folder"], "stage.json")


def load(s):
    try:
        with open(stage_file(s), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save(s, st):
    with open(stage_file(s), "w", encoding="utf-8") as f:
        json.dump(st, f)


def run(python, s, args, stdin=""):
    """(reply dict or None, error text) from one server process."""
    try:
        state = os.path.join(s["run_folder"], "state.json")  # the copy; the data folder may be unreadable here
        r = subprocess.run([python, SERVER, "--root", s["root"], "--state", state] + args, input=stdin,
                           cwd=s["root"], capture_output=True, text=True, timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as x:
        return None, str(x)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1]), ""
    except (ValueError, IndexError):
        return None, (r.stderr.strip() or r.stdout.strip() or "no reply")[-2000:]


def interpreter(root, given):
    if given:
        return given
    for p in (os.path.join(root, ".venv", "bin", "python"), os.path.join(root, "venv", "bin", "python"),
              os.path.join(os.environ["CONDA_PREFIX"], "bin", "python") if os.environ.get("CONDA_PREFIX") else ""):
        if p and os.path.exists(p):
            return p
    return shutil.which("python3") or sys.executable


def start(s, argv):
    given = argv[argv.index("--python") + 1] if "--python" in argv[:-1] else None
    python = interpreter(s["root"], given)
    hello, err = run(python, s, ["--hello"])
    if not hello:
        print("stage did not start with %s: %s" % (python, err))
        return result(s["run_id"], "stage-start", ok=False, python=python, error="did not start")
    save(s, {"python": hello["python"], "steps": []})
    print("stage: python %s (sys.path[0] %s)" % (hello["python"], hello["path0"]))
    return result(s["run_id"], "stage-start", ok=True, python=hello["python"])


def step(s, argv):
    if len(argv) != 1:
        print("usage: rehearse stage step '<one statement or expression>'")
        return result(s["run_id"], "stage-step", accepted=False, project_files=[], error="usage")
    st = load(s)
    if not st:
        print(NOT_RUNNING)
        return result(s["run_id"], "stage-step", accepted=False, project_files=[], error=NOT_RUNNING)
    r, err = run(st["python"], s, [], json.dumps({"steps": st["steps"], "code": argv[0]}))
    if not r:
        print("stage failed: " + err)
        return result(s["run_id"], "stage-step", accepted=False, project_files=[], error="stage failed: " + err)
    if r["stdout"]:
        print(r["stdout"].rstrip("\n"))
    if r["stderr"]:
        print("stderr:\n" + r["stderr"].rstrip("\n"))
    if r["value"] is not None:
        print("value: " + r["value"])
    if r["exception"]:
        print("exception: " + r["exception"])
    elif r["error"]:
        print("refused: " + r["error"])
    if r["project_files"]:
        print("entered: " + ", ".join(r["project_files"]))
    if r.get("replayed"):
        print("replayed %d earlier step%s%s" % (r["replayed"], "" if r["replayed"] == 1 else "s",
              "; changed on replay: step " + ", ".join(str(i) for i in r["drift"]) if r.get("drift") else ""))
    if r.get("network"):
        print("this step opened a network connection; replay will repeat it on every later step. "
              "For requests that change data, use rehearse fetch")
    if r["accepted"]:
        st["steps"].append({"code": argv[0], "seen": [r["stdout"], r["value"], r["exception"]]})
        save(s, st)
    return result(s["run_id"], "stage-step", accepted=r["accepted"], project_files=r["project_files"],
                  error=r["error"])


def stop(s, argv):
    was = load(s) is not None
    try:
        os.remove(stage_file(s))
    except OSError:
        pass
    print("stage stopped" if was else NOT_RUNNING)
    return result(s["run_id"], "stage-stop", ok=was)


def main(s, argv):
    cmd = {"start": start, "step": step, "stop": stop}.get(argv[0] if argv else None)
    if not cmd:
        print(__doc__)
        return result(s["run_id"], "stage", ok=False, error="usage")
    return cmd(s, argv[1:])
