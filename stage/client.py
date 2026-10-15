"""`rehearse stage start [--python <path>] | step '<code>' | stop`: talk to stage/server.py for the current run.

The socket is $XDG_RUNTIME_DIR/rehearse-<8 hex>.sock (else /tmp/...); the server's pid is in <run folder>/stage.pid,
where the Stop hook looks for it.
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import zlib

SERVER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "server.py")
NOT_RUNNING = "stage not running; rehearse stage start"
TIMEOUT = float(os.environ.get("REHEARSE_RUN_TIMEOUT", "600"))


def result(run, kind, **kw):
    print("REHEARSE-RESULT " + json.dumps(dict(run=run, kind=kind, **kw), ensure_ascii=False))


def socket_path(run_id):
    base = os.environ.get("XDG_RUNTIME_DIR")
    base = base if base and os.path.isdir(base) else "/tmp"
    return os.path.join(base, "rehearse-%08x.sock" % (zlib.crc32(run_id.encode()) & 0xffffffff))


def ask(path, req, timeout=TIMEOUT):
    """The server's reply, or None when nothing listens on the socket."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as c:
            c.settimeout(timeout)
            c.connect(path)
            c.sendall((json.dumps(req) + "\n").encode("utf-8"))
            line = c.makefile("r", encoding="utf-8").readline()
    except OSError:
        return None
    return json.loads(line) if line else None


def interpreter(root, given):
    if given:
        return given
    for p in (os.path.join(root, ".venv", "bin", "python"), os.path.join(root, "venv", "bin", "python"),
              os.path.join(os.environ["CONDA_PREFIX"], "bin", "python") if os.environ.get("CONDA_PREFIX") else ""):
        if p and os.path.exists(p):
            return p
    return shutil.which("python3") or sys.executable


def start(s, argv):
    sock = socket_path(s["run_id"])
    hello = ask(sock, {"op": "hello"}, 5)
    if not hello:
        given = argv[argv.index("--python") + 1] if "--python" in argv[:-1] else None
        python = interpreter(s["root"], given)
        log = open(os.path.join(s["run_folder"], "stage.log"), "ab")
        try:
            p = subprocess.Popen([python, SERVER, "--root", s["root"], "--state", s["path"], "--socket", sock,
                                  "--pidfile", os.path.join(s["run_folder"], "stage.pid")],
                                 cwd=s["root"], stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                 start_new_session=True)
        except OSError as x:
            print("stage could not start %s: %s" % (python, x))
            return result(s["run_id"], "stage-start", ok=False, python=python, socket=sock, error=str(x))
        deadline = time.time() + 30
        while not hello and p.poll() is None and time.time() < deadline:
            time.sleep(0.1)
            hello = ask(sock, {"op": "hello"}, 5)
        if not hello:
            print("stage did not start with %s; see %s" % (python, log.name))
            return result(s["run_id"], "stage-start", ok=False, python=python, socket=sock, error="did not start")
    print("stage: python %s (sys.path[0] %s), pid %s" % (hello["python"], hello["path0"], hello["pid"]))
    return result(s["run_id"], "stage-start", ok=True, python=hello["python"], socket=sock)


def step(s, argv):
    if len(argv) != 1:
        print("usage: rehearse stage step '<one statement or expression>'")
        return result(s["run_id"], "stage-step", accepted=False, project_files=[], error="usage")
    r = ask(socket_path(s["run_id"]), {"op": "step", "code": argv[0]})
    if not r:
        print(NOT_RUNNING)
        return result(s["run_id"], "stage-step", accepted=False, project_files=[], error=NOT_RUNNING)
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
    return result(s["run_id"], "stage-step", accepted=r["accepted"], project_files=r["project_files"],
                  error=r["error"])


def stop(s, argv):
    r = ask(socket_path(s["run_id"]), {"op": "stop"}, 10)
    print("stage stopped" if r else NOT_RUNNING)
    return result(s["run_id"], "stage-stop", ok=bool(r))


def main(s, argv):
    cmd = {"start": start, "step": step, "stop": stop}.get(argv[0] if argv else None)
    if not cmd:
        print(__doc__)
        return result(s["run_id"], "stage", ok=False, error="usage")
    return cmd(s, argv[1:])
