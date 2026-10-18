"""Self-check for hooks/rehearse_hook.py and bin/rehearse. Run: python3 tests/test_hooks.py

Drives the hook with Claude Code-shaped payloads in scratch projects (git and non-git) under a temp dir,
with CLAUDE_PLUGIN_DATA pointed at that temp dir. Each block prints "<name>: ok".
"""
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, "hooks", "rehearse_hook.py")
BIN = os.path.join(ROOT, "bin", "rehearse")
TRACER = os.path.join(ROOT, "tracer")
sys.path.insert(0, os.path.join(ROOT, "hooks"))
import fingerprint as F  # noqa: E402

TMP = os.path.realpath(tempfile.mkdtemp(prefix="rehearse-test-"))
DATA = os.path.join(TMP, "plugin-data")
ENV = dict(os.environ, CLAUDE_PLUGIN_DATA=DATA)
ENV.pop("REHEARSE_RUN_TIMEOUT", None)


def hook(payload):
    data = payload if isinstance(payload, str) else json.dumps(payload)
    r = subprocess.run([sys.executable, HOOK], input=data, text=True, capture_output=True, env=ENV)
    assert r.returncode == 0 and not r.stderr, (r.returncode, r.stderr)
    return json.loads(r.stdout) if r.stdout.strip() else None


def text(out):
    return json.dumps(out, ensure_ascii=False) if out else ""


def denied(out):
    return bool(out) and out.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


class Proj:
    n = 0

    def __init__(self, files, git=True):
        Proj.n += 1
        self.sid = "session-%d" % Proj.n
        self.root = tempfile.mkdtemp(dir=TMP)
        for rel, body in files.items():
            self.write(rel, body)
        if git:
            g = lambda *a: subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a],  # noqa: E731
                                          cwd=self.root, capture_output=True, check=True)
            g("init", "-q")
            g("add", "-A")
            g("commit", "-qm", "start", "--allow-empty")

    def j(self, *p):
        return os.path.join(self.root, *p)

    def write(self, rel, body):
        os.makedirs(os.path.dirname(self.j(rel)), exist_ok=True)
        with open(self.j(rel), "w") as f:
            f.write(body)

    def ev(self, event, **kw):
        return hook(dict(hook_event_name=event, session_id=self.sid, cwd=self.root, **kw))

    def prompt(self, t):
        return self.ev("UserPromptSubmit", prompt=t)

    def pre(self, tool, **tin):
        return self.ev("PreToolUse", tool_name=tool, tool_input=tin)

    def bash(self, cmd, stdout="", stderr=""):
        return self.ev("PostToolUse", tool_name="Bash", tool_input={"command": cmd},
                       tool_response={"stdout": stdout, "stderr": stderr, "interrupted": False})

    def run(self, cmd):
        """Run a command for real in the project, then report it to the hook as the Bash tool would."""
        r = subprocess.run(cmd, shell=True, cwd=self.root, capture_output=True, text=True)
        return self.bash(cmd, r.stdout, r.stderr)

    def edit(self, rel, body, tool="Edit"):
        out = self.pre(tool, file_path=self.j(rel))
        if denied(out):
            return out
        self.write(rel, body)
        return self.ev("PostToolUse", tool_name=tool, tool_input={"file_path": self.j(rel)}, tool_response={})

    def rehearse(self, *args, **env):
        r = subprocess.run([sys.executable, BIN, *args], cwd=self.root, capture_output=True, text=True,
                           env=dict(os.environ, **env))
        assert r.returncode == 0, r.stderr
        return r.stdout, self.bash(shlex.join(["rehearse", *args]), r.stdout, r.stderr)

    def job(self, request=None):
        """Activate and record a one-stage plan: the job is in look."""
        self.prompt(request or REQUEST)
        self.rehearse(*PLAN)
        assert self.state()["phase"] == "look", self.state()["phase"]

    def state(self):
        d = os.path.join(DATA, "sessions", self.sid)
        names = sorted(n for n in os.listdir(d) if n.endswith(".json")) if os.path.isdir(d) else []
        return json.load(open(os.path.join(d, names[-1]))) if names else None


BUGGY = "print('total: 10')\n"
FIXED = "print('total: 12')\n"
REQUEST = "rehearse fix the report; it should print total: 12"
ENDING = ["ending", "--cmd", "python3 main.py", "--expect", "prints the right total", "contains", "total: 12",
          "--cite", "request"]
PLAN = ["plan", "--goal", "purpose", "assumed", "the job works", "--goal", "deliverable", "assumed", "the program",
        "--goal", "done", "assumed", "the ending passes", "--goal", "out_of_scope", "assumed", "nothing else",
        "--stage-def", "only", "fix", "do the job", "-", "-"]


def in_confirm(git=True, files=None):
    p = Proj(dict({"main.py": BUGGY}, **(files or {})), git=git)
    p.job()
    p.rehearse(*ENDING)
    assert p.state()["phase"] == "confirm", p.state()["phase"]
    return p


def in_work(**kw):
    p = in_confirm(**kw)
    p.prompt("yes")
    assert p.state()["phase"] == "build"
    return p


try:
    # ---------------- activation ----------------
    p = Proj({"main.py": BUGGY})
    for t in ("rehearse가 왜 안 켜져?", "how does rehearse work", "rehearse stop", "rehearsed it yesterday"):
        assert p.prompt(t) is None and p.state() is None, t
    out = p.prompt("rehearse 이 스크래퍼 고쳐줘")
    s = p.state()
    assert s and s["phase"] == "goal" and s["root"] == os.path.realpath(p.root)
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "[rehearse] job %s activated" % s["run_id"] in ctx and "`Rehearse: job <id>`" in ctx, ctx
    assert out["systemMessage"] == "rehearse is on — type `rehearse stop` to stop"
    assert os.path.isdir(os.path.join(s["run_folder"], "fixtures")) and s["run_folder"].startswith(p.root)
    for t in ("Rehearse: fix x", "/rehearse x", "rehearse build a scraper", "REHEARSE the total is wrong"):
        q = Proj({})  # the words fix and build are no longer read: every job starts in goal
        out = q.prompt(t)
        assert out is not None and "activated" in out["hookSpecificOutput"]["additionalContext"], t
        assert q.state()["phase"] == "goal", t
    assert p.prompt("rehearse stop")["systemMessage"].startswith("rehearse stopped")
    assert p.state()["phase"] == "done.cancelled" and "cancelled by user" in p.state()["notes"]
    print("activation: ok")

    # ---------------- routing ----------------
    p = in_confirm()
    p.prompt("ok, but check the tax too")
    s = p.state()
    assert s["phase"] == "look" and s["confirmation"]["answer"] == "ok, but check the tax too"  # a no: look again
    assert not s["confirmation"]["affirmative"] and s["prompts"] == ["ok, but check the tax too"]
    p.rehearse(*ENDING)
    out = text(p.prompt("네 맞아요"))
    assert "[rehearse]" in out and "next:" not in out and p.state()["phase"] == "build", out  # status line: refusals only
    p.prompt("rehearse fix something else")  # while active: stored, no new run
    s = p.state()
    assert s["phase"] == "build" and s["prompts"][-1] == "rehearse fix something else"
    for yes in ("yes", "y", "ok", "correct", "confirmed", "네", "예", "응", "맞아", "맞아요", " YES "):
        q = in_confirm(git=False)
        q.prompt(yes)
        assert q.state()["phase"] == "build", yes
    q = in_confirm(git=False)
    q.prompt("rehearse stop")
    assert q.state()["phase"] == "done.cancelled"
    print("routing: ok")

    # ---------------- edit gate ----------------
    p = Proj({"main.py": BUGGY, "a.py": "x = 1\n", "nb.ipynb": "{}"})
    p.job()
    run = p.state()["run_folder"]
    for tool in ("Write", "Edit", "MultiEdit"):
        out = p.pre(tool, file_path=p.j("main.py"))
        assert denied(out) and "register and confirm an ending first" in text(out), (tool, out)
        assert "next: look at stage 1" in text(out), out
    assert denied(p.pre("NotebookEdit", notebook_path=p.j("nb.ipynb")))
    for cmd in ("echo x > main.py", "echo x | tee main.py", "cp a.py main.py", "sed -i s/10/12/ main.py",
                "cd sub/.. && echo x >> main.py", "mv a.py main.py"):
        out = p.pre("Bash", command=cmd)
        assert denied(out) and "register and confirm an ending first" in text(out), cmd
    assert p.pre("Write", file_path=os.path.join(run, "notes.py")) is None
    assert p.pre("Bash", command="echo x > %s/x.py" % run) is None
    assert p.pre("Write", file_path=p.j("notes.txt")) is None  # not project code
    p.write("main.py", "print('total: 11')\n")  # python3 -c open('main.py','w')... : unseen by the recorder
    _, out = p.rehearse(*ENDING)
    assert out["decision"] == "block" and "main.py" in out["reason"] and p.state()["phase"] == "look", out
    subprocess.run(["git", "checkout", "-q", "main.py"], cwd=p.root, check=True)
    p.rehearse(*ENDING)
    assert p.state()["phase"] == "confirm"
    p.prompt("yes")
    assert p.edit("main.py", FIXED) is None and p.pre("Bash", command="sed -i s/a/b/ a.py") is None
    print("edit gate: ok")

    # ---------------- created files ----------------
    p = Proj({"main.py": BUGGY, "x.c": "int main(){return 0;}\n", "old.sh": "echo hi\n"})
    p.job()
    run = p.state()["run_folder"]
    out_dir = os.path.join(TMP, "outside")
    os.makedirs(out_dir, exist_ok=True)
    scaffold = os.path.join(run, "scaffold", "new.py")
    assert p.pre("Write", file_path=scaffold) is None
    p.write(scaffold, "print(1)\n")
    assert p.pre("Bash", command="echo 'echo 1' > %s/new.sh" % out_dir) is None
    assert p.pre("Bash", command="curl -o %s/dl.py http://example.test/x" % run) is None
    p.write("new.py", "print(1)\n")  # new files that no recorded channel made
    p.write("newmod.py", "print(1)\n")
    for cmd in ("python3 %s" % scaffold, "bash %s/new.sh" % out_dir, "python3 %s/dl.py" % run, "python3 new.py",
                "python3 -m newmod", "cd . && python3 new.py", "source %s/new.sh" % out_dir):
        out = p.pre("Bash", command=cmd)
        assert denied(out) and "was created during this stage" in text(out), cmd
    for cmd in ("cat new.py", "rm -f new.py.bak", "diff new.py main.py", "python3 main.py", "bash old.sh",
                "cc -o prog x.c && ./prog", "grep print new.py"):
        assert p.pre("Bash", command=cmd) is None, cmd
    assert p.pre("Bash", command="cc -o prog2 x.c") is None and p.pre("Bash", command="./prog2") is None
    print("created files: ok")

    # ---------------- ending gate ----------------
    p = Proj({"main.py": FIXED})  # already prints what the request asks for
    p.job()
    _, out = p.rehearse(*ENDING)
    assert out["decision"] == "block" and "the ending shows nothing wrong" in out["reason"], out
    assert p.state()["phase"] == "look" and p.state()["ending"] is None
    p = Proj({})
    p.job("rehearse build a tool that prints done")
    _, out = p.rehearse("ending", "--cmd", "./newprog", "--expect", "says done", "contains", "done", "--cite", "request")
    s = p.state()
    assert s["phase"] == "confirm" and s["ending"]["before"]["rc"] == 127, s["ending"]
    p = Proj({"main.py": BUGGY}, git=False)
    p.job()
    p.write("main.py", "print('total: 13')\n")
    _, out = p.rehearse(*ENDING)
    assert out["decision"] == "block" and "main.py" in out["reason"] and p.state()["phase"] == "look"
    print("ending gate: ok")

    # ---------------- citations ----------------
    p = Proj({"main.py": BUGGY, "data.txt": "price_cents: 1250\n"})
    p.job()
    p.run("echo 'price_cents: 1250'")  # S2 (S1 is the plan)
    so, out = p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "x", "contains", "total: 99", "--cite", "request")
    assert "does not appear in request" in so and p.state()["phase"] == "look"
    for cite, value in (("step:S9", "price_cents: 1250"), ("step:S2", "price_cents: 9")):
        so, _ = p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "x", "contains", value, "--cite", cite)
        assert "ending refused" in so and p.state()["phase"] == "look", so
    rid = p.state()["run_id"]  # S6: the command named through a shell variable, its refusal echoing the value
    p.bash("R=rehearse; $R ending --cmd x --expect x contains 'price_cents: 1250'",
           "ending refused: 'price_cents: 1250' does not appear in step:S9\nREHEARSE-RESULT "
           + json.dumps({"run": rid, "kind": "ending", "ok": False}))
    for cite in ("step:S4", "step:S6"):  # the plugin's own ending output echoes values: never a source, however spelled
        so, _ = p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "x", "contains", "price_cents: 1250",
                           "--cite", cite)
        assert "ending refused" in so and p.state()["phase"] == "look", (cite, so)
    so, _ = p.rehearse("fetch", "file://" + p.j("data.txt"))
    fixture = p.state()["fixtures"][0]
    assert os.path.exists(os.path.join(p.state()["run_folder"], "fixtures", fixture))
    open(os.path.join(p.state()["run_folder"], "fixtures", "fake"), "w").write("price_cents: 1250\n")
    so, _ = p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "x", "contains", "1250", "--cite", "fixture:fake")
    assert "not a plugin-written fixture" in so and p.state()["phase"] == "look", so
    so, _ = p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "x", "regex", r"cents: \d{5}",
                       "--cite", "fixture:" + fixture)
    assert "ending refused" in so
    so, _ = p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "x", "contains", "1250", "--cite", "step:S2",
                       "--expect", "y", "regex", r"cents: \d+", "--cite", "fixture:" + fixture)
    assert p.state()["phase"] == "confirm", so
    so, _ = p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "x", "contains", "1250")
    assert "every --expect needs its own --cite" in so
    print("citations: ok")

    # ---------------- results ----------------
    p = Proj({"main.py": BUGGY})
    p.job()
    rid = p.state()["run_id"]
    good = {"run": rid, "kind": "ending", "ok": True, "all_pass": False, "before": {"rc": 0},
            "ending": {"cmd": "python3 main.py", "tests": None, "expectations": []}}
    line = "REHEARSE-RESULT " + json.dumps(good)
    assert p.bash("cat notes.txt", line) is None and p.state()["phase"] == "look"
    assert p.bash("grep x f | rehearse-other", line) is None and p.state()["phase"] == "look"
    p.bash("rehearse status", "REHEARSE-RESULT " + json.dumps(dict(good, run="other-run")))
    assert p.state()["phase"] == "look"
    out = p.bash("rehearse ending --cmd x | head -5", "first lines only")
    assert "no result recorded for this rehearse command" in text(out)  # nothing was recorded: the command never ran
    p.bash("rehearse ending", line + "\nREHEARSE-RESULT " + json.dumps({"run": rid, "kind": "status", "ok": True}))
    assert p.state()["phase"] == "confirm"  # every result line applies, in order; a later status line changes nothing
    p.bash("cd sub && rehearse ending", "REHEARSE-RESULT {}\n" + line)
    assert p.state()["phase"] == "confirm"
    # rehearse ending / run may take minutes (the program, then the tests): they get the Bash tool's longest timeout
    for cmd in ("rehearse ending --cmd x", "R=/opt/plugin/bin/rehearse\n$R run", "cd sub && rehearse run --as-director",
                "rehearse stage step 'x'"):
        out = p.pre("Bash", command=cmd)
        assert out["hookSpecificOutput"]["updatedInput"]["timeout"] == 600000, (cmd, out)
    assert p.pre("Bash", command="rehearse status") is None and p.pre("Bash", command="python3 run.py") is None
    # The command invoked through an interpreter by path (the executable bit can be lost on a
    # Windows-mounted checkout) is still the plugin command: the program position is the script.
    p = Proj({"main.py": BUGGY})
    p.job()
    rid = p.state()["run_id"]
    p.bash("python3 /opt/plugin/bin/rehearse ending", "REHEARSE-RESULT " + json.dumps(dict(good, run=rid)))
    assert p.state()["phase"] == "confirm"
    # Named through a shell variable (seen when bin/ is not on PATH): the result line still counts.
    p = Proj({"main.py": BUGGY})
    p.job()
    rid = p.state()["run_id"]
    p.bash("R=rehearse; command -v rehearse >/dev/null || R=/opt/plugin/bin/rehearse\n$R ending --cmd x",
           "REHEARSE-RESULT " + json.dumps(dict(good, run=rid)))
    assert p.state()["phase"] == "confirm"
    print("results: ok")

    # ---------------- second activation ----------------
    p = Proj({"main.py": BUGGY, "data.txt": "total: 12\n"})
    p.job()
    first = p.state()
    p.rehearse("fetch", "file://" + p.j("data.txt"))
    p.run("echo 'total: 12'")
    p.prompt("rehearse stop")
    p.job("rehearse fix it again")
    second = p.state()
    assert second["run_id"] != first["run_id"] and second["run_folder"] != first["run_folder"]
    assert second["phase"] == "look" and second["fixtures"] == []
    fx = p.state()["fixtures"] or json.load(open(first["path"]))["fixtures"]
    for cite in ("step:S1", "fixture:" + fx[0], "step:S2"):  # S2 would be the echo of the refused ending
        so, _ = p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "x", "contains", "total: 12", "--cite", cite)
        assert "ending refused" in so and p.state()["phase"] == "look", (cite, so)
    assert denied(p.pre("Edit", file_path=p.j("main.py")))
    print("second activation: ok")

    # ---------------- code change ----------------
    for git in (True, False):
        p = Proj({"main.py": "import json\njson.dump({'n': 10}, open('output.json', 'w'))\nprint('total: 10')\n",
                  "config.yaml": "rate: 1\n"}, git=git)
        p.job()
        p.run("python3 main.py")
        assert os.path.exists(p.j("output.json"))
        p.rehearse(*ENDING)
        assert p.state()["phase"] == "confirm", git
        assert denied(p.pre("Edit", file_path=p.j("config.yaml")))
    p = Proj({"main.py": BUGGY, "config.yaml": "rate: 1\n"}, git=False)
    p.job()
    assert denied(p.pre("Bash", command="sed -i 's/10/12/' main.py"))
    p.rehearse(*ENDING)
    p.prompt("yes")
    p.edit("config.yaml", "rate: 2\n")
    s = p.state()
    assert s["config_edits"][-1]["path"].endswith("config.yaml"), s
    print("code change: ok")

    # ---------------- non-git ----------------
    p = Proj({"main.py": BUGGY, "venv/pyvenv.cfg": "home = /usr\n", "venv/lib/python3/site-packages/pkg.py": "x = 1\n",
              "node_modules/left/index.js": "module.exports = 1\n", "lib/util.py": "y = 1\n"}, git=False)
    fp = F.fingerprint(p.root)
    assert not fp["git"] and sorted(fp["files"]) == ["lib/util.py", "main.py"], fp
    p.job()
    p.write("venv/lib/python3/site-packages/newpkg.py", "z = 1\n")  # what a pip install into the venv leaves
    p.write("node_modules/right/index.js", "module.exports = 2\n")
    assert F.code_change(fp, F.fingerprint(p.root)) == []
    p.rehearse(*ENDING)
    assert p.state()["phase"] == "confirm"
    p.write("lib/util.py", "y = 2\n")
    assert F.code_change(fp, F.fingerprint(p.root)) == ["lib/util.py"]
    print("non-git: ok")

    # ---------------- baseline ----------------
    p = Proj({"main.py": BUGGY, "tests/test_main.py": "def test_ok():\n    assert True\n", ".venv/pyvenv.cfg": "x\n"})
    os.makedirs(p.j(".venv", "bin"))
    os.symlink(sys.executable, p.j(".venv", "bin", "python"))
    p.job()
    p.rehearse(*ENDING)
    b = p.state()["ending"]["baseline"]
    assert b["cmd"] == p.j(".venv", "bin", "python") + " -m pytest" and ("rc" in b or b["note"].startswith("no baseline")), b
    p = Proj({"main.py": BUGGY})
    p.job()
    p.rehearse(*ENDING[:3], "--tests", "no-such-runner-xyz", *ENDING[3:])
    b = p.state()["ending"]["baseline"]
    assert b["note"].startswith("no baseline: ") and "not found" in b["note"], b
    p = Proj({"main.py": BUGGY})
    p.job()
    p.rehearse(*ENDING[:3], "--tests", "sleep 5", *ENDING[3:], REHEARSE_RUN_TIMEOUT="1")
    s = p.state()
    assert s["phase"] == "confirm" and s["ending"]["baseline"]["note"] == "timed out; narrow with --tests", s["ending"]
    p = Proj({"main.py": BUGGY})
    p.job()
    p.rehearse(*ENDING)
    assert p.state()["ending"]["baseline"]["note"] == "no tests found"
    print("baseline: ok")

    # ---------------- log (redaction, kept from 0.7) ----------------
    p = Proj({})
    p.prompt("rehearse fix x")
    p.bash("curl -u me:pw -H 'Authorization: Bearer t0k' https://api.x.com/items?page=2", "a\nAuthorization: Bearer abc")
    p.bash("curl https://me:pw@host/x")
    p.ev("PostToolUseFailure", tool_name="Bash", tool_input={"command": "false"}, error="boom")
    p.ev("PostToolUse", tool_name="Bash", tool_input={"command": "x"}, tool_response=42)
    log = open(os.path.join(p.state()["run_folder"], "log.md")).read()
    assert "-u ***" in log and "Authorization: ***" in log and "https://api.x.com/items?page=2" in log, log
    assert "pw" not in log.replace("://me:***@", "") and "t0k" not in log and "abc" not in log, log
    assert "://me:***@host" in log and "boom" in log and "S4 [goal] $ x" in log
    recs = [json.loads(ln) for ln in open(os.path.join(p.state()["run_folder"], "commands.jsonl"))]
    assert [r["step"] for r in recs] == ["S1", "S2", "S3", "S4"] and all(r["phase"] == "goal" for r in recs)
    print("log: ok")

    # ---------------- tracer (kept from 0.7, re-pointed) ----------------
    def traced(code, d, trace, argv0="-c"):
        env = dict(os.environ, PYTHONPATH=TRACER, REHEARSE_TRACE=trace, REHEARSE_ROOT=d)
        cmd = [sys.executable, "-c", code] if argv0 == "-c" else [sys.executable, argv0]
        return subprocess.run(cmd, cwd=d, env=env, capture_output=True, text=True)

    def events(trace):
        return [json.loads(line) for line in open(trace)] if os.path.exists(trace) else []

    d = tempfile.mkdtemp(dir=TMP)
    j = lambda *q: os.path.join(d, *q)  # noqa: E731
    trace = j(".rehearsal", "trace.jsonl")
    os.makedirs(j(".rehearsal", "scaffold"))
    os.makedirs(j("venv", "lib", "python3", "site-packages"))
    open(j("oldmod.py"), "w").write("def f(x):\n    return x + 1\n\ndef g(i):\n    return i\n")
    open(j(".rehearsal", "scaffold", "helper.py"), "w").write("def h():\n    return 1\n")
    open(j("venv", "lib", "python3", "site-packages", "pkg.py"), "w").write("def p():\n    return 1\n")
    assert traced("import oldmod; oldmod.f(1)", d, trace).returncode == 0
    ev = [e for e in events(trace) if e["func"] == "f"]
    assert [e["t"] for e in ev] == ["call", "return"], ev
    assert ev[0]["file"].endswith("oldmod.py") and ev[0]["args"] == {"x": "1"} and ev[1]["ret"] == "2"
    os.remove(trace)
    code = ("import sys, json; sys.path[:0] = ['.rehearsal/scaffold', 'venv/lib/python3/site-packages']\n"
            "import helper, pkg; helper.h(); pkg.p(); json.dumps({'a': 1})")
    assert traced(code, d, trace).returncode == 0 and events(trace) == []
    os.remove(trace)
    assert traced("import oldmod\nfor i in range(10000): oldmod.g(i)", d, trace).returncode == 0
    assert len(events(trace)) == 2000
    os.remove(trace)
    open(j("loud.py"), "w").write("class Loud:\n    def __repr__(self):\n        print('REPR RAN')\n"
                                  "        return 'Loud()'\n\ndef take(x):\n    return x\n")
    pr = traced("import loud; loud.take(loud.Loud()); print('done')", d, trace)
    assert pr.stdout.strip() == "done" and "<Loud>" in open(trace).read() and "REPR RAN" not in open(trace).read()
    code = "import oldmod; print(oldmod.f(5)); raise SystemExit(3)"
    plain = subprocess.run([sys.executable, "-c", code], cwd=d, capture_output=True, text=True)
    broken = traced(code, d, j(".rehearsal"))  # a directory cannot be opened for append
    assert (broken.returncode, broken.stdout, broken.stderr) == (plain.returncode, plain.stdout, plain.stderr) == (3, "6\n", "")
    # rehearse run shows the trace of the ending's project calls
    p = Proj({"calc.py": "def total(x):\n    return x + 10\n", "main.py": "import calc\nprint('total:', calc.total(0))\n"})
    p.job()
    so, _ = p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "total", "contains", "total: 12",
                       "--cite", "request")
    assert "-> total(x=0) = 10" in so, so
    print("tracer: ok")

    # ---------------- fail open ----------------
    for bad in ("not json", "42", "[]", json.dumps({"tool_name": "Bash", "tool_input": {"command": "x"}})):
        assert hook(bad) is None, bad
    p = Proj({"main.py": BUGGY})
    p.job()
    assert p.ev("SubagentStop") is None  # Stop rules are checked in test_director_checks.py
    assert p.pre("Agent", prompt="x") is None and p.pre("AskUserQuestion", questions=[]) is None
    assert p.ev("PreToolUse", tool_name="Bash", tool_input="not a dict") is None
    assert Proj({}).pre("Bash", command="echo x > main.py") is None  # no run: nothing to gate
    print("fail open: ok")
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print("hooks: all checks passed")
