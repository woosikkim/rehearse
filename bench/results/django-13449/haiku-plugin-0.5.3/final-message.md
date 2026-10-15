The bug reproduces on SQLite, but I have not changed any Django code yet. The fix shape is verified by hand, and the next step is a code change in `django/db/models/expressions.py`, which I can make on your go-ahead.

**Cause.** `SQLiteNumericMixin.as_sqlite` (`django/db/models/expressions.py:18`) wraps a decimal-output expression's SQL in `CAST(... AS NUMERIC)`. `Func` mixes it in, so `Lag` produces `CAST(LAG(...) AS NUMERIC)`. `Window` is a plain `Expression` with template `%(expression)s OVER (%(window)s)`, so the OVER clause lands after the CAST and SQLite rejects it.

**Reproduced.** Running the generated SQL through the `sqlite3` CLI gives `near "OVER": syntax error`, the same error as the ticket.

**Variations.** The same failure happens with `Sum`, `FirstValue`, `Lead`, and `Lag` with a default, all on a decimal source. So the fix belongs in `Window`, not in `Lag`.

**Candidate fix.** Put the CAST around the whole window expression: `CAST(LAG(...) OVER (...) AS NUMERIC)`. On the sample rows it returns the same values as the FloatField workaround (`12.5` on row 2), and `Sum` returns the expected totals.

**Still open.** Inside Django, the inner `Lag` also applies its own CAST, so the fix needs a way to skip that inner cast when the expression sits inside a `Window`. I have not picked that mechanism yet, and I have not run the query through the ORM.

**Baseline.** `expressions_window` passes on SQLite: 49 tests, 3 skipped. The existing `Lag` test uses an IntegerField, so it does not cover this case.

Should I implement the fix in `Window` and add a regression test for a DecimalField `Lag` on SQLite? The rehearsal log is in `/testbed/.rehearsal/REHEARSAL.md`, with fixtures and the `lag.db` probe database in `.rehearsal/fixtures/`. No commit was made.