The reported annotation now works without `ExpressionWrapper`. The fix is in `django/db/models/expressions.py`, and the new regression tests pass.

**Cause:** `CombinedExpression._resolve_output_field` used the generic "all sources share a type" rule. So `end - start` was typed as a `DateTimeField`, and the outer `+ DurationField` then raised the mixed-types error. The same rule also broke bare `end - start` on SQLite: the result was typed as a datetime and the converter failed on the integer it returned.

**Change:** for `-` only, the method now types the result as:
- `DurationField` when both sides are the same temporal type (DateField, DateTimeField, TimeField). This matches the `TemporalSubtraction` branch in `as_sql`.
- the datetime's own field when subtracting a `DurationField`.
- anything else falls through to the existing rule.

**Verification:**
- Replayed on SQLite against values I worked out by hand: the reported annotation gives 2:30, bare `end - start` gives 2:30, `end - 1h` gives 11:30, and a DateField difference gives one day.
- `runtests.py` on `expressions`, `expressions_case`, `expressions_window`, `annotations`, `aggregation`, `db_functions`, `queries` and `model_fields`: 1491 run, OK.
- Two regression tests in `tests/expressions/tests.py` (`test_datetime_subtraction_without_output_field`, `test_datetime_minus_duration_without_output_field`). They error with the mixed-types FieldError without the source change and pass with it.

**Not covered:**
- Only SQLite was run. PostgreSQL, MySQL and Oracle take different paths for temporal subtraction and were not tested.
- `datetime + duration` (`F('end') + Value(timedelta, DurationField())`) still raises the mixed-types error. I left it alone because the report is about subtraction; it's a one-line follow-up if you want it.

The rehearsal log is at `.rehearsal/REHEARSAL.md`, with fixtures in `.rehearsal/fixtures/`. I left it in place as the evidence trail. Nothing is committed.