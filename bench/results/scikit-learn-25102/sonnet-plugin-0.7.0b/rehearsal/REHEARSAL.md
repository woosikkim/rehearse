# Rehearsal: preserve dtypes in pandas output of selectors

repro: /opt/miniconda3/envs/testbed/bin/python -c 'import numpy as np, pandas as pd; from sklearn.feature_selection import VarianceThreshold; X = pd.DataFrame({"a": np.array([1,2,3,4],dtype=np.float16), "c": pd.Series([0,1,0,1]).astype("category")}); print(VarianceThreshold().set_output(transform="pandas").fit_transform(X).dtypes)'

Before: a float64, c float64 (fixtures/before.txt shows the same for SelectKBest).
After: a float16, c category.
