Autodoc now documents attributes inherited from base classes when `:inherited-members:` is set. The fix is in `get_class_members` in `sphinx/ext/autodoc/importer.py`.

**Cause:** that function only picked up `#:`-documented attributes defined in `__init__` when they belonged to the class being documented. For `Derived(Base)`, it looked up `("Derived", "attr")` in the analyzer's cache and never `("Base", "attr")`.

**Fix:** it now walks the class's MRO. For each class it loads that class's own module analyzer and adds documented attributes stored under that class's qualified name. This also covers base classes in other modules.

**Checked by running it:**
- `test_autodoc_typed_inherited_instance_variables` fails on the unmodified checkout. `Derived` was missing the documented attributes `attr4` and `attr5` from its base class. It passes with the fix.
- Across `tests/test_ext_autodoc*.py` and `tests/test_ext_autosummary.py`, 149 tests pass and 5 fail: `test_autodoc` plus four in `test_ext_autosummary.py`. My comparison against the unmodified checkout was inconclusive: its failure list printed identical to the post-fix one, which can't be right because the typed test failed on the baseline. I only confirmed `test_autodoc` and the first two autosummary failures on the baseline, so I haven't confirmed the other two.

**Not done:**
- I didn't add a new test. The existing test already covers the case.
- I didn't try a base class in a different module or a data attribute documented at class level.
- The `analyzer` and `objpath` parameters of `get_class_members` are now unused. I left them so the signature stays the same.

The rehearsal log is in `.rehearsal/REHEARSAL.md`, and I left it there.