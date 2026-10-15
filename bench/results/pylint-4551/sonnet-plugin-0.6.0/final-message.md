pyreverse now shows `__init__` argument annotations as attribute types. Your example class renders as `a : str`. The 24 existing and new pyreverse tests pass. I didn't run the rest of the test suite.

I ran pyreverse on a small file with `a: str = None`, `b: int = 1` and an unannotated `c=None`. The output was `a : str`, `b : int` and `c : NoneType`. Before the change, astroid inferred `None` and `Uninferable` for `a` and ignored the annotation.

- **Annotation lookup:** `get_annotation` and `infer_node` in `pylint/pyreverse/utils.py` look up the annotation of the `__init__` argument that is assigned to `self.x`.
- **Linker:** `handle_assignattr_type` in `pylint/pyreverse/inspector.py` now prefers that annotation over inference.
- **Diagram labels:** `class_names` in `pylint/pyreverse/diagrams.py` now accepts the annotation (a `Name` node) as well as a class.
- **Siblings checked:** the other places that read these attribute types, in `diadefslib` and the association links in `diagrams`, skip `Name` nodes without errors.
- **Tests:** I added `test_get_annotation_from_init_arg` to `tests/unittest_pyreverse_writer.py`.

**Unverified:** only simple names like `str` and `int` are handled. Annotations written as `Optional[str]` or `List[int]` (subscripts) aren't labelled. Only annotations on `__init__` arguments assigned directly to `self` are read.

The rehearsal log is in `.rehearsal/REHEARSAL.md`.