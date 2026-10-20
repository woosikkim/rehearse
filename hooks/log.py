"""The run's readable log (log.md) and machine record (commands.jsonl), both redacted."""
import json
import os
import re
import time

# Applied in order. The -u/--user one runs on the command line only; it over-redacts `sort -u x`, harmlessly.
REDACT = [(re.compile(r"(?i)\b(authorization|cookie|set-cookie)[\"']?\s*:\s*[^\n'\"]*"), r"\1: ***"),
          (re.compile(r"(?i)(bearer\s+)\S+"), r"\1***"),
          (re.compile(r"(?i)((?:api[_-]?key|token|password|secret)[\"']?\s*[=:]\s*[\"']?)[^\s\"'&,]+"), r"\1***")]
REDACT_USER = (re.compile(r"(?<!\S)(--user[= ]|-u\s*)\S+"), r"\1***")
REDACT_URL = (re.compile(r"(://[^/\s:@]+:)[^@\s]+@"), r"\1***@")


def redact(text, command=False):
    for rx, sub in REDACT:
        text = rx.sub(sub, text)
    if command:
        text = REDACT_USER[0].sub(REDACT_USER[1], text)
    return REDACT_URL[0].sub(REDACT_URL[1], text)


def trim(text):
    """First 40 non-blank lines, each at most 400 characters, at most 4 KB in all."""
    lines = [ln[:400] for ln in text.splitlines() if ln.strip()][:40]
    return "\n".join(lines)[:4096]


def output_text(payload):
    out = payload.get("tool_response")
    if payload.get("hook_event_name") == "PostToolUseFailure":
        out = payload.get("error") or out
    if isinstance(out, dict) and {"stdout", "stderr"} & out.keys():
        return "\n".join(str(out[k]) for k in ("stdout", "stderr") if out.get(k))
    return out if isinstance(out, str) else json.dumps(out)


def record(folder, entry):
    with open(os.path.join(folder, "commands.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(dict(entry, time=time.time()), ensure_ascii=False) + "\n")


def records(folder):
    out = []
    try:
        with open(os.path.join(folder, "commands.jsonl"), encoding="utf-8") as f:
            for ln in f:
                try:
                    out.append(json.loads(ln))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


def record_result(folder, res):
    """bin/rehearse and the stage client write every result here before printing it, so the hook reads the
    command's own record and a filter on its output (head, tail -c, cut, a redirect) cannot lose a result."""
    with open(os.path.join(folder, "results.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(res, ensure_ascii=False) + "\n")


def new_results(folder, offset):
    """(the results recorded after byte offset, the offset to read from next time); whole lines only."""
    try:
        with open(os.path.join(folder, "results.jsonl"), "rb") as f:
            f.seek(offset)
            data = f.read()
    except OSError:
        return [], offset
    data = data[:data.rfind(b"\n") + 1]
    out = []
    for ln in data.decode("utf-8", "replace").splitlines():
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if isinstance(r, dict):
            out.append(r)
    return out, offset + len(data)


SEARCH_TOOLS = ("WebSearch", "WebFetch")


def search_steps(folder):
    """The logged steps that count as a search: a WebSearch or WebFetch call, or a `rehearse fetch`."""
    return {r["step"] for r in records(folder) if "step" in r
            and (r.get("tool") in SEARCH_TOOLS or r.get("result") == "fetch")}


def log_command(folder, cmd, output, phase, kinds=None, invocations=0, tool=None):
    """Append one Bash command (or a WebSearch/WebFetch call) and the head of its output; return its step id."""
    step = "S%d" % (1 + sum(1 for r in records(folder) if "step" in r))
    # the plugin's own result kinds (bin/rehearse excludes ending/run steps as sources): from the hook's records,
    # else read from the output before the trim can cut the last line
    kinds = [k for k in kinds or [] if k] or re.findall(r'^REHEARSE-RESULT .*?"kind": "([\w-]+)"', output, re.M)
    cmd, out = redact(cmd, command=True), trim(redact(output))
    # "rehearse": how many rehearse commands this step ran (each should have written a result); since 3.1.0
    entry = {"step": step, "cmd": cmd, "phase": phase, "out": out, "result": kinds[-1] if kinds else None,
             "rehearse": invocations}
    if tool:
        entry["tool"] = tool
    record(folder, entry)
    with open(os.path.join(folder, "log.md"), "a", encoding="utf-8") as f:
        f.write("\n".join(["%s [%s] $ %s" % (step, phase, cmd)] + ([out] if out else [])) + "\n\n")
    return step


def log_edit(folder, tool, path, phase):
    record(folder, {"edit": path, "tool": tool, "phase": phase})
    with open(os.path.join(folder, "log.md"), "a", encoding="utf-8") as f:
        f.write("EDIT [%s] %s %s\n\n" % (phase, tool, path))


def trace_lines(path, since=0, limit=10):
    """Readable lines for the tracer events written to path after byte offset `since`."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            f.seek(since)
            events = [json.loads(ln) for ln in f.read().splitlines() if ln.strip()]
    except (OSError, ValueError):
        return []
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
