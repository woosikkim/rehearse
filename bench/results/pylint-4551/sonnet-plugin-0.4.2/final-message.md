pyreverse now takes the type from the annotation when an instance attribute is assigned straight from an annotated argument. Your example (`self.a = a` with `a: str = None`) now types `a` as `str`, so the diagram should show `a : str`. I confirmed that at the inference level. I did not render a dot or png file, because the rehearsal guard blocked writing a `.py` test file.

The related pyreverse test files pass (24 tests), and I added one new test for this. I didn't run the full pylint suite.

**What changed:**
- **The fix:** `Linker._infer_annotation` in `pylint/pyreverse/inspector.py` infers the annotation instead of the assigned value. Before, `a` inferred to `[Uninferable, None]`, so no type was shown.
- **Unannotated arguments:** they behave as before.
- **Generic hints:** `Optional[str]` comes out as `Optional`, not `str`, because the annotation infers to the generic class.
- **Test and changelog:** the test is in `tests/unittest_pyreverse_inspector.py`, and there is a `ChangeLog` entry.

**Not covered:** only `self.x = arg` with a plain name on the right is handled. Annotations on method signatures in the method list, and class-level `x: int` annotations, are not.

The rehearsal log is in `.rehearsal/`; I left it in place.