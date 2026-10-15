`has_key`, `has_keys` and `has_any_keys` now find numeric keys like `'1111'` on SQLite. `model_fields.test_jsonfield` and `queries` pass (529 tests, OK). I couldn't run MySQL or Oracle here, so those backends are untested.

**Cause:** `HasKeyLookup.as_sql` in `django/db/models/fields/json.py` sent the key through `compile_json_path`. That function turns any integer-looking string into an array index. So `'1111'` became `$[1111]` instead of `$."1111"`. I checked with `sqlite3` by hand that `$."1111"` finds the key and `$[1111]` returns NULL. The same code builds the paths for MySQL and Oracle, so the fix applies there too.

**Fix:**
- A plain string key on the right-hand side is now always treated as an object key (`.` plus the JSON-quoted key).
- Keys that arrive through a `KeyTransform` keep the old behaviour, so `value__d__0` still means array index 0.
- My first attempt broke six existing tests. `key__isnull` and `KeyTransformExact` on Oracle built a `HasKey` from a plain `key_name`, which relies on numeric strings meaning array indexes. I added a small helper, `key_transform_has_key`, that builds the `HasKey` from the full key chain so those callers keep index semantics.
- I added `test_has_key_number` in `tests/model_fields/test_jsonfield.py`. It covers `has_key`, `has_keys`, `has_any_keys` and a nested `has_key` with numeric keys.

**Not verified:** MySQL and Oracle. The Oracle `isnull` and exact-null paths now go through the new helper, and no test here exercised them.

The `.rehearsal/` directory is still in the repo root as the evidence log. The rehearse guard only recorded a few steps in it, so don't rely on it as a full record.