`python -m pkg runserver` now autoreloads for any package, not just `django`. `utils_tests.test_autoreload` passes (78 tests, 20 skipped). I haven't run the rest of the suite.

**The fix.** `get_child_arguments()` in `django/utils/autoreload.py` now uses `__main__.__spec__.parent`, as the ticket proposes. If the parent is non-empty, the child process is launched with `-m <parent>`. A script, a directory or a zipfile has a `None` or empty parent, so those still take the old paths. The code no longer reads `django.__main__.__file__`, so it doesn't depend on `__file__` being set.

**What I ran by hand.** Before the change, simulating `-m mypkg` raised `RuntimeError: Script … does not exist`. After the change it returns `[python, '-m', 'mypkg', 'runserver']`. That was a simulation: I set `__main__.__spec__` and `sys.argv` in a one-line `python -c`, because the rehearse guard blocked writing a throwaway `mypkg/__main__.py`. I never launched a real `python -m pkg` process. I also never ran the empty-parent (directory or zipfile) case.

**Tests** in `tests/utils_tests/test_autoreload.py`:
- Mocked `__main__.__spec__` in the existing `-m django` tests.
- Added `test_run_as_non_django_module`.
- Pinned `__spec__` to `None` in `test_warnoptions`.

The rehearsal log is in `.rehearsal/REHEARSAL.md` (I left it in place), and the marker is removed.