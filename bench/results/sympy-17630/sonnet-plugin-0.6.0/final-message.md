`block_collapse(b * b * b)` now works, and the zero blocks stay `ZeroMatrix` instead of turning into scalar `Zero`. The block-matrix and matmul test files pass.

**Cause:** `BlockMatrix._blockmul` multiplies the two block grids as ordinary matrices. A sum whose terms are all `ZeroMatrix` products collapses to the scalar `Zero`, which has no `.rows` or `.cols`. In this checkout that made `b._blockmul(b)` itself raise a `ValueError` from `BlockMatrix.__new__`, rather than the `AttributeError` in your traceback. It is the same cause.

**Fix:** in `sympy/matrices/expressions/blockmatrix.py`, `_blockmul` now replaces any non-matrix entry in the product with `ZeroMatrix(rowblocksize, colblocksize)` before building the result.

**Checked by hand:**
- `block_collapse(b*b*b)` now gives `Matrix([[a**3, 0], [0, 0]])`.
- `b._blockmul(b)._blockmul(b).blocks[0, 1]` is a `ZeroMatrix`.
- I added `test_issue_17624`, which covers the `b*b`, `b*b*b` and chained `_blockmul` cases.

**Sweep:**
- `BlockDiagMatrix._blockmul` falls back to the fixed method.
- The three call sites in `bc_matmul` all go through it.
- I did not run the rest of the repo's test suite.

The rehearsal log is in `.rehearsal/REHEARSAL.md`.