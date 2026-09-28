# rehearse

**Make coding agents be the program before they write it.**

Ask an agent for a scraper and it usually writes `scrape.py`, runs it and hopes. Then it breaks on a 403, a JavaScript-rendered page, or a missing field on page 7.

`rehearse` flips the order. The agent first **does the program's job itself, by hand**: one `curl`, one browser click, one `sqlite3` query at a time. It logs what really happens, and only then builds the program from the steps that actually worked. And before building anything, it checks whether someone already built it. The responses it recorded become the program's tests.

```
1 Model → 2 Scout → 3 Plan + label → 4 Rehearse (by hand) → 5 Revise plan → 6 Build → 7 Replay → 8 Report
```

## How it works

- **Scout before building.** A ladder: does a tool already do the whole job (`yt-dlp`, `pandoc`, `rclone`)? Does an official API or feed replace the hard part? Does a maintained library do the step? Only then write code. Candidates are checked (alive, used, fits, weight, real name) and then rehearsed on the real target, because a tool found is still an assumption.
- **Surfaces, not program types.** Any program is a mix of eight surfaces: web, CLI, files, GUI, database, time, external services, hardware. Each has a playbook ([surfaces.md](skills/rehearse/references/surfaces.md)), so one skill covers thousands of programs.
- **Plan labels.** Each plan step's hidden assumption is labeled 🟢 rehearse, 🟡 sandbox, 🔴 simulate/ask, ⚪ pure logic, or ❓ blocked. Irreversible actions (sending, paying, deleting, posting) never run without the user's OK.
- **A flow grid** of happy path, input variations, dependency failures, state and user mistakes, ranked by likelihood × damage.
- **Rehearsal rules.** One direct action per call, observe before acting, use the same tool the program will use, sample instead of looping, save evidence, never fake a result.
- **Replay.** Recorded responses become fixture tests, and the finished program is run live on the same sample and compared with the hand results.

Full details are in [SKILL.md](skills/rehearse/SKILL.md).

## Two hooks (Claude Code)

| Hook | Why |
|---|---|
| `UserPromptSubmit` | **Auto-loads the skill.** When a prompt asks to build something that touches the outside world, the agent is told to rehearse first. In testing, the skill description alone did not reliably trigger among ~185 installed skills; with this hook it did. |
| `PreToolUse` | **Guard.** While `.rehearsal/active` exists, it blocks scripts, loops, inline code (`python -c`), background jobs and writes to code files. The agent has to interact directly. |

Both are in [`hooks/guard.py`](hooks/guard.py), which needs only the Python 3 standard library.

## Install

**Claude Code** (skill + both hooks):

```
/plugin marketplace add GITHUB_USER/rehearse
/plugin install rehearse@rehearse
```

**Other agents** (Codex, Gemini CLI, Cursor, Copilot and others that support the [Agent Skills](https://agentskills.io) standard): copy `skills/rehearse/` into your agent's skills folder. The skill works as-is. Auto-loading depends on the description match, and there is no guard unless you wire one up.

**Guard on other agents (experimental, untested):** `hooks/guard.py` reads a pre-tool-use payload as JSON on stdin and exits `2` to block. It also recognizes `shell`/`exec_command`/`run_shell_command` and `write_file`/`replace`/`apply_patch` tool names, so you can point your agent's pre-tool hook at it.

## Test

```
python3 tests/test_guard.py
```

## Limits

- The guard is a speed bump, not a sandbox. An agent can still `rm .rehearsal/active` early. The rehearsal log, with the exact command for every step, is the audit trail.
- Keyword auto-loading can misfire. Say "skip rehearsal" to opt out for a prompt.
- Anything that fails only over time (scheduled runs over days, site changes) is reported as an unverified risk. It is not tested.

## License

MIT
