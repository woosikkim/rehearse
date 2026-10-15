`SelectKBest` and the other feature selectors now keep their input dtypes when you use pandas output. The existing set-output and feature-selection tests pass, plus one new test.

**What I ran:** I reproduced the bug first. A frame with a float16 column, a category column and a float64 column came out of `SelectKBest(chi2, k=2).set_output(transform="pandas")` as all float64. After the change the category column stays `category` and the float64 column stays `float64`. My repro frame didn't actually select the float16 column, so that dtype is covered by the logic but wasn't run.

**How it works:**
- `_wrap_in_pandas_container` in `sklearn/utils/_set_output.py` takes a new `dtypes` argument. For each output column whose name is in the input's dtypes, it casts to that dtype.
- `_wrap_data_with_container` passes the input's `dtypes` only to estimators that set `_sklearn_preserves_dtypes = True`.
- `SelectorMixin` in `sklearn/feature_selection/_base.py` sets that flag, because selectors only drop columns.
- The new test is `test_selector_preserves_dtypes_pandas_output` in `sklearn/feature_selection/tests/test_base.py`.

**Behaviour to know about:**
- The behaviour is on by default for selectors with pandas output. It isn't a separate user-facing option, as the issue floated.
- Other transformers that don't change values are not covered yet. They would need to set the same flag, and I left that out to keep the change small.
- The log is in `.rehearsal/REHEARSAL.md`. It only records the reproduction step, not the later build and replay.

**Unverified:** I didn't test a selector on a frame with string categories. `check_array` may reject those before they reach the wrapper.