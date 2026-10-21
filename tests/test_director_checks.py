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
       if not k.startswith(("CLAUDE_PLUGIN_OPTION_", "REHEARSE_", "EVAL_REHEARSE_"))}
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

    def start(self, env=None):
        """Activate and record a one-stage plan: the job is in look."""
        self.ev("UserPromptSubmit", env, prompt="rehearse fix the report; it should print total: 12")  # the mode is fixed here
        self.rehearse(*PLAN, env=env)
        assert self.state()["phase"] == "look", self.state()["phase"]

    def ev(self, event, env=None, **kw):
        return hook(dict(hook_event_name=event, session_id=self.sid, cwd=self.root, **kw), **(env or {}))

    def stop(self, **env):
        return self.ev("Stop", env, stop_hook_active=False)

    def pre(self, tool, who=None, env=None, **tin):
        return self.ev("PreToolUse", env, tool_name=tool, tool_input=tin, **(who or {}))

    def bash(self, cmd, stdout="", who=None, env=None):
        return self.ev("PostToolUse", env, tool_name="Bash", tool_input={"command": cmd},
                       tool_response={"stdout": stdout, "stderr": "", "interrupted": False}, **(who or {}))

    def edit(self, rel, body):
        out = self.pre("Edit", file_path=self.j(rel))
        assert not denied(out), out
        self.write(rel, body)
        return self.ev("PostToolUse", tool_name="Edit", tool_input={"file_path": self.j(rel)}, tool_response={})

    def rehearse(self, *args, who=None, env=None):
        r = subprocess.run([sys.executable, BIN, *args], cwd=self.root, capture_output=True, text=True, env=ENV)
        assert r.returncode == 0, r.stderr
        return r.stdout, self.bash(shlex.join(["rehearse", *args]), r.stdout, who, env)

    def spawn(self, env=None, kind="rehearse:director"):
        return self.pre("Agent", env=env, subagent_type=kind, description="judge", prompt="judge the fix")

    def verdict(self, text, agent_type="rehearse:director", env=None):
        return self.ev("SubagentStop", env, agent_type=agent_type, agent_id="a1b2c3", agent_transcript_path="/x",
                       stop_hook_active=False, last_assistant_message=text)

    def state(self):
        d = os.path.join(DATA, "sessions", self.sid)
        names = sorted(n for n in os.listdir(d) if n.endswith(".json")) if os.path.isdir(d) else []
        return json.load(open(os.path.join(d, names[-1]))) if names else None

    def report(self, line):
        with open(os.path.join(self.state()["run_folder"], "report.md"), "w") as f:
            f.write(line + "\n\nbody\n\n## Not verified\nnone\n")

    def findings(self):
        return json.load(open(os.path.join(self.state()["run_folder"], "findings.json")))


BUGGY = "print('total: 10')\n"
FIXED = "print('total: 12')\n"
ENDING = ["ending", "--cmd", "python3 main.py", "--expect", "prints the right total", "contains", "total: 12",
          "--cite", "request"]
PASS = 'Checked everything.\n{"verdict": "PASS", "findings": [], "extra_inputs": [], "tests": {"now": "ok"}}'
PLAN = ["plan", "--goal", "purpose", "assumed", "the job works", "--goal", "deliverable", "assumed", "the program",
        "--goal", "done", "assumed", "the ending passes", "--goal", "out_of_scope", "assumed", "nothing else",
        "--stage-def", "only", "fix", "do the job", "-", "-"]
REWORK = '{"verdict": "REWORK", "findings": ["only the sample input is handled"], "extra_inputs": [], "tests": {}}'


def in_confirm(git=True, files=None):
    p = Proj(dict({"main.py": BUGGY}, **(files or {})), git=git)
    p.start()
    p.rehearse(*ENDING)
    assert p.state()["phase"] == "confirm", p.state()["phase"]
    return p


def in_work(**kw):
    p = in_confirm(**kw)
    p.ev("UserPromptSubmit", prompt="yes")
    assert p.state()["phase"] == "build"
    return p


def rejected_three_times(env=None):
    if env:  # headless from activation: the ending is accepted at registration, so the job is in build at once
        p = Proj({"main.py": BUGGY})
        p.start(env)
        p.rehearse(*ENDING, env=env)
        assert p.state()["phase"] == "build", p.state()["phase"]
    else:
        p = in_work()
    for n in range(3):
        p.spawn()
        p.verdict(REWORK, env=env)
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
    assert ui["run_in_background"] is False, ui  # the agent waits for the verdict instead of polling
    assert s["phase"] == "judge" and s["spawn_fingerprint"] and "main.py" not in str(s["spawn_fingerprint"]["files"])
    assert p.spawn({"REHEARSE_DIRECTOR_MODEL": "sonnet"})["hookSpecificOutput"]["updatedInput"]["model"] == "sonnet"
    both = {"REHEARSE_DIRECTOR_MODEL": "sonnet", "CLAUDE_PLUGIN_OPTION_DIRECTOR_MODEL": "haiku"}
    assert p.spawn(both)["hookSpecificOutput"]["updatedInput"]["model"] == "haiku"
    assert p.spawn(kind="director") is None  # only the namespaced rehearse:director is the plugin's director
    assert p.pre("Agent", subagent_type="general-purpose", prompt="x") is None
    print("spawn: ok")

    # ---------------- verdict ----------------
    p = in_work()
    p.edit("main.py", FIXED)
    p.spawn()
    before = p.state()
    p.verdict(PASS, agent_type="rehearse:rehearser")  # a foreign agent changes nothing
    after = p.state()
    assert (after["phase"], after["verdicts"], len(after["strike_log"])) == ("judge", [], 0), after["phase"]
    p.verdict(PASS)
    s = p.state()
    assert s["phase"] == "done.passed" and s["verdicts"][-1]["verdict"] == "PASS"

    p = in_work()
    p.spawn()
    p.verdict("not quite.\n" + REWORK)
    assert "next: build stage 1" in p.rehearse("job")[0]  # what to do now, from the command
    s = p.state()
    assert s["phase"] == "build" and len(s["strike_log"]) == 1 and s["findings"] == ["only the sample input is handled"]

    p = in_work(git=False)
    p.spawn()
    p.write("main.py", FIXED)  # changed between spawn and stop
    p.verdict(PASS)
    s = p.state()
    assert s["phase"] == "build" and "void" in s["verdicts"][-1] and "main.py" in s["verdicts"][-1]["void"], s

    p = rejected_three_times({"REHEARSE_CONFIRM_ENDING": "0"})
    s = p.state()
    assert s["phase"] == "build" and len(s["strike_log"]) == 3, s["phase"]  # a count is never failure (4.0.0)
    print("verdict: ok")

    # ---------------- stop matrix ----------------
    assert Proj({}).stop() is None  # no run
    p = in_work()
    p.edit("main.py", FIXED)
    p.rehearse("run")
    p.spawn()
    assert blocked(p.stop(), "next: spawn rehearse:director")  # judge
    p.verdict(PASS)
    p.report("looks good")
    assert blocked(p.stop(), "write report.md starting with fixed / built, not verified")
    p.report("fixed: the total is 12 now")
    assert p.stop() is None and p.state()["closed"]  # verified by rehearse run; the run is over
    p.edit("main.py", FIXED + "# later, unrelated\n")  # a closed run does not come back on a later edit
    assert p.stop() is None and p.state()["phase"] == "done.passed"

    p = rejected_three_times({"REHEARSE_CONFIRM_ENDING": "0"})  # headless, still in build after three REWORKs
    assert blocked(p.stop(), "spawn rehearse:director")
    p.report("fixed")
    assert blocked(p.stop(), "not verified")
    p.report("not fixed: the total still comes from the cached copy\n\n## Not verified\nthe total\n")
    assert p.stop() is None and p.state()["phase"] == "done.not_fixed"  # the honest give-up

    p = in_confirm()
    assert p.stop() is None  # confirm, attended (the default)
    p.ev("UserPromptSubmit", prompt="rehearse stop")
    assert p.stop() is None  # done.cancelled

    p = Proj({"main.py": BUGGY})
    p.start()
    out = p.stop()
    assert blocked(out, "next: look at stage 1") and "phase look" in out["reason"], out
    p = in_work()
    assert blocked(p.stop(), "next: spawn rehearse:director")

    for phase in ("work", "judge"):  # the report rule: "fixed" with an expectation not verified
        p = in_work()
        if phase == "judge":
            p.spawn()
        p.report("fixed")
        assert blocked(p.stop(), "say built, not verified against the real target"), phase
        p.report("built, not verified against the real target: no credentials here")
        assert blocked(p.stop(), "next: spawn rehearse:director"), phase

    p = in_work()  # an honest give-up ends the job only when nobody can answer (headless, fixed at activation)
    p.report("not fixed: the sandbox hides the tool, nothing was changed")
    assert blocked(p.stop(), "next:")  # ask: the user has "stop here"; the agent does not
    assert blocked(p.stop(EVAL_REHEARSE_CONFIRM_ENDING="0"), "next:")  # a variable set later changes nothing
    for make in (lambda: rejected_three_times({"EVAL_REHEARSE_CONFIRM_ENDING": "0"}), None):
        p = Proj({"main.py": BUGGY})
        p.start({"EVAL_REHEARSE_CONFIRM_ENDING": "0"})
        p.report("not fixed: the sandbox hides the tool, nothing was changed")
        assert p.stop() is None and p.state()["phase"] == "done.not_fixed"
        break

    p = in_work()  # the loop breaker rounds setting is read where it is used
    p.edit("main.py", "print('total: 11')\n")
    p.rehearse("run", env={"REHEARSE_LOOP_BREAKER_ROUNDS": "1"})
    assert p.state()["phase"] == "look" and len(p.state()["relocks"]) == 1, p.state()["phase"]

    p = Proj({"main.py": BUGGY})  # the run folder deleted mid-job: decisions read the data folder, the copy comes back
    p.start()
    folder = p.state()["run_folder"]
    shutil.rmtree(folder)
    assert blocked(p.stop(), "next: look at stage 1")
    assert json.load(open(os.path.join(folder, "state.json")))["run_id"] == p.state()["run_id"]
    with open(os.path.join(folder, "state.json"), "w") as f:  # an edited copy changes no decision
        f.write(json.dumps(dict(p.state(), phase="done.passed")))
    assert blocked(p.stop(), "next: look at stage 1")

    p = Proj({"main.py": BUGGY})  # a hook bug fails open, leaves a traceback, tells the user
    p.ev("UserPromptSubmit", prompt="rehearse fix the report; it should print total: 12")
    s = p.state()
    del s["phase"]
    json.dump(s, open(s["path"], "w"))
    out = p.stop()
    assert out and "hook error" in out.get("systemMessage", "") and "hook-errors.log" in out["systemMessage"], out
    assert "KeyError" in open(os.path.join(DATA, "hook-errors.log")).read()

    p = in_confirm()  # stop here, from the confirmation answer: the words decide nothing; rehearse wait does (3.0.1)
    p.ev("UserPromptSubmit", prompt="stop here and write the report")
    assert not p.state().get("stop_here") and p.state()["phase"] == "look"
    p.rehearse("wait", "--stop-here")
    assert p.state()["stop_here"]
    assert blocked(p.stop(), '"not fixed"')
    p.report("not fixed: stopped before the change, at the user's request")
    assert p.stop() is None and p.state()["phase"] == "done.not_fixed"

    p = in_work()  # stop here, from an AskUserQuestion answer while building: recorded by the command alone
    p.ev("PostToolUse", tool_name="AskUserQuestion", tool_input={"questions": []},
         tool_response={"questions": [], "answers": {"Go on?": "Stop here and write the report"}, "annotations": {}})
    assert not p.state().get("stop_here") and p.state()["phase"] == "build"
    p.rehearse("wait", "--stop-here")
    assert p.state()["stop_here"]
    assert blocked(p.stop(), '"not fixed"')
    p.report("not fixed: what is known is in the log")
    assert p.stop() is None and p.state()["phase"] == "done.not_fixed"
    print("stop matrix: ok")

    # ---------------- director runs ----------------
    p = in_work()
    p.spawn()
    assert p.pre("Bash", who=DIRECTOR, command="ls") is None
    p.rehearse("run", "--as-director", who=DIRECTOR)
    s = p.state()
    assert s["director_runs"][-1]["agent_type"] == "rehearse:director" and s["runs"] == [] and s["phase"] == "judge"
    p.write("main.py", FIXED)  # the director changed code through the shell
    p.verdict(PASS)
    assert p.state()["phase"] == "build" and "void" in p.state()["verdicts"][-1]
    print("director runs: ok")

    # ---------------- confirmation via question ----------------
    def ask(p, answer):
        return p.ev("PostToolUse", tool_name="AskUserQuestion", tool_input={"questions": []},
                    tool_response={"questions": [], "answers": {"Is this the ending?": answer}, "annotations": {}})
    p = in_confirm()
    ask(p, "Not quite, the total should include tax")
    s = p.state()
    assert s["phase"] == "look" and s["confirmation"]["answer"].startswith("Not quite") \
        and not s["confirmation"]["affirmative"] and not s.get("stop_here"), s["confirmation"]
    p.rehearse(*ENDING)  # registered again after the no, then confirmed
    ask(p, " Yes ")
    s = p.state()
    assert s["phase"] == "build" and s["confirmation"]["affirmative"] and s["confirmation"]["by"] == "user"
    p = in_confirm()
    ask(p, "Stop here and write the report")  # not a yes: back to look; the stop is recorded by the command
    assert not p.state().get("stop_here") and p.state()["phase"] == "look"
    p.rehearse("wait", "--stop-here")
    assert p.state()["stop_here"]
    print("confirmation via question: ok")

    # ---------------- unattended: the ending is accepted at registration ----------------
    UN = {"REHEARSE_CONFIRM_ENDING": "false"}
    p = Proj({"main.py": BUGGY})
    p.start(UN)
    _, out = p.rehearse(*ENDING, env=UN)
    s = p.state()
    assert s["phase"] == "build" and s["confirmation"]["by"] == "auto" and s["confirmation"]["affirmative"], s
    assert "not confirmed by a person" in json.dumps(out), out
    assert blocked(p.stop(**UN), "next: spawn rehearse:director")
    print("unattended: ok")

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
