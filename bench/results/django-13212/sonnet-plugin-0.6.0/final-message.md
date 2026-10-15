The fix is done. The one failing test, `forms_tests.tests.tests.FormsModelTestCase.test_unicode_filename`, was already failing before my change, so there is nothing to undo.

I re-ran it on the original code (stashed my edits) and it fails the same way with `UnicodeEncodeError: 'ascii' codec can't encode characters`. The cause is the ASCII locale in this environment, not the validators. With my changes restored, the `validators` suite passes (20 tests), and the `forms_tests` and `model_forms` suites have no other failures.

The built-in validators now pass `params={'value': value}`, so a custom message can use `%(value)s`. `tests/validators/tests.py` has a new regression test, `test_value_in_params`.