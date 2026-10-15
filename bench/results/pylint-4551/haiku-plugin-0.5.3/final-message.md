Pyreverse now uses a parameter's type annotation for attribute types, so `a: str = None` shows as `a : str` instead of `a : NoneType`. The pyreverse unit tests pass (25), including two new regression tests.

**Rehearsal:** full, with the log at `.rehearsal/REHEARSAL.md`.
- Using astroid (the parser pyreverse uses), the annotation is present, but inference of `self.a = a` returns only the default's `NoneType` and `Uninferable`.
- The annotation is reachable from the assigned value, so the fix can prefer it.

**Change** (`pylint/pyreverse/inspector.py`): a new `_infer_values` helper returns the annotation's type when the assigned value is an annotated argument, and falls back to inference otherwise. It replaces the two inference calls: the instance-attribute path and the locals path.

**Replay with the real `pyreverse` CLI:**

| Case | Before | After |
|---|---|---|
| `a: str = None` (ticket) | `a : NoneType` | `a : str` |
| `a=None`, no annotation | `NoneType` | `NoneType` (unchanged) |
| `b: int = 3` | `int` | `int` |
| `c: str = None` | `NoneType` | `str` |
| `a: Optional[str] = None` | `Optional` | `Optional` (see below) |

**Tests:** I added `test_annotated_argument_type_wins_over_none_default` and `test_unannotated_none_default_is_kept` to `tests/unittest_pyreverse_inspector.py`. The first fails without the fix.

**Choices and gaps:**
- The ticket says `String`, but the annotation is `str`, so the output shows `str`.
- `Optional[str]` still shows `Optional`. Unwrapping subscripted annotations is a separate change, so I left it out.
- Black would not run in this environment (click import error), so I checked line lengths by hand instead.
- Only annotations on arguments are handled. Annotated assignments such as `self.a: str = ...` are not.
- The tests ran with the `testbed` conda env (astroid 2.6.5, Python 3.9), not the bare system Python.