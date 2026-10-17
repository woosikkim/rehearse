"""Self-check for the v3 job: goal and plan, stages, locks and outputs, the run counter, reopening, stuck, end to end.

    python3 tests/test_job.py

Drives hooks/rehearse_hook.py and bin/rehearse as subprocesses with Claude Code-shaped payloads in scratch
projects under a temp dir, CLAUDE_PLUGIN_DATA pointed there. No model calls. Each block prints "<name>: ok".
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
sys.path.insert(0, os.path.join(ROOT, "hooks"))
import fingerprint as F  # noqa: E402
import findings as FD  # noqa: E402

TMP = os.path.realpath(tempfile.mkdtemp(prefix="rehearse-job-"))
DATA = os.path.join(TMP, "plugin-data")
ENV = {k: v for k, v in os.environ.items()
       if not k.startswith(("CLAUDE_PLUGIN_OPTION_", "REHEARSE_", "EVAL_REHEARSE_"))}
ENV["CLAUDE_PLUGIN_DATA"] = DATA
UN = {"REHEARSE_CONFIRM_ENDING": "0"}
WORKER = {"agent_type": "rehearse:worker", "agent_id": "w1"}
DIRECTOR = {"agent_type": "rehearse:director", "agent_id": "d1"}
PASS = '{"verdict": "PASS", "findings": [], "extra_inputs": [], "tests": {}}'
REWORK = '{"verdict": "REWORK", "findings": ["only the sample"], "extra_inputs": [], "tests": {}}'


def hook(payload, env=None):
    r = subprocess.run([sys.executable, HOOK], input=json.dumps(payload), text=True, capture_output=True,
                       env=dict(ENV, **(env or {})))
    assert r.returncode == 0 and not r.stderr, (r.returncode, r.stderr)
    return json.loads(r.stdout) if r.stdout.strip() else None


def text(out):
    return json.dumps(out, ensure_ascii=False) if out else ""


def denied(out):
    return bool(out) and out.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


def blocked(out, words=""):
    return bool(out) and out.get("decision") == "block" and words in out["reason"]


def ctx(out):
    return (out or {}).get("hookSpecificOutput", {}).get("additionalContext", "")


def goals(src="assumed"):
    out = []
    for item, value in (("purpose", "the job works"), ("deliverable", "the program"), ("done", "the ending passes"),
                        ("out_of_scope", "nothing else")):
        out += ["--goal", item, src, value]
    return out


class Proj:
    n = 0

    def __init__(self, files, git=True):
        Proj.n += 1
        self.sid = "job-session-%d" % Proj.n
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

    def ev(self, event, env=None, who=None, **kw):
        return hook(dict(hook_event_name=event, session_id=self.sid, cwd=self.root, **kw, **(who or {})), env)

    def prompt(self, t, env=None):
        return self.ev("UserPromptSubmit", env, prompt=t)

    def pre(self, tool, who=None, env=None, **tin):
        return self.ev("PreToolUse", env, who, tool_name=tool, tool_input=tin)

    def bash(self, cmd, stdout="", who=None, env=None):
        return self.ev("PostToolUse", env, who, tool_name="Bash", tool_input={"command": cmd},
                       tool_response={"stdout": stdout, "stderr": "", "interrupted": False})

    def edit(self, rel, body, who=None, env=None):
        path = rel if os.path.isabs(rel) else self.j(rel)
        out = self.pre("Edit", who, env, file_path=path)
        if denied(out):
            return out
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(body)
        return self.ev("PostToolUse", env, who, tool_name="Edit", tool_input={"file_path": path}, tool_response={})

    def rehearse(self, *args, who=None, env=None):
        r = subprocess.run([sys.executable, BIN, *args], cwd=self.root, capture_output=True, text=True,
                           env=dict(ENV, **(env or {})))
        assert r.returncode == 0, r.stderr
        return r.stdout, self.bash(shlex.join(["rehearse", *args]), r.stdout, who, env)

    def result(self, kind, who=None, **kw):
        """A REHEARSE-RESULT line the hook reads, for commands whose real run needs more than a test can give."""
        line = "REHEARSE-RESULT " + json.dumps(dict(run=self.state()["run_id"], kind=kind, **kw))
        return self.bash("rehearse " + kind, line, who)

    def spawn(self, kind="rehearse:director", env=None, prompt="go"):
        return self.pre("Agent", None, env, subagent_type=kind, description="x", prompt=prompt)

    def returned(self, kind="rehearse:director", env=None):
        """The worker or director stops (SubagentStop), then its Agent call returns to the manager (PostToolUse)."""
        who = DIRECTOR if kind == "rehearse:director" else WORKER
        self.ev("SubagentStop", env, who, agent_transcript_path="/x", stop_hook_active=False,
                last_assistant_message="done")
        return self.ev("PostToolUse", env, tool_name="Agent", tool_input={"subagent_type": kind, "prompt": "x"},
                       tool_response={"content": "done"})

    def verdict(self, v, env=None):
        self.ev("SubagentStop", env, DIRECTOR, agent_transcript_path="/x", stop_hook_active=False,
                last_assistant_message=v)
        return self.ev("PostToolUse", env, tool_name="Agent", tool_input={"subagent_type": "rehearse:director"},
                       tool_response={"content": v})

    def ask(self, answer, env=None):
        return self.ev("PostToolUse", env, tool_name="AskUserQuestion", tool_input={"questions": []},
                       tool_response={"questions": [], "answers": {"Q?": answer}, "annotations": {}})

    def stop(self, env=None):
        return self.ev("Stop", env, stop_hook_active=False)

    def report(self, body):
        with open(os.path.join(self.state()["run_folder"], "report.md"), "w") as f:
            f.write(body)

    def state(self):
        d = os.path.join(DATA, "sessions", self.sid)
        names = sorted(n for n in os.listdir(d) if n.endswith(".json")) if os.path.isdir(d) else []
        return json.load(open(os.path.join(d, names[-1]))) if names else None

    def phase(self):
        return self.state()["phase"]

    def run_collect(self):
        subprocess.run([sys.executable, "collect.py"], cwd=self.root, capture_output=True)


# ---- a one-stage job whose ending has three expectations, so the number failing can be steered
LINES = ["a: 1", "b: 2", "c: 3"]
REQ3 = "rehearse fix main.py; it should print a: 1 b: 2 c: 3"
PLAN1 = ["plan"] + goals() + ["--stage-def", "only", "fix", "print the three lines", "-", "-"]
END3 = ["ending", "--cmd", "python3 main.py"]
for _v in LINES:
    END3 += ["--expect", _v, "contains", _v, "--cite", "request"]


def prog(passing):
    return "".join("print(%r)\n" % v for v in LINES[:passing]) or "pass\n"


def one_stage(env=None, files=None):
    p = Proj(dict({"main.py": prog(0)}, **(files or {})))
    p.prompt(REQ3, env)
    p.rehearse(*PLAN1, env=env)
    assert p.phase() == "look", p.phase()
    return p


def building(env=None, files=None):
    p = one_stage(env, files)
    p.rehearse(*END3, env=env)
    if p.phase() == "confirm":
        p.prompt("yes")
    assert p.phase() == "build" and p.state()["fewest_failing"] == 3, p.phase()
    return p


def fail(p, n, env=None, who=None):
    """Edit main.py so that n expectations fail, then rehearse run."""
    fail.n = getattr(fail, "n", 0) + 1
    p.edit("main.py", prog(3 - n) + "# try %d\n" % fail.n, who, env)  # every try changes the code
    return p.rehearse("run", who=who, env=env)[1]


def relocked(env=None):
    p = building(env)
    fail(p, 3, env)
    fail(p, 3, env)
    assert p.phase() == "look" and len(p.state()["relocks"]) == 1, p.phase()
    return p


# ---- a two-stage job: collect (writes out/items.md) then draft (writes drafts/summary.md)
REQ2 = "rehearse collect the items (items: 3) and write the draft (summary: done)"
PLAN2 = ["plan"] + goals() + ["--stage-def", "collect", "build", "collect the items", "-", "out/items.md",
                              "--stage-def", "draft", "build", "write the draft", "out/items.md", "drafts/summary.md"]
JOB_END = ["ending", "--job", "--cmd", "cat drafts/summary.md", "--expect", "draft", "contains", "summary: done",
           "--cite", "request", "--unchecked", "the draft reads well"]
S1_END = ["ending", "--cmd", "python3 collect.py", "--expect", "items", "contains", "items: 3", "--cite", "request"]
S2_END = ["ending", "--cmd", "grep summary drafts/summary.md", "--expect", "draft", "contains", "summary: done",
          "--cite", "request"]
COLLECT = "import os\nos.makedirs('out', exist_ok=True)\nopen('out/items.md', 'w').write('x\\ny\\nz\\n')\n" \
          "print('items: 3')\n"


def two_stage(env=None):
    p = Proj({"README.txt": "x\n"})
    p.prompt(REQ2, env)
    p.rehearse(*PLAN2, env=env)
    assert p.phase() == "goal", p.phase()
    p.rehearse(*JOB_END, env=env)
    if p.phase() == "job-confirm":
        p.prompt("yes")
    assert p.phase() == "look" and p.state()["stage"] == 1, p.phase()
    return p


def pass_stage(p, end, build, director_run=False):
    """From look: register the stage ending, confirm, build, director PASS (after its own passing run)."""
    p.rehearse(*end)
    if p.phase() == "confirm":
        p.prompt("yes")
    assert p.phase() == "build", p.phase()
    build(p)
    p.spawn()
    if director_run:
        p.rehearse("run", "--as-director", who=DIRECTOR)
        assert p.state()["director_runs"][-1]["all_pass"]
    return p.verdict(PASS)


def stage1_passed(env=None):
    p = two_stage(env)
    pass_stage(p, S1_END, lambda p: (p.edit("collect.py", COLLECT), p.run_collect()))
    assert p.phase() == "look" and p.state()["stage"] == 2, p.phase()
    return p


def final_stage(env=None):
    p = stage1_passed(env)
    pass_stage(p, S2_END, lambda p: p.edit("drafts/summary.md", "summary: done\n"), director_run=True)
    assert p.phase() == "build" and p.state()["stage"] == 3, p.phase()
    return p


try:
    # ================= goal and plan =================
    p = Proj({"main.py": prog(0)})
    p.prompt(REQ3)
    p.prompt("it is for the nightly report")
    p.ask("only the three lines")
    assert p.state()["prompts"] == ["it is for the nightly report", "only the three lines"], p.state()["prompts"]
    print("goal answers into prompts: ok")

    so, out = p.rehearse(*END3)
    assert "register the plan first" in so and p.state()["ending"] is None
    so, out = p.rehearse(*END3[:1], "--job", *END3[1:])
    assert "register the plan first" in so and p.state()["job_ending"] is None
    assert p.phase() == "goal"
    print("no ending before the plan: ok")

    so, _ = p.rehearse("plan", *goals()[:12], "--stage-def", "only", "fix", "x", "-", "-")
    assert "goal item out_of_scope has no answer" in so and p.state()["stages"] == [], so
    so, _ = p.rehearse("plan", *goals()[:8], "--goal", "done", "request", "it prints d: 4",
                       "--goal", "out_of_scope", "assumed", "x", "--stage-def", "only", "fix", "x", "-", "-")
    assert "does not appear word for word" in so and p.state()["stages"] == [], so
    so, _ = p.rehearse("plan", *goals()[:8], "--goal", "done", "request", "a: 1 b: 2 c: 3",  # in the request
                       "--goal", "out_of_scope", "request", "only the three lines",  # in an answer
                       "--stage-def", "only", "fix", "print the lines", "-", "-")
    s = p.state()
    assert s["phase"] == "look" and s["goal"]["done"] == {"text": "a: 1 b: 2 c: 3", "source": "request"}, so
    print("plan needs four goal items and real citations: ok")

    q = Proj({})
    q.prompt(REQ2)
    so, out = q.rehearse("fetch", "file://" + q.j(".git", "HEAD"))
    assert q.state()["fixtures"] and q.phase() == "goal", so
    print("fetch in goal before the plan: ok")
    q.rehearse(*PLAN2, "--assume", "three items is enough", "--blocker", "the upload needs a login", "--from-request")
    s = q.state()
    assert s["phase"] == "goal" and [x["name"] for x in s["stages"]] == ["collect", "draft"], s["stages"]
    assert s["stages"][1]["inputs"] == ["out/items.md"] and s["stages"][1]["outputs"] == ["drafts/summary.md"]
    assert "three items is enough" in s["assumptions"] and "purpose: the job works" in s["assumptions"]
    assert s["blockers"] == ["the upload needs a login"] and s["stages_from"] == "request"
    assert one_stage().state()["stages_from"] == "manager"
    print("plan recorded; one-stage plan goes to look: ok")

    _, out = q.rehearse(*JOB_END)
    s = q.state()
    assert s["phase"] == "job-confirm" and s["job_ending"]["cmd"] == "cat drafts/summary.md", s["phase"]
    assert s["not_verified"] == ["the draft reads well"]
    _, out = q.rehearse(*JOB_END[:3], "cat drafts/summary.md; true", *JOB_END[4:])
    assert q.state()["job_ending"]["cmd"] == "cat drafts/summary.md; true" and q.phase() == "job-confirm"
    print("ending --job in job-confirm replaces: ok")
    q.prompt("not yet")
    assert q.phase() == "job-confirm" and not q.state()["job_confirmation"]["affirmative"]
    q.rehearse(*PLAN2)
    s = q.state()
    assert s["phase"] == "goal" and s["job_ending"] is None and s["job_confirmation"] is None, s["phase"]
    print("plan in job-confirm returns to goal: ok")
    q.rehearse(*JOB_END)
    q.prompt("yes")
    assert q.phase() == "look" and q.state()["stage"] == 1
    print("job ending to job-confirm, yes to stage 1 look: ok")

    q = Proj({})
    q.prompt(REQ2)
    q.rehearse(*PLAN2)
    q.rehearse(*JOB_END)
    _, out = q.rehearse("plan", *goals(), "--assume", "one stage will do", "--stage-def", "all", "build", "everything",
                        "-", "drafts/summary.md")
    assert q.phase() == "look" and q.state()["job_ending"] is None
    _, out = q.rehearse(*S2_END)
    assert q.phase() == "confirm" and "purpose: the job works" in ctx(out) and "one stage will do" in ctx(out), out
    print("a plan dropping to one stage: look, and the confirmation lists goal and assumptions: ok")

    p = stage1_passed()
    s = p.state()
    assert s["stages"][0]["passed"] and s["stages"][0]["ending"]["cmd"] == "python3 collect.py"
    _, out = p.rehearse(*JOB_END[:3], "cat drafts/summary.md; echo", *JOB_END[4:])  # rewritten after the PASS
    s = p.state()
    assert s["phase"] == "job-confirm" and s["confirm_return"] == 2, (s["phase"], out)
    so, _ = p.rehearse(*PLAN2)
    assert "plain rehearse plan is accepted in goal" in so and p.state()["stages"][0]["passed"]
    p.rehearse("plan", "--stage", "1", "--stage-def", "collect", "build", "again", "-", "out/items.md")
    assert p.state()["stages"][0]["line"] == "collect the items" and p.phase() == "job-confirm"  # passed: refused
    p.rehearse("plan", "--stage", "2", "--stage-def", "draft", "build", "write a shorter draft", "out/items.md",
               "drafts/summary.md")
    assert p.state()["stages"][1]["line"] == "write a shorter draft"
    before = p.state()
    p.prompt("yes")
    s = p.state()
    assert s["phase"] == "look" and s["stage"] == 2 and s["confirm_return"] is None and s["stages"][0]["passed"]
    assert s["fp_activation"] == before["fp_activation"] and s["started_at"] == before["started_at"]
    print("job ending rewritten after a PASS: back to stage 2 look, nothing reset: ok")

    p = stage1_passed()
    p.write("collect.py", COLLECT + "# changed since the stage started\n")
    p.rehearse(*JOB_END[:3], "cat drafts/summary.md; echo", *JOB_END[4:])  # no stage-start file check
    assert p.phase() == "job-confirm", p.phase()
    p.prompt("yes")
    p.rehearse(*JOB_END[:3], "cat drafts/summary.md; echo", *JOB_END[4:])  # unchanged: no confirmation needed
    assert p.phase() == "look" and p.state()["confirm_return"] is None
    p.spawn("rehearse:worker")
    so, _ = p.rehearse(*JOB_END)
    assert "before a worker starts" in so and p.state()["job_ending"]["cmd"] == "cat drafts/summary.md; echo", so
    p = stage1_passed()
    so, _ = p.rehearse(*S2_END)
    assert '"kind": "ending"' in so and '"stage": 2, "stages_passed": 1' in so, so  # the line the multi-stage eval greps
    so, _ = p.rehearse(*JOB_END[:3], "cat drafts/summary.md; echo", *JOB_END[4:])
    assert "before a worker starts or a stage ending exists" in so and p.phase() == "confirm", so
    print("ending --job in look refused after a worker or a stage ending: ok")

    p = final_stage()
    s = p.state()
    assert s["ending"]["cmd"] == "cat drafts/summary.md" and s["ending"]["after"] is None
    assert s["director_runs"] == [] and s["strikes"] == 0 and s["runs"] == [] and s["confirmation"]["affirmative"]
    assert s["stages"][1]["passed"] and s["stages"][1]["director_runs"][-1]["all_pass"]  # archived, then reset
    print("the final stage resets first, then copies the job ending: ok")

    # ================= roles and notes =================
    p = one_stage()
    out = p.spawn("rehearse:worker", prompt="look at the report")
    ui = out["hookSpecificOutput"]["updatedInput"]
    assert ui["prompt"].startswith("[rehearse] stage 1 look\n") and "plan line: print the three lines" in ui["prompt"]
    assert "look at the report" in ui["prompt"] and "purpose: the job works (assumed)" in ui["prompt"]
    assert ui["model"] == "sonnet" and ui["run_in_background"] is False, ui
    assert p.spawn("rehearse:worker", env={"REHEARSE_WORKER_MODEL": "haiku"})["hookSpecificOutput"][
        "updatedInput"]["model"] == "haiku"
    p.rehearse(*END3)
    assert p.phase() == "confirm"
    out = p.spawn("rehearse:worker")
    assert denied(out) and "only in look or build" in text(out), out
    p.prompt("yes")
    ui = p.spawn("rehearse:worker")["hookSpecificOutput"]["updatedInput"]
    assert ui["prompt"].startswith("[rehearse] stage 1 build\n") and '"cmd": "python3 main.py"' in ui["prompt"]
    print("worker spawns: the right half, the worker model, the foreground; refused in confirm: ok")

    out = p.ev("PostToolUse", tool_name="Agent", tool_input={"subagent_type": "general-purpose"}, tool_response={})
    assert out is None
    out = p.returned("rehearse:worker")
    c = ctx(out)
    assert "stage 1 build worker: neither" in c and "phase build" in c and "next: build stage 1" in c, c
    assert '"cmd": "python3 main.py"' in c and '"value": "a: 1"' in c, c
    p.spawn("rehearse:worker")
    fail(p, 0, who=WORKER)
    assert "stage 1 build worker: passed" in ctx(p.returned("rehearse:worker"))
    p = building()
    p.spawn("rehearse:worker")
    fail(p, 3, who=WORKER)
    fail(p, 3, who=WORKER)
    assert "stage 1 build worker: relocked" in ctx(p.returned("rehearse:worker")) and p.state()["strikes"] == 1
    q2 = two_stage()
    so, _ = q2.rehearse(*S1_END)
    assert '"kind": "ending"' in so and '"stage": 1, "stages_passed": 0' in so, so
    q2.prompt("yes")
    q2.edit("collect.py", COLLECT)
    q2.spawn()
    c = ctx(q2.verdict(PASS))
    assert c.startswith("[rehearse] stage 1 passed") and "phase look" in c and "next: look at stage 2" in c, c
    print("Agent notes: only workers and the director; passed / relocked / neither; stage passed: ok")

    p = building()
    p.edit("main.py", prog(1))
    for who in (WORKER, None):  # --as-director from a worker or the manager is a plain run
        p.rehearse("run", "--as-director", who=who)
        s = p.state()
        assert s["director_runs"] == [] and s["runs"][-1]["failing"] == 2, s["runs"]
    p.spawn()
    p.rehearse("run", "--as-director", who=DIRECTOR)
    assert p.state()["director_runs"][-1]["agent_type"] == "rehearse:director" and len(p.state()["runs"]) == 2
    print("--as-director only for the director: ok")

    # ================= locks and outputs =================
    for who in (None, WORKER):
        q = Proj({"main.py": prog(0)})
        q.prompt(REQ2)
        assert denied(q.pre("Edit", who, file_path=q.j("main.py")))  # goal
        q.rehearse(*PLAN2)
        q.rehearse(*JOB_END)
        assert denied(q.pre("Write", who, file_path=q.j("main.py")))  # job-confirm
        q.prompt("yes")
        assert denied(q.pre("Edit", who, file_path=q.j("main.py")))  # look
        q.rehearse(*S1_END)
        assert denied(q.pre("Bash", who, command="echo x > main.py"))  # confirm
        p = relocked()
        for _ in range(2):  # strikes 2 and 3 through two more relocks
            p.result("fetch", ok=True, fixture="f")
            p.rehearse(*END3)
            p.prompt("yes")
            fail(p, 3)
            fail(p, 3)
        assert p.phase() == "stuck" and denied(p.pre("Edit", who, file_path=p.j("main.py")))
    print("edits locked in goal, job-confirm, look, confirm, stuck for any caller: ok")

    q = Proj({".gitignore": "ignored/\n"})
    q.prompt(REQ2)
    q.rehearse("plan", *goals(), "--stage-def", "draft", "build", "write it", "-",
               "drafts/summary.md,ignored/out.md,.hidden/out.md,ignored/gen.py,notes/undeclared.md")
    for rel in ("drafts/summary.md", "ignored/out.md", ".hidden/out.md"):
        out = q.pre("Write", WORKER, file_path=q.j(rel))
        assert denied(out) and "%s is a declared output" % q.j(rel) in text(out), (rel, out)
        out = q.pre("Bash", command="echo x > %s" % rel)
        assert denied(out) and "writes the declared output" in text(out), (rel, out)
    assert q.pre("Write", file_path=q.j("drafts/other.md")) is None  # named nowhere in the plan: not locked
    print("declared outputs locked in look, also in ignored and hidden folders: ok")

    q = Proj({})
    q.prompt(REQ2)
    q.rehearse(*PLAN2)
    q.rehearse(*JOB_END)
    assert q.pre("Write", file_path=q.j("notes", "ending-reads.md")) is None  # undeclared: the stated gap
    q.rehearse("plan", "--stage", "1", "--stage-def", "collect", "build", "collect", "-",
               "out/items.md,notes/ending-reads.md")
    assert denied(q.pre("Write", file_path=q.j("notes", "ending-reads.md")))
    print("an undeclared path is not locked; declaring it locks it: ok")

    p = stage1_passed()
    assert denied(p.pre("Write", WORKER, file_path=p.j("out", "items.md")))  # stage 1's output in stage 2's look
    assert p.pre("Bash", command="python3 collect.py") is None  # stage 1's program may run while stage 2 looks
    assert p.state()["created"] == [] and p.state()["fp_activation"]["files"].get("collect.py")
    print("stage 2's look: stage 1's output locked, its program runnable: ok")

    p = stage1_passed()
    assert not denied(p.pre("Bash", command="rehearse stage step \"open('drafts/summary.md','w').write('x')\""))
    # a stage step that writes a declared output is not refused (stated gap)
    p.write("drafts/summary.md", "summary: done\n")
    _, out = p.rehearse(*S2_END)
    assert "nothing wrong" in text(out) and p.phase() == "look", out  # refused only because it already passes
    os.remove(p.j("drafts", "summary.md"))
    p.rehearse(*S2_END)
    assert p.phase() == "confirm"
    print("a stage step writing an output: not refused; registration refused only when it already passes: ok")

    p = one_stage()
    so = p.rehearse("fetch", "file://" + p.j("main.py"))[0]
    fx = p.state()["fixtures"][0]
    p.write(os.path.join(p.state()["run_folder"], "fixtures", fx), "c: 3\n")  # what the fetch saved (simulated)
    p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "c", "contains", "c: 3", "--cite", "fixture:" + fx)
    assert p.phase() == "confirm"
    print("an ending citing a fixture registers: ok")

    for change in (False, True):
        q = Proj({".gitignore": "ignored/\n", "main.py": prog(0)})
        q.prompt(REQ3)
        q.rehearse("plan", *goals(), "--stage-def", "only", "fix", "x", "-", "notes/out.md,ignored/gen.py")
        q.rehearse(*END3)
        q.prompt("yes")
        q.edit("notes/out.md", "draft\n")
        assert q.state()["project_edits_since_run"] == 1  # a draft written in build counts as an edit
        q.edit("ignored/gen.py", "x = 1\n")
        q.spawn()
        sf = q.state()["spawn_fingerprint"]
        assert "ignored/gen.py" not in sf["files"] and q.j("ignored", "gen.py") in sf["outputs"], sf
        if change:
            q.write("notes/out.md", "draft, changed\n")
        q.verdict(PASS)
        assert q.phase() == ("build" if change else "done.passed"), q.phase()
        assert ("notes/out.md" in q.state()["verdicts"][-1].get("void", "")) == change
    print("declared outputs hashed at the spawn: a change voids the verdict; unchanged ones do not: ok")

    p = final_stage()
    p.spawn()
    p.write("out/items.md", "changed\n")  # stage 1's .md output, after the final director's spawn
    p.verdict(PASS)
    assert p.phase() == "build" and "out/items.md" in p.state()["verdicts"][-1]["void"]
    print("final stage: an earlier stage's output changed after the spawn voids the verdict: ok")

    p = stage1_passed()
    s = p.state()
    for k in ("ending", "confirmation", "findings", "spawn_fingerprint", "reopen", "worker"):
        assert s[k] is None, k
    for k in ("created", "produced", "director_runs", "runs", "relocks", "verdicts", "config_edits"):
        assert s[k] == [], k
    for k in ("failing_runs", "strikes", "project_edits_since_run", "code_edits_since_run", "no_ending", "workers"):
        assert s[k] == 0, k
    assert s["fewest_failing"] is None and not s["pending_change"] and not s["direct_pending"]
    assert s["fp_activation"] == s["fp_phase_entry"] and "collect.py" in s["fp_activation"]["files"]
    a = s["stages"][0]
    assert a["passed"] and a["verdicts"][-1]["verdict"] == "PASS" and a["confirmation"]["affirmative"]
    print("a PASS archives the stage and resets every current-stage field: ok")

    p = final_stage()
    s = p.state()
    assert s["stages"][1]["ending"]["cmd"] == "grep summary drafts/summary.md"
    p.report("fixed\n\n## Not verified\nnone\n")
    out = p.stop()
    assert blocked(out, "say built, not verified"), out  # the stage-2 PASS does not verify the job ending
    print("a stage PASS does not make the final stage verified: ok")

    p = building(files={"tests/test_x.py": "def test_x():\n    assert True\n"})
    p.edit("tests/test_x.py", "def test_x():\n    pass\n")
    fail(p, 3)
    fail(p, 3)
    s = p.state()
    assert s["phase"] == "look" and s["fp_activation"] != s["fp_phase_entry"]
    s["root"] = p.root
    names = [i["path"] for f in json.load(open(FD.write(s)))["findings"] for i in f["items"]]
    assert "tests/test_x.py" in names, names  # compared against the stage start, not the relock
    print("findings compare against the stage start: ok")

    # ================= the run counter =================
    p = building()
    fail(p, 2)
    p.rehearse("run")
    p.rehearse("run")
    s = p.state()
    assert len(s["runs"]) == 3 and s["failing_runs"] == 0 and s["fewest_failing"] == 2, s["runs"]
    print("a run with no project edit since the last run does not count: ok")

    for seq, relock in (([3, 3], True), ([2, 3, 2, 3], True), ([3, 2, 1], False)):
        p = building()
        for n in seq:
            fail(p, n)
        assert (p.phase() == "look") == relock, (seq, p.phase())
        assert len(p.state()["relocks"]) == (1 if relock else 0)
    print("progress against the fewest failing: 3,3 and 2,3,2,3 relock; 3,2,1 does not: ok")

    p = building()
    fail(p, 2)
    p.spawn()
    p.verdict(REWORK)
    assert p.state()["fewest_failing"] == 2 and p.state()["strikes"] == 1 and p.phase() == "build"
    print("a REWORK leaves fewest_failing: ok")

    p = relocked()
    s = p.state()
    assert s["failing_runs"] == 0 and s["strikes"] == 1 and s["fp_phase_entry"] != s["fp_activation"]
    assert denied(p.pre("Edit", file_path=p.j("main.py")))
    p.result("fetch", ok=True, fixture="f")
    p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "a", "contains", "a: 1", "--cite", "request",
               "--expect", "b", "contains", "b: 2", "--cite", "request")
    assert p.state()["fewest_failing"] == 2 and p.phase() == "confirm"
    print("two failing runs relock, snapshot, strike; fewest restarts from the re-registered ending: ok")

    p = building()
    p.edit("main.py", prog(1))
    p.bash("python3 main.py")  # direct run, then an edit: one failing run
    p.edit("main.py", prog(1))
    assert p.state()["failing_runs"] == 1 and not p.state()["direct_pending"]
    p = building()
    p.edit("main.py", prog(0))
    p.bash("cd . && python3 main.py")
    p.rehearse("run")  # direct run, then rehearse run: the direct run does not count; the rehearse run does
    assert p.state()["failing_runs"] == 1 and p.phase() == "build"
    p.edit("main.py", prog(0))
    p.bash("python3 main.py")
    p.rehearse("run")
    assert p.phase() == "look", p.phase()
    print("direct runs: count once when an edit follows; edit, direct, run twice relocks: ok")

    outside = os.path.join(TMP, "outside", "copy.py")
    p = building()
    for i in range(1, 21):
        out = p.edit(outside if i % 2 else "main.py", "x = %d\n" % i)
        assert ("reminder: %d code edits" % i in text(out)) == (i in (10, 20)), (i, out)
    assert "a change that exists only in a copy is not a fix" in text(out)
    p.rehearse("run")
    assert p.state()["code_edits_since_run"] == 0
    p = building()  # what scratch() does not count (2.0.1): the run folder, the director's edits, a text file
    p.edit(os.path.join(p.state()["run_folder"], "notes.py"), "x\n")
    p.edit(outside, "x = 0\n", who=DIRECTOR)
    p.edit(os.path.join(TMP, "outside", "notes.txt"), "x\n")
    assert p.state()["code_edits_since_run"] == 0
    q = one_stage()
    for i in range(12):
        assert q.edit(outside, "y = %d\n" % i) is None  # while looking, scratch work is the point
    assert q.state()["code_edits_since_run"] == 0
    p = building()
    for i in range(9):
        p.edit(outside, "z = %d\n" % i)
    fail(p, 3)  # a run resets the count; so does a relock
    for i in range(9):
        p.edit(outside, "z = %d\n" % i)
    fail(p, 3)
    assert p.phase() == "look" and p.state()["code_edits_since_run"] == 0
    print("the ten-edit reminder: build only, copies count, every ten, reset at a run or relock: ok")

    p = building()
    p.spawn("rehearse:worker")
    assert "neither" in ctx(p.returned("rehearse:worker")) and p.state()["strikes"] == 1
    p = one_stage()
    p.spawn("rehearse:worker")
    assert "no ending" in ctx(p.returned("rehearse:worker")) and p.state()["strikes"] == 0
    p.spawn("rehearse:worker")
    assert "no ending" in ctx(p.returned("rehearse:worker")) and p.state()["strikes"] == 1
    print("strikes: a build worker with no pass and no relock; a second no ending in a row: ok")

    p = building()
    for _ in range(3):
        p.spawn()
        p.verdict(REWORK)
    assert p.phase() == "stuck" and p.state()["strikes"] == 3
    p = building(UN)
    for _ in range(3):
        p.spawn(env=UN)
        p.verdict(REWORK, env=UN)
    assert p.phase() == "done.not_fixed"
    print("strikes at the cap: stuck attended, not fixed unattended: ok")

    # ================= reopening and change =================
    p = relocked()
    so, out = p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "a", "contains", "a: 1", "--cite", "request")
    assert "no look step" in so and p.phase() == "look", so
    p.result("stage-step", accepted=True, project_files=[])
    p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "a", "contains", "a: 1", "--cite", "request")
    assert p.phase() == "look" and p.state()["reopen"]["looks"] == 0
    p.result("stage-step", accepted=True, project_files=["main.py"])
    assert p.state()["reopen"]["looks"] == 1
    for res in ({"kind": "fetch", "ok": True, "fixture": "x"}, {"kind": "fetch", "ok": True, "fixture": "file"}):
        q = relocked()
        q.result(res.pop("kind"), **res)
        assert q.state()["reopen"]["looks"] == 1
    q = relocked()
    q.rehearse("fetch", "file://" + q.j("main.py"))
    assert q.state()["reopen"]["looks"] == 1
    print("a look step: a stage step into project code, or a fetch (file:// too); none, no ending: ok")

    p = building()
    fail(p, 3)  # main.py changes before the relock: the re-registration compares from the relock, not the start
    fail(p, 3)
    assert p.phase() == "look" and F.code_change(p.state()["fp_activation"], p.state()["fp_phase_entry"])
    p.result("fetch", ok=True, fixture="f")
    p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "b", "contains", "b: 2", "--cite", "request")
    assert p.phase() == "confirm" and p.state()["relocks"][-1]["looks"] == 1, p.phase()  # recorded once, here
    p.prompt("yes")
    assert p.phase() == "build" and not p.state()["start_director"]
    print("re-registration compares against the relock snapshot; a failing one goes confirm, then build: ok")

    p = relocked()  # the code was right; the old ending was wrong
    p.result("fetch", ok=True, fixture="f")
    so, out = p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "quiet", "exit_code", "0", "--cite", "request")
    assert p.phase() == "confirm" and "already passes" in ctx(out), (so, out)
    out = p.prompt("yes")
    assert p.phase() == "build" and "start rehearse:director" in ctx(out)
    assert "next: start rehearse:director" in p.rehearse("job")[0]
    p.spawn()
    assert p.phase() == "judge"
    p = relocked(UN)
    p.result("fetch", ok=True, fixture="f")
    so, out = p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "quiet", "exit_code", "0", "--cite", "request",
                         env=UN)
    s = p.state()
    assert s["phase"] == "build" and s["start_director"] and s["confirmation"]["by"] == "unattended", s["phase"]
    print("an already-passing re-registered ending: confirm with a note, then build, start the director: ok")

    p = relocked()
    p.write("main.py", prog(3))  # unseen fix during look (stated gap); the old ending's run passes
    _, out = p.rehearse("run")
    assert p.phase() == "build" and "start rehearse:director" in ctx(out) and p.state()["start_director"]
    assert p.state()["relocks"][-1]["next_run"] == {"passed": True, "edits": 0}
    print("a passing rehearse run in look after a relock goes to build, start the director: ok")

    p = relocked()
    p.spawn("rehearse:worker")
    p.result("fetch", ok=True, fixture="f")
    p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "a", "contains", "a: 1", "--cite", "request")
    assert "re-registered, fails" in ctx(p.returned("rehearse:worker"))
    p = relocked()
    p.spawn("rehearse:worker")
    p.result("fetch", ok=True, fixture="f")
    p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "quiet", "exit_code", "0", "--cite", "request")
    assert "re-registered, already passes" in ctx(p.returned("rehearse:worker"))
    p = relocked()
    p.spawn("rehearse:worker")
    assert "no ending" in ctx(p.returned("rehearse:worker"))
    print("look worker notes: re-registered fails / already passes / no ending: ok")

    # ================= stuck exits =================
    def stuck(env=None):
        p = building(env)
        p.edit("main.py", prog(1))
        for _ in range(3):
            p.spawn()
            p.verdict(REWORK)
        assert p.phase() == "stuck"
        return p

    p = stuck()
    p.prompt("maybe later")
    assert p.phase() == "stuck" and "stuck answer: maybe later" in p.state()["notes"]
    p.prompt("stop here, please")
    assert p.state()["stop_here"] and blocked(p.stop(), '"not fixed"')
    p.report("not fixed: stuck\n\n## Not verified\nthe total\n")
    assert p.stop() is None and p.phase() == "done.not_fixed"
    p = stuck()
    p.ask("Try again with the tax")
    s = p.state()
    assert s["phase"] == "build" and s["strikes"] == 0 and s["failing_runs"] == 0 and not s["pending_change"]
    p = stuck()
    p.prompt("change the stage: only two lines")
    s = p.state()
    assert s["phase"] == "look" and s["strikes"] == 0 and s["pending_change"] and s["reopen"]["why"] == "change"
    assert F.code_change(s["fp_activation"], s["fp_phase_entry"]) == ["main.py"]  # a new snapshot
    print("stuck: other answers stay; stop here; try again; change: ok")

    so, _ = p.rehearse(*PLAN1)
    assert "plain rehearse plan is accepted" in so
    p.rehearse("plan", "--stage", "1", "--stage-def", "only", "fix", "print two lines", "-", "-")
    assert p.state()["stages"][0]["line"] == "print two lines"
    so, _ = p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "c", "contains", "c: 3", "--cite", "request")
    assert "no look step" in so and p.phase() == "look", so  # after change, the look-step rule applies
    p.result("stage-step", accepted=True, project_files=["main.py"])
    p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "c", "contains", "c: 3", "--cite", "request")
    assert p.phase() == "confirm" and not p.state()["pending_change"]
    p.rehearse("plan", "--stage", "1", "--stage-def", "only", "fix", "again", "-", "-")
    assert p.state()["stages"][0]["line"] == "print two lines"  # the mark is cleared: refused
    p = stuck()  # after change, an already-passing ending behaves as after a relock
    p.prompt("change")
    p.result("fetch", ok=True, fixture="f")
    _, out = p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "a", "contains", "a: 1", "--cite", "request")
    assert p.phase() == "confirm" and "already passes" in ctx(out), out
    print("pending_change: plan --stage for the current stage only, cleared by an ending: ok")

    p = one_stage()
    p.spawn("rehearse:worker")
    p.returned("rehearse:worker")  # no ending: the manager asks the stuck question at once
    p.ask("Change the stage")
    assert p.state()["pending_change"] and p.phase() == "look"
    so, _ = p.rehearse("plan", "--stage", "1", "--stage-def", "only", "fix", "smaller", "-", "-")
    assert p.state()["stages"][0]["line"] == "smaller", so
    print("an attended look blocker answered change: plan --stage accepted: ok")

    p = stuck()
    p.prompt("change")
    p.write("main.py", prog(3))
    p.rehearse("run")  # a passing run exits look: the mark is cleared
    assert p.phase() == "build" and not p.state()["pending_change"]
    fail(p, 3)
    fail(p, 3)
    assert p.phase() == "look"
    p.rehearse("plan", "--stage", "1", "--stage-def", "only", "fix", "x", "-", "-")
    assert p.state()["stages"][0]["line"] == "print the three lines"  # the passing run cleared the mark: refused
    p = stuck()
    p.prompt("change")
    p.prompt("stop here")
    assert not p.state()["pending_change"]
    p = one_stage()
    p.spawn("rehearse:worker")
    p.returned("rehearse:worker")
    p.prompt("change")
    p.spawn("rehearse:worker")
    p.returned("rehearse:worker")
    p.spawn("rehearse:worker")
    p.returned("rehearse:worker")  # a second no ending in a row: a strike, which clears the mark
    assert p.state()["strikes"] == 1 and not p.state()["pending_change"]
    print("pending_change cleared by a passing run, stop here, try again and a strike: ok")

    p = final_stage()
    for _ in range(3):
        p.spawn()
        p.verdict(REWORK)
    out = p.prompt("change")
    assert p.phase() == "look" and "Register the job ending again" in ctx(out), out
    so, _ = p.rehearse("plan", "--stage", "2", "--stage-def", "draft", "build", "x", "-", "-")
    assert "in the final stage" in so

    p = final_stage()
    p.rehearse("run")  # passes: summary.md holds the line
    p.edit("drafts/summary.md", "nothing\n")
    p.rehearse("run")
    p.edit("drafts/summary.md", "nothing yet\n")
    p.rehearse("run")
    assert p.phase() == "look", p.phase()
    so, _ = p.rehearse("plan", "--stage", "2", "--stage-def", "draft", "build", "x", "-", "-")
    assert "in the final stage" in so
    p.result("fetch", ok=True, fixture="f")
    p.rehearse("ending", "--cmd", "grep -c summary drafts/summary.md", "--expect", "one", "contains", "summary: done",
               "--cite", "request")
    s = p.state()
    assert s["phase"] == "confirm" and s["ending"]["cmd"] == s["job_ending"]["cmd"] == "grep -c summary drafts/summary.md"
    print("final stage: a relock re-registers the job ending (both replaced); plan --stage refused: ok")

    # ================= end to end and Stop =================
    p = final_stage()
    so, _ = p.rehearse("run", "--stage", "1")
    assert "--stage needs --as-director" in so
    q = stage1_passed()
    so, _ = q.rehearse("run", "--stage", "1", "--as-director", who=DIRECTOR)
    assert "only in the final stage" in so and q.state()["stages"][0]["reruns"] == []
    p.edit("drafts/summary.md", "nothing\n")
    p.spawn()
    p.rehearse("run", "--as-director", who=DIRECTOR)  # the job ending fails
    before = p.state()
    p.rehearse("run", "--stage", "1", "--as-director", who=DIRECTOR)
    s = p.state()
    assert s["stages"][0]["reruns"][-1]["all_pass"] and s["stages"][0]["reruns"][-1]["agent_type"] == "rehearse:director"
    for k in ("director_runs", "runs", "failing_runs", "project_edits_since_run"):
        assert s[k] == before[k], k
    assert s["ending"]["after"] == before["ending"]["after"]
    p.report("fixed\n\n## Not verified\nnone\n")
    assert blocked(p.stop(), "say built, not verified")  # a passing stage rerun does not verify the job
    print("rehearse run --stage: director and final stage only, into reruns only, never verifies: ok")

    p = final_stage()
    p.rehearse("run")
    assert p.state()["ending"]["after"]["all_pass"]
    p.spawn()
    p.verdict(PASS)
    assert p.phase() == "done.passed"
    p.report("fixed: the draft is written\n\nbody\n")
    assert blocked(p.stop(), 'add a "not verified" section')
    p.report("fixed: the draft is written\n\n## Not verified\nthe draft reads well\n")
    assert p.stop() is None and p.state()["closed"]
    print("the final stage runs the job ending; the report needs a not verified section: ok")

    for env in (None, UN):
        q = Proj({})
        q.prompt(REQ2)
        assert (q.stop(env) is None) == (env is None)  # goal
        q.rehearse(*PLAN2)
        q.rehearse(*JOB_END, env=env)
        if env is None:
            assert q.phase() == "job-confirm" and q.stop() is None
            assert blocked(q.stop(UN), "have the job confirmed")
            q.prompt("yes")
        else:
            assert q.phase() == "look" and q.state()["job_confirmation"]["by"] == "unattended"
        q.rehearse(*S1_END, env=env)
        if env is None:
            assert q.phase() == "confirm" and q.stop() is None
            assert blocked(q.stop(UN), "have the stage 1 ending confirmed")
        else:
            assert q.phase() == "build" and q.state()["confirmation"]["by"] == "unattended"
    p = stuck()
    assert p.stop() is None
    q = Proj({})
    q.prompt(REQ2)
    q.rehearse(*PLAN2)
    with_un = q.stop(UN)
    assert blocked(with_un, "register the job ending"), with_un
    print("Stop: attended may wait in goal, job-confirm, confirm, stuck; unattended is blocked: ok")

    # ================= review fixes =================
    p = relocked()  # the already-passing path, then a REWORK: a fresh build worker, not the director again
    p.result("fetch", ok=True, fixture="f")
    p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "quiet", "exit_code", "0", "--cite", "request")
    p.prompt("yes")
    assert p.state()["start_director"]
    p.spawn()
    assert not p.state()["start_director"]
    out = p.verdict(REWORK)
    assert "next: build stage 1 (start rehearse:worker)" in ctx(out) and p.phase() == "build", out
    assert "build stage 1" in p.rehearse("job")[0]
    ui = p.spawn("rehearse:worker")["hookSpecificOutput"]["updatedInput"]
    assert ui["prompt"].startswith("[rehearse] stage 1 build\n")
    print("a REWORK after the already-passing path asks for a build worker: ok")

    old = Proj({"main.py": prog(0)})  # a live 2.0.1 run file: ignored by every v3 hook event
    rid = "20261015T000000000000Z-abcdef"
    folder = old.j(".rehearsal", rid)
    v2 = {"run_id": rid, "session_id": old.sid, "phase": "work", "root": old.root, "run_folder": folder,
          "path": os.path.join(DATA, "sessions", old.sid, rid + ".json"), "ending": None, "created": [],
          "round_open": False, "prompts": [], "notes": []}
    for path in (v2["path"], os.path.join(folder, "state.json")):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        json.dump(v2, open(path, "w"))
    assert old.pre("Edit", file_path=old.j("main.py")) is None and old.edit("main.py", prog(1)) is None
    assert old.prompt("yes") is None and old.bash("rehearse run", "REHEARSE-RESULT " + json.dumps(
        {"run": rid, "kind": "run", "ok": True, "all_pass": False})) is None
    assert old.stop() is None and old.state()["phase"] == "work"
    assert "no active rehearse job" in old.rehearse("job")[0]
    print("a 2.0.1 run file is not run under the v3 rules: ok")

    p = final_stage()  # (a) run --stage by a non-director in the final stage: refused by the hook
    for who in (WORKER, None):
        _, out = p.rehearse("run", "--stage", "1", "--as-director", who=who)
        assert blocked(out, "for the end-to-end director") and p.state()["stages"][0]["reruns"] == [], out
    print("run --stage --as-director from a worker or the manager is refused: ok")

    p = relocked()  # (c) a code change after the relock snapshot is refused at re-registration
    p.result("fetch", ok=True, fixture="f")
    p.write("main.py", prog(1) + "# unseen\n")
    _, out = p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "c", "contains", "c: 3", "--cite", "request")
    assert blocked(out, "code changed while edits were locked: main.py") and p.phase() == "look", out
    q = relocked()  # and bin refuses before running the ending when no look step was logged
    so, _ = q.rehearse("ending", "--cmd", "touch side-effect; false", "--expect", "x", "exit_code", "0",
                       "--cite", "request")
    assert "no look step" in so and not os.path.exists(q.j("side-effect")), so
    print("re-registration: a change since the relock refused; no look step refused before running: ok")

    p = stage1_passed()  # (e) stage 2's look imports stage 1's program through the stage server
    p.rehearse("stage", "start")
    so, _ = p.rehearse("stage", "step", "import collect")
    assert '"accepted": true' in so and "collect.py" in so, so
    p.rehearse("stage", "stop")
    print("stage 2's look imports stage 1's program through the stage: ok")

    import ast  # (f) the stage's locked phases are the job's
    import state as S
    line = [ln for ln in open(os.path.join(ROOT, "stage", "server.py")) if ln.startswith("LOCKED = ")][0]
    assert ast.literal_eval(line.split("=", 1)[1].strip()) == S.LOCKED, line
    print("stage/server.py LOCKED matches state.LOCKED: ok")

    p = building()  # (g) the ten-edit count resets on "change"
    for i in range(5):
        p.edit(outside, "w = %d\n" % i)
    for _ in range(3):
        p.spawn()
        p.verdict(REWORK)
    assert p.phase() == "stuck" and p.state()["code_edits_since_run"] == 5
    p.prompt("change")
    assert p.state()["code_edits_since_run"] == 0
    print("the ten-edit count resets on change: ok")

    p = one_stage()  # (4) the manager on the one-stage path may answer "change" in look, no worker needed
    out = p.prompt("change: the third line is not needed")
    assert p.state()["pending_change"] and p.phase() == "look" and "plan --stage 1" in ctx(out), out
    q = one_stage(UN)
    q.prompt("change it", UN)
    assert not q.state()["pending_change"] and q.state()["prompts"] == ["change it"]
    print("stuck answers in an attended look without a worker: ok")

    p = building()  # (8) rehearse stop after done.passed without a report, and in done.not_fixed
    fail(p, 0)
    p.spawn()
    p.verdict(PASS)
    assert p.phase() == "done.passed" and blocked(p.stop(), "write report.md")
    p.prompt("rehearse stop")
    assert p.phase() == "done.cancelled" and p.stop() is None
    p = building(UN)
    for _ in range(3):
        p.spawn(env=UN)
        p.verdict(REWORK, env=UN)
    assert p.phase() == "done.not_fixed" and blocked(p.stop(UN))
    p.prompt("rehearse stop", UN)
    assert p.phase() == "done.cancelled" and p.stop(UN) is None
    print("rehearse stop after done.passed or done.not_fixed lets the manager stop: ok")

    p = building()  # (6) an Agent call that fails still gets the note
    p.spawn("rehearse:worker")
    out = p.ev("PostToolUseFailure", tool_name="Agent", tool_input={"subagent_type": "rehearse:worker"},
               error="interrupted")
    assert out["hookSpecificOutput"]["hookEventName"] == "PostToolUseFailure" and "phase build" in ctx(out), out
    print("the Agent note on a failed call: ok")

    p = two_stage()  # a "no" at a stage confirmation: back to look, a worker re-registers
    p.rehearse(*S1_END)
    entry, strikes = p.state()["fp_phase_entry"], p.state()["strikes"]
    out = p.prompt("no, the expected value is wrong\nit should say items: 3 exactly")
    s = p.state()
    assert s["phase"] == "look" and s["fp_phase_entry"] == entry and s["strikes"] == strikes, s["phase"]
    assert s["prompts"][-1].startswith("no, the expected value is wrong")
    assert "the user said: no, the expected value is wrong" in ctx(out) and "exactly" not in ctx(out), out
    ui = p.spawn("rehearse:worker")["hookSpecificOutput"]["updatedInput"]
    assert ui["prompt"].startswith("[rehearse] stage 1 look\n")
    p.result("fetch", ok=True, fixture="f")
    p.rehearse(*S1_END[:3], "--expect", "items", "contains", "items: 3 exactly", "--cite", "request")
    assert p.phase() == "confirm" and p.state()["redo"] is None, p.phase()
    c = ctx(p.returned("rehearse:worker"))
    assert "ending registered" in c and "items: 3 exactly" in c, c
    print("a no at a stage confirmation goes back to look for a worker: ok")

    q = Proj({})  # unattended: the activation says so, and goal asks no questions
    out = q.prompt(REQ2, UN)
    assert "unattended: confirmations are off" in ctx(out), out
    r = q.stop(UN)
    assert blocked(r, "then rehearse plan") and "ask the goal questions" not in r["reason"], r
    assert "attended: the user answers confirmations" in ctx(Proj({}).prompt(REQ2))
    print("the activation states the mode; unattended goal records items instead of asking: ok")

    q = Proj({"main.py": prog(0)})  # `$R plan ... && $R job` in one call: both result lines apply, in order
    q.prompt(REQ3)
    so = subprocess.run([sys.executable, BIN, *PLAN1], cwd=q.root, capture_output=True, text=True, env=ENV).stdout
    so += subprocess.run([sys.executable, BIN, "job"], cwd=q.root, capture_output=True, text=True, env=ENV).stdout
    assert so.count("REHEARSE-RESULT ") == 2 and '"kind": "plan"' in so and '"kind": "job"' in so, so
    q.bash("R=rehearse; $R plan ... && $R job", so)
    assert q.phase() == "look" and [x["name"] for x in q.state()["stages"]] == ["only"], q.phase()
    so = subprocess.run([sys.executable, BIN, *END3], cwd=q.root, capture_output=True, text=True, env=ENV).stdout
    so += subprocess.run([sys.executable, BIN, "job"], cwd=q.root, capture_output=True, text=True, env=ENV).stdout
    q.bash("R=rehearse; $R ending ... && $R job", so)
    assert q.phase() == "confirm" and q.state()["ending"]["cmd"] == "python3 main.py", q.phase()
    print("every result line of one command applies, in order: ok")

    # batch apply cannot open a lock hole: a chained call that registers an ending AND writes a project file is
    # refused before it runs, because the edit lock reads the command's write targets at PreToolUse (unattended too)
    q = Proj({"main.py": prog(0)})
    q.prompt(REQ3, UN)
    q.rehearse(*PLAN1, env=UN)
    assert q.phase() == "look"
    ending = "R=rehearse; $R " + shlex.join(END3)
    assert not denied(q.pre("Bash", env=UN, command=ending))  # the registration alone may run (the hook only sets its timeout)
    for tail in (" && cat > main.py <<'EOF'\nprint('a: 1')\nEOF", " && echo x > main.py", "; python3 - > main.py <<'EOF'\nprint(1)\nEOF"):
        out = q.pre("Bash", env=UN, command=ending + tail)
        assert denied(out) and "register and confirm an ending first" in text(out), tail
    assert q.phase() == "look" and q.state()["ending"] is None
    print("a chained ending registration plus a file write is refused before it runs: ok")

    # batch apply rejects mid-sequence: a refused ending followed by `run` and `job` in one call leaves nothing applied
    q = Proj({"main.py": prog(3)})  # every expectation already passes, so the ending is refused
    q.prompt(REQ3, UN)
    q.rehearse(*PLAN1, env=UN)
    so = ""
    for args in (END3, ["run"], ["job"]):
        so += subprocess.run([sys.executable, BIN, *args], cwd=q.root, capture_output=True, text=True, env=dict(ENV, **UN)).stdout
    assert so.count("REHEARSE-RESULT ") == 3, so
    out = q.bash("R=rehearse; $R ending ... ; $R run ; $R job", so, env=UN)
    assert blocked(out, "already passes"), out
    s2 = q.state()
    assert s2["phase"] == "look" and s2["ending"] is None and not s2.get("runs") and s2["strikes"] == 0, s2["phase"]
    print("a refused ending blocks the rest of the same call: ok")

    for word in ("rehearse job", "REHEARSE status  "):  # typed as a prompt: a status answer, never a new job
        q = Proj({})
        out = q.prompt(word)
        assert q.state() is None and "no active rehearse job" in ctx(out), out
        p = building()
        before = p.state()
        out = p.prompt(word)
        s = p.state()
        assert s["run_id"] == before["run_id"] and s["phase"] == "build" and s["prompts"] == before["prompts"]
        assert len(os.listdir(os.path.dirname(s["path"]))) == len(os.listdir(os.path.dirname(before["path"])))
        assert "phase build" in ctx(out) and "phase build" in out["systemMessage"], out
        assert len([n for n in os.listdir(os.path.dirname(s["path"])) if n.endswith(".json")]) == 1
    print("rehearse job / status as a prompt: status only: ok")

    def launched(p, kind, aid):
        """Interactive sessions: the Agent call returns at once and the agent runs in the background (P19, P20)."""
        return p.ev("PostToolUse", tool_name="Agent", tool_input={"subagent_type": kind, "prompt": "x"},
                    tool_response={"isAsync": True, "status": "async_launched", "agentId": aid})

    def stopped(p, who, aid, msg="done"):
        return p.ev("SubagentStop", None, dict(who, agent_id=aid), agent_transcript_path="/x",
                    stop_hook_active=False, last_assistant_message=msg)

    p = building()  # the director in the background
    fail(p, 0)
    p.spawn()
    out = launched(p, "rehearse:director", "bg-d1")
    assert "director launched in the background: end your turn now" in ctx(out), out
    sp = p.state()["spawn"]
    assert sp["background"] and not sp["stopped"] and sp["agent_id"] == "bg-d1", sp
    r = p.stop()
    assert r is None or "decision" not in r, r  # Stop allowed while it runs
    so = p.rehearse("job")[0]
    assert "director running since" in so and "next: wait for the director's notification" in so, so
    stopped(p, {"agent_type": "", "agent_id": "x"}, "stray-1", PASS)  # the stray stop changes nothing
    stopped(p, DIRECTOR, "other-id", PASS)  # nor does a director stop with another id
    assert p.phase() == "judge" and not p.state()["spawn"]["stopped"] and p.state()["verdicts"] == []
    stopped(p, DIRECTOR, "bg-d1", PASS)
    s = p.state()
    assert s["phase"] == "done.passed" and s["verdicts"][-1]["verdict"] == "PASS", s["phase"]
    assert blocked(p.stop(), "write report.md")  # the done rules apply again
    print("a background director: Stop allowed while it runs, its verdict recorded at its stop: ok")

    for half in ("look", "build"):  # a background worker, its outcome recorded at its stop
        p = one_stage() if half == "look" else building()
        p.spawn("rehearse:worker")
        assert "stage 1 worker launched in the background" in ctx(launched(p, "rehearse:worker", "bg-w1"))
        r = p.stop()
        assert r is None or "decision" not in r, r
        assert "worker running since" in p.rehearse("job")[0]
        if half == "build":
            fail(p, 0, who=dict(WORKER, agent_id="bg-w1"))
        stopped(p, dict(WORKER, agent_id="bg-w1"), "bg-w1")
        s = p.state()
        assert s["spawn"]["stopped"] and s["worker"]["outcome"] == ("no ending" if half == "look" else "passed"), s
        assert blocked(p.stop()), half  # the existing rules again
    print("a background worker in look and build: outcome recorded at its stop: ok")

    p = building()  # the foreground path is unchanged
    p.spawn("rehearse:worker")
    out = p.returned("rehearse:worker")
    assert "stage 1 build worker: neither" in ctx(out) and not p.state()["spawn"]["background"], out
    assert blocked(p.stop())
    print("the foreground path is unchanged: ok")

    def job_line(p, head):
        return [ln for ln in p.rehearse("job")[0].splitlines() if ln.startswith(head)][0]

    p = building()  # a background REWORK: build again with the findings; rehearse job tells the result
    fail(p, 0)
    p.spawn()
    launched(p, "rehearse:director", "bg-r1")
    stopped(p, DIRECTOR, "bg-r1", REWORK)
    s = p.state()
    assert s["phase"] == "build" and s["findings"] == ["only the sample"] and s["strikes"] == 1, s["phase"]
    assert "build stage 1 (start rehearse:worker)" in job_line(p, "next:")
    assert "asks for rework" in job_line(p, "last:")
    p = building()  # a background void: the director again, and the last line names the void
    fail(p, 0)
    p.spawn()
    launched(p, "rehearse:director", "bg-v1")
    p.write("main.py", prog(3) + "# changed while the director ran\n")
    stopped(p, DIRECTOR, "bg-v1", PASS)
    assert p.phase() == "build" and "main.py" in p.state()["verdicts"][-1]["void"]
    assert job_line(p, "next:") == "next: start rehearse:director again", job_line(p, "next:")
    assert "the verdict is void" in job_line(p, "last:")
    p = two_stage()  # a background PASS of stage 1: stage 2 starts with no spawn record
    p.rehearse(*S1_END)
    p.prompt("yes")
    p.edit("collect.py", COLLECT)
    p.spawn()
    launched(p, "rehearse:director", "bg-p1")
    stopped(p, DIRECTOR, "bg-p1", PASS)
    assert p.phase() == "look" and p.state()["stage"] == 2 and p.state()["spawn"] is None
    assert "look at stage 2" in job_line(p, "next:")
    print("background REWORK, void and PASS: rehearse job carries the result and the next step: ok")

    p = one_stage()  # a director spawned in look does not revive the stage's stopped worker record
    p.spawn("rehearse:worker")
    launched(p, "rehearse:worker", "bg-w9")
    stopped(p, dict(WORKER, agent_id="bg-w9"), "bg-w9")
    before = p.state()["spawn"]
    assert p.spawn() is None  # not ours to rewrite in look
    launched(p, "rehearse:director", "bg-d9")
    assert p.state()["spawn"] == before and blocked(p.stop()), p.state()["spawn"]
    print("a launch note updates only its own spawn record: ok")

    p = building()  # an interrupted background worker does not excuse a "fixed" report
    p.spawn("rehearse:worker")
    launched(p, "rehearse:worker", "bg-w8")
    r = p.stop()
    assert r is None or "decision" not in r, r
    p.report("fixed\n\n## Not verified\nnone\n")
    assert blocked(p.stop(), "say built, not verified"), p.stop()
    out = p.spawn()  # nor a director while it still runs
    assert denied(out) and "worker still running" in text(out), out
    print("Stop with a running worker: report checks first; no director while a worker runs: ok")
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print("job: all checks passed")
