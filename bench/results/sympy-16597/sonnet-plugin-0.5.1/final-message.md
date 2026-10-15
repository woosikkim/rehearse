The fix is in, and the tests I ran show no regressions from it. The only error is the same one the stashed, pre-change code gives for `S(..., evaluate=False)`. The repo's tests can't parse `evaluate=False` on this Python version. It shows up in `test_sympify.py` and `test_solvers.py::test_base_0_exp_0`.

`Symbol('m', even=True).is_finite` now returns `True`, and so do odd and plain integer symbols.

**The change**
- I added one rule to `_assume_rules` in `sympy/core/assumptions.py`: `'integer -> finite'`.
- A real-only symbol (`real=True`) still has `is_finite` of `None`. A general `complex -> finite` rule would fix that, but it made `import sympy` fail. `oo` is declared positive, which implies real and then complex, which contradicts it being infinite. Fixing that means separating "extended real" from "real", which is a much larger change.
- I also tried `algebraic -> finite` first. It wrongly made `oo` transcendental and irrational, so I dropped it.

**Existing tests I changed**
- `integer -> finite` changes some facts about `oo` and `-oo`. `oo.is_integer`, `is_even`, `is_odd` and `is_composite` are now `False`, and `is_noninteger` is now `True`.
- I updated those expectations in `test_infinity` and `test_neg_infinity` to match. They are correct, but they do change documented behaviour. You may want to look at them.
- I added `test_integer_implies_finite` to `test_assumptions.py`.

**Test results**
- The suites I ran were core, assumptions, functions, series, simplify, ntheory, concrete, sets, matrices and the solver tests.
- Those runs were split: the first was killed at its time limit, after covering 149 test files with no failures. The second covered ntheory, concrete, sets, matrices and the solver tests, with 898 passed.
- I did not run the whole test suite. The rest of the repo, including `sympy/physics`, `sympy/integrals`, `sympy/polys` and `sympy/geometry`, is untested.

The rehearsal log is in `.rehearsal/REHEARSAL.md`. The stop hook keeps flagging my first probe, which failed under the discarded `complex -> finite` rule. That failure was real but is superseded by the rule now in place.