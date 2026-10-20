"""Self-check for the v3 roles: every instruction file the hook names exists, each worker and director spawn gets
the right instruction text, model and foreground flag for each phase and kind, and manager.md holds the P1 and P4
rules and the required first line.

    python3 tests/test_roles.py

Drives hooks/rehearse_hook.py and bin/rehearse as subprocesses, as tests/test_job.py does. No model calls.
"""
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, "hooks", "rehearse_hook.py")
BIN = os.path.join(ROOT, "bin", "rehearse")
INS = os.path.join(ROOT, "hooks", "instructions")
TMP = os.path.realpath(tempfile.mkdtemp(prefix="rehearse-roles-"))
ENV = {k: v for k, v in os.environ.items()
       if not k.startswith(("CLAUDE_PLUGIN_OPTION_", "REHEARSE_", "EVAL_REHEARSE_"))}
ENV["CLAUDE_PLUGIN_DATA"] = os.path.join(TMP, "plugin-data")
KINDS, HALVES = ("fix", "build"), ("look", "build")


def read(name):
    with open(os.path.join(INS, name), encoding="utf-8") as f:
        return f.read().replace("${CLAUDE_PLUGIN_ROOT}", ROOT).rstrip()


def hook(payload, env=None):
    r = subprocess.run([sys.executable, HOOK], input=json.dumps(payload), text=True, capture_output=True,
                       env=dict(ENV, **(env or {})))
    assert r.returncode == 0 and not r.stderr, (r.returncode, r.stderr)
    return json.loads(r.stdout) if r.stdout.strip() else None


class Job:
    n = 0

    def __init__(self, kind):
        Job.n += 1
        self.sid, self.root = "roles-%d" % Job.n, tempfile.mkdtemp(dir=TMP)
        with open(os.path.join(self.root, "main.py"), "w") as f:
            f.write("print('a: 0')\n")
        self.activation = self.ev("UserPromptSubmit", prompt="rehearse make main.py print a: 1")
        goals = []
        for item in ("purpose", "deliverable", "done", "out_of_scope"):
            goals += ["--goal", item, "assumed", "x"]
        self.rehearse("plan", *goals, "--stage-def", "only", kind, "main.py prints a: 1", "-", "-")
        assert self.state()["phase"] == "look", self.state()["phase"]

    def ev(self, event, env=None, **kw):
        return hook(dict(hook_event_name=event, session_id=self.sid, cwd=self.root, **kw), env)

    def rehearse(self, *args):
        r = subprocess.run([sys.executable, BIN, *args], cwd=self.root, capture_output=True, text=True, env=ENV)
        assert r.returncode == 0, r.stderr
        self.ev("PostToolUse", tool_name="Bash", tool_input={"command": shlex.join(["rehearse", *args])},
                tool_response={"stdout": r.stdout, "stderr": "", "interrupted": False})

    def spawn(self, kind, env=None):
        out = self.ev("PreToolUse", env, tool_name="Agent",
                      tool_input=dict(subagent_type=kind, description="x", prompt="go"))
        return out["hookSpecificOutput"]["updatedInput"]

    def state(self):
        d = os.path.join(ENV["CLAUDE_PLUGIN_DATA"], "sessions", self.sid)
        return json.load(open(os.path.join(d, sorted(n for n in os.listdir(d) if n.endswith(".json"))[-1])))


try:
    # (a) every instruction file the hook names exists, and every plugin path an instruction file names
    src = open(HOOK, encoding="utf-8").read()
    names = set(re.findall(r'instruction\("([\w.-]+\.md)"\)', src))
    assert names == {"manager.md", "worker.md", "director.md", "review.md"}, names
    assert 'instruction("%s-%s.md" % (kind, half))' in src  # the worker's half: kind fix|build, phase look|build
    names |= {"%s-%s.md" % (k, h) for k in KINDS for h in HALVES}
    for name in sorted(names):
        assert os.path.isfile(os.path.join(INS, name)), name
    for name in sorted(os.listdir(INS)):
        for path in re.findall(r"`?(%s/[\w./-]+\.md)" % re.escape(ROOT), read(name)):
            assert os.path.isfile(path), (name, path)
    print("every instruction file the hook names exists: ok")

    # (b) worker spawns per kind and phase, and the director spawn
    for kind in KINDS:
        j = Job(kind)
        ui = j.spawn("rehearse:worker")
        assert ui["prompt"].startswith("[rehearse] stage 1 look\n"), ui["prompt"][:80]
        assert read("worker.md") in ui["prompt"] and read("%s-look.md" % kind) in ui["prompt"], kind
        assert "plan line: main.py prints a: 1" in ui["prompt"] and "instructions pending" not in ui["prompt"]
        assert ui["model"] == "sonnet" and ui["run_in_background"] is False, ui
        assert j.spawn("rehearse:worker", {"CLAUDE_PLUGIN_OPTION_WORKER_MODEL": "haiku"})["model"] == "haiku"
        j.rehearse("ending", "--cmd", "python3 main.py", "--expect", "prints a: 1", "contains", "a: 1",
                   "--cite", "request")
        assert j.state()["phase"] == "confirm", j.state()["phase"]
        j.ev("UserPromptSubmit", prompt="yes")
        assert j.state()["phase"] == "build", j.state()["phase"]
        ui = j.spawn("rehearse:worker")
        assert ui["prompt"].startswith("[rehearse] stage 1 build\n"), ui["prompt"][:80]
        assert read("worker.md") in ui["prompt"] and read("%s-build.md" % kind) in ui["prompt"], kind
        assert "plan line: main.py prints a: 1" in ui["prompt"] and '"cmd": "python3 main.py"' in ui["prompt"]
        assert ui["model"] == "sonnet" and ui["run_in_background"] is False, ui
        ui = j.spawn("rehearse:director")
        assert ui["prompt"].startswith(read("director.md")) and "plan line: main.py prints a: 1" in ui["prompt"]
        assert ui["model"] == "opus" and ui["run_in_background"] is False, ui
        assert j.state()["phase"] == "judge"
        k = Job(kind)  # a worker's stop without the result and without a logged search is held (4.0.0)
        k.rehearse("ending", "--cmd", "python3 main.py", "--expect", "prints a: 1", "contains", "a: 1",
                   "--cite", "request")
        k.ev("UserPromptSubmit", prompt="yes")
        k.spawn("rehearse:worker")
        held = k.ev("SubagentStop", agent_type="rehearse:worker", agent_id="w1", agent_transcript_path="/x",
                    stop_hook_active=False, last_assistant_message="done")
        assert held and held.get("decision") == "block" and "search first" in held["reason"], held
        assert k.state()["phase"] == "build" and k.state()["strikes"] == 0
    for agent, tools in (("worker", ["Agent", "AskUserQuestion"]),
                         ("director", ["Write", "Edit", "MultiEdit", "NotebookEdit", "Agent", "AskUserQuestion"]),
                         ("reviewer", ["Write", "Edit", "MultiEdit", "NotebookEdit", "Agent", "AskUserQuestion"])):
        head = open(os.path.join(ROOT, "agents", agent + ".md"), encoding="utf-8").read().split("---")[1]
        line = re.search(r"(?m)^disallowedTools:(.*)$", head).group(1)
        assert [x.strip() for x in line.split(",")] == tools, (agent, line)
    print("worker and director spawns: the right text, model and foreground per kind and phase: ok")

    # (c) manager.md holds the P1 rule for its own plans and the P4 rule for a plan in the request
    m = read("manager.md")
    for rule in ("When you write the plan yourself, make the stages as coarse as checking allows: a stage boundary "
                 "goes only where reality must be checked before the next step can rely on it, or before an "
                 "irreversible step. Never one action per stage.",
                 "When the request already contains a plan, its steps fix the stages: use them as the stages and add "
                 "`--from-request`. You may only propose merging steps into fewer stages; a merge takes effect only "
                 "when the user says yes to it at job confirmation, and never in an auto job."):
        assert rule in m, rule[:60]
    assert "goal items and assumptions" in m and "four goal items" in read("confirm.md")
    print("manager.md: the P1 and P4 rules: ok")

    # (d) the activation context names the required first line
    a = Job("fix").activation
    text = a["hookSpecificOutput"]["additionalContext"]
    assert "**Your first line of output is exactly:** `Rehearse: job <id>`" in text, text[:300]
    assert re.search(r"\[rehearse\] job \S+ activated", text) and "instructions pending" not in text
    assert "${CLAUDE_PLUGIN_ROOT}" not in text
    print("activation: the first line is Rehearse: job <id>: ok")
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print("roles: all checks passed")
