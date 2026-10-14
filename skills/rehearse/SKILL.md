---
name: rehearse
description: Use BEFORE writing or changing code that depends on something outside the code - a site, an API, a file, a database, a device, a service, or another part of the same program. Covers new programs (scraper, bot, API client, command-line tool, file converter, sync job, data pipeline) and fixes or changes to existing code, in any language, even small or "quick" ones. Do not write code and run it to see what happens. Say the size first (skip only when there is nothing to run), then do it by hand one call at a time, act as the fixed file or the whole program, log what really happens, and scout for existing tools so less gets built. Then build from the verified steps and replay them as tests. The word "rehearse" in a prompt always means load this skill.
---

# Rehearse

**Be the program before you write it.** Every plan and every fix hides assumptions about things outside the code: "the page is static HTML", "every date looks like 2024-03-04", "the next file can handle what this one sends". Programs break on those assumptions. You check each one by doing the job yourself, by hand, before any code is written or changed. And you only build what nobody has built already.

## Size it first

One question decides it: **is there anything to run before the change?** A test, a command, a call, a page, a query, another file's function. If yes, the size is full. If there is truly nothing to run (a rename, styling, a comment, a type annotation), the size is skip. A reported bug or a change in behaviour always has something to run, so it is never skip.

| Size | When | What you do |
|---|---|---|
| skip | Nothing to run: a rename, styling, docs, a type annotation | Write normal tests |
| full | Everything else, including bugs that look like one line | The whole loop below, with a log |
| helpers | Full, and Look shows a long chain, slow feedback or a big codebase | The whole loop, with helpers doing the looking. Decided after Look, never up front |

**Your first line of output is the size**, in exactly this shape, even when the size is skip. Then carry on without waiting. If the user later says skip or full, switch to that size.

```
Rehearse: <size>, because <reason>. Say skip or full to override.
```

**There is no light size.** A bug that looks like one line still gets the whole loop: marker, reproduce by hand, log, fix, replay. The cost is a few extra calls. What it buys is a fix that answers what you saw run, not what you read: reading alone finds a plausible cause, and a plausible cause is often the neighbouring bug. A step runs something and records what came back: a `python3 -c` call, a `curl`, a query. Reading a file is Look, not a step. The guard enforces this: code edits open only once `.rehearsal/log.md`, which the guard writes, holds a call that ran while the marker was up. Start the marker before your first probe; you cannot judge code you have not run.

## The loop

```
Look → Act as it → Build → Replay
```

It is the same loop whether you fix something that exists or make something new. Only the first step differs. A failure on replay starts the loop again (see Chains). Do not write or change program code before Build: acting as it can change the plan, so the plan is only final after it.

| | Fixing something that exists | Making something new |
|---|---|---|
| Step 1: Look | Reproduce once, locate, pick the component to become | Scout for what exists, model the program, poke the real target |
| Act as it | Be file 3 with its real rows; then be the fixed file 3 and hand its rows to files 4 and 5 | Be the scraper on three items: fetch each page, find the name and price, write the CSV row by hand |
| Build | Change only what the hand-made fix showed | Transcribe the steps that worked |
| Replay | Saved rows are the inputs; the hand outputs are the expected values | Saved pages are the inputs; the hand-written rows are the expected CSV |
| Chains | The fixed rows make file 4 crash on "12,50": revealed by the date fix | The hand-written rows break the CSV writer on a name with a comma: revealed by the extract step |
| Size | Full, even when a test already fails in seconds; helpers when Look shows a long chain | Full, even for one call to a known API; helpers for a big site with many surfaces |
| Helpers | A helper becomes file 3; the session edits only after the log shows it working | A helper pokes the site and saves pages; the session builds from the log |

## Look

Start the rehearsal, for every size except skip. Run this as its own call, before anything else. The guard checks each call only once the marker exists.

```
mkdir -p .rehearsal/fixtures && touch .rehearsal/active
```

**Fixing something that exists.**
1. **Reproduce once.** Run what shows the problem one time and save the result as a fixture (a fixture is a saved real input or output): `python3 main.py > .rehearsal/fixtures/before.txt`.
2. **Locate.** Follow the stack trace, the logs, or a search (`grep -n "def parse_date" *.py`) to where it goes wrong, and read the code there.
3. **Pick the component to become**: the one where good input turns into wrong output. In the five-files story it is file 3, which drops three March rows because their dates are written `04/03/2024`.

**Making something new.** *Scout first.* Most of what programs need already exists. Go down this ladder for the whole job, then for each need left, and stop at the first rung that holds:

1. **The whole job exists**: a command-line tool, app or service (`yt-dlp`, `pandoc`, `rclone`). The "program" may be one command or a cron line.
2. **An official source replaces the hard part**: an API, feed, sitemap, data export or webhook instead of scraping or polling.
3. **A maintained library does the step**: text extraction, retries, CSV dialects, dates.
4. **Only then write it yourself.**

Search what is installed first (`command -v`, `pip list`, `npm ls`, the project's dependency files), then the target itself (`/api`, `/feed`, `/sitemap.xml`, `robots.txt`), then outside (package registries, GitHub, `awesome-<topic>` lists). Keep 2–3 candidates per need and judge each:

| Alive | Used | Fits | Weight | Real |
|---|---|---|---|---|
| A release or commit in ~12 months | Stars, downloads, dependents | Language, OS, license | Dependencies in proportion to the job | The exact official name, no look-alikes |

A candidate is an assumption too. Rehearse command-line tools by hand; save fixtures to check libraries against in Replay. Install into the project, not globally (🟡). If the user wants it from scratch, do that and mention the alternative in the report.

*Then model it* in the log: actors (who or what uses it), entry points (command, URL, schedule), inputs → outputs, surfaces (web/HTTP, command line, files, browser, database, time, external services, hardware; read the matching sections of [references/surfaces.md](references/surfaces.md)), state between runs, and needs (the jobs inside it). Write the plan as concrete steps that each name a tool, endpoint, file or command, with its hidden assumption and a label.

## Rules of the hand

1. **One action per call, no new logic.** Each step is one direct command or tool call: no script files, loops, conditions or new functions. To call code that already exists, use one console line `python3 -c '<import what exists; set literals; call; print>'`:
   ```
   python3 -c 'import normalize; print(normalize.parse_date("04/03/2024"))'
   python3 -c 'import sys, price; print(price.to_amount(sys.stdin.read()))' < .rehearsal/fixtures/price3.txt
   ```
   The same shape works with `node -e`, `node -p` and `ruby -e`, and the interpreter may be a full path (`/opt/env/bin/python -c '…'`) or follow `PATH=…` when the project lives in a virtualenv or conda env. If the bare interpreter lacks the project's dependencies, find the one that has them first (`.venv/bin/python`, `ls /opt/*/envs`, `conda env list`) and use it by full path for every call, including the tests. Single quotes only, straight-line statements (up to eight: imports, literal values, calls, print; no `for`, `if`, `def`, `with`), and a fixture fed in with `< file`. A setup that needs more than that is a sign to save a fixture and call the next layer down.
2. **Hand-made data are literals.** Type the value you mean, `"12.50"`, not code that computes it: no comprehensions, no `.replace`. Save code-like fixtures as `.txt` (`app.js.txt`).
3. **Observe before you act.** Write down what you saw, then choose the next step from that. "Got 403 → retry with a browser User-Agent" is your decision, and later it becomes code.
4. **Match the program's tool.** If the program will use `requests` or `fetch`, rehearse with `curl` and the same headers, not a tool that renders the page. If it drives a browser, use a browser tool.
5. **Sample, don't loop.** For 1000 items, try the first, one from the middle, the last, an odd one and one that doesn't exist, each as its own call.
6. **Leave evidence.** Log each step right away with a quoted heredoc, and save raw responses as fixtures (`curl -s URL -o .rehearsal/fixtures/item1.html`):
   ```
   cat >> .rehearsal/REHEARSAL.md <<'EOF'
   ### S2: be file 3 with a real March row
   EOF
   ```
7. **Never fake a result.** Blocked by a captcha, a login, a missing tool or a 🔴 step? Stop and ask the user. A workaround you find is a finding: log it.

| Label | Meaning | What you do |
|---|---|---|
| 🟢 Rehearse | Read-only and safe | Do it for real |
| 🟡 Sandbox | Writes, but reversible | Do it in a temp dir, test database or test account |
| 🔴 Simulate / ask | Irreversible or external (sends, pays, deletes, posts publicly) | Never run it without the user's explicit OK. Verify everything up to the side effect, then ask or simulate |
| ⚪ Skip | Pure logic, no outside world | Unit test it in Replay |
| ❓ Blocked | Needs an earlier result, a credential, or a missing tool | Rehearse it later, or ask the user |

**The happy path is not enough.** For each surface, list the flows that apply: happy path; input variations (empty, huge, unicode, wrong format); dependency failure (down, slow, changed layout, rate-limited, auth expired); state (first run, second run, interrupted, two copies at once); user mistakes (wrong args, missing config). Rank them by how likely × how bad, and rehearse from the top. You are done when every ranked flow has a status: rehearsed, sandboxed, simulated, or skipped with a reason.

**For a fix, the variations are the other shapes the same input can take.** The ticket's example is one shape. Before you call the cause found, type the same thing two or three more ways: the optional or nested form, the empty one, the one written at a different level. A variation you can name, you rehearse: if your report would say "untested" or "not covered" about something you could call in one line, go back and call it. "Not covered" is only for what needs a credential, a missing tool or a 🔴 step.

## Act as it

**Fixing something.** Become the component, then become its fix:
1. **Be the broken component with its real input.** `parse_date("04/03/2024")` returns `None`, so file 3 drops the row.
2. **Be the fixed component.** Write by hand, as literals, what it should output: the same row with the date 4 March 2024.
3. **Feed that to the real neighbours, one call at a time**: file 4 gets the row's price, then file 5 gets the rows for its March total.
4. **Those hand outputs become the expected values in Replay.**

**Making something new.** Be the whole program on a small sample: fetch the list page, then three items; find each name and price by hand; write the CSV rows you expect.

## Chains

A neighbour that breaks on the corrected data is a chain link, whether you find it while acting as the fix or on replay. In the five-files story, the revived March rows reach file 4, and `price.to_amount("12,50")` crashes on the comma. That crash was hidden until the date fix let the rows through.

Log the link as its own flow with `Revealed by: <the fix that exposed it>`, for example "Revealed by: S3, file 3 date fix". Then rehearse that link the same way.

More than 3 links means the first fix was wrong: undo it and re-diagnose from Look.

## Helpers and the manager

Send a helper when Look shows a long chain, slow feedback or a big codebase: that is the **helpers** size, chosen after Look. The session is the manager. Helpers only look.

1. **The manager starts the rehearsal** before spawning: `mkdir -p .rehearsal/fixtures && touch .rehearsal/active`.
2. **Spawn `rehearse:rehearser`** with the Agent tool. Say what to become and whom to feed: "Become normalize.py with the 04/03/2024 rows from orders.csv. Act as the fixed file and feed its rows to price.py and report.py, one call at a time."
3. **A helper may look, act as the fix, save fixtures and write the log.** It cannot write code. It returns exactly two lines: the log path and the fixture list. Read the log, not a summary.
4. **Helpers pass data to each other only through files in `.rehearsal/fixtures/`**, never through prose.
5. **The manager ends the rehearsal** after the last helper returns: `rm .rehearsal/active`.
6. **Edit code only when the log shows the hand-made chain working end to end.** Then replay against the fixtures, or send a helper to call the neighbours by hand. Never run the whole thing and hope.

No subagents? Then the session rehearses by itself under the same rules, and owns the marker.

## Build and Replay

Now write the code, and test it with what you saw.

- **End the rehearsal first: `rm .rehearsal/active`.** If the guard then says nothing has been run yet, put the marker back on its own, make one real call, and remove it again.
- **Transcribe what worked by hand.** Use the tools and libraries from Scout and write only the glue.
- Each external call does what a rehearsed step did: same endpoint, headers and parameters.
- Each failure in the log has handling in the code.
- Copy the fixtures into the project's tests (e.g. `tests/fixtures/`). The hand results are the expected values.
- If the code and the expectation differ, fix the code, not the expectation. Change an expectation only if the log was wrong, and say so.
- Each library from Scout must pass on the fixtures. If one fails, switch to the next candidate.
- **Live replay**: run the program once on the same sample you rehearsed and compare with your hand results. A new failure here is a chain link.
- Behaviour that was never rehearsed goes on the list of unverified risks. Anything you could still call in one line does not belong there: call it.
- **Leave `.rehearsal/` in place when you are done.** The log is the evidence; the user decides when to delete it.

## Report

Tell the user plainly:
- **Reused vs built**: which existing tools and libraries do the work, and what was written and why
- **Verified for real**: the flows rehearsed by hand and replayed
- **Sandboxed / simulated**: what was not done for real, and why
- **Unverified risks**: what only time will show (runs over days, layout changes), plus anything skipped with its reason. Never a variation you could have typed

## Log template: `.rehearsal/REHEARSAL.md`

Keep this file as you go; the manager and the tests read it.

```markdown
# Rehearsal: <program or fix>

## Model
- Actors / entry points / inputs → outputs / surfaces / state / needs:

## Scout
| Need | Rung | Candidate | Checks (alive/used/fits/weight/real) | Verdict |
|------|------|-----------|--------------------------------------|---------|

## Plan
| # | Step | Assumption | Label | Status |
|---|------|------------|-------|--------|

## Flows
| Flow | Category | Rank | Result | Revealed by | Evidence |
|------|----------|------|--------|-------------|----------|
| 04/03/2024 rows kept | happy | 1 | ✅ March total includes them | | S3 |
| Comma price "12,50" | input | 1 | ❌ to_amount crashes | S3, file 3 date fix | S4, fixtures/price3.txt |

## Steps
### S1: <what you tried>
- cmd: `python3 -c 'import normalize; print(normalize.parse_date("04/03/2024"))'`
- saw: `None`
- means: file 3 cannot read day/month/year dates, so it drops the row
- next: be the fixed file 3 and feed the row to file 4

## Plan changes
- S4 → price.py must accept a comma as the decimal mark

## What I'd change and why
- normalize.py: read 04/03/2024 as 4 March 2024 (S1, S3)

## Unverified risks
-
```

## Without a guard hook

Some agents have no hook support. The rules still apply. The log, with the exact command for every step, is the audit trail: a reviewer can check that each step was a direct call and not a script.
