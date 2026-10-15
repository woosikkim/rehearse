`expand_func(polylog(2, Rational(1,2)))` now returns `-log(2)**2/2 + pi**2/12`, and `expand_func(polylog(1, z))` returns `-log(1 - z)` with no `exp_polar`. The new test and the zeta test function `test_polylog_expansion` both pass when I call them directly. I could not run the doctest or the hyperexpand tests, so they are unchecked.

- **Change:** both edits are in `_eval_expand_func` in `sympy/functions/special/zeta_functions.py`. The `s == 1` case drops the `exp_polar`, and a new case handles `s == 2, z == 1/2`. I updated the docstring example to match.
- **Tests:** in `test_zeta_functions.py` I changed the `s == 1` assertion to `-log(1 - z)` and added one for the 1/2 value.
- **Checked by hand:** `expand_func(polylog(1, 3))` gives `-log(2) - I*pi`, which has the imaginary part of -π you described for real z > 1. `polylog(3, 1/2)` stays unevaluated, since only the s = 2 value is added.
- **Not run:**
  - The repo's runner (`sympy.test`/`sympy.doctest`) and pytest don't work in this environment: pytest isn't installed, and the runner treats the old-Python deprecation warnings as errors.
  - The hyperexpand test module wouldn't import by hand. A grep shows it doesn't use `expand_func` on `polylog`, so I don't expect an effect.
- **Left alone:** `test_R18` in `test_wester.py` is still marked expected-to-fail. It needs `Sum.doit()` to return `polylog(2, 1/2)` and then `simplify()` to expand it, which `simplify` doesn't do.

The rehearsal log is in `.rehearsal/` (kept there).