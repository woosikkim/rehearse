I added precomputed `_cdf` methods for all 11 distributions in your list, in `sympy/stats/crv_types.py`, and every test case from the issue now returns a closed-form answer instead of hanging, failing or staying half-evaluated. I also added `test_precomputed_cdf` to `sympy/stats/tests/test_continuous_rv.py`. It passes when called directly, along with `test_cdf` and `test_gamma`.

`sympy.test("sympy/stats")` can't give a clean result here. It reports 40 exceptions both with and without my changes. They are Python 3.9 deprecation warnings that SymPy's test runner turns into errors, and pytest isn't installed.

**What changed**
- **New `_cdf` methods:** Arcsin, Dagum, Frechet, Gamma, GammaInverse, Kumaraswamy, Laplace, Logistic, Nakagami, StudentT and UniformSum. They use the Wikipedia formulas: `asin`, `lowergamma`, `uppergamma`, `hyper` or plain expressions.
- **Erlang:** it needed no CDF of its own, because it wraps Gamma. The float came from `1/l` with a Python int `l`, which gives `1.0`. I changed it to `S.One/l`, so `cdf(Erlang("x", 1, 1))(1)` is now `1 - exp(-1)`.
- **Support intervals:** Arcsin now has `set = Interval(a, b)`, and Kumaraswamy's was corrected from `(0, oo)` to `(0, 1)`.

**How I checked**
- **Derivative against PDF:** for each distribution except UniformSum, I differentiated the CDF and compared it with the PDF numerically. The difference was 0 at the sample points.
- **Issue cases:** all of them returned values, for example Laplace gives `1 - exp(-1)/2`.

**Not fully verified**
- **UniformSum:** it still returns an unevaluated `Sum` until you call `.doit()`, which gives 9/40. It was not covered by the derivative check because of the `floor(x)` bound.
- **Gamma with a float shape:** `Gamma("x", 0.1, 2)` returns `0.105*lowergamma(0.1, 3/2)`. That is the closed form with float coefficients, as you'd expect for float input.

The rehearsal log is in `.rehearsal/`, and I left it there.