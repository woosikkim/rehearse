#!/usr/bin/env python3
"""Rehearsal hooks. UserPromptSubmit: nudge build requests toward the rehearse skill.
PreToolUse: while .rehearsal/active exists, block scripts, loops and code-file writes.

Reads a pre-tool-use hook payload (JSON) on stdin. Exit 2 = block (reason on stderr), 0 = allow.
Tool names cover Claude Code; the others are best-effort for agents with similar hooks.
"""
import json
import os
import re
import shlex
import sys

FLAG = os.path.join(".rehearsal", "active")
CODE_EXT = {".py", ".js", ".mjs", ".cjs", ".ts", ".jsx", ".tsx", ".sh", ".bash", ".zsh", ".rb",
            ".go", ".rs", ".java", ".kt", ".php", ".pl", ".lua", ".ps1", ".swift", ".c", ".cpp", ".cs"}
SHELL_TOOLS = {"Bash", "shell", "local_shell", "exec_command", "run_shell_command"}
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit", "write_file", "replace", "edit_file"}
LOOPS = {"for", "while", "until", "xargs", "parallel", "watch", "sleep", "nohup"}
INTERPRETERS = {"python", "py", "node", "deno", "bun", "ruby", "perl", "php", "bash", "sh", "zsh",
                "fish", "pwsh", "powershell", "npx", "tsx", "ts-node", "eval", "source", "."}
RUNNERS = {"npm": {"run", "start", "exec", "test"}, "pnpm": {"run", "start", "exec", "test"},
           "yarn": {"run", "start", "exec", "test"}, "go": {"run"}, "cargo": {"run"}}
WRAPPERS = {"sudo", "env", "time", "nice", "command", "exec"}
VERSION_ARGS = {"--version", "-V", "-v", "version"}


def active(payload):
    dirs = {payload.get("cwd"), os.environ.get("CLAUDE_PROJECT_DIR"), os.getcwd()}
    return any(d and os.path.exists(os.path.join(d, FLAG)) for d in dirs)


def shell_text(cmd):
    if isinstance(cmd, list):  # e.g. ["bash", "-lc", "curl ..."]
        if len(cmd) >= 3 and os.path.basename(cmd[0]) in {"bash", "sh", "zsh"} and cmd[1] in {"-c", "-lc"}:
            return cmd[-1]
        return shlex.join(cmd)
    return cmd or ""


def check_shell(cmd):
    bare = re.sub(r"'[^']*'|\"(?:\\.|[^\"\\])*\"", "''", cmd)  # quoted text can't run anything
    if re.search(r"(?<![&>|])&(?![&>])", bare):
        return "background job (&)"
    for seg in re.split(r"&&|\|\||[;|\n()`]|\$\(", bare):
        toks = seg.split()
        i = 0
        while i < len(toks) and (re.fullmatch(r"\w+=\S*", toks[i]) or toks[i] in WRAPPERS or toks[i] == "timeout"):
            i += 1
            while toks[i - 1] == "timeout" and i < len(toks) and re.fullmatch(r"-\S*|\d[\w.]*", toks[i]):
                i += 1
        if i >= len(toks):
            continue
        prog, args = toks[i], toks[i + 1:]
        name = re.sub(r"[\d.]+$", "", os.path.basename(prog)) or prog
        if name in LOOPS:
            return f"loop/wait command '{name}'"
        if name in INTERPRETERS and not (len(args) == 1 and args[0] in VERSION_ARGS):
            return f"interpreter '{prog}' (scripts and inline code)"
        if name in RUNNERS and args and args[0] in RUNNERS[name]:
            return f"'{prog} {args[0]}' runs a script"
        if prog.startswith("./") or os.path.splitext(prog)[1] in CODE_EXT:
            return f"running script file '{prog}'"
    return None


def check_write(tool_input):
    text = json.dumps(tool_input)
    paths = [tool_input.get(k) for k in ("file_path", "path", "notebook_path")]
    paths += re.findall(r"\*\*\* (?:Add|Update) File: (\S+?)(?:\\n|\s)", text)  # apply_patch format
    for p in filter(None, paths):
        if os.path.splitext(str(p))[1] in CODE_EXT:
            return f"writing code file '{p}'"
    return None


# ponytail: keyword match on the prompt; swap for a classifier if it misfires often.
BUILD = re.compile(r"\b(build|make|write|create|code|develop|implement|automate)\b", re.I)
WORLD = re.compile(r"\b(scrap\w*|crawl\w*|bot|api|client|cli|tool|script|convert\w*|automation|integration|"
                   r"pipeline|sync\w*|webhook|fetch\w*|download\w*|monitor\w*|upload\w*|parser|extractor)\b", re.I)
NUDGE = ("rehearse: this request builds a program that touches the outside world. Before writing any "
         "code, invoke the `rehearse` skill and rehearse the program's job by hand first.")


def nudge(prompt):
    if BUILD.search(prompt) and WORLD.search(prompt) and not re.search(r"\b(skip|no) rehears", prompt, re.I):
        print(NUDGE)
    return 0


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0  # not a payload we understand: fail open
    if payload.get("hook_event_name") == "UserPromptSubmit":
        return nudge(payload.get("prompt", ""))
    if not active(payload):
        return 0
    tool, tin = payload.get("tool_name", ""), payload.get("tool_input") or {}
    if tool in SHELL_TOOLS:
        reason = check_shell(shell_text(tin.get("command")))
    elif tool in WRITE_TOOLS or "patch" in tool.lower():
        reason = check_write(tin)
    else:
        reason = None
    if not reason:
        return 0
    print(f"rehearse: blocked during rehearsal: {reason}. Do this step by hand with one direct "
          "command or tool call (curl, jq, grep, sqlite3, a browser tool...) and log what you see. "
          "Code is written in the build phase, after `rm .rehearsal/active`.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
