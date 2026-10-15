Sliced `Prefetch` querysets now work for reverse foreign keys and many-to-many relations, with and without `to_attr`. The four new tests pass, and the wider related-field and query suites pass (774 tests, 12 skipped and 2 expected failures, as before).

**What changed**
- `django/db/models/query.py`: new helper `_filter_prefetch_queryset`. For a sliced queryset it applies the slice per parent instance with `ROW_NUMBER() OVER (PARTITION BY <fk>)`, so `[:3]` means three rows per category, not three rows total. It raises `NotSupportedError` on backends without window support. It works on a clone, so the user's queryset keeps its slice.
- `prefetch_one_level`: when a sliced queryset is used without `to_attr`, the manager's cached queryset is built from the unsliced clone. The first version of the fix missed this path, and the no-`to_attr` test caught it.
- `django/db/models/fields/related_descriptors.py`: the reverse-FK manager, the reverse-FK descriptor, and the M2M manager call the helper.
- `tests/prefetch_related/tests.py`: four new tests (reverse FK with and without `to_attr`, M2M with and without `to_attr`).

**Things you should know**
- In this repo the error is `TypeError: Cannot filter a query once a slice has been taken.`, not the `AssertionError` in the ticket.
- I did not run the ticket's exact snippet on the unmodified code. The guard blocked inline Python, so I traced the failure by reading the code and saw the same `TypeError` from the new tests before the leaf-path fix.
- My first version of the `to_attr` test had the expected list in the wrong order. I corrected the expectation after checking the data; the code was right.
- The SQL predicate was hand-checked with the `sqlite3` CLI on literal rows: `rn > 0 AND rn <= 3` gives the first three rows per parent.
- The unsupported-backend branch is not tested (SQLite 3.41 here supports window functions).
- `flake8` is not installed in the environment, so the changed files were not linted.
- `GenericRelation` prefetching is not changed.

The rehearsal log is in `.rehearsal/REHEARSAL.md`, with fixtures in `.rehearsal/fixtures/`. I removed the `.rehearsal/active` marker before editing code and left the rest in place, as the skill asks.