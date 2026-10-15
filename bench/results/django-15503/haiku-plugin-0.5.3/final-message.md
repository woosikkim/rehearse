The fix is in and SQLite is verified, but MySQL and Oracle are not: no servers are available here, so those backends are untested.

**Cause:** `compile_json_path` turns any key that parses as an integer into an array index. So `has_key="1111"` compiled to `$[1111]` instead of `$."1111"`, and never matched the object member. The SQLite, MySQL and Oracle lookups all build their paths through this function, so all three were affected.

**Change** (`django/db/models/fields/json.py`):
- `HasKeyLookup` now builds plain (non-`KeyTransform`) keys as object members via a new `key_path` method. `has_key`, `has_keys` and `has_any_keys` all go through it.
- Key transforms passed as the right-hand side (e.g. `F(...)`) still use `compile_json_path`.
- A new `KeyTransformHasKey` subclass keeps index semantics for the `key__isnull` and null-`key__exact` paths. My first attempt changed those too and broke six existing tests (e.g. `value__d__0__isnull=False` on arrays), so I routed those call sites to the subclass.

**Test** (`tests/model_fields/test_jsonfield.py`): added `test_has_key_numeric`, covering `has_key`, `has_keys` and `has_any_keys` with the key `"1111"`, plus `has_key=1111`.

**Results:**
- `model_fields.test_jsonfield`: before the change, 87 tests, OK (skipped=8). After, 88 tests, OK (skipped=8), with the new test included.
- Related modules (`db_functions`, `expressions_case`, `lookup`): 600 tests, OK (skipped=29).
- `black` applied to both files.

**Not verified:**
- MySQL and Oracle: the generated paths should be `$."1111"` on both, but I did not run them against a live database.
- The file `django/db/models/fields/json.py` changed on disk while I was working. I re-read it, and it matches my edits, so I kept the current state.

The rehearsal log is in `.rehearsal/REHEARSAL.md`, with fixtures in `.rehearsal/fixtures/`. I left that directory in place, so it will show as untracked in git.