pyreverse now reads PEP 484 type hints. For `def __init__(self, a: str = None)` with `self.a = a`, the diagram shows `a : str` instead of `NoneType`.

The 24 tests across the three pyreverse test files pass. I only checked what the linker records, not the rendered diagram or a full `pyreverse` run. The new regression test is in `tests/unittest_pyreverse_inspector.py`.

**What was wrong:** astroid already exposes the hints, but pyreverse's linker only inferred from the assigned value. That value was the `None` default, so `a` got `NoneType` and never `str`.

**The fix:** in `pylint/pyreverse/inspector.py`, a new helper `_infer_from_annotation` handles `self.x = arg`, where `arg` is an `__init__` argument. If the argument has a hint, the hint's type is used instead of inferring from the default. Without a hint, or for other kinds of assignment, nothing changes. I also added a ChangeLog entry.

**Checked on a sample class:**
- `a: str = None` gives `str`.
- `b: int = 3` gives `int`.
- Unannotated `c=None` still gives `NoneType`.

**Not covered:**
- Hints on keyword-only or positional-only arguments are ignored.
- Hints on non-`__init__` methods are also ignored, as are `Optional[str]`-style hints (not tried).
- Attributes assigned from an expression rather than directly from the argument are ignored.

I left `.rehearsal/` in place with the fixture. I didn't write a `REHEARSAL.md` log, which the skill asks for.