"""Self-check for hooks/guard.py. Run: python3 tests/test_guard.py"""
import json
import os
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
        "mkdir -p .rehearsal/fixtures && touch .rehearsal/active",
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
        "python3 -c \"print(1)\" old.py",
        "node -e 'x' old.js",
        "PYTHONPATH=.rehearsal python3 -c 'import x'",
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
        "python3 -c 'a=1; b=2; print(a+b)'",
        "python3 -c 'print(1)'\"; __import__('os').system('x')\"",
        "python3 -I -c 'print(1)'",
        "ruby -r 'json' -e 'loop{}'",
        "ruby -e 'puts %x(ls)'",
        "ruby -e 'Kernel.send(\"system\",\"x\")'",
        "node -e 'require(\"fs\").writeFileSync(\"p.js\",\"x\")'",
        "node -e 'require(\"child_process\").execSync(\"x\")'",
        "node -e 'require(\"vm\").runInThisContext(\"1\")'",
        "node -e 'process.mainModule.require(\"child_process\")'",
        "php -r 'echo oldfn(1);'",
        # Heredocs and writes.
        "cat <<'EOF' > probe.py\nx\nEOF",
        "cat <<'EOF' | python3\nprint(1)\nEOF",
        "cat <<EOF\n$(python3 new.py)\nEOF",
        "python3 - <<'EOF'\nprint(1)\nEOF",
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
        "bash <<'EOF'\nls\nEOF",
        "python3 < notes.txt",
    ]
    for c in allowed:
        assert bash(c, d) == 0, f"should allow: {c}"
    for c in blocked:
        assert bash(c, d) == 2, f"should block: {c}"  # exactly 2, never 1

    # Every block message names what to do instead.
    assert "unbalanced quotes" in bash_err("python3 -c 'print(1)", d)
    assert "command substitution inside double quotes" in bash_err('echo "$(python3 new.py)"', d)
    assert "through the shell" in bash_err("echo x > probe.py", d)
    assert "single quotes" in bash_err('python3 -c "print(1)"', d)
    assert "contains logic or file access" in bash_err("python3 -c 'for i in range(3): print(i)'", d)
    assert "written during this rehearsal" in bash_err("python3 new.py", d)
    assert "module path override" in bash_err("PYTHONPATH=.rehearsal python3 -c 'import x'", d)
    assert "cannot be checked" in bash_err("npm run scrape", d)
    assert "single quotes" in bash_err("bash <<'EOF'\nls\nEOF", d)
    assert "single quotes" in bash_err("python3 < notes.txt", d)
    # -O is only a write flag for curl; for python it is a flag before the file, which the plan blocks.
    assert "through the shell" not in bash_err("python3 -O old.py", d)

    assert run("Write", {"file_path": "/p/scraper.py", "content": ""}, d) == 2
    assert run("Edit", {"file_path": "/p/app.ts", "old_string": "a", "new_string": "b"}, d) == 2
    assert run("Write", {"file_path": "/p/.rehearsal/REHEARSAL.md", "content": ""}, d) == 0
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

    # Empty log: marker gone, .rehearsal/ still there, no '### S' step logged yet.
    os.remove(j(".rehearsal", "active"))
    assert run("Write", {"file_path": "a.py", "content": ""}, d) == 2
    assert "no steps" in call({"tool_name": "Write", "tool_input": {"file_path": "a.py"}, "cwd": d}).stderr
    assert bash("cat > a.py <<'EOF'\nx\nEOF", d) == 2
    assert bash("sed -i 's/a/b/' a.py", d) == 2
    assert bash("patch -p1 < x.diff", d) == 2
    assert bash("sed -Ei 's/a/b/' old.py", d) == 2
    assert bash("perl -pi -e 's/a/b/' old.py", d) == 2
    assert bash("python3 new.py", d) == 0  # only write channels are checked without a marker
    assert run("Write", {"file_path": "notes.md", "content": ""}, d) == 0
    with open(j(".rehearsal", "REHEARSAL.md"), "w") as f:
        f.write("# Rehearsal\n\n## Steps\n")
    assert run("Write", {"file_path": "a.py", "content": ""}, d) == 2
    with open(j(".rehearsal", "REHEARSAL.md"), "a") as f:
        f.write("### S1 fetch the page\n")
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
# Fail open: a payload we do not understand never blocks and never exits 1.
assert call("not json").returncode == 0
assert call("42").returncode == 0

print("guard: all checks passed")
