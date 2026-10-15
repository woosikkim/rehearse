I couldn't reproduce the bug on this checkout, so I made no code change.

I built a small docs project using your three aliases and the docstrings from your example. I ran it through the real `sphinx-build` with `sphinx.ext.autodoc` (text builder). All three docstrings render. `ScaffoldOpts`, `FileContents` and `FileOp` each show their full text, including the `::` literal block and the `.. note::`. After each docstring, Sphinx adds an `alias of ...` line.

- **Missing docstrings:** your report was on Sphinx 3.1.2. In this repo (Python 3.9), autodoc already reads `"""` comments under type aliases and shows them.
- **The `alias of ...` line:** you expected the docstring to replace this text, but it is added after the docstring. The existing tests expect exactly this. For example, `test_autodata_GenericAlias` expects `A list of int` followed by `alias of ...`, and so do the NewType, TypeVar and `autoattribute` tests.
- **What I tried:** I made autodoc skip the `alias of` line whenever an alias has a docstring comment, in both `DataDocumenter` and `AttributeDocumenter`. The output looked right on your example. But it broke 8 existing tests, and the tests passed again once I reverted. I took that as a sign that the current output is intended, so I reverted the edit.
- **A separate oddity:** with `:undoc-members:`, aliases with no docstring comment don't appear at all in my test project. I haven't looked into that.

Decision for you: if you want the docstring to replace `alias of ...`, say so. The change is about three lines, but I'd also update those 8 tests, so it changes documented behaviour.

I left the rehearsal log and the test project in `.rehearsal/`.