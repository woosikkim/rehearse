Chained exceptions now survive report serialization, so xdist should show the full chain. I haven't run it under xdist itself, because it isn't installed here. The new roundtrip test and the existing report tests pass (25 passed).

**Cause:** `TestReport._to_json` and `_from_json` in `src/_pytest/reports.py` only handled the last exception's traceback and crash location. The rest of the chain was dropped. On the way back, the report was rebuilt as a plain `ReprExceptionInfo`, which is why xdist printed only `ValueError: 13`.

**Fix:**
- If the report has a chain, `_to_json` now also serializes every `(traceback, crash, description)` entry in it.
- `_from_json` rebuilds an `ExceptionChainRepr` from those entries. Reports without a chain deserialize as before.
- I split the traceback conversion into small helpers so the main traceback and each chained one share the same code.

**Tests:** I added a roundtrip test in `testing/test_reports.py`. It raises a three-link chain (ValueError 11, 12, 13), serializes the report and rebuilds it. It checks that all 3 links and their "direct cause" / "During handling" descriptions survive and that the rendered text is identical. I also added `changelog/5786.bugfix.rst`; 5786 is my guess at the issue number, so please correct it.

**What I didn't do:**
- My plan was to reproduce the bug by hand first, but the rehearsal guard blocked the repro test file, so I didn't. The only call I ran before the fix was the baseline `testing/test_reports.py` run, and I diagnosed the cause by reading the code. I didn't see the old behaviour fail myself, though the new test would fail on the old code, which had no `chain` to compare.
- I did not try variations such as chains with cycles or suppressed context (`from None`). Those go through the same serialization path, but I haven't run them.

The rehearsal log is in `.rehearsal/REHEARSAL.md`; I left it in place.