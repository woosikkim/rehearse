That failure isn't caused by my change. With the change in place and a UTF-8 locale (`LC_ALL=C.UTF-8`), all 1269 tests in `validators`, `forms_tests`, `model_fields` and `model_forms` pass (6 skipped).

`test_unicode_filename` fails because the sandbox's default locale is ASCII. It raises `UnicodeEncodeError` in `os.stat`, which has nothing to do with validators. It failed the same way on the original code when I stashed my change, which is the run the hook flagged.

The fix stands: the built-in validators in `django/core/validators.py` now pass `params={'value': value}` to `ValidationError`.