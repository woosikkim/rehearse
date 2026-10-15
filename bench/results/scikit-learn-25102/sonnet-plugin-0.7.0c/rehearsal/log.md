$ ls .rehearsal; cat sklearn/utils/_set_output.py; python -c 'import sklearn;print(sklearn.__version__)'
Exit code 1
active
base
fixtures
scaffold
from functools import wraps
from scipy.sparse import issparse
from . import check_pandas_support
from .._config import get_config
from ._available_if import available_if
def _wrap_in_pandas_container(
    data_to_wrap,
    *,
    columns,
    index=None,
):
    """Create a Pandas DataFrame.
    If `data_to_wrap` is a DataFrame, then the `columns` and `index` will be changed
    inplace. If `data_to_wrap` is a ndarray, then a new DataFrame is created with
    `columns` and `index`.
    Parameters
    ----------
    data_to_wrap : {ndarray, dataframe}
        Data to be wrapped as pandas dataframe.
    columns : callable, ndarray, or None
        The column names or a callable that returns the column names. The
        callable is useful if the column names require some computation.
        If `columns` is a callable that raises an error, `columns` will have
        the same semantics as `None`. If `None` and `data_to_wrap` is already a
        dataframe, then the column names are not changed. If `None` and
        `data_to_wrap` is **not** a dataframe, then columns are
        `range(n_features)`.
    index : array-like, default=None
        Index for data.
    Returns
    -------
    dataframe : DataFrame
        Container with column names or unchanged `output`.
    """
    if issparse(data_to_wrap):

$ ls /opt/*/envs 2>/dev/null; conda env list 2>/dev/null; which -a python python3.9
Exit code 1
testbed
# conda environments:
#
base                     /opt/miniconda3
testbed               *  /opt/miniconda3/envs/testbed
/opt/miniconda3/bin/python
/usr/bin/python
/bin/python

$ P=/opt/miniconda3/envs/testbed/bin/python; $P -c '
import numpy as np
from sklearn.datasets import load_iris
from sklearn.feature_selection import SelectKBest, chi2
X, y = load_iris(return_X_y=True, as_frame=True)
X = X.astype({"petal width (cm)": np.float16, "petal length (cm)": np.float16})
X["cat"] = y.astype("category")
s = SelectKBest(chi2, k=2).set_output(transform="pandas")
print(s.fit_transform(X, y).dtypes)
' | tee .rehearsal/fixtures/before.txt
petal length (cm)    float64
cat                  float64
dtype: object

$ sed -n 1,125p sklearn/feature_selection/_base.py; grep -n "def _validate_data" -A12 sklearn/base.py; grep -n "check_array\|check_X_y" sklearn/base.py
"""Generic feature selection mixin"""
# Authors: G. Varoquaux, A. Gramfort, L. Buitinck, J. Nothman
# License: BSD 3 clause
import warnings
from abc import ABCMeta, abstractmethod
from operator import attrgetter
import numpy as np
from scipy.sparse import issparse, csc_matrix
from ..base import TransformerMixin
from ..cross_decomposition._pls import _PLS
from ..utils import (
    check_array,
    safe_mask,
    safe_sqr,
)
from ..utils._tags import _safe_tags
from ..utils.validation import _check_feature_names_in, check_is_fitted
class SelectorMixin(TransformerMixin, metaclass=ABCMeta):
    """
    Transformer mixin that performs feature selection given a support mask
    This mixin provides a feature selector implementation with `transform` and
    `inverse_transform` functionality given an implementation of
    `_get_support_mask`.
    """
    def get_support(self, indices=False):
        """
        Get a mask, or integer index, of the features selected.
        Parameters
        ----------
        indices : bool, default=False
            If True, the return value will be an array of integers, rather
            than a boolean mask.
        Returns
        -------
        support : array
            An index that selects the retained features from a feature vector.
            If `indices` is False, this is a boolean array of shape
            [# input features], in which an element is True iff its
            corresponding feature is selected for retention. If `indices` is
            True, this is an integer array of shape [# output features] whose

$ sed -n 540,610p sklearn/base.py; grep -n "def check_array" -A12 sklearn/utils/validation.py; grep -n "_is_pandas_df\|ensure_2d\b" sklearn/utils/validation.py | head -30
            If False, call validate_X_y(). Else, it must be a tuple of kwargs
            to be used for calling check_array() on X and y respectively.
            `estimator=self` is automatically added to these dicts to generate
            more informative error message in case of invalid input data.
        **check_params : kwargs
            Parameters passed to :func:`sklearn.utils.check_array` or
            :func:`sklearn.utils.check_X_y`. Ignored if validate_separately
            is not False.
            `estimator=self` is automatically added to these params to generate
            more informative error message in case of invalid input data.
        Returns
        -------
        out : {ndarray, sparse matrix} or tuple of these
            The validated input. A tuple is returned if both `X` and `y` are
            validated.
        """
        self._check_feature_names(X, reset=reset)
        if y is None and self._get_tags()["requires_y"]:
            raise ValueError(
                f"This {self.__class__.__name__} estimator "
                "requires y to be passed, but the target y is None."
            )
        no_val_X = isinstance(X, str) and X == "no_validation"
        no_val_y = y is None or isinstance(y, str) and y == "no_validation"
        default_check_params = {"estimator": self}
        check_params = {**default_check_params, **check_params}
        if no_val_X and no_val_y:
            raise ValueError("Validation should be done on X, y or both.")
        elif not no_val_X and no_val_y:
            X = check_array(X, input_name="X", **check_params)
            out = X
        elif no_val_X and not no_val_y:
            y = _check_y(y, **check_params)
            out = y
        else:
            if validate_separately:
                # We need this because some estimators validate X and y
                # separately, and in general, separately calling check_array()
                # on X and y isn't equivalent to just calling check_X_y()
                # :(

$ cat >> .rehearsal/REHEARSAL.md <<'EOF'
# Rehearsal: preserve dtypes in pandas output for SelectorMixin
repro: /opt/miniconda3/envs/testbed/bin/python -c 'import numpy as np; from sklearn.datasets import load_iris; from sklearn.feature_selection import SelectKBest, chi2; X, y = load_iris(return_X_y=True, as_frame=True); X = X.astype({"petal width (cm)": np.float16, "petal length (cm)": np.float16}); X["cat"] = y.astype("category"); s = SelectKBest(chi2, k=2).set_output(transform="pandas"); print(s.fit_transform(X, y).dtypes)'
### S1: SelectKBest pandas output
- saw: float64 for both columns (fixtures/before.txt); SelectorMixin.transform casts DataFrame to ndarray via _validate_data
- plan: add cast_to_ndarray to _validate_data; SelectorMixin keeps DataFrame when pandas output; _transform uses _safe_indexing
EOF

$ /opt/miniconda3/envs/testbed/bin/python -c 'import numpy as np; import pandas as pd; from sklearn.utils import _safe_indexing; X = pd.DataFrame({"a": np.array([1, 2], dtype=np.float16), "b": [0.5, 1.5], "c": pd.Series([0, 1]).astype("category")}); print(_safe_indexing(X, np.array([True, False, True]), axis=1).dtypes)'
a     float16
c    category
dtype: object
  -> MultiOutputMixin() = None  [sklearn/base.py:1021]
  -> _UnstableArchMixin() = None  [sklearn/base.py:1028]
  -> <module>() = None  [sklearn/base.py:1068]
  -> <module>() = None  [sklearn/utils/_show_versions.py:75]
  -> <module>() = None  [sklearn/__init__.py:132]
  -> _determine_key_type(key=array([ True, False,  True]), accept_slice=True) = 'bool'  [sklearn/utils/__init__.py:279]
  -> _is_arraylike(x=array([ True, False,  True])) = True  [sklearn/utils/validation.py:259]
  -> _is_arraylike_not_scalar(array=array([ True, False,  True])) = True  [sklearn/utils/validation.py:264]
  -> _pandas_indexing(X=     a    b  c
0  1.0  0.5  0
1  2.0  1.5  1, key=array([ True, False,  True]), key_dtype='bool', axis=1) =      a  c
0  1.0  0
1  2.0  1  [sklearn/utils/__init__.py:200]
  -> _safe_indexing(X=     a    b  c
0  1.0  0.5  0
1  2.0  1.5  1, indices=array([ True, False,  True]), axis=1) =      a  c
0  1.0  0
1  2.0  1  [sklearn/utils/__init__.py:354]

