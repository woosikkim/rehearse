`DataArray.integrate` now takes `coord`, matching `Dataset.integrate`, and `dim=` still works as a deprecated alias.

I answered the deprecation question with a short cycle. Passing `dim=` gives the same result as `coord=` plus a `FutureWarning`. It raises `ValueError` if you pass both `coord` and `dim`. If you pass neither, it raises `TypeError` saying `coord` is required. Positional calls like `da.integrate("x")` are unchanged.

**Verified:** I ran `da.integrate` five ways on a small 1-D array: positional, `coord="x"`, `dim="x"`, both, and neither. The first three returned 4.5, with the warning on `dim=`. The last two raised the errors above. I ran the integrate tests in `test_dataset.py` and `test_units.py`: 2 passed in the first file, and 8 passed with 4 skipped in the second. I did not run the rest of the test suite.

**Changes:**
- **`xarray/core/dataarray.py`:** the signature, docstring and argument handling.
- **`xarray/tests/test_units.py`:** one existing call switched from `dim="x"` to `coord="x"`.
- **`doc/whats-new.rst`:** an entry under Deprecations.

I didn't add tests for the new warning and error paths. The five calls above are only recorded in this reply, not in the test files. The rehearsal log is in `.rehearsal/REHEARSAL.md`.