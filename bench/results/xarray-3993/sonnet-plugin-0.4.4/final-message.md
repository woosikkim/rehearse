`DataArray.integrate` now takes `coord`, the same as `Dataset.integrate`. I kept `dim` as a deprecated keyword, so existing code still works.

`da.integrate(dim="x")` still gives the same result but now emits a `FutureWarning`. Passing both `coord` and `dim` raises a `ValueError`. Passing neither raises a `TypeError`. I answered the deprecation question by keeping the old keyword and warning, rather than removing it outright.

I ran `da.integrate(coord="x")`, `da.integrate("x")` and `da.integrate(dim="x")` on a small array and all three gave 4.0. The `integrate` tests in `xarray/tests/test_dataset.py` pass (2 passed). I did not add new tests for the warning or the two error cases. Nothing else in the repo calls `integrate` with `dim=`.

The change is in `xarray/core/dataarray.py`, with a note under breaking changes in `doc/whats-new.rst`. The rehearsal log is in `.rehearsal/`.