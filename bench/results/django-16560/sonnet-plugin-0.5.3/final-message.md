`CheckConstraint`, `UniqueConstraint` and `BaseConstraint` now accept `violation_error_code`, and it's passed as the `code` of the `ValidationError` they raise. The constraint, migration-autodetector and validation tests pass (356 run, 53 skipped), including the new tests.

Before the change, `CheckConstraint(..., violation_error_code="c")` raised `TypeError: unexpected keyword argument`, which I ran by hand. I didn't re-run that same call after the fix because I hadn't configured settings. The new tests cover it instead.

- **Constructor and `deconstruct()`:** the argument is added to all three classes, and `deconstruct()` includes it when set, so migrations and `clone()` keep it.
- **`__eq__` and `__repr__`:** both now include the code for `CheckConstraint` and `UniqueConstraint`.
- **Where the code applies:** `CheckConstraint.validate()` and the `UniqueConstraint` paths that use `get_violation_error_message()` (expression-based and conditional) raise with the code.
- **Where it doesn't apply:** a `UniqueConstraint` with `fields` and no condition still raises through `Model.unique_error_message()`, which has its own codes (`unique`, `unique_together`). I left that alone for backward compatibility. This matches how `violation_error_message` already behaves there.
- **Docs and tests:** I added the argument to `docs/ref/models/constraints.txt` and a 5.0 release note, plus tests for deconstruct and for `validate()` on both constraint types.

I didn't run the full Django suite.

The `.rehearsal/` log is left in place with the one reproduction step in it.