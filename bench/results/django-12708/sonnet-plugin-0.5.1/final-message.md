Removing an `index_together` no longer crashes when a `unique_together` covers the same fields. The `schema` and `migrations` suites pass (665 tests, 24 skipped).

**Cause:** The unique constraint is also reported as an index when the database is introspected. Looking for an index on those columns found two matches, the `_uniq` and the `_idx` one, and `_delete_composed_index` raised the `ValueError`.

**Fix:** In `django/db/backends/base/schema.py` (line 396), `alter_index_together` now passes `{'index': True, 'unique': False}`. It only matches the non-unique index, so the unique constraint stays in place.

**Test:** I added `test_index_together_with_unique_together_same_fields` in `tests/schema/tests.py`. Before the fix it failed with `ValueError: Found wrong number (2) of constraints`. It passes now, and it checks that the unique constraint is still there afterwards.

**What I ran:**
- I ran everything on SQLite only.
- I didn't rehearse the second point in the ticket, that moving an index declaration to `Options.indexes` shouldn't recreate the index. That is a separate migration-autodetector matter, and I didn't change it.
- The rehearsal log is in `.rehearsal/REHEARSAL.md`. I left it in place.

I haven't committed anything.