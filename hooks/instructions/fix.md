# rehearse: fix

You are in a rehearse run. You will see the bug happen by hand before you change any code, write down what the right result is, have it confirmed, fix it, and have an independent director check it. Project code edits stay locked until the ending is registered and confirmed.

**Your first line of output is exactly:** `Rehearse: fix · run <id>` (the run id is at the end of these instructions).

## 1. Look by hand

Every command you run is logged as a step (S1, S2, ...) in `.rehearsal/<run id>/log.md`. You cite those steps later, so make each one count.

1. **Reproduce once.** Run the program the way the user does and see the wrong result.
2. **Start the stage**: `rehearse stage start` (add `--python <path>` when the project has its own interpreter, such as `.venv/bin/python`). The stage replays your accepted steps before each new one, so the names you set stay available; it says how many it replayed and which came out differently. A step that opens a network connection is repeated on every later step, so a request that changes data (POST, PUT, DELETE) belongs in `rehearse fetch <url> -X POST -H ... -d ...`, which sends it once and saves the answer as a fixture.
3. **Become the component.** With `rehearse stage step '<one statement or expression>'`, import the project's own code and call it with the real input, one call per step. Find the component where good input becomes wrong output.
4. **Chase the wrong value upstream.** If the wrong value arrives from a call into other code, call that code by hand with the same input, and keep going until you reach the call whose inputs are right and whose output is wrong. The fix belongs there, where the value is first made wrong, not where it is first noticed. A patch at the point of noticing leaves every other caller broken. A plausible bug next to the symptom is often not the cause; name it, but keep chasing.
5. **Try other shapes.** Type the same input two or three other ways: the optional or nested form, the empty one, the one written at a different level. A variation that gives the wrong answer is part of the bug.
6. **Be the fixed component.** Type by hand, as literals, what it should output, and hand that to the real next component, one call at a time. If the next component breaks on the corrected data, that is a **chain link**: note it with `Revealed by: <the step or fix that exposed it>` and look at it the same way.

For anything on the web, use `rehearse fetch <url>`: it saves the response as a fixture you can cite. Use the stage for Python and `rehearse fetch` for the web; never write a script of your own to do the looking.

Steps that write or send something follow the labels below.

| Label | Meaning | What you do |
|---|---|---|
| Rehearse | Read-only and safe | Do it for real |
| Sandbox | Writes, but reversible | Do it in a temp folder, test database or test account |
| Simulate / ask | Irreversible or external (sends, pays, deletes, posts) | Never run it without the user's OK; verify everything up to it, then ask or simulate |
| Skip | Pure logic, no outside world | Leave it to the tests |
| Blocked | Needs a credential, a captcha or a missing tool | Stop and ask the user; never fake a result |

## 2. Register the ending

The ending is the command that shows the bug, and what it must print once fixed:

```
rehearse ending --cmd '<command>' [--tests '<tests command>'] \
  --expect '<requirement in the user's words>' <check> '<value>' --cite <source> \
  [--expect ... --cite ...]
```

- Checks: `equals`, `contains`, `regex`, `exit_code`, `fixture_equals <fixture name>`.
- Every expected value cites where it came from: `step:S<n>` (a logged step), `fixture:<name>` (a saved fixture) or `request` (the user's words). The value must appear word for word in what you cite, so when you work a number out in the stage, print it the way the program prints it.
- Add `--tests '<command>'` when you know which tests cover this code.
- The ending must fail now. If every expectation already passes, it is refused: it shows nothing wrong.
- Cover every requirement in the request, and every chain link you found.

## 3. Ask the user to confirm

Follow `${CLAUDE_PLUGIN_ROOT}/hooks/instructions/confirm.md`. Edits open when the confirmation is recorded.

## 4. Fix, then rerun

Change the code where the value is first made wrong, and fix any chain link the same way. After each round of edits, rerun the ending with `rehearse run`. If it still fails twice in a row, look again by hand (a stage step into the code, or a fetch) before the next edit; edits lock again until you do.

## 5. The director

When `rehearse run` passes, spawn `rehearse:director` with the Agent tool (any short prompt; the plugin replaces it). It reruns the ending, tries inputs you did not, compares the tests with how they were before, and returns PASS or REWORK. On REWORK, act on its findings and spawn it again.

## 6. Report

Write `.rehearsal/<run id>/report.md`. Its first line is one of:

- `fixed`: only when every expectation was verified by `rehearse run`
- `built, not verified against the real target`
- `not fixed`

then why, in plain words. Then: the ending table (command, before, after, expected, PASS or FAIL) with each chain link as its own row and its "Revealed by"; the director's extra inputs and their results; what changed, file by file, in plain words; what was verified for real and what could not be (and why); if not fixed, what is known and what to try next.

Leave `.rehearsal/` in place. It is the evidence; the user decides when to delete it.
