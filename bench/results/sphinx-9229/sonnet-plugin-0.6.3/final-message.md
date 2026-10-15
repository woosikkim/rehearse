I fixed the case where a docstring on an alias of a class from another module was dropped and only `alias of ...` was shown. I did not reproduce your exact `file.py`, though. On Python 3.9 all three of your aliases already showed their docstrings. I think your three aliases behaved differently because on Python 3.6 some typing aliases are real classes, but I couldn't check that on 3.6.

The tests in `tests/test_ext_autodoc*.py` pass (164), including a new one.

- **Reproduced:** `Alias = Path` followed by a docstring (with `Path` imported from `pathlib`) rendered only `alias of "pathlib.Path"`.
- **Cause:** autodoc looked for the doc comment in `pathlib`'s source instead of the module defining the alias. `ClassDocumenter.add_content` also overwrote the content with the `alias of` text.
- **Fix, in `sphinx/ext/autodoc/__init__.py`:**
  - It now reads the doc comment from the module that defines the alias.
  - `alias of ...` is shown only when there's no doc comment, which is the "docs instead of the default text" behaviour you asked for.
- **Behaviour change:** a same-module alias that has a doc comment (`Alias = Foo` followed by a docstring) no longer gets `alias of ...` appended after the docstring.
- **Test added:** `test_class_alias_having_doccomment`, with a `PathAlias` fixture in `tests/roots/test-ext-autodoc/target/classes.py`.

Not covered: Python 3.6 and your exact `file.py`. The rehearsal log and scaffold are in `.rehearsal/` for you to delete when you like.