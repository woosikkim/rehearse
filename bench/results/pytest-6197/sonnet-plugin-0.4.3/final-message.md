Fixed: pytest no longer imports a package's `__init__.py` during collection unless that file matches `python_files`.

**Cause.** `Package.collect` in `src/_pytest/python.py` called `self._mount_obj_if_needed()` first, and that call imports the package's `__init__.py`. That is why your `assert False` in `foobar/__init__.py` blew up. The fix removes the call. `Package.setup` already loads the module lazily through `self.obj` when setup/teardown functions need it.

**Verification.**
- The new regression test `test_does_not_eagerly_collect_packages` in `testing/test_collection.py` fails without the fix and passes with it.
- I ran `test_collection.py`, `test_pytester.py` and `python/collect.py`. Four tests fail in that run. They fail the same way with my change stashed, so they aren't caused by it.
- I added a changelog entry, `changelog/6194.bugfix.rst`. I guessed the issue number 6194, so rename the file if it's wrong.

**Reproduction.** The rehearsal guard blocked creating `.py` files from the shell, so I never ran your exact `tox` reproduction. The regression test builds the same layout instead: a package whose `__init__.py` is `assert False`, plus one passing test.

I haven't run the rest of the test suite. The rehearsal log is in `.rehearsal/REHEARSAL.md`.