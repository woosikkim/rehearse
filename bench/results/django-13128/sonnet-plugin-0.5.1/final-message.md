`F('end') - F('start') + Value(timedelta(), output_field=DurationField())` should now resolve without `ExpressionWrapper`. I confirmed that on a hand-built version of the expression, and the `expressions`, `expressions_case`, `aggregation` and `annotations` test suites pass (359 tests, 4 skipped). I didn't run the exact `Experiment` annotation against a database. I also didn't add a regression test.

**Cause:** subtracting two datetime fields gave an expression whose output type was inferred as `DateTimeField`. Adding a `DurationField` to that mixed the two types and raised the `FieldError`. Only the SQL-generation step knew a datetime-minus-datetime result is a duration.

**Fix:** in `django/db/models/expressions.py`, `CombinedExpression` now has a `_resolve_output_field` method. When the connector is subtraction and both sides are the same date, datetime or time type, it returns `DurationField()`. Other cases fall back to the existing behaviour.

**What I checked:**
- **Before the fix:** the same expression, built from a `DateTimeField` column, raised the exact `FieldError` from the report.
- **After the fix:** that expression's output field is `DurationField`.

The rehearsal log is in `.rehearsal/REHEARSAL.md`, and I left `.rehearsal/` in place.