`:inherited-members:` now documents inherited attributes, both class-level ones (`attr = 1  #: doc`) and instance ones (`self.attr = 1  #: doc`). I checked it with a small docs project, once with the base class in the same module and once in another module.

Tests: the new test and the rest of `tests/test_ext_autodoc_autoclass.py` pass (5 passed). Across the autodoc and autosummary test files, 5 tests fail (`test_autodoc` and four in `test_ext_autosummary.py`). They fail identically without my change. I didn't run the rest of the test suite.

**The cause:** the source-comment docs are stored under the class that defines them (`('Base', 'attr1')`), but autodoc looked them up under the class being documented (`('Derived', 'attr1')`), so they never matched.

**The fix:**
- **Member filter** (`sphinx/ext/autodoc/__init__.py`): with `:inherited-members:`, docs from base classes now count for the derived class, so inherited attributes are kept.
- **Doc lookup** (`Documenter.add_content`, same file): if the attribute has no docs under the current class, it searches the base classes in order and uses the first match.
- **Instance attributes** (`get_class_members` in `sphinx/ext/autodoc/importer.py`): `self.x` comments in base classes are now collected. They were never listed before.

Without `:inherited-members:`, the inherited attributes stay hidden, as before.

**Regression test:** `test_autodoc_inherited_members_attributes` in `tests/test_ext_autodoc_autoclass.py`, using a new `tests/roots/test-ext-autodoc/target/inherited_attrs.py`.

**Not covered:** `sphinx/ext/autosummary` has its own attribute-doc lookups (`generate.py`, `__init__.py`). I didn't change or test them, so inherited attributes there may still be missed.

The rehearsal log and scaffold are in `.rehearsal/`. I left them in place for you to delete.