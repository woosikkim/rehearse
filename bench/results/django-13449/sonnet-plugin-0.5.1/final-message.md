`Lag()` over a `DecimalField` now works on SQLite. The `CAST(... AS NUMERIC)` wraps the whole window expression instead of just the `LAG(...)` call. The `expressions_window` and `expressions` test suites pass (204 tests, 5 skipped).

I reproduced the bug by compiling a `Window(Lag(<decimal>, 7))` against SQLite. It produced `CAST(LAG(%s, %s) AS NUMERIC) OVER (...)`, the same broken shape as in your report. After the change the output is `CAST(LAG(%s, %s) OVER (ORDER BY %s ASC) AS NUMERIC)`. I didn't run your exact `LagTest` model or the full query against a real table.

**Fix** (`django/db/models/expressions.py`): `Window` now uses `SQLiteNumericMixin` and has its own `as_sqlite()`. When the output field is a `DecimalField`, it compiles the inner expression as a float, so no cast lands inside the `OVER` clause. It then applies the cast around the whole window. The inner expression is copied first, so the caller's `Lag` object is not changed.

**Test**: I added `test_lag_decimal` to `tests/expressions_window/tests.py`. It casts `salary` to a decimal so it didn't need a model change.

I didn't test other window functions over decimals, such as `Lead` or `FirstValue`, or the case where `output_field` is set explicitly. They all go through the same new `as_sqlite()`, so I expect them to behave the same.

The rehearsal log is in `.rehearsal/REHEARSAL.md`, and I left it in place for you to delete when you're ready.