# Phase 0 probe results (US-001), Claude Code 2.1.300, 2026-10-15

Probe plugin: `tests/probes/plugin/` (hooks/log.py logs every hook input to /tmp/probe-log.jsonl).

Base command, run from /tmp/probe-work with inherited CLAUDE_* env unset and stdin from /dev/null:

    claude -p --plugin-dir tests/probes/plugin --permission-mode bypassPermissions --output-format json --model sonnet [--settings S] "<prompt>"

From P7 on, S = `{"enabledPlugins":{"rehearse@rehearse":false}}`, because the installed rehearse plugin rewrote Bash commands in the first P15 run.
Env knobs read by log.py: PROBE_STOP_LIMIT (Stop blocks, default 3), PROBE_STOP_REASON, PROBE_NO_AGENT_REWRITE.

## P12, P2, P4
- Prompt `/probe:nothing — just reply OK` and `rehearse: hello`: UserPromptSubmit input.prompt = the text as typed. Input keys: session_id, transcript_path, cwd, prompt_id, permission_mode, hook_event_name, prompt.
- Prompt `/probe:hello rehearse task` (real plugin skill): UserPromptSubmit prompt `"/probe:hello rehearse task"`, then UserPromptExpansion `{"expansion_type":"slash_command","command_name":"probe:hello","command_args":"rehearse task","command_source":"plugin"}`.
- systemMessage: absent from -p JSON stdout and stderr. Interactive (tmux): shown under the prompt as `⎿  UserPromptSubmit says: PROBE: system message shown?`.
- env_keys: CLAUDE_PLUGIN_DATA, CLAUDE_PLUGIN_ROOT, CLAUDE_PROJECT_DIR, CLAUDE_CODE_SESSION_ID, ... CLAUDE_PLUGIN_DATA = /home/joshu/.claude/plugins/data/probe-inline, hook wrote a file there: writable.
- CLAUDE_PLUGIN_OPTION_PROBE_FLAG: absent with only the manifest default. With `--settings '{"pluginConfigs":{"probe@inline":{"options":{"probe_flag":true}}}}'`: present, value `true`.

## P1, P15
- Prompt: spawn probe:probe with prompt 'do your job'. PreToolUse Agent tool_input `{"prompt":"do your job","subagent_type":"probe:probe",...}`; hook returned updatedInput prompt "PROBE-PROMPT: reply with exactly the word PROBEOK and nothing else", model "haiku".
- Subagent transcript first user message = the replaced prompt; assistant model `claude-haiku-5-5`; modelUsage had sonnet + haiku only, although user settings set CLAUDE_CODE_SUBAGENT_MODEL=opus (without the override, P3's probe agent ran on opus).
- Subagent PreToolUse Write and Bash: `agent_type: "probe:probe"`, `agent_id: "a5551b4a5f4d30f7b"`. Main-thread calls have neither field.
- SubagentStop: `agent_type "probe:probe"`, agent_id, agent_transcript_path, stop_hook_active false, `last_assistant_message: "PROBEOK"`, background_tasks, session_crons, effort.

## P7
| Run | Stop events | Blocks honoured | Note |
|---|---|---|---|
| limit 3 | 4 | 3 | stop_hook_active false, then true on each continuation |
| limit 12, default cap | 9 | 8 | 9th block ignored; -p result was "" |
| limit 12, CLAUDE_CODE_STOP_HOOK_BLOCK_CAP=16 | 13 | 12 | |
| limit 12, each block asks for `echo tick` | 13 | 12 | count resets on a tool call |
- `"timeout": 900` on the Stop hook: accepted, stderr empty. Maximum not learned.
- `CLAUDE_CODE_OAUTH_TOKEN=bad`: exit 1, result "Failed to authenticate. API Error: 401 Invalid bearer token", terminal_reason api_error. Hooks fired: UserPromptSubmit, StopFailure `{"error":"authentication_failed","last_assistant_message":"Failed to authenticate. ..."}`, SessionEnd `{"reason":"other"}`. No Stop.
- Interrupt (interactive tmux, Escape during a 60 s Bash call): log holds UserPromptSubmit and PreToolUse only; no Stop, no PostToolUse, nothing after 5 s. Usage limit: untested.

## P14
- `sleep 130 && echo slept`: Claude Code's own foreground-sleep block steered the model to run_in_background; timeout 900000 did appear in the PostToolUse tool_input.
- `python3 -c "import time; time.sleep(130); print('slept')"` in the foreground: run took 138 s, stdout "slept", PostToolUse tool_input `"timeout": 900000`. Pass.

## P3
- `probe-stage start` → "started"; separate call `probe-stage step 1+1` → "2"; `probe-stage stop` → "stopped". Process survives Bash calls.
- Subagent: probe:probe misread "step 2+3" as steps of its own body (agent body confound). Second run, general-purpose subagent: `probe-stage step x+2` → `error: NameError("name 'x' is not defined")`, an answer from the live server (my `step x=40` setup was an assignment, which eval rejects). The subagent reaches the process; cross-caller state not shown with a value.
- Per step from a shell (`/usr/bin/time probe-stage step 1+1`, 5 runs): 0.02 s each.
- Fingerprint (`git status --porcelain=v1 -z --untracked-files=all` + sha1 of each listed file), django --depth 1 clone on /tmp (ext4, 7084 tracked files): 0.02 s clean, 0.02 s with 22 changed or untracked files; sha1 of all 7084 files 0.07 s.
- Same fingerprint on this repo on /mnt/d (Windows drive via WSL, 567 untracked files): 2.1 s; git status alone 1.0 s.

## P6
- -p: prompt "Ask me a question with the AskUserQuestion tool ..." → result "I couldn't ask you. The AskUserQuestion tool isn't available in this session"; no PreToolUse for it.
- Interactive (tmux): PreToolUse and PostToolUse both fire. PostToolUse tool_response: `{"questions":[...],"answers":{"Which colour do you prefer, red or blue?":"Blue"},"annotations":{}}`.

## P11
- Case: `evals/hello/prompt.md` ("Reply with only the word HELLO.") + `evals/hello/graders/says-hello.md` (frontmatter `type: regex`, `pattern: HELLO`). No case.yaml needed.
- Command: `claude plugin eval tests/probes/plugin --runs 1 --trust-plugin --no-publish --case hello` → exit 0, 5 s, $0.08: with 1.00, without 1.00 (ablation with-without is the default for a path target; `--ablation none` for one arm).
- Report: `<plugin>/evals/results/<timestamp>/report.html` (deleted after the run). No sandbox error; bwrap and socat are needed only when a case grants Bash. `--bare` not needed.

## P16 (2.0.1): `run_in_background` set by a hook, Claude Code 2.1.301, 2026-10-16
- Probe plugin rebuilt in the scratchpad (`probe-fg/`: hooks/log.py logs PreToolUse Agent, PostToolUse Agent and SubagentStop; on PreToolUse Agent it returns `updatedInput` with the prompt, `model: haiku` and `run_in_background: false`). Run with `--settings '{"enabledPlugins":{"rehearse@rehearse":false}}'`.
- Prompt asked for the spawn with `run_in_background` true and an immediate DONE reply. PreToolUse `tool_input` arrived with `run_in_background: true`; PostToolUse `tool_input` had `run_in_background: false`, and its `tool_response` was `{"status": "completed", ..., "content": [{"type": "text", "text": "PROBEOK"}]}`, the subagent's answer, not a background-task id. SubagentStop (`last_assistant_message: "PROBEOK"`) fired before the main agent's DONE. 11 s, $0.12. Pass: a hook-set `run_in_background` is honoured.
- The SubagentStop hook's `systemMessage` does not appear in the main transcript (only `hook_success` attachments), so the agent never reads it; the Agent tool's result is what the agent sees.
