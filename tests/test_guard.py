"""Self-check for hooks/guard.py. Run: python3 tests/test_guard.py"""
import json
import os
import subprocess
import sys
import tempfile

GUARD = os.path.join(os.path.dirname(__file__), "..", "hooks", "guard.py")


def run(tool, tool_input, cwd):
    payload = json.dumps({"tool_name": tool, "tool_input": tool_input, "cwd": cwd})
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    return subprocess.run([sys.executable, GUARD], input=payload, text=True, capture_output=True,
                          cwd=tempfile.gettempdir(), env=env).returncode


def bash(cmd, cwd):
    return run("Bash", {"command": cmd}, cwd)


with tempfile.TemporaryDirectory() as d:
    # Flag off: everything allowed.
    assert bash("for i in 1 2; do curl x; done", d) == 0
    assert run("Write", {"file_path": "s.py", "content": ""}, d) == 0

    os.makedirs(os.path.join(d, ".rehearsal"))
    open(os.path.join(d, ".rehearsal", "active"), "w").close()

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
    ]
    blocked = [
        "for i in 1 2 3; do curl x; done",
        "while true; do curl x; done",
        "python3 scrape.py",
        "python -c 'print(1)'",
        "node -e 'console.log(1)'",
        "curl -s x | python3 -m json.tool",
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
    ]
    for c in allowed:
        assert bash(c, d) == 0, f"should allow: {c}"
    for c in blocked:
        assert bash(c, d) == 2, f"should block: {c}"

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

def nudged(prompt):
    payload = json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": prompt})
    out = subprocess.run([sys.executable, GUARD], input=payload, text=True, capture_output=True).stdout
    return "rehearse" in out


assert nudged("Build me a small scraper for example.com")
assert nudged("write a discord bot that posts daily weather")
assert nudged("make a CLI tool that converts CSV to xlsx")
assert not nudged("what does this function do?")
assert not nudged("build a scraper, skip rehearsal")
assert not nudged("fix the typo in README")

print("guard: all checks passed")
