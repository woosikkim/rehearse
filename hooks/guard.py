#!/usr/bin/env python3
"""Rehearsal hooks, one script for every event.

SessionStart: print the standing rule. UserPromptSubmit: the word "rehearse" loads the skill.
PreToolUse: loading the rehearse skill creates .rehearsal/active if none exists (so the first probe is
already guarded); while .rehearsal/active exists, run only what existed before the rehearsal began
(no new scripts, no new logic, no code writes); once .rehearsal/ exists, code writes wait until the guard's own
log shows one call that ran something (a one-liner, a client tool, an existing script); notes do not count.
PostToolUse / PostToolUseFailure: while the marker exists, append each shell command and its output
to .rehearsal/log.md; while .rehearsal/ exists, append test runs to .rehearsal/tests.log.
While .rehearsal/ exists and the marker is down (build phase), every shell command goes to
.rehearsal/build.log and each code edit is noted there.
Stop: while .rehearsal/ exists, refuse to finish, once, if the last logged test run shows failures, or if code
was edited and no sweep followed (a codebase search plus a new by-hand call after the first edit).

Reads a hook payload (JSON) on stdin. Exit 2 = block (reason on stderr), 0 = allow. Never exits 1.
Tool names cover Claude Code; the others are best-effort for agents with similar hooks.
"""
import json
import os
import re
import shlex
import sys
import time

FLAG = os.path.join(".rehearsal", "active")
CODE_EXT = {".py", ".js", ".mjs", ".cjs", ".ts", ".jsx", ".tsx", ".sh", ".bash", ".zsh", ".rb",
            ".go", ".rs", ".java", ".kt", ".php", ".pl", ".lua", ".ps1", ".swift", ".c", ".cpp", ".cs"}
SHELL_TOOLS = {"Bash", "shell", "local_shell", "exec_command", "run_shell_command"}
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit", "write_file", "replace", "edit_file"}
LOOPS = {"for", "while", "until", "xargs", "parallel", "watch", "sleep", "nohup"}
INTERPRETERS = {"python", "py", "node", "deno", "bun", "ruby", "perl", "php", "bash", "sh", "zsh",
                "fish", "pwsh", "powershell", "tsx", "ts-node", "eval", "source", "."}
ONELINER_LANGS = {"python", "py", "node", "ruby", "php"}
RUNNERS = {"npm": {"run", "start", "exec", "test"}, "pnpm": {"run", "start", "exec", "test"},
           "yarn": {"run", "start", "exec", "test"}, "go": {"run"}, "cargo": {"run"}}
WRAPPERS = {"sudo", "env", "time", "nice", "command", "exec"}
# Logged commands that count as having run something; reading (cat, grep, sed, ls) and notes do not.
EXEC_TOOLS = {"curl", "sqlite3", "psql", "mysql", "mongosh", "redis-cli", "http", "https", "grpcurl", "nc",
              "ssh", "pytest", "make"}
# Package launchers run a tool: allowed, but the tool they launch is checked too (npx tsx a.ts is still a script).
LAUNCHERS = {"npx": None, "bunx": None, "uvx": None, "uv": "run", "pipx": "run", "pnpm": "dlx"}
VERSION_ARGS = {"--version", "-V", "-v", "version"}
IN_PLACE = {"patch", "tar", "unzip", "wget"}
GIT_WRITES = {"apply", "checkout", "restore", "stash", "reset", "switch", "pull", "merge", "cherry-pick", "am"}

HEREDOC = re.compile(r"<<-?\s*(['\"])(\w+)\1([^\n]*)\n.*?\n[\t]*\2[ \t]*(?=\n|$)", re.S)
QUOTED = re.compile(r"'[^']*'|\"(?:\\.|[^\"\\])*\"")
SEPARATORS = re.compile(r"&&|\|\||;|\||\n|\$\(|\(|\)|`")
# ponytail: one strict one-liner shape plus keyword filters, frozen as of 0.3.0;
# upgrade path is ast.parse for Python, or "existing" = committed to git.
ONELINER = re.compile(r"^\s*(?:PATH=\S+\s+)?(?:\S*/)?(?:(python3?(?:\.\d+)?)\s+-c|node\s+-[ep]|ruby\s+-e)\s+'([^']*)'\s*(?:<\s*\S+\s*)?$")
CONTROL = re.compile(r"\b(for|while|if|elif|else|def|function|fn|class|lambda|try|except|catch|finally|with)\b|=>|\n")
ACCESS = re.compile(r"\b(exec\w*|spawn\w*|eval|compile|__import__|__builtins__|getattr|importlib|runpy|subprocess|"
                    r"child_process|worker_threads|vm|os|fs|shutil|pathlib|system|popen|chdir|open|write\w*|"
                    r"append\w*|copy\w*|rename\w*|unlink\w*|utime|touch|rmtree|move|symlink|replace|send|Kernel|"
                    r"Open3|FileUtils|IO|File|mainModule|sys\.path|PYTHONPATH|NODE_PATH)\b|%x|require\(\s*[\"']node:|`|\n")
ONE_SHAPE = "use python3 -c '<calls>' (single quotes, no other flags, optional < fixture; the interpreter may be a full path or follow PATH=...)"
NO_STEPS = ("rehearsal started but nothing has been run yet; while .rehearsal/active exists, make one real call "
            "the guard can log (python3 -c '...' against existing code, curl, a query, an existing script or test), "
            "then rm the marker. Reading files and writing notes do not count. If the marker is already down, put it "
            "back on its own first. Or delete .rehearsal/ entirely if no rehearsal is needed")
OWN_LOG = "the guard writes .rehearsal/log.md itself; put notes in .rehearsal/REHEARSAL.md"
# Test runners whose output the Stop hook reads, and what a red run looks like in that output.
TEST_CMD = re.compile(r"(?:^|[\s;&|/])(?:pytest|py\.test|runtests\.py|manage\.py test|-m unittest|-m pytest|tox|nose2?|"
                      r"npm test|pnpm test|yarn test|jest|mocha|vitest|go test|cargo test|make test|rspec|rake test|"
                      r"phpunit|mvn test|gradle test|dotnet test)\b")
RED = re.compile(r"\b[1-9]\d* (?:failed|errors?)\b|FAILED \(|^FAILED\b|^FAIL\b|--- FAIL|Tests:\s+[1-9]\d* failed|"
                 r"error during collection|^ERROR[: ]|AssertionError|Traceback \(most recent call last\)", re.M)
SEARCH_CMD = re.compile(r"(?:^|[\s;&|(])(?:grep|rg|ag|ack|git\s+grep|find)\s")
EDIT_SHELL = re.compile(r"(?:sed|perl)\s+-[^\s]*i|(?:^|[\s;&|])patch\s|(?:>>?|tee)\s*\S+\.(?:" +
                        "|".join(e[1:] for e in sorted(CODE_EXT)) + r")\b")
SWEEP = ("rehearse: you changed code, and the record shows no sweep after your first edit: {missing}. A fix that "
         "answers only the reported example leaves its siblings broken. Search the codebase for every caller of what "
         "you changed and every other place that does the same job (grep -rn <name>), call each by hand with the bad "
         "input, fix what fails, then finish.")
NOT_DONE = ("rehearse: your last test run shows failures: `{cmd}`. A test that passed before your change and fails after it "
            "means the fix is not done. Fix the cause or undo your change (git stash, git checkout -- <file>), run the "
            "tests again, and only then report what is and is not fixed.")
SESSION_RULE = ("Before building or fixing anything that depends on something outside the code (a site, a file, "
                "a service, a database, a device, another part of the program), load the rehearse skill and let it "
                "size the job. The word 'rehearse' in a prompt always means load it.")
NUDGE = ('rehearse: load the rehearse skill now (Skill tool, "rehearse:rehearse") and let it size the job '
         "before anything else.")
# Redaction for the auto-log, applied in order. The -u/--user one runs on the command line only;
# it over-redacts `sort -u x` there, which is harmless.
REDACT = [(re.compile(r"(?i)\b(authorization|cookie|set-cookie)[\"']?\s*:\s*[^\n'\"]*"), r"\1: ***"),
          (re.compile(r"(?i)(bearer\s+)\S+"), r"\1***"),
          (re.compile(r"(?i)((?:api[_-]?key|token|password|secret)[\"']?\s*[=:]\s*[\"']?)[^\s\"'&,]+"), r"\1***")]
REDACT_USER = (re.compile(r"(?<!\S)(--user[= ]|-u\s*)\S+"), r"\1***")
REDACT_URL = (re.compile(r"(://[^/\s:@]+:)[^@\s]+@"), r"\1***@")


def candidate_dirs(payload):
    return [d for d in (payload.get("cwd"), os.environ.get("CLAUDE_PROJECT_DIR"), os.getcwd()) if d]


def marker(payload):
    return next((os.path.join(d, FLAG) for d in candidate_dirs(payload) if os.path.exists(os.path.join(d, FLAG))), None)


def rehearsal_dir(payload):
    return next((os.path.join(d, ".rehearsal") for d in candidate_dirs(payload)
                 if os.path.isdir(os.path.join(d, ".rehearsal"))), None)


def marker_age_hours(path):
    return (time.time() - os.path.getmtime(path)) / 3600


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def shell_text(cmd):
    if isinstance(cmd, list):  # e.g. ["bash", "-lc", "curl ..."]
        if len(cmd) >= 3 and os.path.basename(cmd[0]) in {"bash", "sh", "zsh"} and cmd[1] in {"-c", "-lc"}:
            return cmd[-1]
        return shlex.join(cmd)
    return cmd if isinstance(cmd, str) else ""


def predates_marker(path, m, cur):
    """True if path is an existing file outside .rehearsal/ that is older than the marker."""
    p = os.path.abspath(os.path.join(cur, os.path.expanduser(path)))
    if ".rehearsal" in p.split(os.sep):
        return False
    return os.path.isfile(p) and os.path.getmtime(p) < os.path.getmtime(m)


def resolve_module(name, cur, js=False):
    base = os.path.join(cur, name if js else name.replace(".", "/"))
    tails = ["", ".js", "/index.js"] if js else [".py", "/__init__.py", "/__main__.py"]
    return next((base + t for t in tails if os.path.isfile(base + t)), None)  # None: stdlib or installed


def segments(cmd):
    """Blank quoted text without changing its length, cut on separators found in the blanked text, return raw slices."""
    bare = QUOTED.sub(lambda q: q.group(0)[0] + "_" * (len(q.group(0)) - 2) + q.group(0)[-1], cmd)
    cuts = [0] + [x for s in SEPARATORS.finditer(bare) for x in s.span()] + [len(cmd)]
    return bare, [cmd[a:b] for a, b in zip(cuts[::2], cuts[1::2])]


def executed(cmd):
    """True if some segment of a logged command ran something, as opposed to reading or taking notes."""
    for seg in segments(HEREDOC.sub(r"<<\3", cmd))[1]:
        if ONELINER.match(seg):
            return True
        try:
            toks = tokens(seg)
        except ValueError:
            toks = seg.split()
        i = prog_index(toks)
        if i >= len(toks):
            continue
        prog = toks[i]
        name = re.sub(r"[\d.]+$", "", os.path.basename(prog)) or prog
        args = [a for a in toks[i + 1:] if not a.startswith("-")]
        if {name, os.path.basename(prog)} & EXEC_TOOLS or prog.startswith("./") or os.path.splitext(prog)[1] in CODE_EXT:
            return True
        if name in INTERPRETERS and args and (os.path.splitext(args[0])[1] in CODE_EXT or toks[i + 1:i + 2] == ["-m"]):
            return True
        if name in RUNNERS and args and args[0] in RUNNERS[name]:
            return True
    return False


def has_executed_step(d):
    return any(executed(ln[2:]) for ln in read(os.path.join(d, "log.md")).splitlines() if ln.startswith("$ "))


def tokens(seg):
    lx = shlex.shlex(seg, posix=True, punctuation_chars=True)
    lx.whitespace_split = True
    return list(lx)


def prog_index(toks):
    i = 0
    while i < len(toks) and (re.fullmatch(r"\w+=\S*", toks[i]) or toks[i] in WRAPPERS or toks[i] == "timeout"):
        i += 1
        while toks[i - 1] == "timeout" and i < len(toks) and re.fullmatch(r"-\S*|\d[\w.]*", toks[i]):
            i += 1
    return i


def check_shell(cmd, cwd, m, full=True):
    """Full rules while the marker exists; with full=False only the shell's code-write channels."""
    cmd = HEREDOC.sub(r"<<\3", cmd)  # quoted heredoc bodies are data
    if full:
        try:
            shlex.split(cmd)
        except ValueError:
            return "unbalanced quotes; write the command as one plain line"
        if re.search(r'"(?:\\.|[^"\\])*?(?:\$\(|`)', cmd):
            return "command substitution inside double quotes; run the inner command on its own"
    bare, segs = segments(cmd)
    if full and re.search(r"(?<![&>|])&(?![&>])", bare):
        return "background job (&); run one command at a time and wait for it"
    cur = cwd
    for seg in segs:
        try:
            toks = tokens(seg)
        except ValueError:
            toks = seg.split()
        if toks[:1] == ["cd"] and len(toks) == 2:
            cur = os.path.join(cur, os.path.expanduser(toks[1]))
            continue
        reason = check_shell_writes(toks)
        if reason:
            return reason
        if not full:
            continue
        one = ONELINER.match(seg)
        reason = check_snippet(one.group(2), cur, m) if one else check_tokens(toks, cur, m)
        if reason:
            return reason
    return None


def check_marker_start(cmd):
    """The command that creates the marker must do nothing else, or its probes run unchecked."""
    cmd = QUOTED.sub("''", HEREDOC.sub(r"<<\3", cmd))  # quoted text and heredoc bodies are data
    if not re.search(r"touch\s+\S*\.rehearsal/active", cmd):
        return None
    for seg in re.split(r"&&|\|\||[;|\n]", cmd):
        toks = seg.split()
        i = prog_index(toks)
        if i < len(toks) and os.path.basename(toks[i]) not in {"mkdir", "touch"}:
            return ("start the rehearsal on its own: run mkdir -p .rehearsal/fixtures && touch .rehearsal/active "
                    "as one call, with nothing else, then rehearse")
    return None


def check_shell_writes(toks):
    i = prog_index(toks)
    prog = os.path.basename(toks[i]) if i < len(toks) else ""
    args = toks[i + 1:]
    if (prog in IN_PLACE or (prog == "git" and args[:1] and args[0] in GIT_WRITES)
            or (prog in {"sed", "perl"} and any(re.match(r"-[^-]*i", a) or a.startswith("--in-place") for a in args))):
        return (f"'{prog}' edits or unpacks files in place; not during rehearsal "
                "(use curl -o into .rehearsal/fixtures/ for downloads)")
    targets = []
    for k, t in enumerate(toks):
        nxt = toks[k + 1] if k + 1 < len(toks) else ""
        if (t in {">", ">>", ">|", "&>", "&>>", "-o", "--output"} or (prog == "curl" and re.fullmatch(r"-[A-Za-z]*o", t))
                or (t == ">&" and not re.fullmatch(r"\d+|-", nxt))):
            targets.append(nxt)
        elif t.startswith("--output="):
            targets.append(t.split("=", 1)[1])
    if prog == "tee":
        targets += [a for a in args if not a.startswith("-")]
    if prog in {"cp", "mv", "install"} and args:
        targets.append(args[-1])
    if prog == "dd":
        targets += [a[3:] for a in args if a.startswith("of=")]
    if prog == "curl" and any(re.fullmatch(r"-[A-Za-z]*O", a) for a in args):  # curl -O saves under the URL's file name
        targets += [a.rsplit("/", 1)[-1] for a in args if not a.startswith("-")]
    for t in targets:
        if os.path.basename(t) == "log.md":
            return OWN_LOG
        if t != "/dev/null" and os.path.splitext(t)[1] in CODE_EXT:
            return (f"writing code file '{t}' through the shell; code is written in the build phase, "
                    "after rm .rehearsal/active. Save a code-like fixture as .txt.")
    return None


def written(path):
    return f"'{path}' was written during this rehearsal or does not exist; run only files that existed before it began"


def check_tokens(toks, cur, m):
    i = prog_index(toks)
    path_override = any(re.match(r"(PYTHONPATH|NODE_PATH|RUBYLIB)=", t) for t in toks[:i])
    if i >= len(toks):
        return None
    prog, args = toks[i], toks[i + 1:]
    name = re.sub(r"[\d.]+$", "", os.path.basename(prog)) or prog
    if name in LAUNCHERS and (LAUNCHERS[name] is None or args[:1] == [LAUNCHERS[name]]):
        rest = args if LAUNCHERS[name] is None else args[1:]
        return check_tokens([t for t in rest if not t.startswith("-")], cur, m)
    if name in LOOPS:
        return f"loop/wait command '{name}'; do one step by hand, then the next"
    if name in INTERPRETERS:
        if len(args) == 1 and args[0] in VERSION_ARGS:
            return None
        if path_override:
            return "module path override; import from the project directory instead"
        if name in {"python", "py"} and args[:1] == ["-m"] and len(args) > 1:
            mod = resolve_module(args[1], cur)
            if mod and not predates_marker(mod, m, cur):
                return f"module '{args[1]}' was written during this rehearsal; run only modules that existed before it"
            return next((written(a) for a in args[2:]
                         if os.path.splitext(a)[1] in CODE_EXT and not predates_marker(a, m, cur)), None)
        if args and args[0] in {"<", "<<", "<<<"}:  # inline code fed through stdin
            return f"inline code in this shape is not accepted; {ONE_SHAPE}"
        if args and not args[0].startswith("-"):
            return None if predates_marker(args[0], m, cur) else written(args[0])
        if args and name in ONELINER_LANGS:
            return f"inline code in this shape is not accepted; {ONE_SHAPE}"
        return f"interpreter '{prog}' with inline code or stdin; run a file that existed before the rehearsal, or {ONE_SHAPE}"
    if name in RUNNERS and args and args[0] in RUNNERS[name]:
        target = next((a for a in args[1:] if not a.startswith("-")), "")
        if name == "go" and target.endswith(".go") and predates_marker(target, m, cur):
            return None
        return f"'{prog} {args[0]}' target cannot be checked; run the underlying command directly"
    if prog.startswith("./") or os.path.splitext(prog)[1] in CODE_EXT:
        return None if predates_marker(prog, m, cur) else written(prog)
    return None


def check_snippet(snippet, cur, m):
    """A one-liner that matched ONELINER: straight-line calls to existing code, no logic, no file access, nothing new imported."""
    blank = re.sub(r'"(?:\\.|[^"\\])*"', '""', snippet)  # data strings cannot trip the logic check
    hit = CONTROL.search(blank) or ACCESS.search(snippet)
    if hit:
        return (f"inline code contains logic or file access ({hit.group(0)!r}); call one existing function and "
                "print the result as a literal, or feed a fixture through < stdin")
    statements = [s.strip() for s in blank.split(";") if s.strip()]
    if len(statements) > 12:  # ponytail: straight-line calls only; the keyword checks above already ban logic
        return f"inline code has {len(statements)} statements; at most twelve (imports, literals, calls, print)"
    mods = [(r, True) for r in re.findall(r"require\(\s*\"(\.{1,2}/[^\"]*)\"\s*\)", snippet)]
    for s in statements:
        if s.startswith("import "):
            mods += [(p.split(" as ")[0].strip(), False) for p in s[7:].split(",")]
        elif s.startswith("from "):
            mods.append((s.split()[1], False))
    for name, js in mods:
        path = resolve_module(name, cur, js) if name and not name.startswith(".") or js else None
        if path and not predates_marker(path, m, cur):
            return f"module '{name}' was written during this rehearsal; import only what existed before it began"
    return None


def check_write(tool_input, m, empty_log):
    text = json.dumps(tool_input)
    paths = [tool_input.get(k) for k in ("file_path", "path", "notebook_path")]
    paths += re.findall(r"\*\*\* (?:Add|Update) File: (\S+?)(?:\\n|\s)", text)  # apply_patch format
    for p in filter(None, paths):
        if os.path.basename(str(p)) == "log.md":
            return OWN_LOG
        if os.path.splitext(str(p))[1] not in CODE_EXT:
            continue
        if m:
            return f"writing code file '{p}'; code is written in the build phase, after rm .rehearsal/active"
        if empty_log and ".rehearsal" not in str(p).replace("\\", "/").split("/"):
            return NO_STEPS
    return None


def log_command(payload, path):
    cmd = shell_text((payload.get("tool_input") or {}).get("command"))
    out = payload.get("tool_response")
    if payload.get("hook_event_name") == "PostToolUseFailure":
        out = payload.get("error") or out
    if isinstance(out, dict) and {"stdout", "stderr"} & out.keys():
        out = "\n".join(str(out[k]) for k in ("stdout", "stderr") if out.get(k))
    elif not isinstance(out, str):
        out = json.dumps(out)
    for rx, sub in REDACT:
        cmd, out = rx.sub(sub, cmd), rx.sub(sub, out)
    cmd = REDACT_USER[0].sub(REDACT_USER[1], cmd)
    cmd, out = REDACT_URL[0].sub(REDACT_URL[1], cmd), REDACT_URL[0].sub(REDACT_URL[1], out)
    lines = [ln[:400] for ln in out.splitlines() if ln.strip()][:40]  # no blank lines: entries are blank-line separated
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join([f"$ {cmd}"] + lines) + "\n\n")


def start_marker(cwd):
    """Create .rehearsal/fixtures and the marker, only when no marker exists. Failure is not a reason to block."""
    try:
        os.makedirs(os.path.join(cwd, ".rehearsal", "fixtures"), exist_ok=True)
        with open(os.path.join(cwd, FLAG), "a", encoding="utf-8"):
            pass
    except OSError:
        pass


def build_entries(d):
    return [e for e in read(os.path.join(d, "build.log")).split("\n\n") if e.startswith(("$ ", "EDIT "))]


def sweep_missing(d):
    """What the sweep still lacks after the first code edit, or None if no edit happened or the sweep is complete."""
    entries = build_entries(d)
    first = next((i for i, e in enumerate(entries)
                  if e.startswith("EDIT ") or EDIT_SHELL.search(e.partition("\n")[0])), None)
    if first is None:
        return None
    before = {ln[2:] for ln in read(os.path.join(d, "log.md")).splitlines() if ln.startswith("$ ")}
    after = [e.partition("\n")[0][2:] for e in entries[first + 1:] if e.startswith("$ ")]
    searched = any(SEARCH_CMD.search(c) for c in after)
    new_call = any(executed(c) and not TEST_CMD.search(c) and c not in before for c in after)
    missing = [x for x, ok in (("no search of the codebase", searched),
                               ("no new by-hand call (the original reproduction and test runs do not count)", new_call)) if not ok]
    return " and ".join(missing) or None


def last_test_run(d):
    """(command, output) of the last entry in .rehearsal/tests.log, or None."""
    entries = [e for e in read(os.path.join(d, "tests.log")).split("\n\n") if e.startswith("$ ")]
    if not entries:
        return None
    cmd, _, out = entries[-1].partition("\n")
    return cmd[2:], out


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0  # not a payload we understand: fail open
    if not isinstance(payload, dict):
        return 0
    event = payload.get("hook_event_name") or "PreToolUse"
    m = marker(payload)
    if event == "SessionStart":
        note = f" A rehearsal marker exists at .rehearsal/active ({int(marker_age_hours(m))} h old)." if m else ""
        print(SESSION_RULE + note)
        return 0
    if event == "UserPromptSubmit":
        if re.search(r"\brehearse\b", str(payload.get("prompt", "")), re.I):
            print(NUDGE)
        return 0
    tool = str(payload.get("tool_name") or "")
    tin = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    if event == "PreToolUse" and tool == "Skill":
        if re.fullmatch(r"(rehearse:)?rehearse", str(tin.get("skill") or "")) and not m:
            start_marker(payload.get("cwd") or os.getcwd())  # never touch an existing marker: its mtime is the age line
        return 0
    d = rehearsal_dir(payload)
    if event in {"PostToolUse", "PostToolUseFailure"}:
        if tool in SHELL_TOOLS:
            if m:
                log_command(payload, os.path.join(os.path.dirname(m), "log.md"))
            elif d:
                log_command(payload, os.path.join(d, "build.log"))
            if d and TEST_CMD.search(shell_text(tin.get("command"))):
                log_command(payload, os.path.join(d, "tests.log"))
        return 0
    if event == "Stop":
        last = None if payload.get("stop_hook_active") or not d else last_test_run(d)
        # A baseline check (git stash ... run tests ... git stash pop) is red on purpose: not a hand-back.
        if last and RED.search(last[1]) and "git stash" not in last[0]:
            print(json.dumps({"decision": "block", "reason": NOT_DONE.format(cmd=last[0][:200])}))
            return 0
        missing = None if payload.get("stop_hook_active") or not d else sweep_missing(d)
        if missing:
            print(json.dumps({"decision": "block", "reason": SWEEP.format(missing=missing)}))
        return 0
    if event != "PreToolUse":
        return 0
    empty_log = bool(d) and not has_executed_step(d)
    cwd = payload.get("cwd") or os.getcwd()
    reason = None
    if tool in SHELL_TOOLS:
        cmd = shell_text(tin.get("command"))
        reason = None if m else check_marker_start(cmd)
        if m and re.search(r"touch\s+\S*\.rehearsal/active", QUOTED.sub("''", HEREDOC.sub(r"<<\3", cmd))):
            reason = ("the rehearsal is already started (the guard created the marker when the skill loaded); "
                      "do not touch .rehearsal/active again, just rehearse")
        if not reason and (m or empty_log):
            reason = check_shell(cmd, cwd, m, full=bool(m))
            if reason and not m:
                reason = f"{NO_STEPS} ({reason})"
    elif tool in WRITE_TOOLS or "patch" in tool.lower():
        reason = check_write(tin, m, empty_log)
        if not reason and d and not m:
            for p in (tin.get(k) for k in ("file_path", "path", "notebook_path")):
                if p and os.path.splitext(str(p))[1] in CODE_EXT:
                    with open(os.path.join(d, "build.log"), "a", encoding="utf-8") as f:
                        f.write(f"EDIT {p}\n\n")
    if not reason:
        return 0
    if m and marker_age_hours(m) > 24:
        reason = f"rehearsal marker is {int(marker_age_hours(m))} h old; if this rehearsal is over, run: rm {m}. {reason}"
    hint = (" Do this step by hand with one direct command or tool call (curl, jq, grep, sqlite3, a browser tool...) "
            "and log what you see." if m else "")
    print(f"rehearse: blocked: {reason}.{hint}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # a guard bug must never turn into exit 1
        sys.exit(0)
