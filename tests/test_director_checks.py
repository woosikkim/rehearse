"""Self-check for the director, the verdict, the Stop rules and the shortcut findings (story 4).

    python3 tests/test_director_checks.py

Drives hooks/rehearse_hook.py with Claude Code-shaped payloads in scratch projects (git and non-git) under a temp
dir, with CLAUDE_PLUGIN_DATA pointed at that temp dir. Each block prints "<name>: ok".
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
TEXT = open(os.path.join(ROOT, "hooks", "instructions", "director.md"), encoding="utf-8").read().rstrip()

TMP = os.path.realpath(tempfile.mkdtemp(prefix="rehearse-director-"))
DATA = os.path.join(TMP, "plugin-data")
ENV = {k: v for k, v in os.environ.items()
       if not k.startswith(("CLAUDE_PLUGIN_OPTION_", "REHEARSE_"))}
ENV["CLAUDE_PLUGIN_DATA"] = DATA


def hook(payload, **env):
    r = subprocess.run([sys.executable, HOOK], input=json.dumps(payload), text=True, capture_output=True,
                       env=dict(ENV, **env))
    assert r.returncode == 0 and not r.stderr, (r.returncode, r.stderr)
    return json.loads(r.stdout) if r.stdout.strip() else None


def denied(out):
    return bool(out) and out.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


def blocked(out, words=""):
    return bool(out) and out.get("decision") == "block" and words in out["reason"]


DIRECTOR = {"agent_type": "rehearse:director", "agent_id": "a1b2c3"}


class Proj:
    n = 0

    def __init__(self, files, git=True):
        Proj.n += 1
        self.sid = "session-%d" % Proj.n
        self.root = tempfile.mkdtemp(dir=TMP)
        for rel, body in files.items():
            self.write(rel, body)
        if git:
            for a in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "start", "--allow-empty"]):
                subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=self.root,
                               capture_output=True, check=True)

    def j(self, *p):
        return os.path.join(self.root, *p)

    def write(self, rel, body):
        os.makedirs(os.path.dirname(self.j(rel)), exist_ok=True)
        with open(self.j(rel), "w") as f:
            f.write(body)

    def ev(self, event, env=None, **kw):
        return hook(dict(hook_event_name=event, session_id=self.sid, cwd=self.root, **kw), **(env or {}))

    def stop(self, **env):
        return self.ev("Stop", env, stop_hook_active=False)

    def pre(self, tool, who=None, env=None, **tin):
        return self.ev("PreToolUse", env, tool_name=tool, tool_input=tin, **(who or {}))

    def bash(self, cmd, stdout="", who=None):
        return self.ev("PostToolUse", tool_name="Bash", tool_input={"command": cmd},
                       tool_response={"stdout": stdout, "stderr": "", "interrupted": False}, **(who or {}))

    def edit(self, rel, body):
        out = self.pre("Edit", file_path=self.j(rel))
        assert not denied(out), out
        self.write(rel, body)
        return self.ev("PostToolUse", tool_name="Edit", tool_input={"file_path": self.j(rel)}, tool_response={})

    def rehearse(self, *args, who=None):
        r = subprocess.run([sys.executable, BIN, *args], cwd=self.root, capture_output=True, text=True, env=ENV)
        assert r.returncode == 0, r.stderr
        return self.bash(shlex.join(["rehearse", *args]), r.stdout, who)

    def spawn(self, env=None, kind="rehearse:director"):
        return self.pre("Agent", env=env, subagent_type=kind, description="judge", prompt="judge the fix")

    def verdict(self, text, agent_type="rehearse:director"):
        return self.ev("SubagentStop", agent_type=agent_type, agent_id="a1b2c3", agent_transcript_path="/x",
                       stop_hook_active=False, last_assistant_message=text)

    def state(self):
        d = os.path.join(DATA, "sessions", self.sid)
        names = sorted(n for n in os.listdir(d) if n.endswith(".json")) if os.path.isdir(d) else []
        return json.load(open(os.path.join(d, names[-1]))) if names else None

    def set(self, **kw):
        s = self.state()
        s.update(kw)
        json.dump(s, open(s["path"], "w"))

    def report(self, line):
        with open(os.path.join(self.state()["run_folder"], "report.md"), "w") as f:
            f.write(line + "\n\nbody\n")

    def findings(self):
        return json.load(open(os.path.join(self.state()["run_folder"], "findings.json")))


BUGGY = "print('total: 10')\n"
FIXED = "print('total: 12')\n"
ENDING = ["ending", "--cmd", "python3 main.py", "--expect", "prints the right total", "contains", "total: 12",
          "--cite", "request"]
PASS = 'Checked everything.\n{"verdict": "PASS", "findings": [], "extra_inputs": [], "tests": {"now": "ok"}}'
REWORK = '{"verdict": "REWORK", "findings": ["only the sample input is handled"], "extra_inputs": [], "tests": {}}'


def in_confirm(git=True, files=None):
    p = Proj(dict({"main.py": BUGGY}, **(files or {})), git=git)
    p.ev("UserPromptSubmit", prompt="rehearse fix the report; it should print total: 12")
    p.rehearse(*ENDING)
    assert p.state()["phase"] == "confirm", p.state()["phase"]
    return p


def in_work(**kw):
    p = in_confirm(**kw)
    p.ev("UserPromptSubmit", prompt="yes")
    assert p.state()["phase"] == "work"
    return p


def rejected_three_times():
    p = in_work()
    for n in range(3):
        p.spawn()
        p.verdict(REWORK, agent_type="director" if n == 1 else "rehearse:director")
    return p


try:
    # ---------------- spawn ----------------
    p = in_work()
    out = p.spawn()
    ui = out["hookSpecificOutput"]["updatedInput"]
    s = p.state()
    assert ui["prompt"].startswith(TEXT) and s["run_folder"] in ui["prompt"], ui["prompt"][-400:]
    assert "findings.json" in ui["prompt"] and s["root"] in ui["prompt"]
    assert ui["model"] == "opus" and ui["subagent_type"] == "rehearse:director", ui
    assert s["phase"] == "judge" and s["spawn_fingerprint"] and "main.py" not in str(s["spawn_fingerprint"]["files"])
    assert p.spawn({"REHEARSE_DIRECTOR_MODEL": "sonnet"})["hookSpecificOutput"]["updatedInput"]["model"] == "sonnet"
    both = {"REHEARSE_DIRECTOR_MODEL": "sonnet", "CLAUDE_PLUGIN_OPTION_DIRECTOR_MODEL": "haiku"}
    assert p.spawn(both)["hookSpecificOutput"]["updatedInput"]["model"] == "haiku"
    assert p.spawn(kind="director")["hookSpecificOutput"]["updatedInput"]["prompt"].startswith(TEXT)
    assert p.pre("Agent", subagent_type="general-purpose", prompt="x") is None
    print("spawn: ok")

    # ---------------- verdict ----------------
    p = in_work()
    p.edit("main.py", FIXED)
    p.spawn()
    before = p.state()
    p.verdict(PASS, agent_type="rehearse:rehearser")  # a foreign agent changes nothing
    after = p.state()
    assert (after["phase"], after["verdicts"], after["rejections"]) == ("judge", [], 0), after["phase"]
    p.verdict(PASS)
    s = p.state()
    assert s["phase"] == "done.passed" and s["verdicts"][-1]["verdict"] == "PASS" and s["pass_fingerprint"]
    p.write("main.py", "print('total: 13')\n")  # a code change after PASS, seen at the next hook call
    p.pre("Bash", command="ls")
    assert p.state()["phase"] == "work", p.state()["phase"]

    p = in_work()
    p.spawn()
    p.verdict("not quite.\n" + REWORK)
    s = p.state()
    assert s["phase"] == "work" and s["rejections"] == 1 and s["findings"] == ["only the sample input is handled"]

    p = in_work(git=False)
    p.spawn()
    p.write("main.py", FIXED)  # changed between spawn and stop
    p.verdict(PASS)
    s = p.state()
    assert s["phase"] == "work" and "void" in s["verdicts"][-1] and "main.py" in s["verdicts"][-1]["void"], s

    p = rejected_three_times()
    s = p.state()
    assert s["phase"] == "done.not_fixed" and s["rejections"] == 3 and s["report_pending"], s["phase"]
    print("verdict: ok")

    # ---------------- stop matrix ----------------
    assert Proj({}).stop() is None  # no run
    p = in_work()
    p.edit("main.py", FIXED)
    p.rehearse("run")
    p.spawn()
    assert blocked(p.stop(), "next: spawn rehearse:director")  # judge
    p.verdict(PASS)
    assert p.stop() is None  # done.passed
    p.report("fixed: the total is 12 now")
    assert p.stop() is None  # verified by rehearse run
    p.report("looks good")
    assert blocked(p.stop(), "write report.md starting with fixed / built, not verified")

    p = rejected_three_times()
    assert blocked(p.stop(), 'write report.md starting with "not fixed"')
    p.report("fixed")
    assert blocked(p.stop(), '"not fixed"')
    p.report("not fixed: the total still comes from the cached copy")
    assert p.stop() is None

    p = in_confirm()
    assert p.stop() is None  # confirm, attended (the default)
    assert blocked(p.stop(REHEARSE_CONFIRM_ENDING="false"), "next: spawn rehearse:director")
    assert blocked(p.stop(CLAUDE_PLUGIN_OPTION_CONFIRM_ENDING="false"), "next:")
    p.ev("UserPromptSubmit", prompt="rehearse stop")
    assert p.stop() is None  # done.cancelled

    p = Proj({"main.py": BUGGY})
    p.ev("UserPromptSubmit", prompt="rehearse fix the report; it should print total: 12")
    out = p.stop()
    assert blocked(out, "next: register an ending with rehearse ending") and "phase observe" in out["reason"], out
    p = in_work()
    assert blocked(p.stop(), "next: spawn rehearse:director")
    p.set(phase="rework-observe")
    assert blocked(p.stop(), "next: spawn rehearse:director")

    for phase in ("work", "judge"):  # the report rule: "fixed" with an expectation not verified
        p = in_work()
        if phase == "judge":
            p.spawn()
        p.report("fixed")
        assert blocked(p.stop(), "say built, not verified against the real target"), phase
        p.report("built, not verified against the real target: no credentials here")
        assert blocked(p.stop(), "next: spawn rehearse:director"), phase

    p = in_confirm()  # stop here, from the confirmation answer
    p.ev("UserPromptSubmit", prompt="stop here and write the report")
    assert p.state()["stop_here"] and p.state()["phase"] == "confirm"
    assert blocked(p.stop(), '"not fixed"')
    p.report("not fixed: stopped before the change, at the user's request")
    assert p.stop() is None and p.state()["phase"] == "done.not_fixed"

    p = in_work()  # stop here, from an AskUserQuestion answer
    p.ev("PostToolUse", tool_name="AskUserQuestion", tool_input={"questions": []},
         tool_response={"questions": [], "answers": {"Go on?": "Stop here and write the report"}, "annotations": {}})
    assert p.state()["stop_here"]
    assert blocked(p.stop(), '"not fixed"')
    stage = subprocess.Popen(["sleep", "60"])
    with open(os.path.join(p.state()["run_folder"], "stage.pid"), "w") as f:
        f.write("%d\n" % stage.pid)
    p.report("not fixed: what is known is in the log")
    assert p.stop() is None and p.state()["phase"] == "done.not_fixed"
    assert stage.wait(10) == -15  # an allowed Stop kills the stage
    print("stop matrix: ok")

    # ---------------- director edits ----------------
    p = in_work()
    p.spawn()
    assert denied(p.pre("Write", who=DIRECTOR, file_path=p.j("main.py"), content=FIXED))
    assert denied(p.pre("Edit", who=DIRECTOR, file_path=p.j("main.py"), old_string="10", new_string="12"))
    assert p.pre("Write", who=DIRECTOR, file_path=os.path.join(TMP, "notes.txt"), content="x") is None
    assert p.pre("Bash", who=DIRECTOR, command="ls") is None
    p.rehearse("run", "--as-director", who=DIRECTOR)
    s = p.state()
    assert s["director_runs"][-1]["agent_type"] == "rehearse:director" and s["rounds"] == [] and s["phase"] == "judge"
    p.write("main.py", FIXED)  # the director changed code through the shell
    p.verdict(PASS)
    assert p.state()["phase"] == "work" and "void" in p.state()["verdicts"][-1]
    print("director edits: ok")

    # ---------------- shortcut findings ----------------
    tests = {"tests/test_main.py": "def test_total():\n    assert True\n",
             "tests/test_other.py": "import pytest\n\ndef test_other():\n    assert True\n"}
    for git in (True, False):
        p = in_work(git=git, files=tests)
        os.remove(p.j("tests/test_main.py"))
        assert p.pre("Bash", command="rm tests/test_main.py") is None
        if git:
            p.edit("tests/test_other.py", "import pytest\n\n@pytest.mark.skip\ndef test_other():\n    assert True\n")
        else:
            assert not denied(p.pre("Write", file_path=p.j("tests/test_new.py")))
            p.write("tests/test_new.py", "import pytest\n\n@pytest.mark.skip\ndef test_new():\n    pass\n")
        assert blocked(p.stop(), "next: spawn rehearse:director")
        f = {x["kind"]: x["items"] for x in p.findings()["findings"]}
        assert {"path": "tests/test_main.py", "status": "deleted"} in f["test files changed or deleted"], f
        assert any(i["line"] == "@pytest.mark.skip" for i in f["skip markers added"]), f
    print("shortcuts: ok")

    # ---------------- baseline ----------------
    s = p.state()
    base = s["ending"]["baseline"]
    assert base and base.get("cmd") and p.findings()["baseline"] == base, (base, p.findings())
    assert "stored at registration" in TEXT and "baseline" in TEXT and "timed out" in TEXT
    print("baseline: ok")
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print("director: all checks passed")
