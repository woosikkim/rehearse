Pyreverse now reads argument annotations. Your example gives `a : str` instead of `NoneType`. I haven't added a regression test or a ChangeLog entry.

I ran a probe class with `a: str = None`, `b: int = 1` and an unannotated `c=None`. The attributes come out as `a : str`, `b : int` and `c : NoneType`. The 23 existing pyreverse tests (inspector, diadefs, writer) pass.

**Cause.** `self.a = a` was inferred from the default value, so the annotation was ignored.

**Fix.** In `pylint/pyreverse/inspector.py`, a new helper `_infer_from_annotation` handles `self.x = arg` when `arg` is a parameter with an annotation. It uses the annotation's inferred type, and anything else still goes through normal inference.

**Not covered.**
- Only plain `self.x = arg` assignments are handled. Annotations on class-level attributes (`x: int = 0`) and on attributes assigned from other expressions are not read.
- I only probed simple annotations like `str` and `int`. Generic forms such as `Optional[str]` or `List[int]` are untested, so I don't know what they show.

The rehearsal log is in `.rehearsal/REHEARSAL.md`.