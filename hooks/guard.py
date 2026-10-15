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
import hashlib
import json
import os
import re
import shlex
import subprocess
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
RUNNERS = {"npm": {"run", "start", "exec", "test"}, "pnpm": {"run", "start", "exec", "test"},
           "yarn": {"run", "start", "exec", "test"}, "go": {"run"}, "cargo": {"run"}}
WRAPPERS = {"sudo", "env", "time", "nice", "command", "exec"}
# Commands that only read, move or note things: a logged command made of these never counts as having run something.
READ_ONLY = {"cat", "sed", "grep", "rg", "ag", "ack", "ls", "find", "head", "tail", "wc", "echo", "printf", "pwd", "which",
             "type", "command", "stat", "file", "od", "xxd", "hexdump", "strings", "tree", "diff", "cmp", "less", "more",
             "cd", "mkdir", "touch", "rm", "rmdir", "cp", "mv", "ln", "chmod", "chown", "tee", "sort", "uniq", "cut", "tr",
             "awk", "jq", "yq", "basename", "dirname", "realpath", "readlink", "env", "export", "set", "unset", "true",
             "false", "test", "[", "date", "sleep", "git", "du", "df", "free", "nproc", "uname", "id", "whoami", "hostname",
             "ps", "pgrep", "kill", "seq", "yes", "clear", "exit", "wait", "time", "timeout", "nohup", "xargs", "conda"}
# Package and build managers count only when they run something (install/list do not).
SETUP = {"pip": set(), "pip3": set(), "apt": set(), "apt-get": set(), "apk": set(), "brew": set(), "uv": {"run"}, "pipx": {"run"},
         "npm": {"run", "test", "start", "exec"}, "pnpm": {"run", "test", "start", "exec", "dlx"}, "yarn": {"run", "test", "start"},
         "cargo": {"run", "test", "build", "bench"}, "go": {"run", "test", "build"}, "npx": None, "bunx": None, "docker": {"run", "exec", "compose"}}
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
# Which flag hands an interpreter inline code; "$" stands for an interpreter held in a shell variable.
INLINE_FLAGS = {"python": {"-c"}, "py": {"-c"}, "node": {"-e", "-p"}, "bun": {"-e"}, "deno": {"eval"}, "ruby": {"-e"},
                "php": {"-r"}, "perl": {"-e", "-E"}, "bash": {"-c"}, "sh": {"-c"}, "zsh": {"-c"}, "fish": {"-c"},
                "pwsh": {"-c", "-Command"}, "powershell": {"-c", "-Command"}, "$": {"-c", "-e"}}
# Syntax keywords only: method names such as .filter() or .map() are ordinary calls and must not trip this.
CONTROL = re.compile(r"\b(for|while|until|do|if|elif|elsif|else|unless|def|function|fn|class|lambda|proc|try|except|"
                     r"catch|finally|with|begin|rescue)\b|=>|->")
ACCESS = re.compile(r"\b(exec\w*|spawn\w*|eval|compile|__import__|__builtins__|getattr|importlib|runpy|subprocess|"
                    r"child_process|worker_threads|vm|os|fs|shutil|pathlib|system|popen|chdir|open|write\w*|"
                    r"append\w*|copy\w*|rename\w*|unlink\w*|utime|touch|rmtree|move|symlink|replace|send|Kernel|"
                    r"Open3|FileUtils|IO|File|mainModule|sys\.path|PYTHONPATH|NODE_PATH)\b|%x|require\(\s*[\"']node:|`")
ONE_SHAPE = ("inline code may use any interpreter and flags, quoted or in a quoted heredoc, but may not contain loops, "
             "branches, definitions or file/process access")
NO_STEPS = ("rehearsal started but nothing has been run yet; while .rehearsal/active exists, make one real call "
            "the guard can log (python3 -c '...' against existing code, curl, a query, an existing script or test), "
            "then rm the marker. Reading files and writing notes do not count. If the marker is already down, put it "
            "back on its own first. Or delete .rehearsal/ entirely if no rehearsal is needed")
OWN_LOG = "the guard writes .rehearsal/log.md itself; put notes in .rehearsal/REHEARSAL.md"
SCAFFOLD_HINT = ("A specimen a real tool reads (a docs project, a sample package, a settings module, a dummy class) goes "
                 "under .rehearsal/scaffold/; you still cannot run or import it yourself")


def in_scaffold(path, cur=""):
    p = os.path.abspath(os.path.join(cur, os.path.expanduser(str(path)))).replace("\\", "/")
    return "/.rehearsal/scaffold/" in p
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
REPRO_SAME = ("rehearse: your reproduction `{cmd}` behaves the same on the original code and on your fixed code "
              "(same output and exit code), so it never showed the bug. Find a call that gives the wrong result before "
              "your change and the right one after, write it as `repro: <command>` in .rehearsal/REHEARSAL.md, run it, "
              "then finish.")
UNSAFE_REPLAY = re.compile(r"(?:^|[\s;&|(])rm\s|(?<![<>&\d])>(?!&)|curl\b[^|;&]*-X\s*(?:POST|PUT|DELETE|PATCH)", re.I)
REPLAY_NOISE = re.compile(r"0x[0-9a-fA-F]{4,}|\b\d+\.\d+s\b|\d{2}:\d{2}:\d{2}")
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


def written_list(m):
    return os.path.join(os.path.dirname(m), "written")


def record_written(d, paths, cur):
    """Remember files the agent wrote during the rehearsal: those may never be run or imported."""
    try:
        with open(os.path.join(d, "written"), "a", encoding="utf-8") as f:
            for p in paths:
                if p and p != "/dev/null":
                    f.write(os.path.abspath(os.path.join(cur, os.path.expanduser(str(p)))) + "\n")
    except OSError:
        pass


def may_run(path, m, cur):
    """True if path is an existing file outside .rehearsal/ that the agent did not write during the rehearsal.
    A code file newer than the marker is refused too, as a backstop for a write the guard did not see."""
    p = os.path.abspath(os.path.join(cur, os.path.expanduser(path)))
    if ".rehearsal" in p.split(os.sep) or not os.path.isfile(p):
        return False
    if p in set(read(written_list(m)).splitlines()):
        return False
    return os.path.splitext(p)[1] not in CODE_EXT or os.path.getmtime(p) < os.path.getmtime(m)


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
    """True if some segment of a logged command ran something: anything that is not a read-only or setup command."""
    for seg in segments(HEREDOC.sub(r"<<\3", cmd))[1]:
        try:
            toks = tokens(seg)
        except ValueError:
            toks = seg.split()
        i = prog_index(toks)
        if i >= len(toks):
            continue
        prog = toks[i]
        name = re.sub(r"[\d.]+$", "", os.path.basename(prog)) or prog
        if name in READ_ONLY or os.path.basename(prog) in READ_ONLY:
            continue
        if name in SETUP:
            sub = next((a for a in toks[i + 1:] if not a.startswith("-")), "")
            if SETUP[name] is not None and sub not in SETUP[name]:
                continue
        return True
    return False


TRACER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tracer")


def path_override(toks, i):
    """A PYTHONPATH/NODE_PATH/RUBYLIB prefix, except the guard's own tracer prefix."""
    for t in toks[:i]:
        if re.match(r"(PYTHONPATH|NODE_PATH|RUBYLIB)=", t) and not t.startswith("PYTHONPATH=" + TRACER_DIR):
            return True
    return False


def inject_tracer(cmd, cwd, d):
    """Switch the Python call recorder on for a by-hand command; test runners and non-shell text are left alone."""
    if not cmd or TEST_CMD.search(cmd) or "REHEARSE_TRACE=" in cmd:
        return cmd
    env = ("REHEARSE_TRACE=%s REHEARSE_ROOT=%s PYTHONPATH=%s${PYTHONPATH:+:$PYTHONPATH} "
           % (shlex.quote(os.path.join(d, "trace.jsonl")), shlex.quote(os.path.abspath(cwd)), shlex.quote(TRACER_DIR)))
    return env + cmd


def trace_events(d, since=0):
    """Trace events appended after byte offset `since`, and the new offset."""
    path = os.path.join(d, "trace.jsonl")
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            f.seek(since)
            lines = f.read()
            return [json.loads(ln) for ln in lines.splitlines() if ln.strip()], since + len(lines.encode("utf-8"))
    except (OSError, ValueError):
        return [], since


def trace_tail(d, limit=10):
    """Readable lines for the trace events logged since the last command, for the log entry."""
    off_path = os.path.join(d, "trace.offset")
    events, offset = trace_events(d, int(read(off_path) or 0))
    with open(off_path, "w", encoding="utf-8") as f:
        f.write(str(offset))
    calls, lines = {}, []
    for ev in events:
        key = (ev.get("qual") or ev.get("func"), ev.get("file"))
        if ev.get("t") == "call":
            calls[key] = ", ".join("%s=%s" % kv for kv in (ev.get("args") or {}).items())
        elif ev.get("t") in ("return", "exception"):
            args = calls.pop(key, "")
            result = ("raised " + ev["exc"]) if ev.get("t") == "exception" else ("= " + str(ev.get("ret")))
            lines.append("  -> %s(%s) %s  [%s:%s]" % (key[0], args, result, ev.get("file"), ev.get("line")))
    return lines[-limit:]


def has_executed_step(d):
    if os.path.getsize(os.path.join(d, "trace.jsonl")) if os.path.exists(os.path.join(d, "trace.jsonl")) else 0:
        return True  # project code ran under the recorder
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
    bodies = [h.group(0).split("\n", 1)[1].rsplit("\n", 1)[0] for h in HEREDOC.finditer(cmd)]  # quoted heredoc bodies
    cmd = HEREDOC.sub(r"<<\3", cmd)
    d = os.path.dirname(m) if m else None
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
    produced = set()  # files an earlier segment of this same command builds (cobc -o prog ... && ./prog)
    for seg in segs:
        try:
            toks = tokens(seg)
        except ValueError:
            toks = seg.split()
        if toks[:1] == ["cd"] and len(toks) == 2:
            cur = os.path.join(cur, os.path.expanduser(toks[1]))
            continue
        reason = check_shell_writes(toks, cur, d, produced)
        if reason:
            return reason
        body = bodies.pop(0) if "<<" in seg and bodies else None
        if not full:
            continue
        snippet = inline_code(toks)
        if snippet is None and body is not None and is_interpreter(toks):
            snippet = body  # python3 - <<'EOF' ... EOF: the body is the inline code
        if snippet is not None and path_override(toks, prog_index(toks)):
            return "module path override; import from the project directory instead"
        reason = check_snippet(snippet, cur, m) if snippet is not None else check_tokens(toks, cur, m, produced)
        if reason:
            return reason
    return None


def is_interpreter(toks):
    i = prog_index(toks)
    if i >= len(toks):
        return False
    prog = toks[i]
    return prog.startswith("$") or (re.sub(r"[\d.]+$", "", os.path.basename(prog)) or prog) in INTERPRETERS


def inline_flags(toks):
    i = prog_index(toks)
    prog = toks[i]
    name = "$" if prog.startswith("$") else (re.sub(r"[\d.]+$", "", os.path.basename(prog)) or prog)
    return INLINE_FLAGS.get(name, set())


def inline_code(toks):
    """The code string handed to an interpreter by its inline flag, whatever the quoting; None if there is none."""
    if not is_interpreter(toks):
        return None
    i = prog_index(toks)
    flags = inline_flags(toks)
    for k in range(i + 1, len(toks) - 1):
        if toks[k] in flags:
            return toks[k + 1]
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


def check_shell_writes(toks, cur="", d=None, produced=None):
    i = prog_index(toks)
    prog = os.path.basename(toks[i]) if i < len(toks) else ""
    args = toks[i + 1:]
    if (prog in IN_PLACE or (prog == "git" and args[:1] and args[0] in GIT_WRITES)
            or (prog in {"sed", "perl"} and any(re.match(r"-[^-]*i", a) or a.startswith("--in-place") for a in args))):
        return (f"'{prog}' edits or unpacks files in place; not during rehearsal "
                "(use curl -o into .rehearsal/fixtures/ for downloads)")
    targets = []   # files the agent itself writes: redirections, copies, downloads
    outputs = []   # files another program writes for it (-o of a compiler or converter): not the agent's code
    for k, t in enumerate(toks):
        nxt = toks[k + 1] if k + 1 < len(toks) else ""
        if t in {">", ">>", ">|", "&>", "&>>"} or (t == ">&" and not re.fullmatch(r"\d+|-", nxt)):
            targets.append(nxt)
        elif t in {"-o", "--output"} or (prog == "curl" and re.fullmatch(r"-[A-Za-z]*o", t)):
            (targets if prog == "curl" else outputs).append(nxt)
        elif t.startswith("--output="):
            (targets if prog == "curl" else outputs).append(t.split("=", 1)[1])
    if prog == "tee":
        targets += [a for a in args if not a.startswith("-")]
    if prog in {"cp", "mv", "install"} and args:
        targets.append(args[-1])
    if prog == "dd":
        targets += [a[3:] for a in args if a.startswith("of=")]
    if prog == "curl" and any(re.fullmatch(r"-[A-Za-z]*O", a) for a in args):  # curl -O saves under the URL's file name
        targets += [a.rsplit("/", 1)[-1] for a in args if not a.startswith("-")]
    for t in targets + outputs:
        if os.path.basename(t) == "log.md":
            return OWN_LOG
        if t != "/dev/null" and os.path.splitext(t)[1] in CODE_EXT and not in_scaffold(t, cur):
            return (f"writing code file '{t}' through the shell; code is written in the build phase, "
                    f"after rm .rehearsal/active. {SCAFFOLD_HINT}, or save a code-like fixture as .txt.")
    if d and targets:
        record_written(d, targets, cur)
    if produced is not None:
        produced.update(os.path.abspath(os.path.join(cur, o)) for o in outputs if o and o != "/dev/null")
    return None


def written(path):
    return f"'{path}' was written during this rehearsal or does not exist; run only files that existed before it began"


def check_tokens(toks, cur, m, produced=()):
    def runnable(path):
        return may_run(path, m, cur) or os.path.abspath(os.path.join(cur, os.path.expanduser(path))) in produced
    i = prog_index(toks)
    override = path_override(toks, i)
    if i >= len(toks):
        return None
    prog, args = toks[i], toks[i + 1:]
    name = re.sub(r"[\d.]+$", "", os.path.basename(prog)) or prog
    if prog.startswith("$"):
        name = "python"  # an interpreter held in a shell variable gets the interpreter rules
    if name in LAUNCHERS and (LAUNCHERS[name] is None or args[:1] == [LAUNCHERS[name]]):
        rest = args if LAUNCHERS[name] is None else args[1:]
        return check_tokens([t for t in rest if not t.startswith("-")], cur, m)
    if name in LOOPS:
        return f"loop/wait command '{name}'; do one step by hand, then the next"
    if name in INTERPRETERS:
        if len(args) == 1 and args[0] in VERSION_ARGS:
            return None
        if override:
            return "module path override; import from the project directory instead"
        if name in {"python", "py"} and args[:1] == ["-m"] and len(args) > 1:
            mod = resolve_module(args[1], cur)
            if mod and not may_run(mod, m, cur):
                return f"module '{args[1]}' was written during this rehearsal; run only modules that existed before it"
            return next((written(a) for a in args[2:]
                         if os.path.splitext(a)[1] in CODE_EXT and not may_run(a, m, cur)), None)
        if args and args[0] == "<" and len(args) > 1:  # code fed from a file: the file must have existed before
            return None if runnable(args[1]) else written(args[1])
        if args and args[0] in {"<<", "<<<"}:  # an unquoted heredoc: its lines were checked as separate segments
            return None
        if any(a in inline_flags(toks) for a in args):
            return f"inline code must be quoted; {ONE_SHAPE}"
        target = next((a for a in args if not a.startswith("-")), None)  # the file to run, after any flags
        if target is None:  # nothing to run but stdin: piped or interactive code
            return f"interpreter '{prog}' reading code from stdin; run a file that existed before the rehearsal, or {ONE_SHAPE}"
        return None if runnable(target) else written(target)
    if name in RUNNERS and args and args[0] in RUNNERS[name]:
        target = next((a for a in args[1:] if not a.startswith("-")), "")
        if name == "go" and target.endswith(".go") and runnable(target):
            return None
        return f"'{prog} {args[0]}' target cannot be checked; run the underlying command directly"
    if prog.startswith("./") or os.path.splitext(prog)[1] in CODE_EXT:
        return None if runnable(prog) else written(prog)
    return None


def check_snippet(snippet, cur, m):
    """Inline code: straight-line calls to existing code, no logic, no file access, nothing new imported."""
    blank = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', '""', snippet)  # data strings cannot trip the logic check
    hit = CONTROL.search(blank) or ACCESS.search(snippet)
    if hit:
        return (f"inline code contains logic or file access ({hit.group(0)!r}); call one existing function and "
                "print the result as a literal, or feed a fixture through < stdin")
    statements = [x.strip() for x in re.split(r"[;\n]", blank) if x.strip()]
    mods = [(r, True) for r in re.findall(r"require\(\s*\"(\.{1,2}/[^\"]*)\"\s*\)", snippet)]
    for s in statements:
        if s.startswith("import "):
            mods += [(p.split(" as ")[0].strip(), False) for p in s[7:].split(",")]
        elif s.startswith("from "):
            mods.append((s.split()[1], False))
    for name, js in mods:
        path = resolve_module(name, cur, js) if name and not name.startswith(".") or js else None
        if path and not may_run(path, m, cur):
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
        if m and not in_scaffold(p):
            return f"writing code file '{p}'; code is written in the build phase, after rm .rehearsal/active. {SCAFFOLD_HINT}"
        if empty_log and ".rehearsal" not in str(p).replace("\\", "/").split("/"):
            return NO_STEPS
    return None


TRACER_PREFIX = re.compile(r"^REHEARSE_TRACE=\S+ REHEARSE_ROOT=\S+ PYTHONPATH=\S+ ")


def log_command(payload, path):
    cmd = TRACER_PREFIX.sub("", shell_text((payload.get("tool_input") or {}).get("command")))  # the guard's own prefix is noise
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
    lines += trace_tail(os.path.dirname(path))
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join([f"$ {cmd}"] + lines) + "\n\n")


def start_marker(cwd):
    """Create .rehearsal/fixtures and the marker, only when no marker exists. Failure is not a reason to block."""
    try:
        os.makedirs(os.path.join(cwd, ".rehearsal", "fixtures"), exist_ok=True)
        os.makedirs(os.path.join(cwd, ".rehearsal", "scaffold"), exist_ok=True)
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


def first_edit_index(entries):
    return next((i for i, e in enumerate(entries)
                 if e.startswith("EDIT ") or EDIT_SHELL.search(e.partition("\n")[0])), None)


def pick_repro(d):
    """The reproduction to replay: a `repro:` line in REHEARSAL.md, else the last by-hand run before the first edit."""
    m = re.search(r"^repro:\s*`?(.+?)`?\s*$", read(os.path.join(d, "REHEARSAL.md")), re.M)
    if m:
        return m.group(1).strip()
    cmds = [ln[2:] for ln in read(os.path.join(d, "log.md")).splitlines() if ln.startswith("$ ")]
    entries = build_entries(d)
    first = first_edit_index(entries)
    cmds += [e.partition("\n")[0][2:] for e in (entries[:first] if first is not None else entries) if e.startswith("$ ")]
    cmds = [c for c in cmds if executed(c) and not TEST_CMD.search(c)]
    return cmds[-1] if cmds else None


def run_for_replay(cmd, cwd):
    timeout = float(os.environ.get("REHEARSE_REPLAY_TIMEOUT", "120"))
    # A fresh bytecode cache per run: a stale .pyc with the same mtime second and size would hide the change.
    cache = os.path.join(cwd, ".rehearsal", "pycache-%d" % time.time_ns())
    env = dict(os.environ, PYTHONPYCACHEPREFIX=cache)
    try:
        p = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, timeout=timeout, env=env)
    finally:
        for root, dirs, files in os.walk(cache, topdown=False):
            for f in files:
                os.remove(os.path.join(root, f))
            for x in dirs:
                os.rmdir(os.path.join(root, x))
        if os.path.isdir(cache):
            os.rmdir(cache)
    out = REPLAY_NOISE.sub("", (p.stdout + p.stderr).decode("utf-8", "replace"))
    return p.returncode, out


def replay(d, cmd, cwd):
    """Run the reproduction on the original code (changes stashed) and on the current code. True if they differ."""
    def note(msg):
        with open(os.path.join(d, "build.log"), "a", encoding="utf-8") as f:
            f.write(f"replay: {msg}\n\n")
    if not cmd:
        note("skipped: no reproduction found")
        return None
    if UNSAFE_REPLAY.search(QUOTED.sub("''", cmd)):
        note("skipped: command writes")
        return None
    git = lambda *a: subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True)
    if git("rev-parse", "--is-inside-work-tree").returncode != 0:
        note("skipped: not a git repository")
        return None
    changed = []
    for item in git("status", "--porcelain", "-z").stdout.split("\0"):
        path = item[3:].split(" -> ")[-1] if len(item) > 3 else ""
        if path and not path.replace("\\", "/").startswith((".rehearsal", "__pycache__")):
            changed.append(path)
    stashes = git("stash", "list").stdout
    if changed and git("stash", "push", "-u", "-q", "--", *changed).returncode != 0:
        note("skipped: git stash failed")
        return None
    try:
        before = run_for_replay(cmd, cwd)
    except subprocess.TimeoutExpired:
        before = None
    finally:
        if changed:
            git("stash", "pop", "-q")
    if git("stash", "list").stdout != stashes:
        note("warning: the stash list changed; check git stash list")
    if before is None:
        note("timed out on the original code")
        return None
    try:
        after = run_for_replay(cmd, cwd)
    except subprocess.TimeoutExpired:
        note("timed out on the fixed code")
        return None
    differs = before != after
    note("differs" if differs else "same")
    return differs


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
            building = d and (not m or os.path.exists(os.path.join(d, "build.log")))  # once edits begin, even if the marker comes back
            if building:
                log_command(payload, os.path.join(d, "build.log"))
            elif m:
                log_command(payload, os.path.join(os.path.dirname(m), "log.md"))
            if d and TEST_CMD.search(shell_text(tin.get("command"))):
                log_command(payload, os.path.join(d, "tests.log"))
        return 0
    if event == "Stop":
        last = None if payload.get("stop_hook_active") or not d else last_test_run(d)
        # A baseline check (git stash ... run tests ... git stash pop) is red on purpose: not a hand-back.
        if last and RED.search(last[1]) and "git stash" not in last[0]:
            print(json.dumps({"decision": "block", "reason": NOT_DONE.format(cmd=last[0][:200])}))
            return 0
        if d and not payload.get("stop_hook_active") and first_edit_index(build_entries(d)) is not None \
                and "replay: " not in read(os.path.join(d, "build.log")):
            cmd = pick_repro(d)
            if replay(d, cmd, payload.get("cwd") or os.getcwd()) is False:
                print(json.dumps({"decision": "block", "reason": REPRO_SAME.format(cmd=cmd[:200])}))
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
        if not reason and d:
            record_written(d, [tin.get(k) for k in ("file_path", "path", "notebook_path")], cwd)
        if not reason and d and not m:
            for p in (tin.get(k) for k in ("file_path", "path", "notebook_path")):
                if p and os.path.splitext(str(p))[1] in CODE_EXT:
                    with open(os.path.join(d, "build.log"), "a", encoding="utf-8") as f:
                        f.write(f"EDIT {p}\n\n")
    if not reason:
        if m and tool in SHELL_TOOLS and os.path.exists(os.path.join(os.path.dirname(m), "refused")):
            os.remove(os.path.join(os.path.dirname(m), "refused"))  # any other command ends the one-retry allowance
        if m and tool == "Bash" and isinstance(tin.get("command"), str):
            traced = inject_tracer(tin["command"], cwd, os.path.dirname(m))
            if traced != tin["command"]:  # switch the Python call recorder on for this by-hand command
                print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                         "updatedInput": dict(tin, command=traced)}}))
        return 0
    if m and "was written during this rehearsal" in reason:  # refuse once: the second identical attempt goes through, marked
        key = hashlib.sha1(cmd.encode("utf-8", "replace")).hexdigest() if tool in SHELL_TOOLS else None
        refused = os.path.join(os.path.dirname(m), "refused")
        if key and read(refused).strip() == key:  # the same command, tried again right after the refusal
            os.remove(refused)
            with open(os.path.join(os.path.dirname(m), "log.md"), "a", encoding="utf-8") as f:
                f.write(f"forced: {cmd}\n\n")
            return 0
        if key:
            with open(refused, "w", encoding="utf-8") as f:
                f.write(key)
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
