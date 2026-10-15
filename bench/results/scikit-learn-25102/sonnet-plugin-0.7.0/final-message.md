I replaced the repro with a single-line command that shows the bug. Before the change it printed `[dtype('float64'), dtype('float64')]`. After the change it prints `[dtype('float16'), dtype('float16')]`.

I ran it on the fixed code only. I didn't re-run it on the original code, so the "before" output comes from my first run of the issue's snippet (`.rehearsal/fixtures/before.txt`), not from this exact command. The command is logged as `repro:` in `.rehearsal/REHEARSAL.md`.

The earlier summary still applies: only feature selectors keep their dtypes with pandas output, and I added tests for the new behaviour.