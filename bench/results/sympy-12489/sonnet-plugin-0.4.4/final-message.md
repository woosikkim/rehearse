`Permutation` can now be subclassed: instances created by `Q([1,0,2])` and by the operations on it keep the subclass type. The 116 combinatorics tests pass (3 are expected failures), and the change is in `sympy/combinatorics/permutations.py`.

**Cause.** `_af_new` was a `staticmethod` that hardcoded `Basic.__new__(Perm, ...)`. `__new__` itself already used `cls`, so `Q([1,0,2])` came out as `Q`. But `Q*Q` and `Q**-1` went through `_af_new` and came back as plain `Permutation` (saved in `.rehearsal/fixtures/before.txt`).

**Fix.**
- `_af_new` is now a `classmethod` and builds `cls` instances.
- `__new__` calls `cls._af_new` and `cls(...)`.
- The instance methods and classmethods in that file call `self._af_new` instead of the module-level `_af_new`. This covers `__mul__`, `__pow__`, `__invert__`, `__xor__`, `commutator`, `next_lex`, `next_trotterjohnson`, `unrank_*`, `random` and `from_inversion_vector`.
- `__add__` and `next_nonlex` use `self.unrank_lex` and `self.unrank_nonlex` instead of `Perm.`.

I left the module-level `_af_new = Perm._af_new` alone, because 53 call sites in other modules rely on it and still get `Permutation`. `rmul_with_af` is a static method with no class to use, so it also still returns `Permutation`.

**Checked by running:**
- With `Q = type("Q", (Permutation,), {})`, every operation I tried returns `Q`: `*`, `**-1`, `~`, `next_lex`, `commutator`, `random`, `unrank_lex`, cycle-form construction, `Q(3)`, `+` and `next_nonlex`. I did not check `from_inversion_vector`, `unrank_trotterjohnson`, `next_trotterjohnson`, `rmul` or `mul_inv`.
- The doctests in `permutations.py` show 22 failures both with and without my change, so they predate it.
- The system Python lacked `mpmath` and `pytest`, so I used the `testbed` conda env's Python and sympy's own test runner.

The rehearsal log is in `.rehearsal/`. I didn't add a regression test for subclassing; say if you want one.