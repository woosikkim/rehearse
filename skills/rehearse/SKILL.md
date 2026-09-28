---
name: rehearse
description: Use BEFORE writing code for any program that touches the outside world - scraper, crawler, bot, API client, CLI tool, file converter, automation, integration, sync job, data pipeline - even small or "quick" ones. Do not write a script and run it to see what happens. First do the program's job yourself by hand with direct tool calls (curl, browser tools, CLI commands, sqlite3), one step at a time, and log what really happens. Also scouts for existing tools, APIs and libraries that already do the job, so less gets built. Then build from the verified steps and replay the recorded evidence as tests.
---

# Rehearse

**Be the program before you write it.** Every plan hides assumptions about the outside world: "the page is static HTML", "the API returns JSON", "the CSV is UTF-8". Programs break on those assumptions. You check each one by doing the program's job yourself, by hand, before any code exists. And you only build what nobody has built already.

## When to skip

- Pure logic with no outside world (an algorithm, a refactor, styling): write normal tests instead.
- The user explicitly says to skip rehearsal.

## The loop

```
1 Model → 2 Scout → 3 Plan + label → 4 Rehearse (by hand) → 5 Revise plan → 6 Build → 7 Replay → 8 Report
```

Do not write program code before phase 6. Rehearsal can change the plan, so the plan only becomes final after rehearsal.

---

## 1. Model the program

Before planning, write this down (in `.rehearsal/REHEARSAL.md`, template below):

- **Actors**: who or what uses it (a human at a CLI, cron, a webhook caller)
- **Entry points**: how it starts (command and args, URL, schedule, event)
- **Inputs / outputs**: what goes in, what comes out, and in which format
- **Surfaces**: everything it touches outside its own memory. Choose from: web/HTTP, CLI/stdin, files, GUI/browser, database/state, time, external services, hardware/OS. Read the matching sections of [references/surfaces.md](references/surfaces.md) for each surface the program uses.
- **State**: what it remembers between runs
- **Needs**: the jobs inside the program (fetch pages, extract text, store rows, send alerts...)

## 2. Scout: what already exists?

Smart people have already built most of what programs need. Before planning to write anything, look for it. Go down this ladder for the whole program first, then for each need that is left. Stop at the first rung that holds:

1. **The whole job already exists.** A CLI tool, app or service already does it (downloading media → `yt-dlp`, converting documents → `pandoc`, syncing files → `rclone`). Then the "program" may be one command, a config file or a cron line.
2. **An official source replaces the hard part.** An API, RSS feed, sitemap, data export or bulk download instead of scraping; a webhook instead of polling.
3. **A maintained library does the step.** For example text extraction, retries, CSV dialects, date parsing.
4. **Only then write it yourself.**

**Search in this order:**
- What's already installed (`command -v ...`, `pip list`, `npm ls`, the project's dependency files). A tool already in the project beats a better one that isn't.
- For web targets, the target itself: `/api`, `/feed`, `/sitemap.xml`, `robots.txt`, developer docs, and the network requests its own pages make.
- Then outside: web search, package registries (`pip index versions <name>`, `npm view <name>`), GitHub (`curl -s "https://api.github.com/search/repositories?q=<topic>&sort=stars"`), `awesome-<topic>` lists. [references/surfaces.md](references/surfaces.md) lists good places to start for each surface.

**Judge each candidate:**

| Check | Good sign |
|---|---|
| Alive | A release or commit in the last ~12 months; issues get answered |
| Used | Real adoption: stars, downloads, dependents |
| Fits | Works in this language, OS and environment; its license allows this use |
| Weight | Dependencies in proportion to the job; no framework pulled in for one function |
| Real | The exact official name and repo; watch for typosquats and look-alike packages |

Keep 2–3 candidates per need at most, and don't spend longer scouting than building would take.

**A candidate is an assumption too.** Finding a tool doesn't prove it works on *your* target. Each chosen candidate becomes a plan step with its own assumption ("`yt-dlp` can read this site") and is rehearsed like any other step:
- **CLI tools**: rehearse them directly, by hand, in phase 4 (`yt-dlp --dump-json URL`, `pandoc in.docx -t markdown | head`).
- **Libraries** can't run without code. Save the real inputs as fixtures during rehearsal, and check the library against them in phase 7. If it fails there, fall back to the next candidate or the next rung.
- **Installing** is 🟡: install into the project (venv, local `node_modules`), not globally, unless the user agrees.

If the user wants it built from scratch (to learn, or to avoid a dependency), do that, and mention the alternative in the report.

## 3. Plan and label

Write the plan as **concrete steps**, using the tools you chose while scouting. Each step names its tool, endpoint, file or command. A vague step ("get the data") hides its assumptions, so rewrite it until it names a source.

For each step, write down its hidden assumption(s) and give it a label:

| Label | Meaning | What you do in phase 4 |
|---|---|---|
| 🟢 Rehearse | Read-only and safe | Do it for real |
| 🟡 Sandbox | Writes, but reversible | Do it in a temp dir, test DB or test account |
| 🔴 Simulate / ask | Irreversible or external (sends, pays, deletes, posts publicly) | Never run it without the user's explicit OK. Verify everything up to the side effect, then ask or simulate |
| ⚪ Skip | Pure logic, no outside world | Unit test it in phase 7 |
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

## 4. Rehearse, by hand

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

## 5. Revise the plan

Go through the findings. Every surprise becomes a plan change, and every failure you saw becomes error handling. If rehearsal showed the plan was wrong (for example, the page is rendered by JavaScript, so plain HTTP won't work), rewrite those steps now.

## 6. Build

- Use the tools and libraries you chose while scouting. Write only the glue between them and the parts nothing else covers.
- Each external call in the code does what a rehearsed step did: same endpoint, same headers, same parameters that actually worked.
- Each failure in the log has handling in the code.
- Copy the fixtures into the project's test folder (e.g. `tests/fixtures/`).
- Do not add behavior that was never rehearsed without listing it as an unverified risk.

## 7. Replay

1. **Fixture tests.** Saved input → the output you extracted by hand = expected result. Saved failure responses → tests that the program handles them.
2. **Unit tests** for the ⚪ logic steps.
3. **Library checks.** Each library chosen while scouting must pass on the real fixtures. If one fails, switch to the next candidate.
4. **Live replay.** Run the program once on the same sample you rehearsed, and compare its output with your hand results.
5. If they differ, fix the code, not the expectation. Change the expectation only if your rehearsal log was wrong, and say so.

## 8. Report

Tell the user plainly:

- **Reused vs built**: which existing tools and libraries do the work, and what was written by hand and why
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
- Needs:

## Scout
| Need | Rung | Candidate | Checks (alive/used/fits/weight/real) | Verdict |
|------|------|-----------|--------------------------------------|---------|
| Fetch page | 2 | site has /api/products JSON | docs + S1 | ✅ use API, no scraping |

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
