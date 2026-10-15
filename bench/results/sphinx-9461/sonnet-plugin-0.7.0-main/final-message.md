I've rewritten the repro as `repro: <command>` in `.rehearsal/REHEARSAL.md` and run it. The old repro never showed the bug because both runs printed a stale `.rehearsal/out/index.txt`. Sphinx's incremental build doesn't rebuild when only Sphinx's own code changes.

The new command forces a fresh build with `-E -a` and counts the `class property f` entries:

- **With the fix:** it prints `2`, one for `mod.A` and one for the inherited copy on `mod.B`.
- **Before the fix:** it should print `0`, since the output earlier showed only `property g`. I didn't re-run it against the original code, so I'm inferring that. The stop hook does that comparison itself.

I haven't committed anything.