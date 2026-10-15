Fixed: `Dataset.reset_index(..., drop=True)` no longer leaves a dropped name in `_coord_names`. Your example now prints normally instead of raising `ValueError: __len__() should return >= 0`.

**Cause:** `reset_index` removed the dropped variable (`z`) from `_variables` but left it in `_coord_names`. `DataVariables.__len__` computes `len(_variables) - len(_coord_names)`, so it went negative.

**Fix:** in `xarray/core/dataset.py` (`reset_index`), the dropped names are now subtracted from `coord_names`:
```python
coord_names = (set(new_variables) | self._coord_names) - set(drop_variables)
```

**Checked:**
- **Your example:** after the fix, `_coord_names` is `{'a', 'b'}` and `a` and `b` stay as non-index coordinates on `z`.
- **Level drop:** `reset_index("a", drop=True)` was already fine. It keeps `z` as a MultiIndex with only level `b`.
- **Callers:** `DataArray.reset_index` goes through `Dataset.reset_index`, so it gets the fix too.
- **Existing tests:** the existing `set_index`/`reset_index` tests in `test_dataset.py` pass (3 tests).

I didn't add a regression test for the `drop=True` case. I also didn't run the rest of the test suite. The rehearsal log is in `.rehearsal/` and I left it in place.