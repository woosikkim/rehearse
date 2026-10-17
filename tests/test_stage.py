"""Self-check for stage/server.py and `rehearse stage`. Run: python3 tests/test_stage.py

Scratch projects under a temp dir, CLAUDE_PLUGIN_DATA pointed there. Each block prints "<name>: ok".
"""
import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, "hooks", "rehearse_hook.py")
BIN = os.path.join(ROOT, "bin", "rehearse")
TMP = os.path.realpath(tempfile.mkdtemp(prefix="rehearse-stage-"))
os.environ.update(CLAUDE_PLUGIN_DATA=os.path.join(TMP, "data"))
os.environ.pop("CONDA_PREFIX", None)
sys.path.insert(0, os.path.join(ROOT, "hooks"))
sys.path.insert(0, os.path.join(ROOT, "stage"))
import server  # noqa: E402
import state as S  # noqa: E402

REFUSAL = server.REFUSAL


def hook(payload):
    r = subprocess.run([sys.executable, HOOK], input=json.dumps(payload), text=True, capture_output=True)
    assert r.returncode == 0 and not r.stderr, r.stderr
    return json.loads(r.stdout) if r.stdout.strip() else None


class Proj:
    n = 0

    def __init__(self, files):
        Proj.n += 1
        self.sid = "stage-session-%d" % Proj.n
        self.root = tempfile.mkdtemp(dir=TMP)
        for rel, body in files.items():
            self.write(rel, body)
        hook(dict(hook_event_name="UserPromptSubmit", session_id=self.sid, cwd=self.root,
                  prompt="rehearse fix the total"))
        assert self.state()["phase"] == "goal"

    def write(self, rel, body):
        with open(os.path.join(self.root, rel), "w") as f:
            f.write(body)

    def state(self):
        return S.current(self.sid)

    def set(self, **kw):
        with S.locked(self.state()) as cur:
            cur.update(kw)

    def rh(self, *args):
        r = subprocess.run([sys.executable, BIN] + list(args), cwd=self.root, capture_output=True, text=True,
                           timeout=60)
        lines = r.stdout.strip().splitlines()
        assert lines and lines[-1].startswith("REHEARSE-RESULT "), (r.stdout, r.stderr)
        return r.stdout, json.loads(lines[-1][len("REHEARSE-RESULT "):])

    def step(self, code):
        return self.rh("stage", "step", code)

    def bash(self, cmd, stdout):
        hook(dict(hook_event_name="PostToolUse", session_id=self.sid, cwd=self.root, tool_name="Bash",
                  tool_input={"command": cmd}, tool_response={"stdout": stdout, "stderr": "", "interrupted": False}))


def steps_of(p):
    with open(os.path.join(p.state()["run_folder"], "stage.json")) as f:
        return json.load(f)["steps"]


try:
    # ---- parser
    refused = ["def f(): pass", "async def f(): pass", "class C: pass", "for i in x: pass", "async def f():\n async for i in x: pass",
               "while 1: pass", "if x: y = 1", "y = 1 if x else 2", "with open('f') as f: pass", "try: x\nexcept: pass",
               "f = lambda: 1", "[i for i in x]", "{i for i in x}", "{i: i for i in x}", "sum(i for i in x)",
               "global x", "nonlocal x", "match x:\n case 1: pass", "x = 1; y = 2", "", "del x", "assert x", "pass",
               "exec('1')", "eval('1')", "y = compile('1', 'f', 'eval')", "__import__('os')", "import importlib",
               "import importlib.util", "from importlib import util", "from runpy import run_path", "import runpy.x"]
    if hasattr(ast, "TryStar"):
        refused.append("try: x\nexcept* E: pass")
    for code in refused:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            continue  # e.g. match on an old Python
        assert server.refuse(tree) == REFUSAL, code
    for code in ["re.compile('a')", "model.eval()", "x = 1", "x += 1", "x: int = 1", "import os",
                 "from os import path", "print(x)", "obj.exec_thing(eval_me)"]:
        assert server.refuse(ast.parse(code)) is None, code
    print("parser: ok")

    # ---- session
    p = Proj({"lib.py": "def total(items):\n    return sum(items)\n", "main.py": "import lib\n"})
    out, res = p.rh("stage", "start")
    assert res["kind"] == "stage-start" and res["ok"] and res["python"], res
    out, res = p.step("x = 1")
    assert res["kind"] == "stage-step" and res["accepted"] and res["error"] is None, res
    out, res = p.step("print(x)")
    assert out.splitlines()[0] == "1" and res["accepted"], out
    out, res = p.step("x / 0")
    assert "ZeroDivisionError" in out and "ZeroDivisionError" in res["error"] and res["accepted"], out
    out, res = p.step("x + 1")
    assert "value: 2" in out, out
    out, res = p.step("for i in range(3): print(i)")
    assert REFUSAL in out and not res["accepted"] and res["error"] == REFUSAL, out
    assert [s["code"] for s in steps_of(p)] == ["x = 1", "print(x)", "x / 0", "x + 1"], steps_of(p)  # refused steps are not replayed
    out, res = p.step("print(x)")  # replay: output of the earlier steps stays quiet, the names stay
    assert out.splitlines()[0] == "1" and out.count("1\n") == 1 and "replayed 4 earlier steps" in out, out
    assert "changed on replay" not in out
    print("session: ok")

    # ---- replay drift and the network notice
    out, res = p.step("import time")
    out, res = p.step("time.time()")  # its value differs on every replay
    out, res = p.step("x")
    assert "replayed 7 earlier steps; changed on replay: step 7" in out, out
    out, res = p.step("import socket")
    out, res = p.step("socket.create_connection(('127.0.0.1', 9), timeout=0.2)")
    assert "opened a network connection" in out and res["accepted"], out
    out, res = p.step("x")
    assert "opened a network connection" not in out, out
    print("replay notices: ok")

    # ---- call record
    p.set(phase="build")
    out, res = p.step("import lib")
    assert res["accepted"] and res["project_files"] == ["lib.py"], res  # importing runs the module body
    out, res = p.step("lib.total([5, 7])")
    assert "value: 12" in out and res["project_files"] == ["lib.py"], (out, res)
    out, res = p.step("import json")
    assert res["accepted"] and res["project_files"] == [], res
    out, res = p.step("json.dumps({'a': [1]})")
    assert res["accepted"] and res["project_files"] == [], res
    print("call record: ok")

    # ---- created-module import
    p.write("helper.py", "VALUE = 3\n")
    p.set(phase="look", created=[os.path.join(p.root, "helper.py")])
    for code in ("import helper", "from helper import VALUE"):
        out, res = p.step(code)
        assert not res["accepted"] and res["error"] == server.CREATED and server.CREATED in out, (code, out)
    p.set(phase="build")
    out, res = p.step("from helper import VALUE")
    assert res["accepted"] and res["error"] is None, res
    out, res = p.step("VALUE")
    assert "value: 3" in out, out
    print("created-module import: ok")

    # ---- stop
    out, res = p.rh("stage", "stop")
    assert res["kind"] == "stage-stop" and res["ok"], out
    assert not os.path.exists(os.path.join(p.state()["run_folder"], "stage.json"))
    out, res = p.step("x")
    assert "stage not running; rehearse stage start" in out and res["kind"] == "stage-step" \
        and res["accepted"] is False, out
    print("session stop: ok")

    # ---- interpreter
    q = Proj({"lib.py": "X = 1\n"})
    os.makedirs(os.path.join(q.root, ".venv", "bin"))
    venv = os.path.join(q.root, ".venv", "bin", "python")
    os.symlink(os.path.realpath(sys.executable), venv)
    out, res = q.rh("stage", "start")
    assert res["ok"] and res["python"] == venv and ("sys.path[0] %s" % q.root) in out, (out, res)
    q.rh("stage", "stop")
    out, res = q.rh("stage", "start", "--python", os.path.realpath(sys.executable))
    assert res["ok"] and res["python"] == os.path.realpath(sys.executable), res
    q.rh("stage", "stop")
    print("interpreter: ok")
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print("stage: all checks passed")
