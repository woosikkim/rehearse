`qs1 | qs2` no longer raises the `AssertionError`. I ran `queries`, `or_lookups`, `many_to_many`, `null_queries`, `expressions`, `aggregation`, `filtered_relation` and `lookup`, 869 tests in all, and they pass.

**Cause:** when `Query.combine` joined rhs's tables into lhs, `table_alias` picked new alias numbers that could land on aliases rhs already used. In your case the map became `{T4: T5, T5: T6}`, which `change_aliases` rejects because an alias could be renamed twice.

**Fix (`django/db/models/sql/query.py`):**
- `Query.join` and `Query.table_alias` take an `exclude` argument.
- `combine` passes `rhs.alias_map` as `exclude`.
- New aliases skip any name in `exclude` or already in the query's own `alias_map`.
- The assertion in `change_aliases` now has a comment explaining what it guards against, as you suggested.

My first version only skipped rhs's aliases. That produced a different failure, `no such column: T6.baz_id`, because two joins were given `T6`. Skipping the query's own aliases too fixed it.

**Test:** `QuerySetOrCombineAliasTests` in `tests/queries/tests.py`, with new `Foo`, `Bar`, `Baz` and `Qux` models in `tests/queries/models.py`. It runs both `qs2 | qs1` and `qs1 | qs2`. It fails with the `AssertionError` without the fix and passes with it. It only checks that the combined queries run and return no rows, since the test creates no data.

**Not done:** the note in the report about OR not being commutative is not in the docs. The two orderings can still produce different SQL, and I didn't touch that.

The rehearsal log is in `.rehearsal/REHEARSAL.md` and I left it in place. I couldn't run the report's exact reproduction before writing the test, because the models didn't exist in the repo. The new test is the reproduction.