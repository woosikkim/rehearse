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

## P17 (v3 planning): resume a stopped subagent with its context, Claude Code 2.1.301, 2026-10-16
- Scratchpad plugin `probe-resume/` (hooks log every PreToolUse, PostToolUse on Agent and SendMessage, and SubagentStop; a `probe` agent with Bash only, haiku). Main agent sonnet, headless `claude -p`, 18 s, $0.15.
- Prompt: spawn the subagent with "echo step1; remember the word MARIGOLD"; then continue the SAME subagent with "echo step2; reply with the word". The main agent loaded `SendMessage` through ToolSearch and sent to the agent id. PostToolUse(SendMessage) result: `{"success": true, "message": "Resuming agent a16f36a", "resumedAgentId": "a16f36a7ae5d0c7d9", "revivedAgentId": "a16f36a7ae5d0c7d9"}`. The resumed subagent's PreToolUse(Bash) carried the SAME `agent_id` and `agent_type`; SubagentStop fired again with `last_assistant_message: "MARIGOLD"`. Final line: `RESUMED=MARIGOLD METHOD=sendmessage`.
- Facts: a subagent can be continued with its context after it stopped; the hook sees the same agent identity after the resume; SubagentStop fires once per stop; the SendMessage result returns at once and the resumed agent's answer arrives later as a notification, not as the tool result. (v3 defers resuming: a fresh foreground worker per phase instead.)

## P18a (v3 planning): hook text on the Agent result, event order, tool removal; three runs, 2026-10-16
- Scratchpad plugin `probe-ctx/`: PostToolUse(Agent) returns `additionalContext` with a token; the `probe` agent file carries `disallowedTools: Agent, AskUserQuestion, Write, Edit`. Headless, sonnet, 17 s, $0.02-$0.12 per run.
- All three runs: the main agent's final line contained `CTX=ZEBRA-4471` (the hook's token); the subagent reported `AGENT=no, ASK=no` (ToolSearch found neither tool); SubagentStop fired BEFORE PostToolUse(Agent) (4.73 s vs 4.86 s in run 1; same order in runs 2 and 3).
- Facts: PostToolUse(Agent) `additionalContext` reaches the main agent; a verdict recorded at SubagentStop is in state before the PostToolUse(Agent) hook runs; `disallowedTools` in a plugin agent file is a structural lock.

## P18d (v3 planning): notes and refusals reaching a subagent; a refused spawn; three runs, 2026-10-16
- Scratchpad plugin `probe-sub/`: hook denies any Agent spawn of `probe:blocked` (reason token LION-8102), denies a subagent Bash command containing "forbidden" (token OTTER-5523), returns `additionalContext` HERON-3390 on every subagent PostToolUse(Bash). Headless, sonnet, $0.02-$0.12 per run.
- All three runs ended `SUBNOTE=HERON-3390 SUBDENY=OTTER-5523 MAINDENY=LION-8102`. The subagent's PostToolUse(Bash) payloads carried `agent_type=probe:probe` and its `agent_id`.
- Facts: a PostToolUse note and a PreToolUse deny reason reach a subagent; a PreToolUse deny on an Agent spawn reaches the main agent with its reason; `agent_type`/`agent_id` are present on a subagent's PostToolUse events, not only PreToolUse.

## P18b (v3 step 1): the stage lock across two workers, and the session id after `--resume`; three pairs, 2026-10-16
- Scratchpad plugin `probe-lock/`: state file with `phase` (starts `look`; a prompt beginning "yes" moves it to `build`); PreToolUse denies Write/Edit from `agent_type == probe:worker` while `look` (token CRANE-6610); the `worker` agent has `disallowedTools: Agent, AskUserQuestion`, haiku. Main agent sonnet, headless.
- Run 1 (`claude -p`): spawn the worker, which tries a Write, then `echo marker-1`. Run 2 (`claude -p --resume <session id> "yes. Now spawn a FRESH worker ..."`): the hook moves to `build`; a fresh worker tries a Write.
- All three pairs: run 1 `W1=REFUSED CRANE-6610`, `lock1.txt` absent; run 2 `W2=WROTE`, `lock2.txt` present; the session id in run 2's output and in every hook payload equals run 1's (e.g. `6735a880-…` in both), so `--resume` keeps the session id and the hook's UserPromptSubmit sees the "yes" under the same id. Pass on both items; plan §7 rule 1 and rule 2 do not apply.

## P18c (v3 step 1): the eval runner with a plugin worker; three runs, 2026-10-16
- Scratchpad plugin `probe-eval/`: a `worker` agent (`disallowedTools: Agent, AskUserQuestion`, haiku); a PostToolUse(Agent) hook returning `additionalContext` with the token `PROBE-NOTE-EVAL-5561`; one case `evals/worker-spawn/` (`allowed_tools: [Bash, Read, Write, Edit, Glob, Grep, Agent]`, prompt: spawn `probe:worker`, which runs `echo WORKER-RAN-7781`, writes `out.txt` with the Write tool and replies OK; the manager then reports the answer and `NOTE=<token>`). Five graders: `tool_used` Agent, `file_exists` out.txt, `regex` for the worker's echo, `regex` for the hook token, `regex` for the Write entry's `"file_path"…out.txt…"content"` order.
- Command: `claude plugin eval <plugin> --runs 3 --ablation none --allow-tools Bash Write Edit --trust-plugin --no-publish --keep-temp --max-cost-usd 3 --json p18c.json` → exit 1 (score below threshold), 35 s, $0.31; kept traces under `/tmp/claude-eval-*/out/trace.jsonl` (open with `chmod 700 <dir> <dir>/sealed`).
- Results, identical in all three runs: `tool_used` Agent PASS ("Agent called 1x"); `file_exists` out.txt PASS (the worker's Write ran in the sandbox); the main agent's last line was `OK NOTE=5561`, so the hook note reached the manager. The three `regex` graders FAILED with "pattern not found in last_message": a `regex` grader's default `target` is `last_message`; the repository's own graders say `target: trace`, which this probe omitted.
- Read from the kept trace: the worker (`probe:worker`, listed among the session's agents) appears as `system/task_started`, `task_progress` (with `subagent_type` and `last_tool_name`) and `task_notification` entries; the worker's own tool calls appear as ordinary `assistant` `tool_use` entries (`Bash` `echo WORKER-RAN-7781`, `ToolSearch`, `Write {"file_path": ".../out.txt", "content": "DONE"}`) with their `user` `tool_result` entries; the subagent's prompt is in the trace; the token `PROBE-NOTE-EVAL-5561` and the string `additionalContext` appear NOWHERE in the trace. Also seen: the sandbox prints `.bashrc: Permission denied` on every Bash call (harmless).
- Verdict per item: worker spawn inside the eval runner PASS; worker Bash and Write in the sandbox PASS; worker's tool calls in the trace PASS (so `tool_order` graders can key on the worker's calls and on the manager's Agent calls, and `regex` graders with `target: trace` can match the worker's tool inputs); hook notes in the trace FAIL → plan §7 rule 4 applies: the stage-order grader becomes `tool_order` on the manager's Agent calls, applied to brief §13 and plan §6/§8 before the brief is placed; the report grader's assumption PASS (`"file_path"` precedes `"content"` in the Write entry). Rule 3 does not apply.

## P19 (v3 step 9): is a hook-set foreground spawn still honoured on Claude Code 2.1.302, headless and interactive? 2026-10-16
- Scratchpad plugin `probe-fg2/` (as P16, plus a Stop hook that logs; the rewritten prompt makes the subagent `sleep 20` then reply PROBEOK). Prompt: spawn `probe:probe` with `run_in_background` true, then reply DONE.
- Headless (`claude -p`, 2.1.302): PreToolUse Agent (the model asked for background) 0.0 s → SubagentStop 23.8 s → PostToolUse(Agent) `status: completed` 23.9 s → Stop 25.1 s. The hook's `run_in_background: False` held the manager's turn: P16 still true headless.
- Interactive (tmux, 2.1.302, same plugin): PreToolUse Agent 0.0 s → PostToolUse(Agent) at 0.1 s with `{'isAsync': True, 'status': 'async_launched', 'agentId': …}` → **Stop at 0.9 s** → SubagentStop at 2.4 s. The screen showed "Backgrounded agent" and "Waiting for 1 background agent to finish". The hook's `run_in_background: False` was NOT honoured: in an interactive session the Agent call returns at once as an async launch, and the main agent's turn ends (Stop fires) while the subagent runs. The subagent's result then reaches the main agent as a background-task notification.
- Consequence for v3: the brief's handoff design (option B: every spawn in the foreground, its answer the tool result) holds for headless runs and the evals, not for an attended interactive session. Seen in the step-9 real run: the Stop hook blocked the manager five times in `judge` with "next: spawn rehearse:director" while the director was already running; the manager escaped with a wait loop on `rehearse job`.

## P20 (v3 step 9): does a background subagent's completion wake the main agent interactively? 2026-10-16
- Same plugin as P19, interactive (tmux, 2.1.302). Prompt: spawn in the background, reply DONE at once, and "if you are later told that the subagent finished, reply WOKE plus its word".
- Hook events: PreToolUse Agent 0.0 s → PostToolUse(Agent) `async_launched` 0.1 s → Stop 0.9 s (the main agent's turn ended after "DONE") → a stray SubagentStop at 2.0 s with `agent_type: ""`, another agent id and no message (an internal helper; ignore it) → SubagentStop 23.9 s with the probe's `agent_type`, the `agentId` from the launch result, `last_assistant_message: PROBEOK` → Stop 24.8 s. The main transcript shows a `<task-notification>` user entry one second after the subagent stopped, then the assistant's `WOKE PROBEOK`, with nothing typed; the screen showed "Agent … finished · 23s" then the reply.
- Fact: a background subagent's completion wakes the main agent by itself in an interactive session; the hook sees the real stop with the launch's agent id; the notification text is Claude Code's own (hooks cannot annotate it), so the manager must read `rehearse job` after it.
