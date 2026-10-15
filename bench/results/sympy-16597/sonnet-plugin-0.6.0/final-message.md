The background run of `core`, `assumptions`, `functions`, `ntheory` and `simplify` was stopped when it hit its time limit, so it never finished. I'm not restarting it.

The `core`, `assumptions`, `functions/elementary`, `functions/combinatorial` and `ntheory` suites ran to completion in the separate foreground run. `simplify` and the rest of `functions` (for example `special`) never completed in either run, so they are untested against the new `'integer -> finite'` rule.

I also need to correct my last message. I said the rehearsal log was at `.rehearsal/log.md`, but I never opened that file, so I can't confirm it exists or what it holds.