"""The stage: one Python process per run, one step per request over a Unix socket (plan 2.7).

    python server.py --root <project root> --state <state json> --socket <path> --pidfile <path>

Started detached by `rehearse stage start` under the project's interpreter, so it keeps to old-Python syntax
and loads the plugin's helpers under private names (never on sys.path, where they could shadow project modules).
Requests and replies are JSON lines: {"op": "hello"|"step"|"stop", "code": ...}. Writes its pid to --pidfile.
"""
import argparse
import ast
import builtins
import contextlib
import importlib.util
import io
import json
import os
import socket
import sys
import traceback

HERE = os.path.dirname(os.path.realpath(__file__))
REFUSAL = "one step at a time; put the loop in the program, not the rehearsal"
CREATED = "written during this rehearsal; the program that existed may read it, you may not import it"
LOCKED = ("observe", "confirm", "rework-observe")
ALLOWED = (ast.Expr, ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Import, ast.ImportFrom)
REFUSED = tuple(t for t in (getattr(ast, n, None) for n in (
    "FunctionDef", "AsyncFunctionDef", "ClassDef", "For", "AsyncFor", "While", "If", "IfExp", "With", "AsyncWith",
    "Try", "TryStar", "Lambda", "ListComp", "SetComp", "DictComp", "GeneratorExp", "Global", "Nonlocal", "Match"))
    if t is not None)
LOADERS = {"exec", "eval", "compile", "__import__"}
SAFE = (bool, int, float, complex, str, bytes, type(None))
SIZED = (list, tuple, dict, set, frozenset, bytearray)


def _load(name):
    spec = importlib.util.spec_from_file_location("_rehearse_" + name, os.path.join(HERE, "..", "hooks", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


S = _load("state")
F = _load("fingerprint")


def refuse(tree):
    """REFUSAL when the parsed code is not one plain step, else None. Attribute names are never looked at."""
    if len(tree.body) != 1 or not isinstance(tree.body[0], ALLOWED):
        return REFUSAL
    for node in ast.walk(tree):
        if isinstance(node, REFUSED) or (isinstance(node, ast.Name) and node.id in LOADERS):
            return REFUSAL
        names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
            [node.module or ""] if isinstance(node, ast.ImportFrom) else []
        if any(n in ("importlib", "runpy") or n.startswith(("importlib.", "runpy.")) for n in names):
            return REFUSAL
    return None


def safe_repr(v):
    """Never runs project code: exact builtin scalars by repr, anything else by type name (and length if builtin)."""
    t = type(v)
    if t in SAFE:
        return repr(v)[:200]
    if t in SIZED:
        return ("<%s len=%d>" % (t.__name__, len(v)))[:200]
    return ("<%s>" % t.__name__)[:200]


def created_import(node, state_path):
    """The created file an import step would load while edits are locked, else None."""
    s = S.load(state_path) or {}
    if s.get("phase") not in LOCKED:
        return None
    created = set(os.path.realpath(p) for p in s.get("created") or [])
    if isinstance(node, ast.Import):
        mods = [a.name for a in node.names]
    elif node.level:
        mods = []  # ponytail: relative imports are not resolved; a step runs as __main__ so they fail anyway
    else:
        mods = [node.module] + [node.module + "." + a.name for a in node.names if a.name != "*"]
    for mod in mods:
        parts = mod.split(".")
        for i in range(1, len(parts) + 1):  # parents first: find_spec("a.b") imports package a
            try:
                spec = importlib.util.find_spec(".".join(parts[:i]))
            except (ImportError, ValueError, AttributeError):
                break
            if spec is None:
                break
            origin = spec.origin if spec.origin not in (None, "built-in", "frozen") else None
            if origin and os.path.realpath(origin) in created:
                return origin
    return None


class Stage:
    def __init__(self, root, state_path):
        self.root = os.path.realpath(root)
        self.state_path = state_path
        self.ns = {"__name__": "__main__", "__builtins__": builtins}
        self.kinds = {}

    def project_file(self, filename):
        hit = self.kinds.get(filename)
        if hit is None:
            path = os.path.realpath(filename) if os.path.isabs(filename) else ""
            rel = os.path.relpath(path, self.root) if path.startswith(self.root + os.sep) else None
            hit = rel if rel and F.is_code(rel) and not F.excluded(self.root, rel) else ""
            self.kinds[filename] = hit
        return hit

    def step(self, code):
        reply = {"accepted": False, "project_files": [], "stdout": "", "stderr": "", "value": None,
                 "exception": None, "error": None}
        try:
            tree = ast.parse(code, "<stage>")
        except SyntaxError as x:
            reply["error"] = "SyntaxError: %s" % x
            return reply
        why = refuse(tree)
        node = tree.body[0] if tree.body else None
        if not why and isinstance(node, (ast.Import, ast.ImportFrom)) and created_import(node, self.state_path):
            why = CREATED
        if why:
            reply["error"] = why
            return reply
        reply["accepted"] = True
        files = set()

        def tracer(frame, event, arg):
            f = self.project_file(frame.f_code.co_filename)
            if f:
                files.add(f)

        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                sys.settrace(tracer)
                try:
                    if isinstance(node, ast.Expr):
                        value = eval(compile(ast.Expression(node.value), "<stage>", "eval"), self.ns)
                    else:
                        exec(compile(tree, "<stage>", "exec"), self.ns)
                        value = None
                finally:
                    sys.settrace(None)
            if value is not None:
                reply["value"] = safe_repr(value)
        except BaseException as x:  # the namespace survives any step, SystemExit included
            reply["exception"] = "".join(traceback.format_exception_only(type(x), x)).strip()[:2000]
            reply["error"] = reply["exception"]
        reply.update(stdout=out.getvalue(), stderr=err.getvalue(), project_files=sorted(files))
        return reply


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--socket", required=True)
    ap.add_argument("--pidfile", required=True)
    a = ap.parse_args()
    os.chdir(a.root)
    sys.path[0] = os.path.realpath(a.root)  # as `python -c` from the root, not this file's folder
    stage = Stage(a.root, a.state)
    with contextlib.suppress(OSError):
        os.unlink(a.socket)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(a.socket)
    srv.listen(4)
    with open(a.pidfile, "w") as f:
        f.write("%d\n" % os.getpid())
    while True:
        conn, _ = srv.accept()
        with conn:
            try:
                req = json.loads(conn.makefile("r", encoding="utf-8").readline())
            except ValueError:
                continue
            op = req.get("op")
            if op == "step":
                reply = stage.step(str(req.get("code") or ""))
            else:
                reply = {"python": sys.executable, "path0": sys.path[0], "pid": os.getpid()}
            conn.sendall((json.dumps(reply, ensure_ascii=False) + "\n").encode("utf-8"))
            if op == "stop":
                break
    srv.close()
    for p in (a.socket, a.pidfile):
        with contextlib.suppress(OSError):
            os.unlink(p)


if __name__ == "__main__":
    main()
