$ ls .rehearsal 2>&1; python3 -c '
from sympy import *
a = MatrixSymbol("a", 2, 2)
z = ZeroMatrix(2, 2)
b = BlockMatrix([[a, z], [z, z]])
print(type(b._blockmul(b).blocks[0,1]))
' ; grep -n "_blockmul" -B3 -A12 sympy/matrices/expressions/blockmatrix.py | sed -n 1,60p
active
fixtures
scaffold
Traceback (most recent call last):
  File "/testbed/sympy/__init__.py", line 19, in <module>
    import mpmath
ModuleNotFoundError: No module named 'mpmath'
During handling of the above exception, another exception occurred:
Traceback (most recent call last):
  File "<string>", line 2, in <module>
  File "/testbed/sympy/__init__.py", line 21, in <module>
    raise ImportError("SymPy now depends on mpmath as an external library. "
ImportError: SymPy now depends on mpmath as an external library. See https://docs.sympy.org/latest/install.html#mpmath for more information.
161-            and self.rowblocksizes == other.rowblocksizes
162-            and self.colblocksizes == other.colblocksizes)
163-
164:    def _blockmul(self, other):
165-        if (isinstance(other, BlockMatrix) and
166-                self.colblocksizes == other.rowblocksizes):
167-            return BlockMatrix(self.blocks*other.blocks)
168-
169-        return self * other
170-
171-    def _blockadd(self, other):
172-        if (isinstance(other, BlockMatrix)
173-                and self.structurally_equal(other)):
174-            return BlockMatrix(self.blocks + other.blocks)
175-
176-        return self + other
--
328-    def _eval_transpose(self):
329-        return BlockDiagMatrix(*[mat.transpose() for mat in self.args])
330-
331:    def _blockmul(self, other):
332-        if (isinstance(other, BlockDiagMatrix) and
333-                self.colblocksizes == other.rowblocksizes):
334-            return BlockDiagMatrix(*[a*b for a, b in zip(self.args, other.args)])
335-        else:
336:            return BlockMatrix._blockmul(self, other)
337-

$ ls /opt/*/envs 2>&1; ls .venv/bin/python 2>&1; which -a python python3; python -c 'import mpmath' 2>&1
Exit code 1
testbed
ls: cannot access '.venv/bin/python': No such file or directory
/opt/miniconda3/bin/python
/usr/bin/python
/bin/python
/opt/miniconda3/bin/python3
/usr/bin/python3
/bin/python3
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'mpmath'

$ P=/opt/miniconda3/envs/testbed/bin/python; $P -c '
from sympy import *
a = MatrixSymbol("a", 2, 2)
z = ZeroMatrix(2, 2)
b = BlockMatrix([[a, z], [z, z]])
print(type(b._blockmul(b).blocks[0,1]))
print(type((b.blocks*b.blocks)[0,1]))
'
Exit code 1
Traceback (most recent call last):
  File "<string>", line 6, in <module>
  File "/testbed/sympy/matrices/expressions/blockmatrix.py", line 167, in _blockmul
    return BlockMatrix(self.blocks*other.blocks)
  File "/testbed/sympy/matrices/expressions/blockmatrix.py", line 86, in __new__
    raise ValueError(filldedent('''
ValueError: 
expecting a sequence of 1 or more rows containing Matrices.

$ sed -n 70,100p sympy/matrices/expressions/blockmatrix.py; grep -n "def _entry\|def __new__\|ZeroMatrix" sympy/matrices/expressions/matadd.py sympy/matrices/expressions/matmul.py | head -20
    [1, 1, 2, 2, 2],
    [1, 1, 2, 2, 2],
    [3, 3, 3, 4, 4],
    [3, 3, 3, 4, 4]])
    See Also
    ========
    sympy.matrices.matrices.MatrixBase.irregular
    """
    def __new__(cls, *args, **kwargs):
        from sympy.matrices.immutable import ImmutableDenseMatrix
        from sympy.utilities.iterables import is_sequence
        isMat = lambda i: getattr(i, 'is_Matrix', False)
        if len(args) != 1 or \
                not is_sequence(args[0]) or \
                len(set([isMat(r) for r in args[0]])) != 1:
            raise ValueError(filldedent('''
                expecting a sequence of 1 or more rows
                containing Matrices.'''))
        rows = args[0] if args else []
        if not isMat(rows):
            if rows and isMat(rows[0]):
                rows = [rows]  # rows is not list of lists or []
            # regularity check
            # same number of matrices in each row
            blocky = ok = len(set([len(r) for r in rows])) == 1
            if ok:
                # same number of rows for each matrix in a row
                for r in rows:
                    ok = len(set([i.rows for i in r])) == 1
                    if not ok:
sympy/matrices/expressions/matadd.py:13:    ZeroMatrix, GenericZeroMatrix)
sympy/matrices/expressions/matadd.py:34:    identity = GenericZeroMatrix()
sympy/matrices/expressions/matadd.py:36:    def __new__(cls, *args, **kwargs):
sympy/matrices/expressions/matadd.py:41:        # TypeErrors from GenericZeroMatrix().shape
sympy/matrices/expressions/matadd.py:57:    def _entry(self, i, j, **kwargs):
sympy/matrices/expressions/matadd.py:129:rules = (rm_id(lambda x: x == 0 or isinstance(x, ZeroMatrix)),
sympy/matrices/expressions/matmul.py:11:        Identity, ZeroMatrix, GenericIdentity)
sympy/matrices/expressions/matmul.py:34:    def __new__(cls, *args, **kwargs):
sympy/matrices/expressions/matmul.py:60:    def _entry(self, i, j, expand=True, **kwargs):
sympy/matrices/expressions/matmul.py:220:    if any([arg.is_zero or (arg.is_Matrix and arg.is_ZeroMatrix)

$ /opt/miniconda3/envs/testbed/bin/python -c '
from sympy import *
a = MatrixSymbol("a", 2, 2)
z = ZeroMatrix(2, 2)
b = BlockMatrix([[a, z], [z, z]])
m=b.blocks*b.blocks
print(m)
print(type(m[0,1]), type(m[1,1]))
'
Matrix([[a**2, 0], [0, 0]])
<class 'sympy.core.numbers.Zero'> <class 'sympy.core.numbers.Zero'>
  -> __eq__(a=Not(extended_positive), b='zero') = False  [sympy/core/logic.py:210]
  -> __eq__(a=Not(zero), b='zero') = False  [sympy/core/logic.py:210]
  -> And.__new__() = And(Not(extended_positive), Not(zero))  [sympy/core/logic.py:200]
  -> And.__new__() = And(Not(extended_positive), Not(zero))  [sympy/core/logic.py:313]
  -> Not.__new__() = Not(extended_real)  [sympy/core/logic.py:200]
  -> Not.__new__() = Not(extended_real)  [sympy/core/logic.py:375]
  -> Not.__new__(arg=Not(extended_negative)) = 'extended_negative'  [sympy/core/logic.py:380]
  -> <listcomp>(.0=<tuple_iterator object at 0x7fe858eb2670>) = [Not(extended_real), 'extended_negative']  [sympy/core/logic.py:341]
  -> __eq__(a=Not(extended_real), b=True) = False  [sympy/core/logic.py:210]
  -> __eq__(a=Not(extended_real), b=False) = False  [sympy/core/logic.py:210]

$ sed -n 100,135p sympy/matrices/expressions/blockmatrix.py; git diff --stat
                    if not ok:
                        break
                blocky = ok
                # same number of cols for each matrix in each col
                for c in range(len(rows[0])):
                    ok = len(set([rows[i][c].cols
                        for i in range(len(rows))])) == 1
                    if not ok:
                        break
            if not ok:
                # same total cols in each row
                ok = len(set([
                    sum([i.cols for i in r]) for r in rows])) == 1
                if blocky and ok:
                    raise ValueError(filldedent('''
                        Although this matrix is comprised of blocks,
                        the blocks do not fill the matrix in a
                        size-symmetric fashion. To create a full matrix
                        from these arguments, pass them directly to
                        Matrix.'''))
                raise ValueError(filldedent('''
                    When there are not the same number of rows in each
                    row's matrices or there are not the same number of
                    total columns in each row, the matrix is not a
                    block matrix. If this matrix is known to consist of
                    blocks fully filling a 2-D space then see
                    Matrix.irregular.'''))
        mat = ImmutableDenseMatrix(rows, evaluate=False)
        obj = Basic.__new__(cls, mat)
        return obj
    @property
    def shape(self):
        numrows = numcols = 0
        M = self.blocks
        for i in range(M.shape[0]):

