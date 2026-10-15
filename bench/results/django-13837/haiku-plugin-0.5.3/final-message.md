`get_child_arguments()` now detects `python -m <package>` from `__main__.__spec__.parent` instead of only `-m django`. The autoreload test module passes (79 run, OK, 20 skipped), but I could not run a real `python -m <non-django package> runserver` end to end.

**Rehearsal size:** full. The rehearsal log is at `.rehearsal/REHEARSAL.md`.

**The change** (`django/utils/autoreload.py`):
- Removed the `django.__main__.__file__` comparison.
- If `__main__.__spec__` is set and its `parent` is non-empty, the child is re-run as `-m <parent>`. This covers `-m django` and any other package.
- Everything else is unchanged: `-W` options, the `.exe` and `-script.py` fallbacks, and the final `sys.argv` fallback.

**Tests** (`tests/utils_tests/test_autoreload.py`):
- `test_run_as_module` and `test_python_m_django` now set `__main__.__spec__` with parent `'django'` instead of relying on the path.
- Added `test_run_as_non_django_module` (parent `'utils_tests'` gives `-m utils_tests`).
- Added `test_run_as_script` (spec `None` gives the script path).

**What the rehearsal showed:**
- Under `python -m json.tool`, `__main__.__spec__.parent` is `'json'`, and under `-m django` it is `'django'`. That matches the ticket's rule.
- I could not reproduce the original bug by running it. The testbed env is Python 3.6, where pdb has no `-m`. The base interpreter lacks `asgiref`. The guard also blocked writing a test package and overriding the module path. The pdb wrapper also reports a different `sys.argv` than a real `-m` launch, so I discarded that probe. The bug is confirmed by reading the code and the ticket, not by running it.

**Unverified risks:**
- A real `python -m <non-django pkg> runserver` is not run end to end.
- Running `python django/__main__.py runserver` by path now re-executes the file path rather than `-m django`. I expect it to work, but I did not run it.

**Note:** `tests/utils_tests/test_autoreload.py` changed on disk while I was working. I re-read the region before editing and kept the change.

I did not commit anything.