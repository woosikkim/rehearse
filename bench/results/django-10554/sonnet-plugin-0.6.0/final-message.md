I made no code change, because this bug is already fixed in the current checkout. The fix is the commit right before this one, 14d026cccb, "Fixed #30572".

**Cause:** `get_combinator_sql` called `set_values()` directly on the sub-queries of a union. Those sub-queries are shared with the original queryset. So `qs.order_by().values_list('pk', flat=True)` cut their columns down to `id`, while the original `qs` still ordered by `(4)` and failed with "ORDER BY position 4 is not in select list". The fix is the line `compiler.query = compiler.query.clone()` before `set_values`, at `django/db/models/sql/compiler.py:429`.

**What I ran:**
- **Before the fix (`HEAD~2`):** I built `Tag` union queries and called `.order_by().values_list('pk', flat=True)`. Afterwards `qs.query` selected only `id` but still ended with `ORDER BY (2)`. That is the reported breakage.
- **Current code:** the same calls leave `qs.query` unchanged, for `Number` and `Tag`, with and without an ordered sub-query, and whether `qs` is compiled before or after the `values_list`.

**Not run for real:** I couldn't run it on PostgreSQL, which is where the original traceback comes from. SQLite rejects ORDER BY inside compound sub-queries. I patched `supports_slicing_ordering_in_compound` to `True` so the query would compile, and only looked at the generated SQL, not at executed results.

I left a log in `.rehearsal/REHEARSAL.md`. I didn't add a test, because `tests/queries/test_qs_combinators.py` already got one in 14d026cccb. If you want a regression test for the ordered-sub-query case specifically, I can add one.