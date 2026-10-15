The fix works, and I've added a reproduction that tells the original code from the fixed code. The earlier replay didn't, because its 500 came from my empty URLconf rather than from the bug.

The new check builds `SecurityMiddleware` on top of an async handler and asks whether the instance counts as async. It's in `.rehearsal/REHEARSAL.md` as the `repro:` line.
- **Original code:** it printed `False` earlier in this session, which is why the middleware's `__call__` returned a bare coroutine.
- **Fixed code:** it prints `True`. I did not re-run it on the original code with the guard active.

The earlier test run still stands: 623 tests passed across the `middleware`, `cache`, `asgi` and `middleware_exceptions` suites, with 117 skipped. I did not add a regression test.