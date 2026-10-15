# Rehearsal: autodoc alias docstring
### S1: build scaffold project with 3 aliases (cmd: python -m sphinx -b text .rehearsal/scaffold/proj .rehearsal/out)
- saw: docstring shown, then "alias of ..." appended for Dict/Union/Callable aliases
- means: DataDocumenter.add_content always calls update_content; a docstring-comment should replace the default
repro: /opt/miniconda3/envs/testbed/bin/python -m sphinx -q -E -b text .rehearsal/scaffold/proj .rehearsal/out
### S2: replay with exact issue docstrings on unmodified HEAD
- saw: all three docstrings render; "alias of ..." is appended after each. Not ignored.
- my edit (skip alias when a comment exists) broke 8 existing tests that expect docstring + "alias of" (test_autodata_GenericAlias etc.), so it was reverted.
