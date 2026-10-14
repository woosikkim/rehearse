# rehearse

**Make coding agents be the program before they write it.**

Ask an agent for a scraper and it usually writes `scrape.py`, runs it and hopes. Then it breaks on a 403, a JavaScript-rendered page, or a missing field on page 7.

`rehearse` flips the order. The agent first **does the program's job itself, by hand**: one `curl`, one browser click, one `sqlite3` query at a time. It logs what really happens, and only then builds the program from the steps that actually worked. And before building anything, it checks whether someone already built it. The responses it recorded become the program's tests.

```
Look (by hand) → Act as it (by hand) → Build (transcribe) → Replay (hand results are the tests)
```

The same loop covers a new program and a change to existing code. For a bug, the agent *becomes the broken file*: it feeds the real input to the real neighbours one call at a time, finds where things go wrong, then acts as the fixed file by hand before any code is written.

## How it works

- **It sizes itself.** Four questions (outside world? fast failing test? one place or a chain? slow feedback or big codebase?) pick a size: skip, light, full, or helpers. The agent announces one line, `Rehearse: <size>, because <reason>. Say light, skip or full to override.`, and goes on. The word **rehearse** in a prompt always loads the skill.
- **Look first, in both directions.** Existing code: reproduce once, locate, pick the file to become. New program: scout for a tool that already does the job, then poke the real target by hand.
- **Act as the fix.** The agent produces by hand what the fixed component should output and feeds it to the real neighbours. Those hand outputs become the expected values in the tests.
- **Chains are tracked.** A neighbour that breaks on corrected data is a chain link, logged with *Revealed by: <the fix>*. More than three links means undo and re-diagnose.
- **Helpers that can only look.** For slow feedback or a chain, the session sends a `rehearse:rehearser` agent that has no write tools. It brings back a log path and a fixture list; the session edits only when the log shows the hand-made chain working, then replays.

- **Scout before building.** A ladder: does a tool already do the whole job (`yt-dlp`, `pandoc`, `rclone`)? Does an official API or feed replace the hard part? Does a maintained library do the step? Only then write code. Candidates are checked (alive, used, fits, weight, real name) and then rehearsed on the real target, because a tool found is still an assumption.
- **Surfaces, not program types.** Any program is a mix of eight surfaces: web, CLI, files, GUI, database, time, external services, hardware. Each has a playbook ([surfaces.md](skills/rehearse/references/surfaces.md)), so one skill covers thousands of programs.
- **Plan labels.** Each plan step's hidden assumption is labeled 🟢 rehearse, 🟡 sandbox, 🔴 simulate/ask, ⚪ pure logic, or ❓ blocked. Irreversible actions (sending, paying, deleting, posting) never run without the user's OK.
- **A flow grid** of happy path, input variations, dependency failures, state and user mistakes, ranked by likelihood × damage.
- **Rehearsal rules.** One direct action per call, observe before acting, use the same tool the program will use, sample instead of looping, save evidence, never fake a result.
- **Replay.** Recorded responses become fixture tests, and the finished program is run live on the same sample and compared with the hand results.

Full details are in [SKILL.md](skills/rehearse/SKILL.md).

## Four hooks (Claude Code)

| Hook | Why |
|---|---|
| `SessionStart` | **One standing rule.** Adds one sentence at startup, resume and after compaction: before building or fixing anything that depends on something outside the code, load the rehearse skill and let it size the job. No keyword list. |
| `UserPromptSubmit` | **Force word.** A prompt containing the word `rehearse` always loads the skill. |
| `PreToolUse` | **Guard.** While `.rehearsal/active` exists: anything that existed before the marker may run; anything written since may not. One-line calls to existing code (`python3 -c '…'`, `node -e`, `node -p`, `ruby -e`, single quotes) are allowed when they contain no logic or file access. Loops, background jobs, new scripts, shell writes to code files, in-place editors and command substitution inside double quotes are blocked, each with a message naming the alternative. Once the marker is gone, code edits stay blocked until the guard's own log holds one call that ran something (a one-liner, `curl`, a query, an existing script or test); reading files and writing notes do not count, and the log cannot be written by hand. |
| `PostToolUse` / `PostToolUseFailure` | **Automatic evidence.** Every shell command and the first lines of its output are appended to `.rehearsal/log.md`, with common secrets redacted. |

All four run [`hooks/guard.py`](hooks/guard.py), which needs only the Python 3 standard library. The plugin also ships one agent, [`agents/rehearser.md`](agents/rehearser.md).

## Install

**Claude Code** (skill, four hooks and the `rehearser` agent):

```
/plugin marketplace add woosikkim/rehearse
/plugin install rehearse@rehearse
```

**Other agents** (Codex, Gemini CLI, Cursor, Copilot and others that support the [Agent Skills](https://agentskills.io) standard): copy `skills/rehearse/` into your agent's skills folder. The skill works as-is. Auto-loading depends on the description match, and there is no guard unless you wire one up.

**Guard on other agents (experimental, untested):** `hooks/guard.py` reads a pre-tool-use payload as JSON on stdin and exits `2` to block. It also recognizes `shell`/`exec_command`/`run_shell_command` and `write_file`/`replace`/`apply_patch` tool names, so you can point your agent's pre-tool hook at it.

## Test

```
python3 tests/test_guard.py
```

## Limits

- The guard is a speed bump, not a sandbox. An agent can `rm .rehearsal/active` early, but cannot edit code until its log shows one real call; the only other exit is deleting `.rehearsal/` entirely, which leaves no log at all. A meaningless call (`python3 -c 'print(1)'`) satisfies the gate; it also sits in the log for the reader to see.
- The guard's rules are frozen as of 0.3.0. Known ways around it are listed here, not patched, until a git-tracked "existing" check lands: backdating a file with `touch -d`; logic hidden in `awk` or `jq` programs; editing an extension-less file such as a `Makefile` or `justfile` and running `make` or `just`; `io.FileIO("a.py", "w")` creating an empty code file; standard-library runners that execute code or files handed to them as arguments (`python3 -m timeit -s 'import os' 'os.system("…")'`, `python3 -m pdb notes.txt`, `python3 -m trace --count notes.txt`); wrappers the guard does not know (`nice -n 5 python3 new.py`, `time -p …`, `env -S …`, `stdbuf`, `setsid`, `pypy3`); a program name taken from a variable or substitution (`P=python3; $P x.txt`, `$(which python3) x.txt`); `find . -exec python3 x.txt \;`; `ruby -e 'load "x.txt"'` and `require_relative`; `node -e 'import("./x.js")'`; attribute lookups that spell a blocked name in pieces (`__dict__["__built" + "ins__"]`); starting the marker with a substitution hidden in the same call (`touch .rehearsal/active $(python3 new.py)`) or creating it without `touch` (`: > .rehearsal/active`), which skips the start-on-its-own rule. A bypass that shows up unprompted in a real rehearsal log (ordinary habit, not evasion) is patched.
- Known false blocks, each with a message naming the accepted alternative: unquoted heredocs with shell-like prose; double-quoted one-liners; one-liners with extra flags (an interpreter given by full path or after `PATH=` is accepted); an interpreter flag before a file (`python3 -O old.py`); `php -r`; data strings inside a one-liner containing an access word as a whole word (`"open late"`, `"File not found"`); single-quoted text containing `"$(`; an unquoted `$(…)` after a closing `"` on the same line; `sort -u` arguments over-redacted in the logged command.
- The auto-log redacts common secret patterns (`Authorization`, `Cookie`, bearer tokens, `token=`/`password=`, `curl -u`, URL credentials) but is not a secrets filter.
- Sizing can misjudge. Say `light`, `skip` or `full` to override.
- Anything that fails only over time (scheduled runs over days, site changes) is reported as an unverified risk. It is not tested.

## License

MIT
