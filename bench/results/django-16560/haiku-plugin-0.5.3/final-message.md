I added a `violation_error_code` parameter to `BaseConstraint`, `CheckConstraint` and `UniqueConstraint`. The code is passed to the `ValidationError` raised from `validate()`, and the existing `violation_error_message` behaviour is unchanged. Nothing is committed.

**What changed**
- `django/db/models/constraints.py`: the new keyword-only parameter is stored on every constraint, included in `deconstruct()`, `__eq__` and `__repr__`, and passed as `code=` on the custom-message raises in `CheckConstraint.validate()` and in `UniqueConstraint.validate()` (expression and condition paths).
- `tests/constraints/tests.py`: tests for the code on validation, clone and deconstruction.
- `docs/ref/models/constraints.txt`: documents the parameter with `versionadded:: 6.0`, since this checkout is the 6.0 dev line.

**Verification**
- Test suites `constraints`, `model_forms`, `validation` and `check_framework` pass (`OK`, with the existing skips).
- Replay caught a bug in my first build: both `__repr__` format strings needed one more `%s`. Fixed, and the suites pass after the fix.
- Not verified: `flake8` isn't installed in the project env, so I didn't lint.

**Choices I made**
- I named the parameter `violation_error_code`, matching `violation_error_message`. The issue asked for a code customisation without fixing a name.
- The fields-based `UniqueConstraint` path still uses `unique_error_message()`, so its code stays `"unique"`. That path has never used `violation_error_message`, so I left it alone.

The rehearsal log is in `.rehearsal/REHEARSAL.md` and I left it in place.