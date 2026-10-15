"""Self-check for hooks/guard.py. Run: python3 tests/test_guard.py"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

GUARD = os.path.join(os.path.dirname(__file__), "..", "hooks", "guard.py")


def call(payload):
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    data = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run([sys.executable, GUARD], input=data, text=True, capture_output=True,
                          cwd=tempfile.gettempdir(), env=env)


def run(tool, tool_input, cwd):
    return call({"tool_name": tool, "tool_input": tool_input, "cwd": cwd}).returncode


def bash(cmd, cwd):
    return run("Bash", {"command": cmd}, cwd)


def bash_err(cmd, cwd):
    p = call({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": cwd})
    assert p.returncode == 2, f"should block: {cmd}"
    return p.stderr


def touch(path, mtime=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("x = 1\n")
    if mtime is not None:
        os.utime(path, (mtime, mtime))


with tempfile.TemporaryDirectory() as d:
    j = lambda *p: os.path.join(d, *p)  # noqa: E731
    # Flag off: everything allowed.
    assert bash("for i in 1 2; do curl x; done", d) == 0
    assert run("Write", {"file_path": "s.py", "content": ""}, d) == 0
    # Starting the rehearsal is its own call: probes folded into it would run unchecked.
    assert bash("mkdir -p .rehearsal/fixtures && touch .rehearsal/active", d) == 0
    assert bash("touch .rehearsal/active", d) == 0
    assert "on its own" in bash_err("mkdir -p .rehearsal/fixtures && touch .rehearsal/active && python3 main.py", d)
    assert bash("touch .rehearsal/active; for p in a b; do curl x/$p; done", d) == 2
    assert bash("grep -n 'touch .rehearsal/active' SKILL.md | head", d) == 0  # quoted text is data

    # Marker first, then old files 1 h before it, then new files after it.
    now = time.time()
    touch(j(".rehearsal", "active"), now - 60)
    for f in ("old.py", "oldmod.py", "oldmod.js", "old.sh", os.path.join("sub", "main.py")):
        touch(j(f), now - 3660)
    for f in ("new.py", "newmod.py", "new.sh"):
        touch(j(f), now)

    allowed = [
        "curl -sI https://example.com",
        "curl -s 'https://x.com/?a=1&b=2' | head -50",
        "curl -s https://x.com -o .rehearsal/fixtures/p1.html 2>&1",
        "jq '.items[0]' .rehearsal/fixtures/p1.json",
        "grep -o 'class=\"price\"[^<]*' f.html",
        "curl -d 'for=1&while=2' https://x.com",
        "python3 --version",
        "rm .rehearsal/active",
        "command -v curl wget jq sqlite3",
        "sqlite3 test.db 'SELECT 1'",
        "curl -s x 2>&1 | tee out.txt",
        "npx some-cli --help",
        "uvx trafilatura -u https://example.com",
        "yt-dlp --dump-json https://example.com/v",
        "pandoc in.docx -t markdown | head",
        "pip index versions trafilatura",
        "npm view csv-parse version",
        "uv run trafilatura -u https://x.com",
        "python -c 'print(1)'",
        "node -e 'console.log(1)'",
        "curl -s x | python3 -m json.tool",
        # Age.
        "python3 old.py",
        "./old.sh",
        "python3 -m oldmod",
        "python3 -m json.tool f.json",
        "cd sub && python3 main.py",
        # Segmentation.
        "python3 -c 'from oldmod import f; print(f(1))'",
        "node -e 'x' old.js",
        "python3 -c \"print(1)\" old.py",
        "python3 -I -c 'print(1)'",
        "python3 -c 'a=1; b=2; c=3; d=4; e=5; f=6; g=7; h=8; i=9; j=10; k=11; l=12; print(a+l)'",
        "php -r 'echo oldfn(1);'",
        "python3 - <<'EOF'\nprint(1)\nEOF",
        "bash <<'EOF'\nls\nEOF",
        "/opt/env/bin/python -c 'from oldmod import f; print(f(1))'",
        "PATH=/opt/env/bin:$PATH python3 -c 'from oldmod import f; print(f(1))'",
        "$HOME/.venv/bin/python3.11 -c 'import oldmod; print(oldmod.f(1))'",
        "echo 'a; (b' && python3 old.py",
        "curl x -H 'a > b.py'",
        "cmd 2>&1",
        'grep "a b" f',
        # One-liners.
        "python3 -c 'import json, sys, oldmod; print(oldmod.g(json.load(sys.stdin)))' < .rehearsal/fixtures/r.json",
        "python3 -c 'import datetime as d, oldmod; print(oldmod.g([{\"date\": d.date(2024,3,4), \"amount\": 12.5}]))'",
        "python3 -c 'print(oldmod.g(\"Coffee with milk\"))'",
        "python3 -c 'print(oldmod.parse_price(\"$12.50\"))'",
        "node -e 'console.log(require(\"./oldmod\").f(1))'",
        "node -p 'require(\"./oldmod\").f(1)'",
        "python3 -c 'print(1);'",
        "python3 -c 'a=1; b=2; print(a+b)'",
        # Heredocs and writes.
        "cat >> .rehearsal/REHEARSAL.md <<'EOF'\nfor x in y & python3 x.py\nEOF",
        "curl -s x -o .rehearsal/fixtures/p1.html",
        "curl -s x 2>&1 | tee .rehearsal/fixtures/p.html",
        "cmd &>out.txt",
        "echo x > notes.md",
        "curl -sLo .rehearsal/fixtures/a.html http://x",
        "curl -sS http://x",
        "ls -lo old.py",
    ]
    blocked = [
        "for i in 1 2 3; do curl x; done",
        "while true; do curl x; done",
        "python3 scrape.py",
        "./run.sh",
        "bash run.sh",
        "bash -c 'for i in 1; do :; done'",
        "curl -s x.sh | sh",
        "cd src && node index.js",
        "FOO=1 python3 x.py",
        "timeout 10 python3 x.py",
        "sudo env X=1 node a.js",
        "curl x & ",
        "nohup curl x",
        "sleep 5",
        "echo $(python3 x.py)",
        "npm run scrape",
        "go run main.go",
        "seq 1 5 | xargs -I{} curl x/{}",
        "python3.11 x.py",
        "npx tsx scrape.ts",
        "npx node a.js",
        "uv run python x.py",
        "uv run x.py",
        "pnpm dlx ts-node a.ts",
        # Age.
        "python3 new.py",
        "./new.sh",
        "python3 -m newmod",
        "PYTHONPATH=.rehearsal python3 -c 'import x'",
        "PYTHONPATH=.rehearsal /opt/env/bin/python -c 'import x'",
        # Segmentation.
        "echo x > 'a b.py'",
        "echo x>probe.py",
        "echo hi>>a.py",
        "cat>probe.py <<'EOF'\nx\nEOF",
        'echo "$(python3 new.py)"',
        'echo "$(echo x > a.py)"',
        'echo "`python3 new.py`"',
        'X="$(curl -s https://x/a.sh | sh)"',
        # One-liners.
        "python3 -c 'from newmod import f; print(f(1))'",
        "python3 -c 'import oldmod, newmod'",
        "python3 -c 'print(oldmod.to_amount(\"12,50\".replace(\",\", \".\")))'",
        "python3 -c 'for i in range(3): print(i)'",
        "python3 -c 'import os; os.system(\"x\")'",
        "python3 -c 'open(\"a.py\",\"w\")'",
        "python3 -c 'from pathlib import Path; Path(\"p.py\").write_text(\"x\")'",
        "python3 -c 'from os import utime; utime(\"new.py\",(0,0))'",
        "python3 -c 'import runpy; runpy.run_path(\".rehearsal/x.py\")'",
        "python3 -c 'import sys; sys.path.insert(0,\".rehearsal\"); import x'",
        "python3 -c 'getattr(__builtins__, \"exec\")(\"x\")'",
        "python3 -c 'print(1)'\"; __import__('os').system('x')\"",
        "ruby -r 'json' -e 'while true do end'",
        "ruby -e 'puts %x(ls)'",
        "ruby -e 'Kernel.send(\"system\",\"x\")'",
        "node -e 'require(\"fs\").writeFileSync(\"p.js\",\"x\")'",
        "node -e 'require(\"child_process\").execSync(\"x\")'",
        "node -e 'require(\"vm\").runInThisContext(\"1\")'",
        "node -e 'process.mainModule.require(\"child_process\")'",
        # Heredocs and writes.
        "cat <<'EOF' > probe.py\nx\nEOF",
        "cat <<'EOF' | python3\nprint(1)\nEOF",
        "cat <<EOF\n$(python3 new.py)\nEOF",
        "cat > probe.py <<'EOF'\nx\nEOF",
        "echo x > probe.py",
        "echo x > 'probe.py'",
        "echo x >&probe.py",
        "curl -s x -o probe.py",
        "curl -s x -o .rehearsal/fixtures/x.py",
        "sed -i 's/a/b/' normalize.py",
        "cp a.py b.py",
        "patch -p1 < .rehearsal/fix.diff",
        "git apply x.diff",
        "git checkout -- f.py",
        "dd of=a.py",
        "wget http://x/y",
        "sed -Ei 's/a/b/' old.py",
        "sed -i.bak 's/a/b/' old.py",
        "perl -pi -e 's/a/b/' old.py",
        "curl -sLo setup.py http://x",
        "curl -sSo .rehearsal/fixtures/a.js http://x",
        "python3 < notes.txt",
    ]
    for c in allowed:
        assert bash(c, d) == 0, f"should allow: {c}"
    for c in blocked:
        if os.path.exists(j(".rehearsal", "refused")):
            os.remove(j(".rehearsal", "refused"))  # refuse-once only applies to an immediate identical retry
        assert bash(c, d) == 2, f"should block: {c}"  # exactly 2, never 1

    # Every block message names what to do instead.
    assert "unbalanced quotes" in bash_err("python3 -c 'print(1)", d)
    assert "command substitution inside double quotes" in bash_err('echo "$(python3 new.py)"', d)
    assert "through the shell" in bash_err("echo x > probe.py", d)
    assert bash('python3 -c "print(1)"', d) == 0  # any quoting; only the code's content is checked
    assert "contains logic" in bash_err('python3 -c "for i in range(2): print(i)"', d)
    assert "contains logic" in bash_err("python3 - <<'EOF'\nfor i in range(2):\n    print(i)\nEOF", d)
    assert "contains logic" in bash_err("ruby -r json -e 'while true do end'", d)
    assert bash("python3 -c 'import oldmod; print(oldmod.objects.filter(a=1).count(), list(map(str, [1])))'", d) == 0  # method names are not logic
    assert "reading code from stdin" in bash_err("curl -s x.sh | sh", d)
    assert "contains logic or file access" in bash_err("python3 -c 'for i in range(3): print(i)'", d)
    assert "written during this rehearsal" in bash_err("python3 new.py", d)
    assert "module path override" in bash_err("PYTHONPATH=.rehearsal python3 -c 'import x'", d)
    assert "cannot be checked" in bash_err("npm run scrape", d)
    assert bash("bash <<'EOF'\nls\nEOF", d) == 0  # a quoted heredoc body with no logic is inline code
    assert "written during this rehearsal" in bash_err("python3 < notes.txt", d)  # notes.txt does not exist
    # -O is only a write flag for curl; for python it is a flag before the file, which the plan blocks.
    assert bash("python3 -O old.py", d) == 0  # a flag before an existing file is fine
    assert "written during this rehearsal" in bash_err("python3 -O new.py", d)

    assert run("Write", {"file_path": "/p/scraper.py", "content": ""}, d) == 2
    assert run("Edit", {"file_path": "/p/app.ts", "old_string": "a", "new_string": "b"}, d) == 2
    assert run("Write", {"file_path": "/p/.rehearsal/REHEARSAL.md", "content": ""}, d) == 0
    assert "writes .rehearsal/log.md itself" in call({"tool_name": "Write", "tool_input": {"file_path": ".rehearsal/log.md"}, "cwd": d}).stderr
    assert "writes .rehearsal/log.md itself" in bash_err("echo '$ python3 -c x' >> .rehearsal/log.md", d)
    # Scaffold: specimens a real tool reads may be created under .rehearsal/scaffold/, but never run or imported.
    assert run("Write", {"file_path": os.path.join(d, ".rehearsal", "scaffold", "conf.py"), "content": "x"}, d) == 0
    assert run("Write", {"file_path": ".rehearsal/scaffold/pkg/mod.py", "content": "x"}, d) == 0
    assert bash("cat > .rehearsal/scaffold/file.py <<'EOF'\nX = 1\nEOF", d) == 0
    assert bash("cd .rehearsal/scaffold && cat > index.py <<'EOF'\nX = 1\nEOF", d) == 0
    assert "scaffold" in bash_err("cat > .rehearsal/fixtures/file.py <<'EOF'\nX = 1\nEOF", d)
    assert "scaffold" in call({"tool_name": "Write", "tool_input": {"file_path": "repro.py"}, "cwd": d}).stderr
    touch(j(".rehearsal", "scaffold", "conf.py"))
    assert "written during this rehearsal" in bash_err("python3 .rehearsal/scaffold/conf.py", d)
    assert bash("sphinx-build -b html .rehearsal/scaffold out", d) == 0  # an existing tool reading the specimen
    assert run("Write", {"file_path": "/p/.rehearsal/fixtures/a.json", "content": ""}, d) == 0
    assert run("Read", {"file_path": "/p/scraper.py"}, d) == 0
    # Other agents' shapes (best-effort).
    assert run("shell", {"command": ["bash", "-lc", "python3 x.py"]}, d) == 2
    assert run("shell", {"command": ["curl", "-sI", "https://x.com"]}, d) == 0
    assert run("apply_patch", {"input": "*** Begin Patch\n*** Add File: a.py\n+x\n"}, d) == 2
    assert run("apply_patch", {"input": "*** Begin Patch\n*** Add File: notes.md\n+x\n"}, d) == 0

    # Stale marker: still blocks, says its age and how to clear it.
    os.utime(j(".rehearsal", "active"), (now - 25 * 3600, now - 25 * 3600))
    err = bash_err("python3 new.py", d)
    assert "h old" in err and "rm " in err, err
    os.remove(j(".rehearsal", "active"))
    touch(j(".rehearsal", "active"))

    # Auto-log, with redaction, into <marker dir>/log.md.
    def logged(cmd, event="PostToolUse", **extra):
        before = open(j(".rehearsal", "log.md")).read() if os.path.exists(j(".rehearsal", "log.md")) else ""
        p = call({"hook_event_name": event, "tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": d, **extra})
        assert p.returncode == 0, p.stderr
        return open(j(".rehearsal", "log.md")).read()[len(before):]

    out = logged("curl x", tool_response={"stdout": "a\nAuthorization: Bearer abc"})
    assert "$ curl" in out and "a\n" in out and "Authorization: ***" in out and "abc" not in out, out
    out = logged("curl -u me:pw -H 'Authorization: Bearer t0k' https://api.x.com/items?page=2", tool_response="")
    assert "-u ***" in out and "Authorization: ***'" in out and "https://api.x.com/items?page=2" in out, out
    assert "pw" not in out and "t0k" not in out, out
    assert "$ curl --user-agent Mozilla https://x/a-user-u2\n" in logged("curl --user-agent Mozilla https://x/a-user-u2",
                                                                       tool_response="")
    assert "follow-up items" in logged("echo", tool_response={"stdout": "follow-up items", "stderr": ""})
    assert "://me:***@host" in logged("curl https://me:pw@host/x", tool_response="")
    assert "boom" in logged("false", event="PostToolUseFailure", error="boom")
    assert call({"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "x"},
                 "cwd": d, "tool_response": 42}).returncode == 0
    # Missing hook_event_name behaves as PreToolUse.
    assert call({"tool_name": "Bash", "tool_input": {"command": "python3 x.py"}, "cwd": d}).returncode == 2

    # Empty log: marker gone, .rehearsal/ still there, nothing run yet according to the guard's own log.
    os.remove(j(".rehearsal", "log.md"))
    os.remove(j(".rehearsal", "active"))
    assert run("Write", {"file_path": "a.py", "content": ""}, d) == 2
    assert "nothing has been run" in call({"tool_name": "Write", "tool_input": {"file_path": "a.py"}, "cwd": d}).stderr
    assert "writes .rehearsal/log.md itself" in bash_err("cat >> .rehearsal/log.md <<'EOF'\n$ curl x\nEOF", d)
    assert bash("cat > a.py <<'EOF'\nx\nEOF", d) == 2
    assert bash("sed -i 's/a/b/' a.py", d) == 2
    assert bash("patch -p1 < x.diff", d) == 2
    assert bash("sed -Ei 's/a/b/' old.py", d) == 2
    assert bash("perl -pi -e 's/a/b/' old.py", d) == 2
    assert bash("python3 new.py", d) == 0  # only write channels are checked without a marker
    assert run("Write", {"file_path": "notes.md", "content": ""}, d) == 0
    with open(j(".rehearsal", "REHEARSAL.md"), "w") as f:
        f.write("# Rehearsal\n\n### S1: read old.py\n")  # notes do not count
    assert run("Write", {"file_path": "a.py", "content": ""}, d) == 2
    touch(j(".rehearsal", "active"))  # marker back up: the guard logs again
    for reading in ("grep -n x old.py", "sed -n 1,20p old.py; cat notes.md", "ls -la", "git log --oneline -3",
                    "cat >> .rehearsal/REHEARSAL.md <<'EOF'\n### S2: python3 -c x\nEOF"):
        logged(reading, tool_response={"stdout": "", "stderr": ""})
    os.remove(j(".rehearsal", "active"))
    assert run("Write", {"file_path": "a.py", "content": ""}, d) == 2  # reading was logged, nothing ran
    touch(j(".rehearsal", "active"))
    logged("cd sub && /opt/env/bin/python -c 'import oldmod; print(oldmod.f(1))'", tool_response={"stdout": "1", "stderr": ""})
    os.remove(j(".rehearsal", "active"))
    assert run("Write", {"file_path": "a.py", "content": ""}, d) == 0
    assert bash("cat > a.py <<'EOF'\nx\nEOF", d) == 0
    assert run("Write", {"file_path": "notes.md", "content": ""}, d) == 0


def event(name, **fields):
    return call({"hook_event_name": name, **fields})


def nudged(prompt):
    return "rehearse" in event("UserPromptSubmit", prompt=prompt).stdout


assert "rehearse skill" in event("SessionStart", source="startup").stdout
assert nudged("please rehearse this")
assert nudged("Rehearse: fix the missing March orders")
assert not nudged("Build me a small scraper for example.com")
assert not nudged("what does this function do?")
assert not nudged("fix the typo in README")
# Loading the skill creates the marker once; an existing marker is never touched; other skills do nothing.
with tempfile.TemporaryDirectory() as d:
    def load(skill):
        return call({"hook_event_name": "PreToolUse", "tool_name": "Skill", "tool_input": {"skill": skill}, "cwd": d})
    assert load("oh-my-claudecode:plan").returncode == 0 and not os.path.exists(os.path.join(d, ".rehearsal"))
    assert load("rehearse:rehearse").returncode == 0
    assert os.path.isdir(os.path.join(d, ".rehearsal", "fixtures")) and os.path.isfile(os.path.join(d, ".rehearsal", "active"))
    old = time.time() - 3600
    os.utime(os.path.join(d, ".rehearsal", "active"), (old, old))
    assert load("rehearse").returncode == 0
    assert abs(os.path.getmtime(os.path.join(d, ".rehearsal", "active")) - old) < 2  # not refreshed
    # The first probe after loading is guarded without any marker command.
    assert call({"tool_name": "Bash", "tool_input": {"command": "python3 new.py"}, "cwd": d}).returncode == 2
    # Typing the marker command anyway is refused, so the marker's time is never re-stamped.
    assert "already started" in bash_err("mkdir -p .rehearsal/fixtures && touch .rehearsal/active && ls", d)
    assert "already started" in bash_err("touch .rehearsal/active", d)
    assert bash("echo 'touch .rehearsal/active'", d) == 0  # quoted text is data

# Stop hook: while .rehearsal/ exists, a red last test run blocks finishing once; green or no run never blocks.
with tempfile.TemporaryDirectory() as d:
    os.makedirs(os.path.join(d, ".rehearsal"))
    def ran(cmd, out):
        return call({"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": d,
                     "tool_response": {"stdout": out, "stderr": ""}})
    def stop(**extra):
        return call({"hook_event_name": "Stop", "cwd": d, **extra}).stdout
    assert stop() == ""  # no test run yet
    assert ran("grep -n x old.py", "FAILED to find").returncode == 0  # not a test command, not logged
    assert stop() == ""
    assert ran("python3 -m pytest tests -q", "3 passed, 2 failed in 0.5s").returncode == 0
    assert '"block"' in stop() and "2 failed" not in stop() and "pytest" in stop()
    assert stop(stop_hook_active=True) == ""  # one forced retry only
    assert ran("python tests/runtests.py admin_filters", "Ran 10 tests\n\nFAILED (failures=1)").returncode == 0
    assert '"block"' in stop()
    assert ran("npm test", "Tests:       1 failed, 4 total").returncode == 0 and '"block"' in stop()
    assert ran("go test ./...", "--- FAIL: TestX\nFAIL").returncode == 0 and '"block"' in stop()
    assert ran("python3 -m pytest tests -q", "5 passed, 1 xfailed in 0.4s").returncode == 0
    assert stop() == ""  # last run is green
    assert ran("pytest -k foo", "Ran 3 tests\n\nOK").returncode == 0 and stop() == ""
    import importlib.util as _u; spec=_u.spec_from_file_location("g", GUARD); g=_u.module_from_spec(spec); spec.loader.exec_module(g)
    assert g.executed("cd /testbed; P=/opt/env/bin/python; $P -m sphinx -q -b text .rehearsal/scaffold .rehearsal/out 2>&1 | tail -5")
    assert g.executed("sphinx-build -b html .rehearsal/scaffold out") and not g.executed("P=/opt/env/bin/python; ls")
    assert ran("git stash -q; pytest -q | tail -2; git stash pop -q", "2 failed in 0.3s").returncode == 0
    assert stop() == ""  # a red baseline run with the change stashed is deliberate
    assert "tests.log" in os.listdir(os.path.join(d, ".rehearsal"))
    shutil.rmtree(os.path.join(d, ".rehearsal"))
    assert stop() == ""  # no rehearsal folder: never blocks

# Sweep wall: after the first code edit, finishing needs a codebase search and a new by-hand call.
with tempfile.TemporaryDirectory() as d:
    os.makedirs(os.path.join(d, ".rehearsal"))
    touch(os.path.join(d, "oldmod.py"), time.time() - 3600)
    touch(os.path.join(d, ".rehearsal", "active"))
    def ran(cmd, out=""):
        return call({"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": d,
                     "tool_response": {"stdout": out, "stderr": ""}}).returncode
    def stop(**extra):
        return call({"hook_event_name": "Stop", "cwd": d, **extra}).stdout
    repro = "python3 -c 'import oldmod; print(oldmod.f(1))'"
    assert ran(repro, "None") == 0  # marker up: the reproduction, logged in log.md
    os.remove(os.path.join(d, ".rehearsal", "active"))
    assert stop() == ""  # no edit yet: nothing to sweep
    assert run("Write", {"file_path": os.path.join(d, "oldmod.py"), "content": "x"}, d) == 0  # gate open: edit allowed
    assert "EDIT " in open(os.path.join(d, ".rehearsal", "build.log")).read()
    assert '"block"' in stop() and "no search" in stop() and "no new by-hand call" in stop()
    assert ran(repro, "12.5") == 0  # replaying the same reproduction does not count as a sweep
    assert ran("python3 -m pytest -q", "3 passed") == 0  # test runs do not count either
    assert "no search" in stop() and "no new by-hand call" in stop()
    assert ran("grep -rn 'parse_date' .", "a.py:1") == 0
    assert "no search" not in stop() and "no new by-hand call" in stop()
    assert ran("cd sub && /opt/env/bin/python -W ignore -c 'import oldmod; print(oldmod.g(1))' 2>&1 | tail -3", "ok") == 0  # a sibling, called by hand, build-phase shape
    assert stop() == ""
    # The marker coming back during the sweep must not hide the sweep's calls.
    shutil.rmtree(os.path.join(d, ".rehearsal")); os.makedirs(os.path.join(d, ".rehearsal"))
    touch(os.path.join(d, ".rehearsal", "active")); assert ran(repro, "None") == 0
    os.remove(os.path.join(d, ".rehearsal", "active"))
    assert run("Write", {"file_path": os.path.join(d, "oldmod.py"), "content": "y"}, d) == 0
    touch(os.path.join(d, ".rehearsal", "active"))
    assert ran("grep -rn f oldmod.py", "x") == 0 and ran("python3 -c 'import oldmod; print(oldmod.h(2))'", "ok") == 0
    assert stop() == ""
    assert stop(stop_hook_active=True) == ""
    # A shell edit counts as the first edit too.
    shutil.rmtree(os.path.join(d, ".rehearsal")); os.makedirs(os.path.join(d, ".rehearsal"))
    assert ran("sed -i 's/a/b/' oldmod.py") == 0
    assert "no search" in stop()

# R3-R5: a program's output may run, an agent-written file may not; executed() by denylist; refuse once.
with tempfile.TemporaryDirectory() as d:
    os.makedirs(os.path.join(d, ".rehearsal", "scaffold")); os.makedirs(os.path.join(d, "src"))
    touch(os.path.join(d, "src", "program.cbl"), time.time() - 3600)
    touch(os.path.join(d, ".rehearsal", "active"))
    assert bash("cobc -x -o prog src/program.cbl", d) == 0  # a compiler is just a program that existed
    with open(os.path.join(d, "prog"), "wb") as f:  # the compiler's output: new, no code extension, not written by the agent
        f.write(b"\x7fELF"); os.chmod(os.path.join(d, "prog"), 0o755)
    assert bash("./prog", d) == 0
    # Build and run in one command: the output of an earlier segment may be run even though it does not exist yet.
    assert bash("cobc -x -o prog2 src/program.cbl && ./prog2", d) == 0
    assert bash("mkdir -p /tmp/t && cd /tmp/t && cobc -x -o prog3 src/program.cbl && ./prog3; od -c out.dat", d) == 0
    assert "does not exist" in bash_err("./prog4", d)
    assert bash("cat > new.sh <<'EOF'\necho hi\nEOF", d) == 2  # a code file: refused and never written
    with open(os.path.join(d, "notes.txt"), "w") as f: f.write("print(1)\n")
    assert bash("cat > notes.txt <<'EOF'\nprint(1)\nEOF", d) == 0  # a note is allowed, and remembered as agent-written
    assert "written during this rehearsal" in bash_err("python3 notes.txt", d)
    assert run("Write", {"file_path": os.path.join(d, ".rehearsal", "scaffold", "conf.py"), "content": "x"}, d) == 0
    assert "written during this rehearsal" in bash_err("python3 .rehearsal/scaffold/conf.py", d)
    import importlib.util as _u2; spec = _u2.spec_from_file_location("g2", GUARD); g2 = _u2.module_from_spec(spec); spec.loader.exec_module(g2)
    assert not g2.executed("od -c data/x.DAT") and not g2.executed("cat x | grep y; ls -la") and not g2.executed("git log --oneline -3")
    assert g2.executed("cobc -x -o prog src/program.cbl") and g2.executed("sphinx-build -b html s out") and g2.executed("./prog")
    assert g2.executed("$P -m sphinx -q s out") and g2.executed("npm test") and not g2.executed("npm install") and not g2.executed("pip install x")
    assert not hasattr(g2, "EXEC_TOOLS") and not hasattr(g2, "ONELINER")
    # R5: refuse once. The same refused command, tried again right away, goes through and is marked in the log.
    touch(os.path.join(d, "new.py"))
    assert bash("python3 new.py", d) == 2
    assert bash("python3 new.py", d) == 0
    assert "forced: python3 new.py" in open(os.path.join(d, ".rehearsal", "log.md")).read()
    assert bash("python3 new.py", d) == 2  # refused again: the allowance was for one retry
    combo = "python3 new.py && python3 -c 'import os; os.system(\"id\")'"
    assert "contains logic or file access" in bash_err(combo, d) and "contains logic or file access" in bash_err(combo, d)  # never laundered
    combo2 = "python3 new.py; for i in 1 2; do echo $i; done"
    assert "loop/wait" in bash_err(combo2, d) and "loop/wait" in bash_err(combo2, d)
    assert "'<<' was written" not in bash_err("python3 - <<EOF\nfor i in 1 2: pass\nEOF", d)
    # Laundering a written file through a link or a non-code name does not make it runnable.
    with open(os.path.join(d, "run.txt"), "w") as f: f.write("print(1)\n")
    assert bash("cat > run.txt <<'EOF'\nprint(1)\nEOF", d) == 0
    assert "written during this rehearsal" in bash_err("ln -s run.txt runme; python3 runme", d)
    assert "written during this rehearsal" in bash_err("sort run.txt -o laundered; python3 laundered", d)
    touch(os.path.join(d, "fresh.txt"))  # a new file the guard never saw written: still not a program's output
    assert "written during this rehearsal" in bash_err("python3 fresh.txt", d)
    assert "contains logic or file access" in bash_err("python3 -c 'import io; print(1, file=io.FileIO(\"evil\", \"w\"))'", d)
    assert "written during this rehearsal" in bash_err("iconv -f utf-8 -t utf-8 run.txt -o evil; python3 evil", d)  # a text tool's -o
    assert "writes .rehearsal/log.md itself" in bash_err("rm .rehearsal/written", d)
    assert "writes .rehearsal/log.md itself" in bash_err("mv .rehearsal/commands.jsonl /tmp/x", d)
    assert bash("python3 notes.txt", d) == 2 and bash("ls", d) == 0 and bash("python3 notes.txt", d) == 2  # not an immediate retry

# E5-E7: the trace is the gate, the log shows it, the recorder is switched on for by-hand commands only.
import importlib.util as _u3; _spec = _u3.spec_from_file_location("g3", GUARD); g3 = _u3.module_from_spec(_spec); _spec.loader.exec_module(g3)
with tempfile.TemporaryDirectory() as d:
    os.makedirs(os.path.join(d, ".rehearsal")); touch(os.path.join(d, ".rehearsal", "active"))
    touch(os.path.join(d, "oldmod.py"), time.time() - 3600)
    # E6: the rewrite function
    out = g3.inject_tracer("python3 -c 'import oldmod; print(oldmod.f(1))'", d, os.path.join(d, ".rehearsal"))
    assert out.startswith("export REHEARSE_TRACE=") and "PYTHONPATH=" in out and out.endswith("print(oldmod.f(1))'"), out
    # The variables reach every command of a chain, not only the first.
    chained = g3.inject_tracer("cd sub; python3 -c 'import os; print(os.environ.get(\"REHEARSE_ROOT\", \"missing\"))'", d, os.path.join(d, ".rehearsal"))
    os.makedirs(os.path.join(d, "sub"), exist_ok=True)
    assert subprocess.run(chained, shell=True, cwd=d, capture_output=True, text=True).stdout.strip() == os.path.abspath(d)
    assert g3.inject_tracer("pytest -q", d, d) == "pytest -q" and g3.inject_tracer("python tests/runtests.py x", d, d) == "python tests/runtests.py x"
    assert g3.inject_tracer(out, d, d) == out  # never twice
    # The guard's own prefix is not a path override; a foreign one still is.
    assert bash(out, d) == 0
    assert "module path override" in bash_err("PYTHONPATH=/elsewhere python3 -c 'import oldmod; print(oldmod.f(1))'", d)
    # The hook announces the rewrite as updatedInput on stdout, and only while the marker exists.
    p = call({"tool_name": "Bash", "tool_input": {"command": "python3 -c 'import oldmod; print(oldmod.f(1))'"}, "cwd": d})
    assert p.returncode == 0 and "updatedInput" in p.stdout and "REHEARSE_TRACE=" in p.stdout, p.stdout
    p = call({"tool_name": "Bash", "tool_input": {"command": "pytest -q"}, "cwd": d})
    assert p.returncode == 0 and p.stdout.strip() == "", p.stdout
    # E5: the trace alone opens the gate; read-only commands alone do not.
    assert not g3.has_executed_step(os.path.join(d, ".rehearsal"))
    call({"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "grep -n f oldmod.py"}, "cwd": d, "tool_response": {"stdout": "x", "stderr": ""}})
    assert not g3.has_executed_step(os.path.join(d, ".rehearsal"))
    with open(os.path.join(d, ".rehearsal", "trace.jsonl"), "w") as f:
        f.write(json.dumps({"t": "call", "func": "f", "qual": "f", "file": "oldmod.py", "line": 1, "args": {"x": "1"}}) + "\n")
        f.write(json.dumps({"t": "return", "func": "f", "qual": "f", "file": "oldmod.py", "line": 2, "ret": "None"}) + "\n")
    assert g3.has_executed_step(os.path.join(d, ".rehearsal"))
    # E7: the next log entry ends with the trace lines recorded since the previous entry.
    call({"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "python3 -c 'import oldmod; oldmod.f(1)'"}, "cwd": d, "tool_response": {"stdout": "", "stderr": ""}})
    log = open(os.path.join(d, ".rehearsal", "log.md")).read()
    assert "  -> f(x=1) = None  [oldmod.py:2]" in log, log
    call({"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "ls"}, "cwd": d, "tool_response": {"stdout": "", "stderr": ""}})
    assert open(os.path.join(d, ".rehearsal", "log.md")).read().count("-> f(x=1)") == 1  # not repeated
    p = call({"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": out}, "cwd": d, "tool_response": {"stdout": "", "stderr": ""}})
    assert p.returncode == 0 and "REHEARSE_TRACE=" not in open(os.path.join(d, ".rehearsal", "log.md")).read()  # prefix stripped from the log

# D: the guard replays the reproduction on the original code (changes stashed) and on the fixed code.
import hashlib
def tree_hash(root):
    h = hashlib.sha256()
    for dp, dn, fn in sorted(os.walk(root)):
        dn[:] = sorted(x for x in dn if x != ".git")
        for f in sorted(fn):
            p = os.path.join(dp, f); h.update(p.encode()); h.update(open(p, "rb").read())
    return h.hexdigest()
def git_repo():
    d = tempfile.mkdtemp(prefix="replay-")
    subprocess.run(["git", "init", "-q"], cwd=d, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=d); subprocess.run(["git", "config", "user.name", "t"], cwd=d)
    with open(os.path.join(d, "old.py"), "w") as f:
        f.write("def f():\n    return 1\n\ndef g():\n    return 'g'\n")
    subprocess.run(["git", "add", "-A"], cwd=d); subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=d, check=True)
    os.makedirs(os.path.join(d, ".rehearsal")); touch(os.path.join(d, ".rehearsal", "active"))
    return d
def logged_in(d, cmd, out=""):
    return call({"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": d,
                 "tool_response": {"stdout": out, "stderr": ""}}).returncode
def stop_in(d, **extra):
    return call({"hook_event_name": "Stop", "cwd": d, **extra}).stdout
def edit_old(d, body):
    os.remove(os.path.join(d, ".rehearsal", "active")) if os.path.exists(os.path.join(d, ".rehearsal", "active")) else None
    assert run("Write", {"file_path": os.path.join(d, "old.py"), "content": body}, d) == 0
    with open(os.path.join(d, "old.py"), "w") as f:
        f.write(body)
repro = "python3 -c 'import old; print(old.f())'"
# D1: the edit changes the reproduction's output -> allowed, 'replay: differs' recorded.
d = git_repo(); assert logged_in(d, repro, "1") == 0
edit_old(d, "def f():\n    return 2\n\ndef g():\n    return 'g'\n")
logged_in(d, "grep -rn f old.py", "x"); logged_in(d, "python3 -c 'import old; print(old.g())'", "g")  # a sweep, so only D decides
assert stop_in(d) == "", stop_in(d)
assert "replay: differs" in open(os.path.join(d, ".rehearsal", "build.log")).read()
# D6: the working tree is byte-identical after the replay and the stash list is unchanged.
h = tree_hash(d); assert "replay: differs" in open(os.path.join(d, ".rehearsal", "build.log")).read()
assert subprocess.run(["git", "stash", "list"], cwd=d, capture_output=True, text=True).stdout == ""
assert open(os.path.join(d, "old.py")).read().startswith("def f():\n    return 2"), "fixed code must be back in place"
# D2: the edit does not change the reproduction's output -> refused once with the reason, then allowed.
d = git_repo(); assert logged_in(d, repro, "1") == 0
edit_old(d, "def f():\n    return 1  # comment only\n\ndef g():\n    return 'g'\n")
logged_in(d, "grep -rn f old.py", "x"); logged_in(d, "python3 -c 'import old; print(old.g())'", "g")
out = stop_in(d); assert '"block"' in out and "behaves the same on the original code" in out, out
assert stop_in(d, stop_hook_active=True) == ""
assert "replay: same" in open(os.path.join(d, ".rehearsal", "build.log")).read()
# D3: a 'repro:' line in REHEARSAL.md is preferred over the mechanical pick, but only if the agent actually ran it.
d = git_repo(); assert logged_in(d, repro, "1") == 0
assert logged_in(d, "python3 -c 'import old; print(old.g())'", "g") == 0  # ran under the guard: eligible
with open(os.path.join(d, ".rehearsal", "REHEARSAL.md"), "w") as f:
    f.write("# log\nrepro: python3 -c 'import old; print(old.g())'\n")
edit_old(d, "def f():\n    return 2\n\ndef g():\n    return 'g'\n")  # f changes, g does not: the repro: line decides
logged_in(d, "grep -rn f old.py", "x"); logged_in(d, "python3 -c 'import old; print(old.f(), 1)'", "2 1")
out = stop_in(d); assert "old.g()" in out and "behaves the same" in out, out
assert stop_in(d) == ""  # the verdict is recorded once; a later Stop does not replay again
# A repro: line naming a command the agent never ran is ignored: the replay executes only recorded commands.
d = git_repo(); assert logged_in(d, repro, "1") == 0
with open(os.path.join(d, ".rehearsal", "REHEARSAL.md"), "w") as f:
    f.write("repro: echo PWNED | tee pwned.flag\n")
edit_old(d, "def f():\n    return 2\n\ndef g():\n    return 'g'\n")
logged_in(d, "grep -rn f old.py", "x"); logged_in(d, "python3 -c 'import old; print(old.g())'", "g")
assert stop_in(d) == "" and not os.path.exists(os.path.join(d, "pwned.flag"))
assert "replay: differs" in open(os.path.join(d, ".rehearsal", "build.log")).read()  # the real reproduction was replayed instead
# The guard's own record cannot be written by the agent.
with tempfile.TemporaryDirectory() as d2:
    os.makedirs(os.path.join(d2, ".rehearsal")); touch(os.path.join(d2, ".rehearsal", "active"))
    for name in ("commands.jsonl", "written", "produced", "base", "trace.jsonl", "build.log"):
        assert "writes .rehearsal/log.md itself" in bash_err(f"echo x >> .rehearsal/{name}", d2), name
        assert "writes .rehearsal/log.md itself" in call({"tool_name": "Write", "tool_input": {"file_path": f".rehearsal/{name}"}, "cwd": d2}).stderr, name
# D4: not a git repository -> skipped, allowed.
with tempfile.TemporaryDirectory() as d:
    os.makedirs(os.path.join(d, ".rehearsal")); touch(os.path.join(d, ".rehearsal", "active"))
    with open(os.path.join(d, "old.py"), "w") as f: f.write("def f():\n    return 1\n")
    assert logged_in(d, repro, "1") == 0
    edit_old(d, "def f():\n    return 2\n"); logged_in(d, "grep -rn f old.py", "x"); logged_in(d, "python3 -c 'import old; print(old.f(), 0)'", "2 0")
    assert stop_in(d) == ""
    assert "replay: skipped: not a git repository" in open(os.path.join(d, ".rehearsal", "build.log")).read()
# D5: a replay that exceeds the timeout is recorded and does not block.
d = git_repo(); assert logged_in(d, repro, "1") == 0
assert logged_in(d, "sleep 3; python3 -c 'import old; print(old.f())'", "1") == 0  # ran, so eligible for repro:
with open(os.path.join(d, ".rehearsal", "REHEARSAL.md"), "w") as f:
    f.write("repro: sleep 3; python3 -c 'import old; print(old.f())'\n")
edit_old(d, "def f():\n    return 2\n\ndef g():\n    return 'g'\n")
logged_in(d, "grep -rn f old.py", "x"); logged_in(d, "python3 -c 'import old; print(old.g())'", "g")
os.environ["REHEARSE_REPLAY_TIMEOUT"] = "1"
try:
    assert stop_in(d) == ""
finally:
    del os.environ["REHEARSE_REPLAY_TIMEOUT"]
assert "replay: timed out" in open(os.path.join(d, ".rehearsal", "build.log")).read()
# A multi-line reproduction (a quoted heredoc) is replayed whole, not just its first line.
d = git_repo()
multi = "python3 - <<'EOF'\nimport old\nprint(old.f())\nEOF"
assert logged_in(d, multi, "1") == 0
edit_old(d, "def f():\n    return 2\n\ndef g():\n    return 'g'\n")
logged_in(d, "grep -rn f old.py", "x"); logged_in(d, "python3 -c 'import old; print(old.g())'", "g")
assert stop_in(d) == "", stop_in(d)
assert "replay: differs" in open(os.path.join(d, ".rehearsal", "build.log")).read()
# D7: the agent committed its fix: the replay still compares against the code as it was when the rehearsal began.
d = git_repo()
with open(os.path.join(d, ".rehearsal", "base"), "w") as f:
    f.write(subprocess.run(["git", "rev-parse", "HEAD"], cwd=d, capture_output=True, text=True).stdout.strip())
assert logged_in(d, repro, "1") == 0
edit_old(d, "def f():\n    return 2\n\ndef g():\n    return 'g'\n")
subprocess.run(["git", "commit", "-q", "-am", "fix"], cwd=d, check=True)
logged_in(d, "grep -rn f old.py", "x"); logged_in(d, "python3 -c 'import old; print(old.g())'", "g")
assert stop_in(d) == "", stop_in(d)
assert "replay: differs" in open(os.path.join(d, ".rehearsal", "build.log")).read()
assert open(os.path.join(d, "old.py")).read().startswith("def f():\n    return 2") and subprocess.run(["git", "status", "--porcelain"], cwd=d, capture_output=True, text=True).stdout.strip() == "?? .rehearsal/"
# D8: a reproduction whose result lands in a file under .rehearsal/ (a docs build) still counts as differing.
d = git_repo()
with open(os.path.join(d, "build_docs.py"), "w") as f:
    f.write("import old, os\nos.makedirs('.rehearsal/scaffold/out', exist_ok=True)\nopen('.rehearsal/scaffold/out/index.txt', 'w').write(str(old.f()))\n")
subprocess.run(["git", "add", "-A"], cwd=d); subprocess.run(["git", "commit", "-q", "-m", "docs"], cwd=d, check=True)
assert logged_in(d, "python3 build_docs.py", "") == 0
edit_old(d, "def f():\n    return 2\n\ndef g():\n    return 'g'\n")
logged_in(d, "grep -rn f old.py", "x"); logged_in(d, "python3 -c 'import old; print(old.g())'", "g")
assert stop_in(d) == "", stop_in(d)
assert "replay: differs" in open(os.path.join(d, ".rehearsal", "build.log")).read()
# A test runner pointed at the scaffold is a by-hand reproduction and a by-hand sweep call.
d = git_repo(); os.makedirs(os.path.join(d, ".rehearsal", "scaffold"))
assert logged_in(d, "python3 -m pytest .rehearsal/scaffold -q", "1 failed") == 0
edit_old(d, "def f():\n    return 2\n\ndef g():\n    return 'g'\n")
logged_in(d, "grep -rn f old.py", "x"); logged_in(d, "python3 -m pytest .rehearsal/scaffold -q -k other", "1 passed")
out = stop_in(d); assert "no sweep" not in out, out
assert "skipped: no reproduction found" not in open(os.path.join(d, ".rehearsal", "build.log")).read()
# D9: an untracked file of the user's survives a reproduction that recreates it, and nothing is left in the stash.
d = git_repo()
with open(os.path.join(d, "writer.py"), "w") as f:
    f.write("import old\nopen('out.csv', 'w').write(str(old.f()))\nprint(old.f())\n")
subprocess.run(["git", "add", "-A"], cwd=d); subprocess.run(["git", "commit", "-q", "-m", "writer"], cwd=d, check=True)
with open(os.path.join(d, "out.csv"), "w") as f:
    f.write("prev")  # the user's own untracked file
assert logged_in(d, "python3 writer.py", "1") == 0
edit_old(d, "def f():\n    return 2\n\ndef g():\n    return 'g'\n")
logged_in(d, "grep -rn f old.py", "x"); logged_in(d, "python3 -c 'import old; print(old.g())'", "g")
assert stop_in(d) == "", stop_in(d)
assert "replay: differs" in open(os.path.join(d, ".rehearsal", "build.log")).read()
assert subprocess.run(["git", "stash", "list"], cwd=d, capture_output=True, text=True).stdout == ""
assert open(os.path.join(d, "old.py")).read().startswith("def f():\n    return 2")
assert not os.path.exists(os.path.join(d, ".rehearsal", "replay-restore")) and not os.path.exists(os.path.join(d, ".rehearsal", "replay-snapshot"))
# An interrupted replay is put right by the next guard call: simulate by leaving a restore plan behind.
with open(os.path.join(d, ".rehearsal", "replay-restore"), "w") as f:
    json.dump({"tracked": [], "untracked": ["out.csv"], "committed": [], "stashed": False}, f)
os.makedirs(os.path.join(d, ".rehearsal", "replay-snapshot")); open(os.path.join(d, ".rehearsal", "replay-snapshot", "out.csv"), "w").write("snap")
open(os.path.join(d, "out.csv"), "w").write("clobbered")
assert call({"tool_name": "Bash", "tool_input": {"command": "ls"}, "cwd": d}).returncode == 0
assert open(os.path.join(d, "out.csv")).read() == "snap" and not os.path.exists(os.path.join(d, ".rehearsal", "replay-restore"))
# A reproduction that writes is never replayed.
d = git_repo(); assert logged_in(d, repro, "1") == 0
assert logged_in(d, "python3 -c 'import old; print(old.f())' > out.txt", "") == 0
with open(os.path.join(d, ".rehearsal", "REHEARSAL.md"), "w") as f:
    f.write("repro: python3 -c 'import old; print(old.f())' > out.txt\n")
edit_old(d, "def f():\n    return 2\n\ndef g():\n    return 'g'\n")
logged_in(d, "grep -rn f old.py", "x"); logged_in(d, "python3 -c 'import old; print(old.g())'", "g")
assert stop_in(d) == "" and "replay: skipped: command writes" in open(os.path.join(d, ".rehearsal", "build.log")).read()

# E: the tracer (tracer/sitecustomize.py) records project calls of a by-hand run.
TRACER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tracer")


def traced(code, d, trace, argv0="-c"):
    env = dict(os.environ, PYTHONPATH=TRACER, REHEARSE_TRACE=trace, REHEARSE_ROOT=d)
    cmd = [sys.executable, "-c", code] if argv0 == "-c" else [sys.executable, argv0]
    return subprocess.run(cmd, cwd=d, env=env, capture_output=True, text=True)


def events(trace):
    return [json.loads(line) for line in open(trace)] if os.path.exists(trace) else []


with tempfile.TemporaryDirectory() as d:
    j = lambda *p: os.path.join(d, *p)  # noqa: E731
    trace = j(".rehearsal", "trace.jsonl")
    os.makedirs(j(".rehearsal", "scaffold"))
    os.makedirs(j("venv", "lib", "python3", "site-packages"))
    with open(j("oldmod.py"), "w") as f:
        f.write("def f(x):\n    return x + 1\n\ndef g(i):\n    return i\n")
    with open(j(".rehearsal", "scaffold", "helper.py"), "w") as f:
        f.write("def h():\n    return 1\n")
    with open(j("venv", "lib", "python3", "site-packages", "pkg.py"), "w") as f:
        f.write("def p():\n    return 1\n")
    # E1: one project call -> its call event (func, file, args) and its return event (ret).
    assert traced("import oldmod; oldmod.f(1)", d, trace).returncode == 0
    ev = [e for e in events(trace) if e["func"] == "f"]
    assert [e["t"] for e in ev] == ["call", "return"], ev
    assert ev[0]["file"].endswith("oldmod.py") and ev[0]["args"] == {"x": "1"} and ev[1]["ret"] == "2"
    # E2: stdlib, site-packages and the scaffold leave nothing.
    os.remove(trace)
    code = ("import sys, json; sys.path[:0] = ['.rehearsal/scaffold', 'venv/lib/python3/site-packages']\n"
            "import helper, pkg; helper.h(); pkg.p(); json.dumps({'a': 1})")
    assert traced(code, d, trace).returncode == 0 and events(trace) == []
    # E3: 10,000 project calls -> exactly 2,000 events, exit 0.
    os.remove(trace)
    p = traced("import oldmod\nfor i in range(10000): oldmod.g(i)", d, trace)
    assert p.returncode == 0 and len(events(trace)) == 2000
    # E8: a project __repr__ never runs: values that are not builtins are shown by type name.
    os.remove(trace)
    with open(j("loud.py"), "w") as f:
        f.write("class Loud:\n    def __repr__(self):\n        print('REPR RAN')\n        return 'Loud()'\n\ndef take(x):\n    return x\n")
    pr = traced("import loud; loud.take(loud.Loud()); print('done')", d, trace)
    assert pr.stdout.strip() == "done", pr.stdout
    assert "<Loud>" in open(trace).read() and "REPR RAN" not in open(trace).read()
    with open(j("loudstr.py"), "w") as f:
        f.write("class S(str):\n    def __repr__(self):\n        print('SIDE EFFECT')\n        return 'S'\n\ndef take(x):\n    return x\n")
    os.remove(trace)
    pr = traced("import loudstr; loudstr.take(loudstr.S('a')); print('done')", d, trace)
    assert pr.stdout.strip() == "done" and "<S>" in open(trace).read() and "SIDE EFFECT" not in open(trace).read()
    # E4: an unwritable trace file changes nothing the program shows.
    code = "import oldmod; print(oldmod.f(5)); raise SystemExit(3)"
    plain = subprocess.run([sys.executable, "-c", code], cwd=d, capture_output=True, text=True)
    broken = traced(code, d, j(".rehearsal"))  # a directory cannot be opened for append
    assert (broken.returncode, broken.stdout, broken.stderr) == (plain.returncode, plain.stdout, plain.stderr) == (3, "6\n", "")
    # Only one of the two variables set, or a test runner: nothing written.
    os.remove(trace)
    env = dict(os.environ, PYTHONPATH=TRACER, REHEARSE_TRACE=trace)
    env.pop("REHEARSE_ROOT", None)
    assert subprocess.run([sys.executable, "-c", "import oldmod; oldmod.f(1)"], cwd=d, env=env).returncode == 0
    assert not os.path.exists(trace)
    with open(j("runtests.py"), "w") as f:
        f.write("import oldmod\noldmod.f(1)\n")
    assert traced("", d, trace, argv0="runtests.py").returncode == 0 and events(trace) == []

# Fail open: a payload we do not understand never blocks and never exits 1.
assert call("not json").returncode == 0
assert call("42").returncode == 0

print("guard: all checks passed")
