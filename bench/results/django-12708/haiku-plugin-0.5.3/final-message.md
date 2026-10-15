Fixed. Deleting an `index_together` no longer crashes when a `unique_together` covers the same fields. The bug reproduces only on MySQL-family backends, and I reproduced it on MariaDB.

**The cause:** `alter_index_together` deletes the index with `_delete_composed_index(..., {'index': True}, ...)`. On MySQL, the unique key and the index are both reported with `index=True`, so the lookup finds two constraints and raises. On PostgreSQL and SQLite, the unique constraint is not reported with `index=True`, so the bug does not appear there.

**The change:** `django/db/backends/base/schema.py:396` now passes `{'index': True, 'unique': False}`, so only the index matches.

**Verification:**
- **Reproduced:** on MariaDB 10.6, the real delete path raised `ValueError: Found wrong number (2) of constraints for rh_t(a, b)`, with names `['rh_t_a_b_uniq', 'rh_t_a_b_idx']`.
- **Fixed:** the same call now drops only the index, and the unique key stays.
- **Variations:** deleting a plain index with no unique key still works, and deleting the unique key while the index exists still works.
- **Regression test:** I added `test_index_together_with_unique_together_on_same_fields` to `tests/schema/tests.py`. It fails without the fix with the same `ValueError`, and passes with it.
- **Full `schema` suite:** passes on SQLite (skipped=24), MariaDB (skipped=18), and PostgreSQL (skipped=4).

**Not done:**
- The ticket's second point, that moving an `index_together` into `Meta.indexes` re-creates the index, is not addressed or tested.
- I tested MariaDB 10.6, not MySQL 8.

**Environment changes:** I installed PostgreSQL 14 and MariaDB 10.6 with apt. In the `testbed` conda env I installed `psycopg2-binary==2.8.6` and `mysqlclient`. The rehearsal notes and fixtures are in `/testbed/.rehearsal/`, which I left in place as the evidence log. The scratch SQLite file is at `/tmp/rh.db`.