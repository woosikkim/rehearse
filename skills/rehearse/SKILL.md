---
name: rehearse
description: Use BEFORE writing code for any program that touches the outside world - scraper, crawler, bot, API client, CLI tool, file converter, automation, integration, sync job, data pipeline - even small or "quick" ones. Do not write a script and run it to see what happens. First do the program's job yourself by hand with direct tool calls (curl, browser tools, CLI commands, sqlite3), one step at a time, and log what really happens. Then build from the verified steps and replay the recorded evidence as tests.
---

# Rehearse

**Be the program before you write it.** Every plan hides assumptions about the outside world: "the page is static HTML", "the API returns JSON", "the CSV is UTF-8". Programs break on those assumptions. You check each one by doing the program's job yourself, by hand, before any code exists.

## When to skip

- Pure logic with no outside world (an algorithm, a refactor, styling): write normal tests instead.
- The user explicitly says to skip rehearsal.

## The loop

```
1 Model → 2 Plan + label → 3 Rehearse (by hand) → 4 Revise plan → 5 Build → 6 Replay → 7 Report
```

Do not write program code before phase 5. Rehearsal can change the plan, so the plan only becomes final after rehearsal.

---

## 1. Model the program

Before planning, write this down (in `.rehearsal/REHEARSAL.md`, template below):

- **Actors**: who or what uses it (a human at a CLI, cron, a webhook caller)
- **Entry points**: how it starts (command and args, URL, schedule, event)
- **Inputs / outputs**: what goes in, what comes out, and in which format
- **Surfaces**: everything it touches outside its own memory. Choose from: web/HTTP, CLI/stdin, files, GUI/browser, database/state, time, external services, hardware/OS. Read the matching sections of [references/surfaces.md](references/surfaces.md) for each surface the program uses.
- **State**: what it remembers between runs

## 2. Plan and label

Write the plan as **concrete steps**. Each step names its tool, endpoint, file or command. A vague step ("get the data") hides its assumptions, so rewrite it until it names a source.

For each step, write down its hidden assumption(s) and give it a label:

| Label | Meaning | What you do in phase 3 |
|---|---|---|
| 🟢 Rehearse | Read-only and safe | Do it for real |
| 🟡 Sandbox | Writes, but reversible | Do it in a temp dir, test DB or test account |
| 🔴 Simulate / ask | Irreversible or external (sends, pays, deletes, posts publicly) | Never run it without the user's explicit OK. Verify everything up to the side effect, then ask or simulate |
| ⚪ Skip | Pure logic, no outside world | Unit test it in phase 6 |
| ❓ Blocked | Needs an earlier step's result, a credential, or a missing tool | Rehearse it later, or ask the user |

### Flow grid

The happy path is not enough. For each surface the program uses, go through these categories and write down the flows that apply:

| Category | Examples |
|---|---|
| Happy path | The main job works end to end |
| Input variations | Each kind of input; empty, huge, unicode, wrong format |
| Dependency failure | Down, slow, changed layout or schema, rate-limited, auth expired |
| State | First run, second run, interrupted halfway and resumed, two copies running at once |
| User mistakes | Wrong args, missing config, cancel midway |

Rank the flows by **how likely × how bad if it breaks**, and rehearse from the top down.

## 3. Rehearse, by hand

Start the rehearsal. This turns on the guard hook, if one is installed:

```
mkdir -p .rehearsal/fixtures && touch .rehearsal/active
```

First check which tools exist (`command -v curl wget jq sqlite3 ...`, plus any browser or MCP tools you have).

### Rules

1. **One action per call. No scripts.** Every step is a single direct command or tool call. Do not write and run a file, do not write loops, and do not run inline code (`python -c`, `node -e`). A script bakes in the very assumptions you are trying to check.
2. **Observe before you act.** After each step, write down what you saw, then choose the next step based on that. "Got 403 → retry with a browser User-Agent" is a decision *you* make by looking, and it later becomes code.
3. **Match the program's tool.** Rehearse with the tool closest to what the program will use. If the program will use `requests` or `fetch`, rehearse with `curl` and the same headers, method and cookies, not with a fetch tool that renders or proxies the page. If the program drives a browser, rehearse with a browser tool.
4. **Sample, don't loop.** For 1000 items, rehearse a few by hand: the first, one from the middle, the last, one that looks odd, and one that doesn't exist. Each is its own call. Looping is the program's job.
5. **Leave evidence.** Log every step right away: command → raw output excerpt → what it means. Save raw responses as fixtures (`curl -s URL -o .rehearsal/fixtures/item1.html`). Saving output is fine; processing it with code is not.
6. **Never fake a result.** If you are blocked (captcha, login, missing tool, a 🔴 step), stop and ask the user. A workaround you find is a finding: log it. If it changes the design (a new tool, a new dependency, a login requirement), mark it as a plan change.

| ✅ Allowed | ❌ Not allowed |
|---|---|
| `curl -sI https://site.com/item/1` | writing `test.py` and running it |
| `curl -s URL \| head -50` (pipes only to *view*) | `for i in 1 2 3; do curl ...; done` |
| `curl -s URL -o .rehearsal/fixtures/p1.html` | `python -c "..."`, `node -e "..."` |
| `jq '.items[0]' .rehearsal/fixtures/p1.json` | background jobs (`&`, `nohup`) and waiting |
| `grep -o 'class="price"[^<]*' fixture.html` | `sleep` loops polling for a result |
| browser tool: navigate, click, read | any code that makes decisions for you |

**You are done rehearsing** when every ranked flow has a status: rehearsed, sandboxed, simulated, or skipped with a reason. Then end the rehearsal:

```
rm .rehearsal/active
```

## 4. Revise the plan

Go through the findings. Every surprise becomes a plan change, and every failure you saw becomes error handling. If rehearsal showed the plan was wrong (for example, the page is rendered by JavaScript, so plain HTTP won't work), rewrite those steps now.

## 5. Build

- Each external call in the code does what a rehearsed step did: same endpoint, same headers, same parameters that actually worked.
- Each failure in the log has handling in the code.
- Copy the fixtures into the project's test folder (e.g. `tests/fixtures/`).
- Do not add behavior that was never rehearsed without listing it as an unverified risk.

## 6. Replay

1. **Fixture tests.** Saved input → the output you extracted by hand = expected result. Saved failure responses → tests that the program handles them.
2. **Unit tests** for the ⚪ logic steps.
3. **Live replay.** Run the program once on the same sample you rehearsed, and compare its output with your hand results.
4. If they differ, fix the code, not the expectation. Change the expectation only if your rehearsal log was wrong, and say so.

## 7. Report

Tell the user plainly:

- **Verified for real**: the flows rehearsed live and replayed
- **Sandboxed / simulated**: what was not done for real, and why
- **Unverified risks**: things only time will show (scheduled runs over days, layout changes, memory growth), plus anything skipped

---

## Log template: `.rehearsal/REHEARSAL.md`

```markdown
# Rehearsal: <program>

## Model
- Actors:
- Entry points:
- Inputs → outputs:
- Surfaces:
- State:

## Plan
| # | Step | Assumption | Label | Status |
|---|------|------------|-------|--------|
| 1 | Fetch product page with curl (as requests) | Static HTML, no bot block | 🟢 | ✅ / ❌ / changed |

## Flows
| Flow | Category | Rank | Result | Evidence |
|------|----------|------|--------|----------|
| Normal product page | happy | 1 | ✅ price "$1,299.00" | S2, fixtures/item1.html |

## Steps
### S1: <what you tried>
- cmd: `curl -sI https://...`
- saw: `HTTP/2 403`
- means: blocks default UA
- next: retry with a browser UA

## Plan changes
- S1 → program must send a browser User-Agent

## Unverified risks
- 
```

## Without a guard hook

Some agents have no hook support. The rules still apply. The log, with the exact command for every step, is the audit trail: a reviewer can check that each step was a direct call and not a script.
