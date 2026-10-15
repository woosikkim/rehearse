Fixed. `reset_index(..., drop=True)` left the dropped name in `_coord_names`, so the repr's `len(_variables) - len(_coord_names)` went negative.

**Rehearse: full.** I reproduced the error before changing code, then checked the state and variations.

**Cause:** in `Dataset.reset_index` (`xarray/core/dataset.py`), `drop=True` removes the name from the variables but never removes it from `coord_names`. `drop_vars` in the same file already does this correctly.

**Fix:** one line in `reset_index`:
```python
coord_names = self._coord_names - set(drop_variables) | set(new_variables)
```

**Verified:**
- The MVCE now renders, and `_coord_names` is `{'a', 'b'}`, matching `_variables`.
- Variations also render: a three-coordinate version, a single-level `set_index(x="a").reset_index("x", drop=True)`, and the `drop=False` control.
- Added `test_reset_index_drop_removes_coord_names` to `xarray/tests/test_dataset.py`. It fails without the fix and passes with it.
- `test_dataset.py` and `test_indexes.py`: 439 passed, 1 skipped, 1 xfailed, 1 xpassed.

**Notes:**
- The bare `python3` has no numpy, so I ran everything with `/opt/miniconda3/envs/testbed/bin/python`.
- Other index-drop paths were not rehearsed one by one; the full test modules cover them only indirectly.
- The log is in `.rehearsal/REHEARSAL.md`. I left it in place as evidence.
- I did not commit anything.