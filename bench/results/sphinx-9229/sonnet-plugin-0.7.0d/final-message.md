I've changed autodoc so that a class alias with a doc comment (like `Bar = Foo` followed by a `"""..."""` string) shows that comment instead of "alias of ...". I couldn't reproduce your exact symptom, where the docstring is dropped and only "alias of ..." appears. The 163 autodoc tests pass, but I didn't add a test for the new behaviour.

**What I reproduced:** I rebuilt your three aliases with the real `sphinx` on Python 3.9. All three docstrings showed up. On this Python the typing aliases are generic aliases, not classes, so they take a different code path. Your Python 3.6 setup probably took the class path. I couldn't run 3.6, so I haven't confirmed that.

**What I did find:** a plain class alias with a doc comment (`Bar = Foo`) showed the comment and then an extra "alias of file.Foo" line. The class-alias code path always forces that line in.

**The fix**, in `sphinx/ext/autodoc/__init__.py` (`ClassDocumenter`):
- A new `get_variable_comment()` looks up the doc comment for the alias.
- When a comment exists, `get_doc()` returns an empty list so the class's own docstring isn't mixed in.
- When a comment exists, `add_content()` skips the "alias of ..." line.

After the change, `Bar` renders as just "Doc of Bar alias."

**Not verified:**
- Python 3.6 aliases. This is the main gap.
- A class alias in a different module from the one being documented. I only tried the same-module case.
- Whether the comment still renders when `autodoc_inherit_docstrings` is off.

The rehearsal log and scaffold are in `.rehearsal/`.