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
import log as L  # noqa: E402

TMP = os.path.realpath(tempfile.mkdtemp(prefix="rehearse-job-"))
DATA = os.path.join(TMP, "plugin-data")
ENV = {k: v for k, v in os.environ.items()
       if not k.startswith(("CLAUDE_PLUGIN_OPTION_", "REHEARSE_", "EVAL_REHEARSE_"))}
ENV["CLAUDE_PLUGIN_DATA"] = DATA
UN = {"REHEARSE_CONFIRM_ENDING": "0"}
WORKER = {"agent_type": "rehearse:worker", "agent_id": "w1"}
DIRECTOR = {"agent_type": "rehearse:director", "agent_id": "d1"}
REVIEWERWHO = {"agent_type": "rehearse:reviewer", "agent_id": "r1"}
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

    def rehearse(self, *args, who=None, env=None, filt=None):
        """Run the command for real; the hook sees its output, or what a filter leaves of it (filt: text -> text)."""
        r = subprocess.run([sys.executable, BIN, *args], cwd=self.root, capture_output=True, text=True,
                           env=dict(ENV, **(env or {})))
        assert r.returncode == 0, r.stderr
        cmd = shlex.join(["rehearse", *args]) + (" 2>&1 | filter" if filt else "")
        return r.stdout, self.bash(cmd, filt(r.stdout) if filt else r.stdout, who, env)

    def cli(self, *args):
        """Run the command for real with NO hook call afterwards: the record is written, nothing has read it."""
        r = subprocess.run([sys.executable, BIN, *args], cwd=self.root, capture_output=True, text=True, env=ENV)
        assert r.returncode == 0, r.stderr
        return r.stdout

    def result(self, kind, who=None, **kw):
        """A REHEARSE-RESULT line the hook reads, for commands whose real run needs more than a test can give."""
        line = "REHEARSE-RESULT " + json.dumps(dict(run=self.state()["run_id"], kind=kind, **kw))
        return self.bash("rehearse " + kind, line, who)

    def spawn(self, kind="rehearse:director", env=None, prompt="go"):
        return self.pre("Agent", None, env, subagent_type=kind, description="x", prompt=prompt)

    def search(self, query, who=None, env=None):
        """A WebSearch call: a logged step that counts as a search."""
        return self.ev("PostToolUse", env, who, tool_name="WebSearch", tool_input={"query": query},
                       tool_response={"content": "results for " + query})

    def last_step(self):
        return [r for r in L.records(self.state()["run_folder"]) if "step" in r][-1]["step"]

    def stop_only(self, kind="rehearse:worker", env=None, msg="done"):
        """Only the SubagentStop: its output says whether the stop was held."""
        who = DIRECTOR if kind == "rehearse:director" else REVIEWERWHO if kind == "rehearse:reviewer" else WORKER
        return self.ev("SubagentStop", env, who, agent_transcript_path="/x", stop_hook_active=False,
                       last_assistant_message=msg)

    def returned(self, kind="rehearse:director", env=None):
        """The agent stops (SubagentStop), then its Agent call returns to the manager (PostToolUse)."""
        who = DIRECTOR if kind == "rehearse:director" else REVIEWERWHO if kind == "rehearse:reviewer" else WORKER
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

    def ask_calls(self, answers, env=None):
        """AskUserQuestion with the questions as asked: judgment calls word for word, or anything else."""
        return self.ev("PostToolUse", env, tool_name="AskUserQuestion",
                       tool_input={"questions": [{"question": q} for q in answers]},
                       tool_response={"questions": [], "answers": answers, "annotations": {}})

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


def decide(p, *flags, say="my answer"):
    """The user speaks (any words), then the manager records the stuck decision with rehearse stuck."""
    p.prompt(say)
    return p.rehearse("stuck", *flags)


def exhausted(p, who=WORKER, env=None, route="the obvious way", outcome="no result"):
    """The worker searched, tried one route, recorded it with the search step, and stops without the result."""
    p.search("other ways to do it", who, env)
    p.rehearse("tried", "--route", route, "--steps", p.last_step(), "--outcome", outcome, who=who, env=env)
    return p.returned("rehearse:worker", env)


def exhaust_loop(p, env=None):
    """From look or build: a worker searched and tried, stopped without the result; the manager reviewed with a
    logged search and found no candidate; failed --exhausted: the stage waits (headless: not fixed)."""
    p.spawn("rehearse:worker", env=env)
    exhausted(p, env=env)
    p.search("methods", None, env)
    p.rehearse("review", "--searched", p.last_step(), env=env)
    return p.rehearse("failed", "--exhausted", env=env)[1]


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
                       "--goal", "out_of_scope", "answer", "only the three lines",  # in an answer (3.0.1: answer)
                       "--stage-def", "only", "fix", "print the lines", "-", "-")
    s = p.state()
    assert s["phase"] == "look" and s["goal"]["done"] == {"text": "a: 1 b: 2 c: 3", "source": "request"}, so
    assert s["goal"]["out_of_scope"]["source"] == "answer"
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
    held = p.stop_only("rehearse:worker")  # a stop without the result and without a logged search is held
    assert blocked(held, "search first"), held
    out = exhausted(p)
    c = ctx(out)
    assert "stage 1 build worker: stopped without a pass" in c and "review its log" in c and "phase build" in c, c
    assert '"cmd": "python3 main.py"' in c and '"value": "a: 1"' in c, c
    assert denied(p.spawn("rehearse:worker"))  # gate one: a review first
    p.search("methods", None)
    p.rehearse("review", "--searched", p.last_step(), "--candidate", "the other way", "uses the export")
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
    print("Agent notes: only workers and the director; passed / relocked / stopped without a pass; stage passed: ok")

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
        exhaust_loop(p)  # the look worker's loop ends exhausted: the stage waits
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
    for k in ("ending", "confirmation", "findings", "spawn_fingerprint", "reopen", "worker", "review_due", "failed",
              "reviewer"):
        assert s[k] is None, k
    for k in ("created", "produced", "director_runs", "runs", "relocks", "verdicts", "config_edits", "tried", "reviews"):
        assert s[k] == [], k
    for k in ("failing_runs", "strikes", "project_edits_since_run", "code_edits_since_run", "workers"):
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
    assert "stopped without a pass" in ctx(exhausted(p)) and p.state()["strikes"] == 1 and p.state()["review_due"]
    p = one_stage()
    p.spawn("rehearse:worker")
    assert blocked(p.stop_only("rehearse:worker"), "search first") and p.state()["strikes"] == 0
    assert "no ending" in ctx(exhausted(p)) and p.state()["strikes"] == 1
    assert p.state()["review_due"]["half"] == "look" and denied(p.spawn("rehearse:worker"))  # the review first
    print("strikes: a stop without the result is recorded once earned; the next worker waits for a review: ok")

    p = building()
    for _ in range(3):
        p.spawn()
        p.verdict(REWORK)
    assert p.phase() == "build" and p.state()["strikes"] == 3  # a count is never failure
    assert not denied(p.spawn("rehearse:worker"))  # a REWORK needs no review: the findings are the candidates
    p = building(UN)
    for _ in range(3):
        p.spawn(env=UN)
        p.verdict(REWORK, env=UN)
    assert p.phase() == "build" and p.state()["strikes"] == 3
    print("strikes are records only: three REWORKs leave the stage in build, attended or headless: ok")

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
    assert not denied(p.edit("main.py", prog(2)))  # the relock is over: edits are allowed again after the look and the yes
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
    assert s["phase"] == "build" and s["start_director"] and s["confirmation"]["by"] == "auto", s["phase"]
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
    so, _ = p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "a", "contains", "a: 1", "--cite", "request")
    out = p.returned("rehearse:worker")
    assert "re-registered, fails" in ctx(out), (out, so[-300:], p.state()["worker"], p.phase())
    p = relocked()
    p.spawn("rehearse:worker")
    p.result("fetch", ok=True, fixture="f")
    p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "quiet", "exit_code", "0", "--cite", "request")
    assert "re-registered, already passes" in ctx(p.returned("rehearse:worker"))
    p = relocked()
    p.spawn("rehearse:worker")
    assert "no ending" in ctx(exhausted(p))
    print("look worker notes: re-registered fails / already passes / no ending: ok")

    # ================= stuck exits =================
    def stuck(env=None, run=False):
        """Stuck through the loop: a worker stops without a pass (searched, tried, recorded), the manager's review
        finds no candidate, and failed --exhausted is recorded: the stage waits (headless: not fixed)."""
        p = building(env)
        p.edit("main.py", prog(1))
        if run:
            p.rehearse("run", env=env)
        p.spawn("rehearse:worker", env=env)
        exhausted(p, env=env, outcome="b and c still fail")
        p.search("methods for the three lines", None, env)
        p.rehearse("review", "--searched", p.last_step(), env=env)
        p.rehearse("failed", "--exhausted", env=env)
        assert p.phase() == ("done.not_fixed" if env else "stuck"), p.phase()
        return p

    p = stuck()
    _, out = p.rehearse("stuck", "--try-again")  # structural: nobody has answered since the stage became stuck
    assert blocked(out, "no answer from the user") and p.phase() == "stuck" and p.state()["strikes"] == 1, out
    out = p.prompt("maybe later")
    assert p.phase() == "stuck" and "stuck answer: maybe later" in p.state()["notes"] and "rehearse stuck" in ctx(out)
    out = p.ask("what is stuck? what's going on?")  # the manager asked "Continue?"; the user asks back
    assert p.phase() == "stuck" and "rehearse stuck" in ctx(out), out
    p.prompt("change")  # the words alone decide nothing (3.0.0 reopened the stage on them)
    p.ask("stop here")
    s = p.state()
    assert s["phase"] == "stuck" and not s.get("stop_here") and not s["pending_change"] and s["strikes"] == 1, s
    so, _ = p.rehearse("stuck", "--change")  # change needs the user's second yes
    assert "--confirmed" in so and p.phase() == "stuck" and not p.state()["pending_change"], so
    so, _ = p.rehearse("stuck")
    assert "one of" in so and p.phase() == "stuck"
    p.rehearse("stuck", "--stop-here")
    assert p.state()["stop_here"] and blocked(p.stop(), '"not fixed"')
    p.report("not fixed: stuck\n\n## Not verified\nthe total\n")
    assert p.stop() is None and p.phase() == "done.not_fixed"
    p = stuck()
    decide(p, "--try-again")
    s = p.state()
    assert s["phase"] == "build" and s["strikes"] == 0 and s["failing_runs"] == 0 and not s["pending_change"]
    assert not s["start_director"] and "stuck decision: try again" in s["notes"]
    p = building()
    so, _ = decide(p, "--try-again")  # not stuck: refused by the command
    assert "accepted in stuck" in so and p.phase() == "build"
    p = stuck()
    decide(p, "--change", "--confirmed")
    s = p.state()
    assert s["phase"] == "look" and s["strikes"] == 0 and s["pending_change"] and s["reopen"]["why"] == "change"
    assert F.code_change(s["fp_activation"], s["fp_phase_entry"]) == ["main.py"]  # a new snapshot
    print("stuck: the words decide nothing (a paraphrase, a question, change, stop here); rehearse stuck does: ok")

    # ================= 3.0.1: no director while stuck; try again after a passing check =================
    p = stuck()
    assert denied(p.spawn()) and p.phase() == "stuck"
    p.write("main.py", prog(3))
    p.rehearse("run")  # the manager's own check passes while stuck: not counted, but remembered
    assert p.phase() == "stuck" and p.state()["strikes"] == 1
    _, out = decide(p, "--try-again")
    s = p.state()
    assert s["phase"] == "build" and s["start_director"] and "start rehearse:director" in text(out), out
    assert not denied(p.spawn()) and p.phase() == "judge"
    p.verdict(PASS)
    assert p.phase() == "done.passed"
    p = building()  # the director already judged that passing run: try again means a build worker, not the director
    p.write("main.py", prog(3))
    p.rehearse("run")
    for _ in range(3):
        p.spawn()
        p.verdict(REWORK)
    decide(p, "--try-again")
    assert p.phase() == "build" and not p.state()["start_director"]
    print("the director is refused while stuck; try again after a passing check goes to the director: ok")

    # ================= 3.0.1: results come from the command's own record, not the output =================
    cut = lambda t: "\n".join(ln[:200] for ln in t.splitlines())  # noqa: E731  cut -c1-200 breaks the JSON line
    p = building()
    p.write("main.py", prog(3))
    n = len(p.state()["runs"])
    _, out = p.rehearse("run", filt=cut)
    assert len(p.state()["runs"]) == n + 1 and p.state()["runs"][-1]["passing"] and not out, out
    p.rehearse("run", filt=lambda t: t[-600:])  # tail -c 600
    p.rehearse("run", filt=lambda t: "")  # > /dev/null
    assert len(p.state()["runs"]) == n + 3
    assert [r["result"] for r in L.records(p.state()["run_folder"]) if "step" in r][-3:] == ["run"] * 3
    p.rehearse("run")  # the full output: its printed line (with an id) is not applied a second time
    assert len(p.state()["runs"]) == n + 4
    with open(os.path.join(p.state()["run_folder"], "results.jsonl")) as f:
        last = f.read().splitlines()[-1]
    p.bash("cd /x/rehearse && grep REHEARSE-RESULT log.md", "REHEARSE-RESULT " + last)  # an echo of an old line
    assert len(p.state()["runs"]) == n + 4
    out = p.bash("rehearse run | tail -1", "")  # nothing recorded: the command did not run here
    assert "no result recorded" in text(out), out
    print("results from the command's record: cut, tail -c and a redirect lose nothing; an echo, the missing case: ok")

    p = building()  # the false strike: a build worker's passing run, filtered, then its stop
    p.spawn("rehearse:worker")
    p.edit("main.py", prog(3), WORKER)
    so, _ = p.rehearse("run", who=WORKER, filt=cut)
    out = p.returned("rehearse:worker")
    assert "passed" in ctx(out) and p.state()["strikes"] == 0, (out, so[-300:], p.state()["worker"], p.state()["runs"])
    print("a build worker's filtered passing run is no strike: ok")

    # ================= 3.0.1: the run folder's own records are written by the plugin only =================
    p = building()
    rf = p.state()["run_folder"]
    for who in (None, WORKER, DIRECTOR):
        assert denied(p.pre("Write", who, file_path=os.path.join(rf, "results.jsonl"), content="x"))
        assert denied(p.pre("Edit", who, file_path=os.path.join(rf, "state.json")))
        assert denied(p.pre("Bash", who, command="echo x >> %s/results.jsonl" % rf))
        assert denied(p.pre("Bash", who, command="cp /tmp/x %s/state.json" % rf))
        assert denied(p.pre("Bash", who, command="tee -a %s/commands.jsonl < /dev/null" % rf))
        assert denied(p.pre("Bash", who, command="cd %s && sed -i s/a/b/ log.md" % rf))
    assert not denied(p.pre("Bash", command="cat %s/results.jsonl" % rf))
    assert not denied(p.pre("Write", file_path=os.path.join(rf, "report.md"), content="x"))
    print("the run folder's records are refused to edit tools and shell writes, any phase, any caller: ok")

    p = building()  # (3.0.1 finding) --stage <current> --as-director on a one-stage job runs the live ending
    p.write("main.py", prog(3))
    p.spawn()
    so, _ = p.rehearse("run", "--stage", "1", "--as-director", who=DIRECTOR)
    assert p.state()["director_runs"][-1]["all_pass"] and "reruns" not in p.state()["stages"][0], so
    so, _ = p.rehearse("run", "--stage", "2", "--as-director", who=DIRECTOR)
    assert "current stage" in so and len(p.state()["director_runs"]) == 1, so
    print("run --stage for the current stage runs the live ending: ok")

    p = Proj({"main.py": prog(0)})  # (3.0.1 finding) a goal item from the user's answer is labelled answer
    p.prompt(REQ3)
    p.prompt("the purpose: a tidy report")
    g = ["--goal", "purpose", "answer", "a tidy report", "--goal", "deliverable", "request", "main.py",
         "--goal", "done", "assumed", "x", "--goal", "out_of_scope", "assumed", "y"]
    stg = ["--stage-def", "only", "fix", "x", "-", "-"]
    so, _ = p.rehearse("plan", *g, *stg)
    assert p.state()["goal"]["purpose"] == {"text": "a tidy report", "source": "answer"}, so
    q = Proj({"main.py": prog(0)})
    q.prompt(REQ3)
    q.prompt("the purpose: a tidy report")
    so, _ = q.rehearse("plan", "--goal", "purpose", "request", "a tidy report", *g[4:], *stg)
    assert "word for word in the request" in so and q.state()["stages"] == [], so
    so, _ = q.rehearse("plan", "--goal", "purpose", "answer", "nothing said", *g[4:], *stg)
    assert "the user's answers" in so and q.state()["stages"] == [], so
    print("goal sources: request, answer, assumed, each checked against its own text: ok")

    # ================= P4b: the Process section, computed by the plugin from the job file =================
    p = relocked()  # strike 1: a relock; then an edit refused while locked
    assert denied(p.pre("Edit", file_path=p.j("main.py")))
    p.result("fetch", ok=True, fixture="f")
    p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "a", "contains", "a: 1", "--cite", "request")
    p.prompt("yes")
    assert p.phase() == "build"
    p.spawn("rehearse:worker")
    exhausted(p)  # strike 2: a build worker stopped without a pass (searched, tried, recorded)
    p.spawn()
    p.verdict(REWORK)  # strike 3: REWORK with the finding "only the sample"; a count is never failure
    assert p.phase() == "build"
    p.search("methods", None)
    p.rehearse("review", "--searched", p.last_step())  # the manager's review: no candidate left
    p.rehearse("failed", "--exhausted")
    assert p.phase() == "stuck"
    p.prompt("what now?")
    decide(p, "--try-again")
    so, _ = p.rehearse("job")
    for want in ("## Process", "strikes: 3 (relock 1, build worker stopped without a pass 1, REWORK 1)",
                 "REWORK reasons (1):\n  - stage 1: only the sample", "refusals: edits are locked 1",
                 "stuck: 1 (try again); free-text answers while stuck: 2", "relocks: 1",
                 "routes tried: 1; reviews: 1; candidates dropped: 0; failed: stage 1: exhausted",
                 # 10 invocations: plan, ending, run, run, ending, tried, review, failed, stuck for real, plus the
                 # faked fetch line above, which no command wrote: the one without a record
                 "rehearse commands: 10; results recorded: 9; without a record: 1\n"):
        assert want in so, (want, so)
    assert "(since 3.1.0" not in so  # every step of this job was counted exactly
    p.bash("grep 'rehearse ending' log.md | head", "")  # quoted text is not an invocation
    assert "rehearse commands: 11; results recorded: 10; without a record: 1" in p.rehearse("job")[0]  # + the job call
    decide(p, "--stop-here")
    p.report("not fixed: stuck\n\n## Not verified\nnone\n")
    rpath = os.path.join(p.state()["run_folder"], "report.md")
    assert p.stop() is None and p.phase() == "done.not_fixed"
    rep = open(rpath).read()
    assert rep.count("## Process") == 1 and "strikes: 3 (relock 1," in rep and rep.startswith("not fixed"), rep
    assert p.stop() is None and open(rpath).read().count("## Process") == 1  # appended once
    p = building()  # a passed job gets it too
    fail(p, 0)
    p.spawn()
    p.verdict(PASS)
    p.report("fixed\n\n## Not verified\nnone\n")
    assert p.stop() is None and "strikes: 0 (none)" in open(os.path.join(p.state()["run_folder"], "report.md")).read()
    print("the Process section: strikes by cause, REWORK reasons, refusals, stuck answers, relocks; appended once: ok")

    def downgrade(p):
        """Make the job file 3.0.1-shaped: no strike_log, stuck_log or refusals; the steps and records as 3.0.1 wrote them."""
        s = p.state()
        for k in ("strike_log", "stuck_log", "refusals", "tried", "reviews", "review_due", "failed", "reviewer"):
            s.pop(k, None)  # the 4.0.0 loop records are missing too: a 3.x job file
        json.dump(s, open(s["path"], "w"))
        f = s["run_folder"]
        recs = [json.loads(ln) for ln in open(os.path.join(f, "commands.jsonl")) if ln.strip()]
        with open(os.path.join(f, "commands.jsonl"), "w") as fh:
            for r in recs:
                r.pop("rehearse", None)
                fh.write(json.dumps(r) + "\n")
        res = [json.loads(ln) for ln in open(os.path.join(f, "results.jsonl")) if ln.strip()]
        with open(os.path.join(f, "results.jsonl"), "w") as fh:
            for r in res:
                r.pop("at", None)
                fh.write(json.dumps(r) + "\n")

    p = two_stage()  # a 3.0.1-shaped job file goes through a stage PASS under 3.1.0 (archive with defaults)
    p.rehearse(*S1_END)
    p.prompt("yes")
    p.edit("collect.py", COLLECT)
    p.run_collect()
    p.spawn()
    p.verdict(REWORK)  # a strike nobody can log: stays unknown
    assert p.state()["strikes"] == 1
    downgrade(p)
    assert denied(p.pre("Edit", file_path=p.j("drafts/x.md")) or {}) is False  # a refusal log that is missing stays missing
    p.spawn("rehearse:worker")  # a worker stop in the old-shaped stage: held like any other, no crash on the missing list
    assert blocked(p.stop_only("rehearse:worker"), "search first")
    p.spawn()
    p.verdict(PASS)
    s = p.state()
    assert s["phase"] == "look" and s["stage"] == 2 and s["stages"][0]["passed"], s["phase"]
    assert s["stages"][0]["strike_log"] is None and s["stages"][0]["stuck_log"] is None and s["strike_log"] == []
    p.rehearse("job")
    so, _ = p.rehearse("job")  # unknown is never printed as zero; the first job call is the one exact command so far
    for want in ("strikes: 0 (none); not recorded for stage 1 (job predates 3.1.0)",
                 "stuck: 0 (none); not recorded for stage 1 (job predates 3.1.0)",
                 "refusals: not recorded (job predates 3.1.0)",
                 "routes tried: 0; reviews: 0; candidates dropped: 0; failed: none; not recorded for stage 1 "
                 "(job predates 4.0.0)",
                 "rehearse commands: 1; results recorded: 1; without a record: 0 (since 3.1.0; earlier: 3 commands by "
                 "text, 3 results recorded by 3.0.1,"):
        assert want in so, (want, so)
    assert "REWORK reasons (1):\n  - stage 1: only the sample" in so and "relocks: 0" in so
    print("a 3.0.1 job file: PASS archives with defaults; missing logs print as not recorded, never zero: ok")

    # ================= 3.1.0: self-healing: every unread record applies before a decision =================
    p = building()  # a build worker's passing run whose PostToolUse hook call never came: no false strike
    p.spawn("rehearse:worker")
    p.edit("main.py", prog(3), WORKER)
    p.cli("run")
    assert p.state()["runs"] == []
    out = p.returned("rehearse:worker")
    assert "passed" in ctx(out) and p.state()["strikes"] == 0 and p.state()["runs"][-1]["passing"], out
    p = building()  # the director's own run, its hook call missed: applied at its stop as a director run
    p.write("main.py", prog(3))
    p.spawn()
    p.cli("run", "--as-director")
    p.verdict(PASS)
    s = p.state()
    assert s["phase"] == "done.passed" and s["director_runs"][-1]["all_pass"], s["director_runs"]
    assert s["director_runs"][-1]["agent_type"] == "rehearse:director"
    p = building()  # the manager's passing run, missed: Stop reads it, so "fixed" is verified
    p.write("main.py", prog(3))
    p.spawn()
    p.verdict(PASS)
    p.cli("run")
    p.report("fixed\n\n## Not verified\nnone\n")
    assert p.stop() is None and p.state()["closed"], p.stop()
    p = building()  # a spawn decision: the missed passing run is read before the director is prepared
    p.write("main.py", prog(3))
    p.cli("run")
    p.spawn()
    assert p.state()["runs"][-1]["passing"] and p.phase() == "judge"
    p = stuck()  # rehearse stuck after a missed passing check: try again goes to the director
    p.write("main.py", prog(3))
    p.cli("run")
    p.prompt("try again")
    p.rehearse("stuck", "--try-again")
    assert p.phase() == "build" and p.state()["start_director"]
    print("self-healing: a missed hook call never costs a strike, a verdict, a verified report or a next step: ok")

    # ================= 3.1.1: no decision compares a raw OS time (the wall clock steps back on WSL2) =================
    def clock_back(p, seconds=5.0):
        """As if the wall clock had been ahead by `seconds` at the last stamp and then stepped back: the job file's
        stamps sit in the future of every later hook process."""
        s = p.state()
        s["clock"] = s.get("clock", 0) + seconds
        if s.get("worker"):
            s["worker"]["at"] += seconds
        json.dump(s, open(s["path"], "w"))
    p = building()  # a worker's run and stop after the clock stepped back since its spawn: still "passed"
    p.spawn("rehearse:worker")
    clock_back(p)
    p.edit("main.py", prog(3), WORKER)
    p.rehearse("run", who=WORKER)
    s = p.state()
    assert s["runs"][-1]["at"] >= s["worker"]["at"] and any("clock stepped back" in n for n in s["notes"]), s["notes"]
    assert "passed" in ctx(p.returned("rehearse:worker")) and p.state()["strikes"] == 0
    p = one_stage()  # a file written during the stage with a modification time from before the stage: still new
    p.write("tool.py", "print('x')\n")
    old = p.state()["started_at"] - 10
    os.utime(p.j("tool.py"), (old, old))
    assert denied(p.pre("Bash", command="python3 tool.py")), "a created file's age is not read from its mtime"
    big = p.j("big.py")  # a big file's signature is its content, not its modification time
    with open(big, "wb") as f:
        f.write(b"#" * (F.BIG + 100))
    sig1 = F._sig(big)
    st = os.stat(big)
    with open(big, "r+b") as f:
        f.seek(F.BIG + 50)
        f.write(b"!")
    os.utime(big, (st.st_atime, st.st_mtime))  # same size, same mtime, different bytes
    assert F._sig(big) != sig1 and F._sig(big).startswith("big:")
    q = two_stage()  # a same-size edit in the middle of a 3 MB declared output, mtime as the write sets it: void
    q.rehearse(*S1_END)
    q.prompt("yes")
    q.edit("collect.py", COLLECT)
    q.run_collect()
    with open(q.j("out", "items.md"), "wb") as f:
        f.write(b"x" * (3 * 1024 * 1024))
    q.spawn()
    with open(q.j("out", "items.md"), "r+b") as f:
        f.seek(1024 * 1024 + 7)
        f.write(b"y")
    q.verdict(PASS)
    assert q.phase() == "build" and "out/items.md" in q.state()["verdicts"][-1].get("void", ""), q.state()["verdicts"][-1]
    import datetime
    import state as S  # a later job of the same session sorts after an earlier one even if the clock stepped back

    class Earlier:  # the wall clock reads years earlier when the second job is created
        timezone, timedelta = datetime.timezone, datetime.timedelta

        class datetime(datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2020, 1, 1, tzinfo=tz)
    first = p.state()
    os.environ["CLAUDE_PLUGIN_DATA"] = DATA
    try:
        S.datetime = Earlier
        second = S.new_run(p.sid, p.root, "rehearse again", F.fingerprint(p.root))
        newest = S.newest(p.sid)["run_id"]
    finally:
        S.datetime = datetime
        del os.environ["CLAUDE_PLUGIN_DATA"]
    assert second["run_id"] > first["run_id"] and newest == second["run_id"], (first["run_id"], second["run_id"])
    print("no decision reads a raw OS time: worker outcome, a created file's age, big-file signature, job order: ok")

    # ================= 3.2.0: judgment calls are asked up front, as their own question =================
    p = one_stage()
    so, out = p.rehearse(*END3, "--call", "a: 1", "is a a tool?")
    s = p.state()
    assert s["phase"] == "confirm" and s["ending"]["calls"] == [{"requirement": "a: 1", "question": "is a a tool?",
                                                                 "answer": None}], s["ending"].get("calls")
    assert "judgment call" in ctx(out) and "is a a tool?" in ctx(out), out
    so, _ = p.rehearse(*END3, "--call", "zzz", "q")
    assert "no --expect has that requirement" in so and p.phase() == "confirm"
    out = p.ask_calls({"is a a tool?": "yes, a is a tool"})  # the call, asked word for word: not the confirmation
    s = p.state()
    assert s["phase"] == "confirm" and s["ending"]["calls"][0]["answer"] == "yes, a is a tool", s["ending"]["calls"]
    assert "judgment call answered" in ctx(out) and "yes, a is a tool" in s["prompts"], out
    p.ask("yes")
    assert p.phase() == "build"
    p = one_stage()  # the answer changes a check: the ending is registered again with the user's words, then confirmed
    p.rehearse(*END3, "--call", "a: 1", "is a a tool?")
    p.ask_calls({"is a a tool?": "no: a is not a tool, so it should print a: skipped"})
    assert p.phase() == "confirm" and not p.state()["confirmation"]
    so, _ = p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "a", "contains", "a: skipped", "--cite",
                       "request", "--expect", "b: 2", "contains", "b: 2", "--cite", "request")
    assert p.phase() == "confirm" and p.state()["ending"]["expectations"][0]["value"] == "a: skipped", so
    p.prompt("yes")  # the answers carried over to the re-registered ending: the confirmation is accepted
    assert p.phase() == "build"
    q = one_stage(UN)  # unattended: nobody is asked, so the call is recorded as not verified
    q.rehearse(*END3, "--call", "a: 1", "is a a tool?", env=UN)
    assert q.phase() == "build" and any("judgment call not put to a person: is a a tool?" in x
                                        for x in q.state()["not_verified"]), q.state()["not_verified"]
    print("judgment calls: tied to the check they decide, asked apart from the confirmation, recorded: ok")

    # ================= 3.2.0: stuck split: "these checks are wrong" keeps the work =================
    def stuck_run():
        """Stuck after a recorded run: main.py prints a: 1 only, so b and c fail; then the loop ends exhausted."""
        p = stuck(run=True)
        assert [r["requirement"] for r in S.failing(p.state())] == ["b: 2", "c: 3"]
        return p
    p = stuck_run()
    p.prompt("b and c are wrong: only a: 1 is required")
    so, _ = p.rehearse("stuck", "--correct")
    assert "--says" in so and p.phase() == "stuck"
    _, out = p.rehearse("stuck", "--correct", "--says", "only a: 1 is required")
    s = p.state()
    assert s["phase"] == "look" and s["reopen"]["why"] == "correct" and s["strikes"] == 0 and not s["pending_change"], out
    assert denied(p.pre("Edit", file_path=p.j("main.py")))  # the work stays, and stays locked
    p.rehearse("plan", "--stage", "1", "--stage-def", "only", "fix", "x", "-", "-")
    assert p.state()["stages"][0]["line"] == "print the three lines"  # correct does not rewrite the stage
    so, out = p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "a: 1", "contains", "a: 1", "--cite", "request")
    s = p.state()
    assert s["phase"] == "confirm" and "no look step" not in so and s["start_director"], (so, out)
    assert [(c["requirement"], c["before"], c["after"], c["user"]) for c in s["corrections"]] == [
        ("b: 2", "contains b: 2", None, "only a: 1 is required"), ("c: 3", "contains c: 3", None, "only a: 1 is required")]
    p.ask("yes")
    assert p.phase() == "build" and not denied(p.spawn())
    p.verdict(PASS)
    assert p.phase() == "done.passed"
    so, _ = p.rehearse("job")
    assert "corrected checks (2):" in so and "b: 2: contains b: 2 -> dropped (the user: only a: 1 is required)" in so, so
    p = stuck()  # "redo this stage" still needs a look step; correct is the only way round it
    decide(p, "--change", "--confirmed")
    so, _ = p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "a: 1", "contains", "a: 1", "--cite", "request")
    assert "no look step" in so and p.phase() == "look"
    p = final_stage()  # in the final stage, correct re-registers the job ending
    p.edit("drafts/summary.md", "summary: not yet\n")
    p.rehearse("run")  # the job ending fails on "draft"
    exhaust_loop(p)
    p.prompt("the draft is fine as it is")
    p.rehearse("stuck", "--correct", "--says", "the draft is fine as it is")
    assert p.phase() == "look" and p.state()["reopen"]["why"] == "correct" and p.state()["reopen"]["failing"] == ["draft"]
    print("stuck: these checks are wrong keeps the work, records each corrected check with the user's words: ok")

    # ================= 3.2.0 guards: correct is anchored to the user's words and the failing checks =================
    p = building()  # (1) --says must be the user's words from an answer since the stuck: not before, not a paraphrase
    p.prompt("only a: 1 is required")  # said before the stage got stuck: does not count
    p.edit("main.py", prog(1))
    p.rehearse("run")
    exhaust_loop(p)
    p.prompt("b and c are wrong")
    so, _ = p.rehearse("stuck", "--correct", "--says", "only a: 1 is required")
    assert "word for word" in so and p.phase() == "stuck", so
    out = p.result("stuck", ok=True, answer="correct", says="the user wants only a")  # a paraphrase, past the command
    assert blocked(out, "word for word") and p.phase() == "stuck", out
    p.prompt("only a: 1 is required")
    p.rehearse("stuck", "--correct", "--says", "only a: 1 is required")
    assert p.phase() == "look" and p.state()["reopen"]["why"] == "correct"
    p = stuck()  # no failing run recorded: correct has nothing to apply
    p.prompt("b is wrong")
    so, _ = p.rehearse("stuck", "--correct", "--says", "b is wrong")
    assert "nothing to apply" in so and p.phase() == "stuck"
    out = p.result("stuck", ok=True, answer="correct", says="b is wrong")
    assert blocked(out, "nothing to apply") and p.phase() == "stuck"
    print("correct: --says must be the user's words since the stuck; nothing to apply without a failing run: ok")

    p = stuck_run()  # (2) only the failing checks (b, c) may change: not a, not a new check, not the command
    p.prompt("only a: 1 is required")
    p.rehearse("stuck", "--correct", "--says", "only a: 1 is required")
    E = ["--cite", "request"]
    _, out = p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "a: 1", "contains", "b: 2", *E)  # a changed
    assert blocked(out, "correct may change only the checks that were failing (b: 2, c: 3)") and "a: 1" in out["reason"], out
    assert p.phase() == "look" and p.state()["reopen"]["why"] == "correct", p.phase()
    _, out = p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "a: 1", "contains", "a: 1", *E,
                        "--expect", "d", "contains", "a: 1", *E)
    assert blocked(out, "refused: d") and p.phase() == "look"
    _, out = p.rehearse("ending", "--cmd", "python3 main.py; true", "--expect", "a: 1", "contains", "a: 1", *E)
    assert blocked(out, "the command or the tests changed") and p.phase() == "look"
    _, out = p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "a: 1", "contains", "a: 1", *E)
    assert p.phase() == "confirm" and len(p.state()["corrections"]) == 2, out
    print("correct: only the failing checks may change, same command and tests: ok")

    p = one_stage()  # (3) the confirmation is refused while a judgment call has no recorded answer
    p.rehearse(*END3, "--call", "a: 1", "is a a tool?")
    out = p.ask("yes")  # the question tool asked something else
    assert p.phase() == "confirm" and not p.state()["confirmation"] and "is a a tool?" in ctx(out), out
    out = p.ask_calls({"Would you call a a tool?": "yes"})  # a paraphrase: not matched, refused
    assert p.phase() == "confirm" and p.state()["ending"]["calls"][0]["answer"] is None and "word for word" in ctx(out)
    out = p.prompt("yes it is")  # no question tool: the next message answers the first open call
    assert p.phase() == "confirm" and p.state()["ending"]["calls"][0]["answer"] == "yes it is" and "not asked yet" in ctx(out)
    p.prompt("yes")
    assert p.phase() == "build"
    print("the confirmation waits for every judgment call's recorded answer, and names the call to ask: ok")

    # ================= 4.0.0 step 1: modes and the fold of unattended into auto =================
    for prompt, mode, task in (("rehearse automate the export", "ask", "automate the export"),
                               ("rehearse auto automate the export", "auto", "automate the export"),
                               ("rehearse Auto fix it", "auto", "fix it"),
                               ("/rehearse auto the task", "auto", "the task"),
                               ("rehearse: auto out the cache", "ask", "auto out the cache"),  # the colon form escapes
                               ("rehearse maximum coverage", "ask", "maximum coverage")):
        q = Proj({})
        out = q.prompt(prompt)
        s = q.state()
        assert s and s["mode"] == mode and s["task"] == task and not s["headless"] and s["request"] == prompt, (prompt, s and s["mode"], s and s["task"])
        assert ("auto:" if mode == "auto" else "ask:") in ctx(out), (prompt, ctx(out)[-300:])
    q = Proj({})
    out = q.prompt("rehearse max out the cache")  # max is reserved: no job, a one-line refusal
    assert q.state() is None and "max is reserved" in out["systemMessage"], out
    q = Proj({})
    q.prompt("rehearse fix it", {"CLAUDE_PLUGIN_OPTION_MODE": "auto"})  # the setting picks the default
    assert q.state()["mode"] == "auto" and not q.state()["headless"]
    q = Proj({})
    q.prompt("rehearse fix it", {"REHEARSE_HEADLESS": "1"})
    assert q.state()["mode"] == "ask" and q.state()["headless"]
    q = Proj({})
    q.prompt("rehearse fix it", UN)  # the old confirm_ending=false: auto plus headless
    assert q.state()["mode"] == "auto" and q.state()["headless"]
    old = Proj({})  # a 3.x job file with the old flag reads as auto plus headless
    old.prompt(REQ3)
    s = old.state()
    s.pop("mode"); s.pop("headless"); s["attended"] = False
    json.dump(s, open(s["path"], "w"))
    assert S.headless(old.state()) and S.auto(old.state()) and "assumed" in S.next_step(old.state())
    print("modes: the word right after rehearse, the colon escape, max reserved, the setting, headless, legacy: ok")

    p = Proj({"README.txt": "x\n"})  # interactive auto: asks up front, accepts later
    out = p.prompt("rehearse auto " + REQ2[len("rehearse "):])
    assert p.state()["mode"] == "auto" and "ask the goal questions" in S.next_step(p.state())
    assert p.stop() is None  # waiting for the user in goal is allowed: someone can answer
    p.rehearse(*PLAN2)
    p.rehearse(*JOB_END)
    assert p.phase() == "job-confirm", p.phase()  # the job is confirmed up front
    p.prompt("yes")
    assert p.phase() == "look" and p.state()["job_confirmation"]["by"] == "user"
    _, out = p.rehearse(*S1_END, "--call", "items", "does a draft item count?")
    s = p.state()
    assert s["phase"] == "build" and s["confirmation"]["by"] == "auto" and "not confirmed by a person" in ctx(out), out
    assert any("judgment call not put to a person: does a draft item count?" in x for x in s["not_verified"])
    q = Proj({"README.txt": "x\n"})  # headless auto: nothing is asked, a wait is blocked with the next step
    q.prompt(REQ2, UN)
    assert "assumed" in S.next_step(q.state()) and blocked(q.stop(UN), "goal")
    print("auto: the goal, the plan and the job ending up front; stage endings and calls accepted and recorded: ok")

    # ================= 4.0.0 step 2: the failure records and the gates =================
    p = building()
    p.spawn("rehearse:worker")
    so, _ = p.rehearse("tried", "--route", "x", "--steps", "S999", "--outcome", "no", who=WORKER)
    assert "every step must be in the log" in so and p.state()["tried"] == []
    p.search("how do people export this", WORKER)
    s1 = p.last_step()
    rec = [r for r in L.records(p.state()["run_folder"]) if r.get("step") == s1][0]
    assert rec["tool"] == "WebSearch" and rec["cmd"].startswith("WebSearch: how do people"), rec
    p.rehearse("tried", "--route", "the page", "--steps", s1, "--outcome", "403", who=WORKER)
    assert p.state()["tried"][-1]["by"] == "rehearse:worker" and p.state()["tried"][-1]["steps"] == [s1]
    out = p.returned("rehearse:worker")
    assert "stopped without a pass" in ctx(out) and p.state()["review_due"], out
    so, _ = p.rehearse("review", "--searched", "S1", "--candidate", "the api", "an api")  # S1 is a Bash step
    assert "must be a logged search" in so and p.state()["reviews"] == []
    so, _ = p.rehearse("review", "--searched", s1, "--candidate", "the page", "same")
    assert "already tried" in so and p.state()["reviews"] == []
    _, out = p.rehearse("review", "--searched", s1, "--candidate", "the api", "an api", who=WORKER)  # its own records
    assert blocked(out, "fresh eyes") and p.state()["reviews"] == []
    so, _ = p.rehearse("failed", "--exhausted")
    assert "no review" in so and p.phase() == "build"
    p.search("export api", None)
    s2 = p.last_step()
    _, out = p.rehearse("review", "--searched", s2, "--candidate", "the api", "an api, not the page",
                        "--drop", "the page with a header", "a variant of the page")
    assert "1 candidate(s) untried" in ctx(out) and len(p.state()["reviews"]) == 1, out
    so, _ = p.rehearse("failed", "--exhausted")  # gate two: a candidate is untried
    assert "neither tried nor dropped: the api" in so and p.phase() == "build"
    ui = p.spawn("rehearse:worker")["hookSpecificOutput"]["updatedInput"]  # gate one passed: the candidates go along
    assert "untried candidates from the review" in ui["prompt"] and "the api (an api, not the page)" in ui["prompt"]
    assert "routes already tried" in ui["prompt"] and p.state()["review_due"] is None
    p.search("api docs", WORKER)
    p.rehearse("tried", "--route", "the api", "--steps", p.last_step(), "--outcome", "needs a key", who=WORKER)
    p.returned("rehearse:worker")
    p.rehearse("failed", "--needs", "an api key")  # every candidate of the latest review is tried: accepted
    s = p.state()
    assert s["phase"] == "stuck" and s["failed"]["needs"] == "an api key" and s["strikes"] == 2, s["phase"]
    assert "routes tried: 2; reviews: 1; candidates dropped: 1; failed: stage 1: needs an api key" in p.rehearse("job")[0]
    print("the loop: tried needs logged steps; a stop needs a search; a review needs a search and fresh eyes; "
          "failed needs the review's candidates tried or dropped: ok")

    p = one_stage()  # a one-stage job: the manager made the tried records, so the review needs the reviewer
    assert denied(p.spawn("rehearse:reviewer"))  # nothing to review yet
    p.search("ways", None)
    s3 = p.last_step()
    p.rehearse("tried", "--route", "the page", "--steps", s3, "--outcome", "403")
    _, out = p.rehearse("review", "--searched", s3)  # the manager reviewing its own tried records
    assert blocked(out, "fresh eyes"), out
    ui = p.spawn("rehearse:reviewer")["hookSpecificOutput"]["updatedInput"]
    assert "Routes tried so far" in ui["prompt"] and "the page: steps" in ui["prompt"] and ui["model"] == "opus", ui
    assert denied(p.pre("Edit", REVIEWERWHO, file_path=p.j("main.py")))  # reads and searches only
    assert denied(p.pre("Bash", REVIEWERWHO, command="echo x > notes.txt"))
    assert not denied(p.pre("Bash", REVIEWERWHO, command="cat main.py"))
    p.search("docs", REVIEWERWHO)
    _, out = p.rehearse("review", "--searched", p.last_step(), "--candidate", "the feed", "a feed", who=REVIEWERWHO)
    assert not blocked(out) and p.state()["reviews"][-1]["by"] == "rehearse:reviewer"
    out = p.returned("rehearse:reviewer")
    assert "reviewer: review recorded: 1 candidate(s) untried" in ctx(out), out
    p.search("feed", None)
    p.rehearse("tried", "--route", "the feed", "--steps", p.last_step(), "--outcome", "empty")
    p.rehearse("failed", "--exhausted")
    assert p.phase() == "stuck" and p.state()["failed"]["exhausted"]
    print("a one-stage job: the reviewer brings fresh eyes, reads and searches only; its candidates are tried: ok")

    # ================= 3.2.0: stop here is said to end the whole job =================
    p = building()
    p.write("main.py", prog(1))
    p.rehearse("run")  # a: 1 passes; b and c fail
    note = ctx(exhaust_loop(p))  # the failure's note: the stage waits with a solution-ready report
    assert "ends the whole rehearse job" in note and "solution-ready report" in note, note
    assert "failing checks: b: 2 (contains b: 2); c: 3 (contains c: 3)" in note, note
    so, _ = p.rehearse("job")
    assert "failing checks: b: 2" in so and "ends the whole rehearse job" in S.NEXT["stuck"]
    p.prompt("ok, stop")
    so, _ = p.rehearse("stuck", "--stop-here")
    assert "the whole rehearse job ends now" in so and p.state()["stop_here"]
    md = open(os.path.join(ROOT, "hooks", "instructions", "confirm.md")).read()
    assert "`stop here`: **ends the whole rehearse job now**" in md and "`these checks are wrong`" in md
    assert "`redo this stage`" in md and "Never frame this as" in md
    print("stop here is named as ending the whole job, in the note, the next step, the command and confirm.md: ok")

    p = stuck()  # after change: plan --stage for the current stage
    decide(p, "--change", "--confirmed")
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
    decide(p, "--change", "--confirmed")
    p.result("fetch", ok=True, fixture="f")
    _, out = p.rehearse("ending", "--cmd", "python3 main.py", "--expect", "a", "contains", "a: 1", "--cite", "request")
    assert p.phase() == "confirm" and "already passes" in ctx(out), out
    print("pending_change: plan --stage for the current stage only, cleared by an ending: ok")

    p = one_stage()
    p.spawn("rehearse:worker")
    exhausted(p)  # no ending after its loop: the manager may still put the question to the user
    _, out = p.rehearse("stuck", "--change", "--confirmed")  # structural: the user has not spoken since the stop
    assert blocked(out, "no answer from the user") and not p.state()["pending_change"], out
    so, out = decide(p, "--change", "--confirmed")
    s = p.state()
    assert s["pending_change"] and s["phase"] == "look", (out, so[-300:], s["worker"], s.get("user_answer_at"),
                                                           s["started_at"], s.get("clock"), s["notes"])
    so, _ = p.rehearse("plan", "--stage", "1", "--stage-def", "only", "fix", "smaller", "-", "-")
    assert p.state()["stages"][0]["line"] == "smaller", so
    print("an attended look blocker answered change: plan --stage accepted: ok")

    p = stuck()
    decide(p, "--change", "--confirmed")
    p.write("main.py", prog(3))
    p.rehearse("run")  # a passing run exits look: the mark is cleared
    assert p.phase() == "build" and not p.state()["pending_change"]
    fail(p, 3)
    fail(p, 3)
    assert p.phase() == "look"
    p.rehearse("plan", "--stage", "1", "--stage-def", "only", "fix", "x", "-", "-")
    assert p.state()["stages"][0]["line"] == "print the three lines"  # the passing run cleared the mark: refused
    p = stuck()
    decide(p, "--change", "--confirmed")
    p.rehearse("stuck", "--stop-here")
    assert not p.state()["pending_change"]
    p = one_stage()
    p.spawn("rehearse:worker")
    exhausted(p)
    decide(p, "--change", "--confirmed")
    assert p.state()["pending_change"] and denied(p.spawn("rehearse:worker"))  # gate one: the review first
    p.search("methods", None)
    p.rehearse("review", "--searched", p.last_step(), "--candidate", "the feed", "a feed, not the page")
    p.spawn("rehearse:worker")
    exhausted(p, route="the feed", outcome="empty feed")  # the candidate tried, no ending: a strike clears the mark
    assert p.state()["strikes"] == 1 and not p.state()["pending_change"]
    print("pending_change cleared by a passing run, stop here, try again and a strike: ok")

    p = final_stage()
    exhaust_loop(p)
    _, out = decide(p, "--change", "--confirmed")
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
        q.prompt(REQ2, env)  # the mode is fixed at activation
        assert (q.stop(env) is None) == (env is None)  # goal
        q.rehearse(*PLAN2)
        q.rehearse(*JOB_END, env=env)
        if env is None:
            assert q.phase() == "job-confirm" and q.stop() is None
            assert q.stop(UN) is None  # a variable set after activation changes nothing
            q.prompt("yes")
        else:
            assert q.phase() == "look" and q.state()["job_confirmation"]["by"] == "auto"
        q.rehearse(*S1_END, env=env)
        if env is None:
            assert q.phase() == "confirm" and q.stop() is None
            assert q.stop(UN) is None  # the mode is fixed at activation
        else:
            assert q.phase() == "build" and q.state()["confirmation"]["by"] == "auto"
    p = stuck()
    assert p.stop() is None
    q = Proj({})
    q.prompt(REQ2, UN)  # headless from activation
    q.rehearse(*PLAN2, env=UN)
    with_un = q.stop(UN)
    assert blocked(with_un, "register the job ending"), with_un
    print("Stop: ask may wait in goal, job-confirm, confirm, stuck; headless is blocked: ok")

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
    exhaust_loop(p)
    assert p.phase() == "stuck" and p.state()["code_edits_since_run"] == 5
    decide(p, "--change", "--confirmed")
    assert p.state()["code_edits_since_run"] == 0
    print("the ten-edit count resets on change: ok")

    p = one_stage()  # (4) the manager on the one-stage path may record "change" in look, no worker needed
    _, out = decide(p, "--change", "--confirmed")
    assert p.state()["pending_change"] and p.phase() == "look" and "plan --stage 1" in ctx(out), out
    q = one_stage(UN)
    q.prompt("change it", UN)
    _, out = q.rehearse("stuck", "--change", "--confirmed", env=UN)  # unattended: nobody was asked; refused
    assert blocked(out, "accepted in stuck") and not q.state()["pending_change"], out
    assert q.state()["prompts"] == ["change it"]
    print("stuck answers in an attended look without a worker: ok")

    p = building()  # (8) rehearse stop after done.passed without a report, and in done.not_fixed
    fail(p, 0)
    p.spawn()
    p.verdict(PASS)
    assert p.phase() == "done.passed" and blocked(p.stop(), "write report.md")
    p.prompt("rehearse stop")
    assert p.phase() == "done.cancelled" and p.stop() is None
    p = stuck(UN)  # headless: the loop's end is not fixed
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
    assert "auto, headless: nobody can answer" in ctx(out), out
    r = q.stop(UN)
    assert blocked(r, "then rehearse plan") and "ask the goal questions" not in r["reason"], r
    assert "ask: the user confirms the goal" in ctx(Proj({}).prompt(REQ2))
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
        bg = dict(WORKER, agent_id="bg-w1")
        if half == "build":
            fail(p, 0, who=bg)
        else:
            p.search("ways", bg)
            p.rehearse("tried", "--route", "the page", "--steps", p.last_step(), "--outcome", "403", who=bg)
        stopped(p, bg, "bg-w1")
        s = p.state()
        assert s["spawn"]["stopped"] and s["worker"]["outcome"].startswith("no ending" if half == "look" else "passed"), s
        assert blocked(p.stop()), half  # the existing rules again
    print("a background worker in look and build: outcome recorded at its stop: ok")

    p = building()  # the foreground path is unchanged
    p.spawn("rehearse:worker")
    out = exhausted(p)
    assert "stage 1 build worker: stopped without a pass" in ctx(out) and not p.state()["spawn"]["background"], out
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

    p = one_stage()  # a director launch note in look does not revive the stage's stopped worker record
    p.spawn("rehearse:worker")
    launched(p, "rehearse:worker", "bg-w9")
    bg = dict(WORKER, agent_id="bg-w9")
    p.search("other ways", bg)  # a stop without an ending is held unless a tried record cites a search
    p.rehearse("tried", "--route", "the obvious way", "--steps", p.last_step(), "--outcome", "no result", who=bg)
    stopped(p, bg, "bg-w9")
    assert p.state()["spawn"]["stopped"]
    before = p.state()["spawn"]
    assert denied(p.spawn())  # the director is refused outside build and judge (3.0.1)
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

    NOTE = "<task-notification>\n<task-id>a1</task-id>\n<status>completed</status>\n</task-notification>"
    q = Proj({})  # a background agent's completion arrives as a prompt: it is not the user's answer
    q.prompt(REQ2)
    for make in ("goal", "job-confirm", "confirm", "stuck"):
        if make == "job-confirm":
            q.rehearse(*PLAN2)
            q.rehearse(*JOB_END)
        if make == "confirm":
            q = two_stage()
            q.rehearse(*S1_END)
        if make == "stuck":
            q = building()
            exhaust_loop(q)
        before = q.state()
        assert before["phase"] == make, (make, before["phase"])
        for wrapped in (NOTE, "  " + NOTE, "<system-reminder>x</system-reminder>"):
            assert q.prompt(wrapped) is None
        s = q.state()
        assert (s["phase"], s["prompts"], s["redo"], s.get("stop_here")) == (
            before["phase"], before["prompts"], before["redo"], before.get("stop_here")), make
    q = two_stage()
    q.rehearse(*S1_END)
    q.prompt("no")  # a typed no still goes back to look
    assert q.phase() == "look" and q.state()["redo"] == "no"
    print("task notifications are not user prompts: ok")

    p = final_stage()  # the final stage is named as such, never "stage 3 of 2"
    so = p.rehearse("job")[0]
    assert "final stage (job ending), 2 of 2 stages passed" in so and "stage 3" not in so, so
    assert "next: build final stage (job ending)" in so, so
    ui = p.spawn("rehearse:worker")["hookSpecificOutput"]["updatedInput"]
    assert ui["prompt"].startswith("[rehearse] final stage (job ending) build\n") and "stage 3" not in ui["prompt"]
    assert "final stage (job ending) build worker" in ctx(p.returned("rehearse:worker"))
    r = p.stop()
    assert blocked(r, "final stage (job ending), phase build") and "stage 3" not in r["reason"], r
    print("the final stage's wording in rehearse job, notes and Stop reasons: ok")
except BaseException:
    # a failed check: show any hook error the hook swallowed (it fails open and logs here), then the traceback
    log = os.path.join(DATA, "hook-errors.log")
    if os.path.exists(log):
        print("hook-errors.log:\n" + open(log).read()[-3000:])
    raise
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print("job: all checks passed")
