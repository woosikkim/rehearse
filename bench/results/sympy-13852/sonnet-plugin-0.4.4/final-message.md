`polylog(2, 1/2)` now evaluates to `-log(2)**2/2 + pi**2/12`, and `expand_func(polylog(1, z))` now gives `-log(-z + 1)` with no `exp_polar`.

**Checked by hand:** before the change, both examples from the report reproduced. mpmath confirms the closed form at 1/2 and that `polylog(1, z)` matches `-log(1 - z)` at z=3 and z=0.3+2j, including the branch (imaginary part -π for real z>1).

**Tests:** I couldn't use pytest or `sympy.test` in this environment (no pytest, and DeprecationWarnings become errors). Instead I called `test_polylog_expansion`, `test_lerchphi_expansion` and `test_derivatives` directly, and they pass.

**Doctests:** I did not get a clean doctest run. The only failures I saw were whitespace-only, in the lerchphi examples. The new `polylog(2, S.Half)` doctest and the updated `expand_func` doctest were not confirmed through a doctest run, though the same expressions print correctly when evaluated directly.

**Changes:**
- **`sympy/functions/special/zeta_functions.py`:** `eval` returns the closed form for `s == 2, z == 1/2`. The `s == 1` branch of `_eval_expand_func` now returns `-log(1 - z)`. I updated the docstring and added the new example.
- **`sympy/functions/special/tests/test_zeta_functions.py`:** added an assertion for `polylog(2, Rational(1, 2))` and changed the expected `s == 1` expansion to `-log(1 - z)`.

The log is in `.rehearsal/REHEARSAL.md`.