The reproduction I gave before only wrote its output to a file and printed nothing, so it looked identical on the old and new code. I've replaced it with one that builds the docs and then prints the result. It's logged as the `repro:` line in `.rehearsal/REHEARSAL.md`.

The new command gives different output before and after the change:

- **Original code:** only `class target.Derived`, with no `attr`.
- **Fixed code:** `attr = 1` followed by "base attr doc".

I ran it on both versions to confirm. The fix itself is unchanged from my earlier summary.