## Look: see the bug happen by hand

1. **Reproduce once.** Run the program the way the user does and see the wrong result.
2. **Start the stage**: `rehearse stage start` (add `--python <path>` when the project has its own interpreter, such as `.venv/bin/python`). The stage replays your accepted steps before each new one, so the names you set stay available; it says how many it replayed and which came out differently. A step that opens a network connection is repeated on every later step, so a request that changes data (POST, PUT, DELETE) belongs in `rehearse fetch <url> -X POST -H ... -d ...`, which sends it once and saves the answer as a fixture.
3. **Become the component.** With `rehearse stage step '<one statement or expression>'`, import the project's own code and call it with the real input, one call per step. Find the component where good input becomes wrong output. The previous stage's checked output is this stage's real input: use it.
4. **Chase the wrong value upstream.** If the wrong value arrives from a call into other code, call that code by hand with the same input, and keep going until you reach the call whose inputs are right and whose output is wrong. The fix belongs there, where the value is first made wrong, not where it is first noticed. A patch at the point of noticing leaves every other caller broken. A plausible bug next to the symptom is often not the cause; name it, but keep chasing until the ending is registered.
5. **Try other shapes.** Type the same input two or three other ways: the optional or nested form, the empty one, the one written at a different level. A variation that gives the wrong answer is part of the bug.
6. **Be the fixed component.** Type by hand, as literals, what it should output, and hand that to the real next component, one call at a time. If the next component breaks on the corrected data, that is a **chain link**: note it with `Revealed by: <the step or fix that exposed it>` and look at it the same way.

For anything on the web, use `rehearse fetch <url>`: it saves the response as a fixture you can cite. Use the stage for Python and `rehearse fetch` for the web; never write a script of your own to do the looking.

## Register the ending, then stop

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
- Cover every requirement in the stage's plan line and the goal, and every chain link you found.

Once it is registered, stop. Your final message names the component where the value is first made wrong and the chain links. The manager has the user confirm the ending, then starts a build worker.
