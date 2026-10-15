# Rehearsal: preserve dtypes in pandas output for SelectorMixin
repro: /opt/miniconda3/envs/testbed/bin/python -c 'import numpy as np; from sklearn.datasets import load_iris; from sklearn.feature_selection import SelectKBest, chi2; X, y = load_iris(return_X_y=True, as_frame=True); X = X.astype({"petal width (cm)": np.float16, "petal length (cm)": np.float16}); X["cat"] = y.astype("category"); s = SelectKBest(chi2, k=2).set_output(transform="pandas"); print(s.fit_transform(X, y).dtypes)'
### S1: SelectKBest pandas output
- saw: float64 for both columns (fixtures/before.txt); SelectorMixin.transform casts DataFrame to ndarray via _validate_data
- plan: add cast_to_ndarray to _validate_data; SelectorMixin keeps DataFrame when pandas output; _transform uses _safe_indexing
### S2: act as fixed _transform: _safe_indexing(DataFrame, mask, axis=1)
- saw: a float16, c category preserved -> fix viable
## Sweep
| Place | Called with | Saw | Fixed |
| VarianceThreshold, RFE, SelectFromModel, SFS (grep SelectorMixin; all share transform) | DataFrame, pandas output | dtypes kept | n/a |
| k=0 (empty selection) | DataFrame | (150, 0), no crash after fix to X.dtype branch | yes |
| ndarray input, default output | | float64 unchanged | n/a |
Tests: feature_selection + test_set_output pass; sklearn/tests/test_base.py::test_clone_sparse... fails before and after (pre-existing).
