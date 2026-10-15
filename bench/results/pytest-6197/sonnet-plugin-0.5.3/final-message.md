Fixed: pytest no longer imports `__init__.py` files that don't match `python_files`. The new regression test fails without the fix and passes with it.

**Cause.** `Package.collect()` in `src/_pytest/python.py` called `self._mount_obj_if_needed()` first. That imported the package's `__init__.py` even when it wasn't a test file. I removed that call. `Package.setup()` still imports the package through `self.obj` when a package's `__init__.py` is actually collected as a test module, so `setup_module` support is unchanged.

**Tests.**
- **Regression test:** I added `test_does_not_eagerly_collect_packages` to `testing/test_collection.py`. It uses a package whose `__init__.py` is `assert False`.
- **Other failures:** `testing/test_collection.py` and `testing/python` have 7 other failures (e.g. `test_import_prepend_append` and several in `fixtures.py`). They fail the same way with my change stashed, so they look unrelated, but I didn't look into why.
- **Not run:** `testing/python/metafunc.py` needs `hypothesis`, which isn't installed, so I skipped it.

**Rehearsal.** I couldn't reproduce the original failure by hand. The rehearse guard blocks creating a `.py` file that does `assert False`. My one live run, on `src/_pytest/_code`, imports cleanly and shows nothing. The diagnosis rests on reading the code and your report's output, and the regression test is the actual reproduction. The `.rehearsal/` directory is still in the repo for you to delete.

I also added `changelog/6194.bugfix.rst`. I picked the number 6194 from memory of the upstream fix, so check it against the real issue or PR number.