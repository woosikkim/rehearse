`get_child_arguments` now relaunches with `-m <pkg>` for any package started with `python -m`, not just `django`. The `utils_tests.test_autoreload` suite passes (79 tests, 20 skipped).

**Change**
- In `django/utils/autoreload.py`, `get_child_arguments` reads `__main__.__spec__.parent`. If it's non-empty, the child gets `-m <parent>` followed by the original args.
- Directory and zip launches have an empty parent, so they take the existing script-path branches. It no longer uses `django.__main__.__file__`.
- In `tests/utils_tests/test_autoreload.py`, `test_python_m_django` now mocks `__spec__` instead of `__file__`. I added tests for a non-django package and for a directory/zip launch.

**Not verified**
- **Real launch:** I never ran `python -m somepkg runserver` end to end. The rehearsal guard blocked me from writing a throwaway package, so I reproduced the old behaviour by setting `sys.argv` by hand (it raised `RuntimeError: Script … does not exist`). The new behaviour is covered only by the mocked-`__spec__` tests.
- **Lint:** flake8 isn't installed in the environment, so I haven't linted the new code.

**Sweep:** nothing else under `django/` references `get_child_arguments` or `django.__main__`. Its only caller is `restart_with_reloader`, which the updated test covers.

The rehearsal log is in `.rehearsal/REHEARSAL.md`.