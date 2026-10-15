`nthroot_mod` now returns `0` when `a % p == 0`. Before the fix, `nthroot_mod(17*17, 5, 17)` raised `ValueError: Log does not exist` instead of just missing the root.

**The fix:** in `sympy/ntheory/residue_ntheory.py`, I added an early return after the prime-modulus check: `if a % p == 0: return [0] if all_roots else 0`. For prime `p`, `0` is the only root in that case, so the full list is `[0]`.

**What I ran:**
- `nthroot_mod(17*17, 5, 17)` now gives `0`, and `[0]` with `all_roots=True`.
- `nthroot_mod(0, 3, 7, True)` and `nthroot_mod(0, 3, 5)` also work now. The first crashed before the fix.
- `nthroot_mod(11, 4, 19, True)` still returns `[8, 11]`.
- `n == 2` already returned `[0]` through `sqrt_mod`, so I left it alone.
- I added two regression assertions to `test_residue` in `sympy/ntheory/tests/test_residue.py`, and `test_residue()` passes. I called it directly because pytest isn't installed in the `testbed` env.

**Not covered:** composite `p` still raises `NotImplementedError` as before, and I didn't change that. I only ran `test_residue`, not the rest of the ntheory tests.

The rehearsal log is in `.rehearsal/`.