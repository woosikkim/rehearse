# rehearse: build

You are in a rehearse run. You will do the job by hand against the real target before you write any code, write down what the right result is, have it confirmed, build it, and have an independent director check it. Project code edits stay locked until the ending is registered and confirmed.

**Your first line of output is exactly:** `Rehearse: build · run <id>` (the run id is at the end of these instructions).

## 1. Look by hand

Every command you run is logged as a step (S1, S2, ...) in `.rehearsal/<run id>/log.md`. You cite those steps later, so make each one count.

1. **Scout first.** Most of what programs need already exists. Go down this ladder for the whole job, then for each need left, and stop at the first rung that holds:
   1. The whole job exists as a tool, app or service. The "program" may be one command.
   2. An official source replaces the hard part: an API, feed, sitemap, export or webhook instead of scraping.
   3. A maintained library does the step.
   4. Only then write it yourself.

   Look at what is installed first, then the target itself (`/api`, `/feed`, `/sitemap.xml`, `robots.txt`, its docs), then outside. A candidate is an assumption too: try it by hand. Documentation can be wrong; what the target really answers wins.
2. **Do the job by hand on a small sample**: a typical item, an empty one, an odd one, and the last one, each as its own step. For 1000 items, never loop; sample.
   - For the web, use `rehearse fetch <url>`: it saves the response as a fixture you can cite.
   - For Python, start the stage with `rehearse stage start` (add `--python <path>` when the project has its own interpreter) and send one statement or expression at a time with `rehearse stage step '<code>'`.
   - Never write a script of your own to do the looking.
3. **Write down what you saw**, then pick the next step from it. "Got 403, so retry with a browser User-Agent" is a decision that later becomes code. Match the tool the program will use: if it will use plain HTTP, look with a fetch, not a browser.

For the surfaces a program can touch (web, files, databases, time, devices), see `${CLAUDE_PLUGIN_ROOT}/skills/rehearse/references/surfaces.md`.

Steps that write or send something follow the labels below.

| Label | Meaning | What you do |
|---|---|---|
| Rehearse | Read-only and safe | Do it for real |
| Sandbox | Writes, but reversible | Do it in a temp folder, test database or test account |
| Simulate / ask | Irreversible or external (sends, pays, deletes, posts) | Never run it without the user's OK; verify everything up to it, then ask or simulate |
| Skip | Pure logic, no outside world | Leave it to the tests |
| Blocked | Needs a credential, a captcha or a missing tool | Stop and ask the user; never fake a result |

If a step you did by hand breaks the next one (a name with a comma breaks the CSV row), that is a **chain link**: note it with `Revealed by: <the step that exposed it>` and look at it the same way.

## 2. Register the ending

The ending is the command that will run the finished program, and what it must print:

```
rehearse ending --cmd '<command>' [--tests '<tests command>'] \
  --expect '<requirement in the user's words>' <check> '<value>' --cite <source> \
  [--expect ... --cite ...]
```

- Checks: `equals`, `contains`, `regex`, `exit_code`, `fixture_equals <fixture name>`.
- Every expected value cites where it came from: `fixture:<name>` (a saved fixture), `step:S<n>` (a logged step) or `request` (the user's words). The value must appear word for word in what you cite.
- Add `--tests '<command>'` when you know which tests should cover it.
- The ending must fail now. A build fails because the program does not exist yet.
- Cover every requirement in the request, with values from the sample you did by hand.

## 3. Ask the user to confirm

Follow `${CLAUDE_PLUGIN_ROOT}/hooks/instructions/confirm.md`. Edits open when the confirmation is recorded.

## 4. Build, then rerun

Build from the steps that worked: the same endpoints, headers and fields you saw. Use what Scout found and write only the glue. Each failure you saw by hand gets handling in the code. After each round of edits, rerun the ending with `rehearse run`. If it still fails twice in a row, look again by hand before the next edit; edits lock again until you do. If the program runs but does not match the ending, carry on as a fix: find where its value is first made wrong.

## 5. The director

When `rehearse run` passes, spawn `rehearse:director` with the Agent tool (any short prompt; the plugin replaces it). It reruns the ending, tries other items from the real target, and returns PASS or REWORK. On REWORK, act on its findings and spawn it again.

## 6. Report

Write `.rehearsal/<run id>/report.md`. Its first line is one of:

- `fixed`: only when every expectation was verified by `rehearse run`
- `built, not verified against the real target`: when something could not be checked for real (a credential, a service that is down, a side effect that was simulated)
- `not fixed`

then why, in plain words. Then: the ending table (command, before, after, expected, PASS or FAIL) with each chain link as its own row and its "Revealed by"; the director's extra inputs and their results; what was reused (tools, APIs, libraries from Scout) and what was written, file by file, in plain words; what was verified for real and what could not be (and why); if not fixed, what is known and what to try next.

Leave `.rehearsal/` in place. It is the evidence; the user decides when to delete it.
