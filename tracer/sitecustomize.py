"""Rehearse tracer. Imported as `sitecustomize` when <plugin>/tracer is on PYTHONPATH.

Does nothing unless REHEARSE_TRACE (a .jsonl path) and REHEARSE_ROOT (the project
directory) are both set. Then it appends one JSON line per call, return or escaped
exception of a function whose file lives under REHEARSE_ROOT, so a by-hand run
leaves a record of the project code it executed. Stdlib only; runs on 3.6+.
It must never change the traced program: every path swallows its own errors, and values are shown by
type name unless they are builtin scalars or containers of them, so no project __repr__ ever runs.
"""
import os
import sys

MAX_EVENTS = 2000
MAX_DEPTH = 50
MAX_REPR = 200
SKIP = ("/.rehearsal/", "site-packages", "dist-packages", "/lib/python")
RUNNERS = ("pytest", "py.test", "runtests.py")


def _is_test_runner():
    argv = list(getattr(sys, "argv", None) or [""])
    joined = " ".join(str(a) for a in (getattr(sys, "orig_argv", None) or []) + argv)
    return (os.path.basename(str(argv[0])).endswith(RUNNERS) or "-m pytest" in joined
            or "-m unittest" in joined or "pytest/__main__" in joined or "unittest/__main__" in joined)


def _start(trace_path, root):
    import json
    import opcode
    import reprlib

    out = open(trace_path, "a", 1, encoding="utf-8")  # line-buffered: every event reaches disk
    prefix = os.path.realpath(root).rstrip(os.sep) + os.sep
    short = reprlib.Repr()
    short.maxstring = short.maxother = MAX_REPR
    # Opcodes a frame normally leaves through; any other means an exception escaped.
    leaving = set(opcode.opmap[n] for n in ("RETURN_VALUE", "RETURN_CONST", "YIELD_VALUE", "YIELD_FROM")
                  if n in opcode.opmap)
    files = {}  # co_filename -> path relative to root, or None when not project code
    state = {"n": 0, "depth": 0, "checked": False}
    pending = {}  # id(frame) -> exception raised inside it, not yet known to escape

    SAFE = (bool, int, float, complex, str, bytes, type(None))

    def r(v, depth=0):
        """A repr that never runs project code: builtin scalars and containers of them; anything else by type name."""
        try:
            t = type(v)  # exact types only: a subclass may override __repr__, __iter__ or __len__ with project code
            if t in SAFE:
                return short.repr(v)[:MAX_REPR]
            if depth < 2 and t in (list, tuple, set, frozenset):
                items = [r(x, depth + 1) for x in list(v)[:8]]
                more = ", ..." if len(v) > 8 else ""
                return (t.__name__ + "[" if t not in (list, tuple) else "[") + ", ".join(items) + more + "]"
            if depth < 2 and t is dict:
                items = ["%s: %s" % (r(k, depth + 1), r(x, depth + 1)) for k, x in list(v.items())[:8]]
                return "{" + ", ".join(items) + (", ...}" if len(v) > 8 else "}")
            return "<%s>" % t.__name__
        except Exception:
            return "<repr failed>"

    def stop():
        try:
            sys.settrace(None)
            out.close()
        except Exception:
            pass

    def rel(code):
        fn = code.co_filename
        if fn not in files:
            files[fn] = None
            if not fn.startswith("<"):
                p = os.path.realpath(fn)
                if p.startswith(prefix) and not any(s in "/" + p[len(prefix):] for s in SKIP):
                    files[fn] = p[len(prefix):]
        return files[fn]

    def qual(frame):
        code = frame.f_code
        q = getattr(code, "co_qualname", None)
        if q:
            return q
        loc = frame.f_locals
        if "self" in loc:
            return type(loc["self"]).__name__ + "." + code.co_name
        if "cls" in loc and isinstance(loc["cls"], type):
            return loc["cls"].__name__ + "." + code.co_name
        return code.co_name

    def emit(ev):
        state["n"] += 1
        out.write(json.dumps(ev) + "\n")
        if state["n"] >= MAX_EVENTS:
            stop()

    def local(frame, event, arg):
        try:
            if event == "exception":
                pending[id(frame)] = arg[1] if arg[1] is not None else arg[0]
            elif event == "return":
                state["depth"] -= 1
                exc = pending.pop(id(frame), None)
                code = frame.f_code
                ev = {"t": "return", "func": code.co_name, "qual": qual(frame), "file": files[code.co_filename],
                      "line": frame.f_lineno}
                if (arg is None and exc is not None and frame.f_lasti >= 0
                        and code.co_code[frame.f_lasti] not in leaving):
                    ev["t"] = "exception"
                    ev["exc"] = (type(exc).__name__ + ": " + str(exc))[:MAX_REPR]
                else:
                    ev["ret"] = r(arg)
                if state["n"] < MAX_EVENTS:
                    emit(ev)
        except Exception:
            stop()
            return None
        return local

    def call(frame, event, arg):
        try:
            if event != "call" or state["n"] >= MAX_EVENTS or state["depth"] >= MAX_DEPTH:
                return None
            code = frame.f_code
            path = rel(code)
            if path is None:
                return None
            if not state["checked"]:
                state["checked"] = True
                if _is_test_runner():
                    stop()
                    return None
            loc = frame.f_locals
            names = code.co_varnames[:code.co_argcount + code.co_kwonlyargcount]
            args = {}
            for name in names[:6]:
                if name not in ("self", "cls") and name in loc:
                    args[name] = r(loc[name])
            state["depth"] += 1
            emit({"t": "call", "func": code.co_name, "qual": qual(frame), "file": path,
                  "line": frame.f_lineno, "args": args})
            try:
                frame.f_trace_lines = False  # 3.7+: no per-line callbacks, only return/exception
            except Exception:
                pass
            return local
        except Exception:
            stop()
            return None

    sys.settrace(call)


try:
    _trace, _root = os.environ.get("REHEARSE_TRACE"), os.environ.get("REHEARSE_ROOT")
    if _trace and _root and not sys.flags.isolated and not sys.flags.no_site:
        _start(_trace, _root)
except Exception:
    pass
