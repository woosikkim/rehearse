$ ls .rehearsal; cat sklearn/utils/_set_output.py; python -c 'import sklearn; print(sklearn.__version__)'
Exit code 1
active
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
        raise ValueError("Pandas output does not support sparse data.")

$ ls /opt/*/envs 2>/dev/null; conda env list 2>/dev/null; command -v python3.9; ls .venv 2>/dev/null
Exit code 2
testbed
# conda environments:
#
base                     /opt/miniconda3
testbed               *  /opt/miniconda3/envs/testbed

$ /opt/miniconda3/envs/testbed/bin/python -c '
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
  -> _InstancesOf.__init__() = None  [sklearn/utils/_param_validation.py:260]
  -> make_constraint(constraint=<class 'numbers.Real'>) = <sklearn.utils._param_validation._InstancesOf object at 0x7fd506794d30>  [sklearn/utils/_param_validation.py:127]
  -> _NoneConstraint.__init__() = None  [sklearn/utils/_param_validation.py:227]
  -> make_constraint(constraint=None) = <sklearn.utils._param_validation._NoneConstraint object at 0x7fd506794d00>  [sklearn/utils/_param_validation.py:125]
  -> <listcomp>(.0=<list_iterator object at 0x7fd506794940>) = [<sklearn.utils._param_validation._InstancesOf object at 0x7fd506794d60>, <sklearn.utils._param_validation._InstancesOf object at 0x7fd506794d30>, <sklearn.utils._param_validation._NoneConstraint obje  [sklearn/utils/_param_validation.py:74]
  -> _InstancesOf.is_satisfied_by(val=1) = True  [sklearn/utils/_param_validation.py:263]
  -> _InstancesOf.__init__() = None  [sklearn/utils/_param_validation.py:227]
  -> _InstancesOf.__init__() = None  [sklearn/utils/_param_validation.py:260]
  -> make_constraint(constraint=<class 'numbers.Integral'>) = <sklearn.utils._param_validation._InstancesOf object at 0x7fd506794cd0>  [sklearn/utils/_param_validation.py:127]
  -> _InstancesOf.__init__() = None  [sklearn/utils/_param_validation.py:227]

$ grep -n "def transform\|def _transform\|class \|def get_feature_names_out" sklearn/feature_selection/_base.py; grep -rn "_wrap_in_pandas_container" --include=*.py . | grep -v "^./build"
24:class SelectorMixin(TransformerMixin, metaclass=ABCMeta):
68:    def transform(self, X):
92:    def _transform(self, X):
146:    def get_feature_names_out(self, input_features=None):
sklearn/utils/_set_output.py:10:def _wrap_in_pandas_container(
sklearn/utils/_set_output.py:130:    return _wrap_in_pandas_container(
sklearn/utils/tests/test_set_output.py:8:from sklearn.utils._set_output import _wrap_in_pandas_container
sklearn/utils/tests/test_set_output.py:14:def test__wrap_in_pandas_container_dense():
sklearn/utils/tests/test_set_output.py:15:    """Check _wrap_in_pandas_container for dense data."""
sklearn/utils/tests/test_set_output.py:21:    dense_named = _wrap_in_pandas_container(X, columns=lambda: columns, index=index)
sklearn/utils/tests/test_set_output.py:27:def test__wrap_in_pandas_container_dense_update_columns_and_index():
sklearn/utils/tests/test_set_output.py:28:    """Check that _wrap_in_pandas_container overrides columns and index."""
sklearn/utils/tests/test_set_output.py:34:    new_df = _wrap_in_pandas_container(X_df, columns=new_columns, index=new_index)
sklearn/utils/tests/test_set_output.py:39:def test__wrap_in_pandas_container_error_validation():
sklearn/utils/tests/test_set_output.py:40:    """Check errors in _wrap_in_pandas_container."""
sklearn/utils/tests/test_set_output.py:45:        _wrap_in_pandas_container(X_csr, columns=["a", "b", "c"])
sklearn/utils/tests/test_set_output.py:225:def test__wrap_in_pandas_container_column_errors():
sklearn/utils/tests/test_set_output.py:234:    X_wrapped = _wrap_in_pandas_container(X_df, columns=get_columns)
sklearn/utils/tests/test_set_output.py:238:    X_wrapped = _wrap_in_pandas_container(X_np, columns=get_columns)

$ /opt/miniconda3/envs/testbed/bin/python -c '
import numpy as np, pandas as pd
X = pd.DataFrame({"a": np.array([1,2,3],dtype=np.float16), "c": pd.Series([0,1,2]).astype("category")})
out = pd.DataFrame(np.array([[1.,0.],[2.,1.],[3.,2.]]), columns=["a","c"])
print(out.astype(X.dtypes.to_dict()).dtypes)
print(out.astype({"a": X.dtypes["a"]}).dtypes)
'
a     float16
c    category
dtype: object
a    float16
c    float64
dtype: object

