Fast-delete queries for the same table are now combined into one `DELETE ... WHERE a OR b`. The ticket's `Entry` example now produces one statement for that table.

**Rehearsal (full size):** I reproduced on SQLite with the `delete` test models. `R.delete()` with four CASCADE FKs from `A` to `R` issued four `DELETE FROM delete_a WHERE <fk>_id IN (...)` statements. After the fix it issues one, with `WHERE (auto_id IN (5) OR auto_nullable_id IN (5) OR cascade_id IN (5) OR cascade_nullable_id IN (5))`. The M2M through tables are different tables, so they stay separate. The log is at `.rehearsal/REHEARSAL.md`.

**Change:**
- `django/db/models/deletion.py`: a new `Collector.add_fast_delete()` ORs a related queryset into an already queued one for the same model. It stops combining once the total primary keys would exceed the backend's `max_query_params`. That limit is 999 on SQLite and `None` (unlimited) elsewhere. Without it, combining batches could exceed SQLite's parameter limit.
- `tests/delete/tests.py`: `test_fast_delete_combined_fks` asserts one DELETE against `delete_a`. It fails on the original code (`4 != 1`) and passes with the fix.

**Verified:** the `delete`, `delete_regress`, `model_inheritance`, `generic_relations`, `many_to_many`, `many_to_one`, `one_to_one`, `proxy_models`, `null_fk`, `admin_views`, `admin_inlines` and `queries` suites all pass (1141 tests in the broad run, with the existing `assertNumQueries` counts unchanged).

**Choices I made that you may want to change:**
- I combine only same-model querysets, which covers the ticket's case. I did not add a query-count assertion for the parameter-limit split.
- Combined `OR` conditions can be slower than separate `IN` lookups on some databases, which I have not measured.

**Not done or unverified:**
- The 999-parameter split path has no dedicated test. The existing batch tests cover single-relation batching only.
- flake8 and isort aren't installed here, so I didn't run them.
- Environment changes: I installed `asgiref`, `sqlparse` and `pytz` into the system Python, and ran `pip install -e /testbed` so the test runner can import Django.
- `.rehearsal/` is untracked in the repo. It holds the log and the SQLite probe database; delete it if you don't want it.