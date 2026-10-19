## Look: do the job by hand

1. **Scout first.** Most of what programs need already exists. Go down this ladder for the whole stage, then for each need left, and stop at the first rung that holds:
   1. The whole job exists as a tool, app or service. The "program" may be one command.
   2. An official source replaces the hard part: an API, feed, sitemap, export or webhook instead of scraping.
   3. A maintained library does the step.
   4. Only then write it yourself.

   Look at what is installed first (including the user's own tools in the project), then the target itself (`/api`, `/feed`, `/sitemap.xml`, `robots.txt`, its docs), then outside. A candidate is an assumption too: try it by hand. Documentation can be wrong; what the target really answers wins.
2. **Do the job by hand on a small sample**: a typical item, an empty one, an odd one, and the last one, each as its own step. For 1000 items, never loop; sample. The previous stage's checked output is this stage's real input: use it.
   - For the web, use `rehearse fetch <url>`: it saves the response as a fixture you can cite.
   - For Python, start the stage with `rehearse stage start` (add `--python <path>` when the project has its own interpreter) and send one statement or expression at a time with `rehearse stage step '<code>'`. The stage replays your accepted steps before each new one; a step that opens a network connection is repeated on every later step, so a request that changes data belongs in `rehearse fetch <url> -X POST -H ... -d ...`, which sends it once and saves the answer as a fixture.
   - Never write a script of your own to do the looking, and never write a declared output while looking.
3. **Write down what you saw**, then pick the next step from it. "Got 403, so retry with a browser User-Agent" is a decision that later becomes code. Match the tool the program will use: if it will use plain HTTP, look with a fetch, not a browser.

For the surfaces a program can touch (web, files, databases, time, devices), see `${CLAUDE_PLUGIN_ROOT}/skills/rehearse/references/surfaces.md`.

If a step you did by hand breaks the next one (a name with a comma breaks the CSV row), that is a **chain link**: note it with `Revealed by: <the step that exposed it>` and look at it the same way.

**A thin source.** If the source gives less than the goal needs (fewer items, missing fields, short text), never pad it or invent the rest. Go down the scout ladder for another source and try it by hand. Register the ending on what was actually collected, and say in your final message what was collected and what is missing.

## Register the ending, then stop

The ending is the command that will run the finished program, and what it must print:

```
rehearse ending --cmd '<command>' [--tests '<tests command>'] \
  --expect '<requirement in the user's words>' <check> '<value>' --cite <source> \
  [--expect ... --cite ...] [--unchecked '<taste item>']
```

- Checks: `equals`, `contains`, `regex`, `exit_code`, `fixture_equals <fixture name>`.
- Every expected value cites where it came from: `fixture:<name>` (a saved fixture), `step:S<n>` (a logged step) or `request` (the user's words). The value must appear word for word in what you cite.
- Add `--tests '<command>'` when you know which tests should cover it.
- A check that rests on a borderline judgment (is X a tool? does Y count? is this the right cut-off?) gets `--call '<requirement>' '<the call, as one question>'`: the manager puts it to the user as its own question before building, never as one line among dozens of checks. Register the call for every such check; a judgment hidden in a check is what gets a stage stuck later.
- The ending must fail now. A build fails because the program or the output does not exist yet.
- Cover every requirement in the stage's plan line and the goal, with values from the sample you did by hand. What only taste can judge (tone, style) goes in `--unchecked`.

Once it is registered, stop. Your final message says what the scout found and what you would reuse. The manager has the user confirm the ending, then starts a build worker.
