"""Where files come from and what a shell command runs. A recorder: it resolves, it never refuses.

parse(command, cwd) splits a Bash command into segments and returns, for each one, the program
position (what actually runs), the test runner it is, and the files it writes: targets the agent
writes itself (redirection, tee, cp, mv, ln, install, dd, curl -o/-O, wget -O, a text tool's -o,
sed/perl -i, patch) and outputs a program produces for it (a compiler's, linker's or packager's -o).
"""
import os
import re
import shlex

QUOTED = re.compile(r"'[^']*'|\"(?:\\.|[^\"\\])*\"")
SEPARATORS = re.compile(r"&&|\|\||;|\||\n|\$\(|\(|\)|`")
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1([^\n]*)\n.*?\n[\t]*\2[ \t]*(?=\n|$)", re.S)
WRAPPERS = {"sudo", "env", "time", "nice", "command", "exec", "nohup"}
INTERPRETERS = {"python", "node", "ruby", "php", "perl", "bash", "sh", "zsh"}
INLINE = {"-c", "-e", "-E", "-r", "-p"}
LAUNCHERS = {"npx": None, "uvx": None, "bunx": None, "uv": "run", "pipx": "run"}
TEST_SUBCOMMANDS = {"npm": "test", "pnpm": "test", "yarn": "test", "go": "test", "cargo": "test"}
PY_RUNNERS = {"pytest", "unittest"}
# Tools whose -o is the agent's own write (a text result), not a program built for it.
TEXT_TOOLS = {"sort", "uniq", "jq", "yq", "pandoc", "iconv", "cut", "tr", "awk", "sed", "base64", "gzip",
              "gunzip", "xz", "bzip2", "zip", "cpp", "m4", "envsubst", "fmt", "fold", "paste", "join", "comm",
              "cat", "echo", "printf", "tee", "head", "tail", "grep", "xxd", "od"}


def realpath(cur, path):
    return os.path.realpath(os.path.join(cur, os.path.expanduser(str(path))))


REHEARSE_CALL = re.compile(r"(?:^|[\s;&|(])(?:\S*rehearse|\$\w+)\s+(?:plan|ending|run|fetch|job|status|wait|wrong|stage|tried|review|failed)\b")


def invocations(cmd):
    """How many rehearse commands the text runs, each expected to write a result (quoted text and heredoc
    bodies blanked, so `grep 'rehearse ending' log.md` and a script fed on stdin do not count)."""
    bare = HEREDOC.sub(lambda m: " " * len(m.group(0)), cmd)
    bare = QUOTED.sub(lambda q: q.group(0)[0] + "_" * (len(q.group(0)) - 2) + q.group(0)[-1], bare)
    return len(REHEARSE_CALL.findall(bare))


def segments(cmd):
    """Blank quoted text without changing its length, cut on separators found in the blanked text, return raw slices."""
    bare = QUOTED.sub(lambda q: q.group(0)[0] + "_" * (len(q.group(0)) - 2) + q.group(0)[-1], cmd)
    cuts = [0] + [x for s in SEPARATORS.finditer(bare) for x in s.span()] + [len(cmd)]
    return [cmd[a:b] for a, b in zip(cuts[::2], cuts[1::2])]


def tokens(seg):
    try:
        lx = shlex.shlex(seg, posix=True, punctuation_chars=True)
        lx.whitespace_split = True
        return list(lx)
    except ValueError:
        return seg.split()


def prog_index(toks):
    i = 0
    while i < len(toks) and (re.fullmatch(r"\w+=\S*", toks[i]) or toks[i] in WRAPPERS or toks[i] == "timeout"):
        i += 1
        while toks[i - 1] == "timeout" and i < len(toks) and re.fullmatch(r"-\S*|\d[\w.]*", toks[i]):
            i += 1
    return i


def base_name(prog):
    name = os.path.basename(prog)
    return re.sub(r"[\d.]+$", "", name) or name


def resolve_module(name, cur):
    base = os.path.join(cur, name.replace(".", "/"))
    return next((os.path.realpath(base + t) for t in (".py", "/__init__.py", "/__main__.py")
                 if os.path.isfile(base + t)), None)


def _position(args, cur):
    """(program position, test runner) for an argv with redirections already removed."""
    if not args:
        return None, None
    prog, rest = args[0], args[1:]
    name = base_name(prog)
    positional = [a for a in rest if not a.startswith("-")]
    if name in LAUNCHERS and (LAUNCHERS[name] is None or rest[:1] == [LAUNCHERS[name]]):
        return _position([a for a in (rest if LAUNCHERS[name] is None else rest[1:]) if not a.startswith("-")], cur)
    if name in ("pytest", "py.test"):
        return (realpath(cur, positional[0]) if positional else None), "pytest"
    if name in TEST_SUBCOMMANDS and rest[:1] == [TEST_SUBCOMMANDS[name]]:
        return name, name + " test"
    if name in ("source", "."):
        return (realpath(cur, rest[0]) if rest else None), None
    if name in INTERPRETERS:
        if any(a in INLINE for a in rest) or not positional or positional[0] == "-":
            return None, None  # inline code or stdin: no file runs
        if name == "python" and rest[:1] == ["-m"] and len(rest) > 1:
            mod = rest[1]
            if mod in PY_RUNNERS:
                after = [a for a in rest[2:] if not a.startswith("-")]
                return (realpath(cur, after[0]) if after else None), mod
            return resolve_module(mod, cur) or mod, None
        return realpath(cur, positional[0]), None
    return (realpath(cur, prog) if "/" in prog else prog), None


def _writes(prog, args, cur):
    targets, outputs = [], []
    for k, t in enumerate(args):
        nxt = args[k + 1] if k + 1 < len(args) else ""
        if t in {">", ">>", ">|", "&>", "&>>"} or (t == ">&" and not re.fullmatch(r"\d+|-", nxt)):
            targets.append(nxt)
        elif t in {"-o", "--output"} or (prog == "curl" and re.fullmatch(r"-[A-Za-z]*o", t)) \
                or (prog == "wget" and t == "-O"):
            (targets if prog in ("curl", "wget") or prog in TEXT_TOOLS else outputs).append(nxt)
        elif t.startswith("--output="):
            (targets if prog == "curl" or prog in TEXT_TOOLS else outputs).append(t.split("=", 1)[1])
    plain = [a for a in args if not a.startswith("-") and a not in {">", ">>", ">|", "&>", "&>>", ">&", "<", "<<"}]
    if prog == "tee":
        targets += plain
    if prog in {"cp", "mv", "install", "ln"} and plain:
        targets.append(plain[-1])
    if prog == "dd":
        targets += [a[3:] for a in args if a.startswith("of=")]
    if prog == "curl" and any(re.fullmatch(r"-[A-Za-z]*O", a) for a in args):  # curl -O saves under the URL's name
        targets += [a.rsplit("/", 1)[-1] for a in plain if "://" in a]
    if prog in {"sed", "perl"} and any(re.match(r"-[^-]*i", a) or a.startswith("--in-place") for a in args):
        scripted = any(a in ("-e", "-f", "--expression", "--file") for a in args)
        targets += plain if scripted else plain[1:]
    if prog == "patch" and plain:
        targets.append(plain[0])
    files = lambda xs: [realpath(cur, x) for x in xs if x and x != "/dev/null"]  # noqa: E731
    return files(targets), files(outputs)


def parse(command, cwd):
    """One dict per segment: prog (basename), pp (program position), runner, targets, outputs, cwd."""
    out = []
    cur = cwd
    for seg in segments(HEREDOC.sub(r"<<\3", command or "")):
        toks = tokens(seg)
        i = prog_index(toks)
        if i >= len(toks):
            continue
        prog, args = toks[i], toks[i + 1:]
        if os.path.basename(prog) == "cd":
            cur = realpath(cur, args[0]) if args else os.path.expanduser("~")
            continue
        argv = [prog]
        k = 0
        while k < len(args):  # drop redirections and their targets: they are not arguments
            if args[k] in {">", ">>", ">|", "&>", "&>>", ">&", "<", "<<", "<<<"}:
                k += 2
                continue
            argv.append(args[k])
            k += 1
        pp, runner = _position(argv, cur)
        targets, outputs = _writes(os.path.basename(prog), args, cur)
        out.append({"prog": os.path.basename(prog), "pp": pp, "runner": runner,
                    "targets": targets, "outputs": outputs, "cwd": cur})
    return out
