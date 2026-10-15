import json, os, sys
STOP_LIMIT = int(os.environ.get("PROBE_STOP_LIMIT", "3"))
inp = json.load(sys.stdin)
ev = inp.get("hook_event_name")
rec = {"event": ev, "input": inp, "env_keys": sorted(k for k in os.environ if k.startswith("CLAUDE_"))}
d = os.environ.get("CLAUDE_PLUGIN_DATA")
if d:
    try:
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "w.txt"), "w").write("x")
        rec["plugin_data"] = [d, "writable"]
    except OSError as e:
        rec["plugin_data"] = [d, repr(e)]
rec["option_probe_flag"] = os.environ.get("CLAUDE_PLUGIN_OPTION_PROBE_FLAG")
with open("/tmp/probe-log.jsonl", "a") as f:
    f.write(json.dumps(rec) + "\n")
out = None
ti = inp.get("tool_input") or {}
if ev == "UserPromptSubmit":
    out = {"systemMessage": "PROBE: system message shown?",
           "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "PROBE-CONTEXT"}}
elif ev == "PreToolUse" and inp.get("tool_name") == "Agent" and not os.environ.get("PROBE_NO_AGENT_REWRITE"):
    new = dict(ti, prompt="PROBE-PROMPT: reply with exactly the word PROBEOK and nothing else", model="haiku")
    out = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedInput": new}}
elif ev == "PreToolUse" and inp.get("tool_name") == "Bash" and ("sleep 130" in ti.get("command", "") or "sleep(130)" in ti.get("command", "")):
    out = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedInput": dict(ti, timeout=900000)}}
elif ev == "Stop":
    try:
        n = int(open("/tmp/probe-stop-count").read())
    except (OSError, ValueError):
        n = 0
    if n < STOP_LIMIT:
        open("/tmp/probe-stop-count", "w").write(str(n + 1))
        out = {"decision": "block", "reason": os.environ.get("PROBE_STOP_REASON", "PROBE: stop blocked, say DONE again")}
if out:
    print(json.dumps(out))
