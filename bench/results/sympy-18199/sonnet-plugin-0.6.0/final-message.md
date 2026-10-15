The fix is in and passing. The failure the hook flagged came from my earlier run, before the edit had been applied, because the guard blocked the first attempt. I reran the same command after the edit, and it now prints `[0] 0 [0] [8, 11]`. `test_residue` also passes, run as a plain function because pytest isn't installed here.

`nthroot_mod` now returns the root `0` whenever `a % p == 0`, with `[0]` for `all_roots=True`. The change is in `sympy/ntheory/residue_ntheory.py`, with four new assertions in `sympy/ntheory/tests/test_residue.py`.

The reported example, `nthroot_mod(17*17, 5, 17)`, already returned `0` before my change. The bug showed up when `n` divides `p - 1`. For example, `nthroot_mod(0, 3, 7, True)` raised `ValueError: Log does not exist`.

I didn't run the `solveset` tests. `sympy/solvers/solveset.py` is the only other caller of `nthroot_mod`, and I didn't call it by hand.