Fixed: values returned from an INSERT now go through the field's `from_db_value` and other db converters, so `create()` gives the wrapper type. I read the ticket as the Django core bug and fixed it in `django/db/models/sql/compiler.py`. I haven't committed anything.

Rehearse: full, because this is a reported bug with code to run before changing it.

**What was wrong:** `SQLInsertCompiler.execute_sql` returned the raw database values for `returning_fields`. Reads run converters through `apply_converters`, but the insert path never did. `save()` and `bulk_create()` then assigned those raw values straight to the attribute.

**The fix:** `execute_sql` builds the returned rows as before, then runs them through `get_converters` / `apply_converters` for the returning fields. Both `save()` and `bulk_create()` get the fix, since they both consume that return value.

**Verification:**
- Reproduced the ticket's shape with the real backend: the field carries `from_db_value`, and the insert path never called it.
- Added `AutoWrapperModel` and two tests in `tests/from_db_value/`.
- `create()` now returns `IntWrapper`: pass.
- `bulk_create()` on SQLite returned `None` for the PK, because this SQLite does not return PKs from a bulk insert. I gated that test on `can_return_rows_from_bulk_insert`, per the ticket's scope.
- Test runs: `from_db_value bulk_create custom_pk model_fields` gave 473 tests OK (18 skipped). `basic queries model_regress` gave 490 tests OK (16 skipped, 2 expected failures).

**Not verified:** the bulk-PK path on a backend that returns rows (PostgreSQL, Oracle). Only SQLite is available here, and it returns no bulk PKs. The code path is shared with `create()`, but it has not been run.

**Rehearsal record:** the log is at `.rehearsal/REHEARSAL.md`. I left `.rehearsal/` in place as evidence. The guard blocked a few of my commands (a pipe after the quoted call, a lambda, a command substitution), so some probes used a different form.