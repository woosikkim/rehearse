The one failing test was already failing before my change, so the fix is done and no test regressed.

**Test results**
- Clean HEAD: `Ran 873 tests`, `FAILED (errors=1, skipped=1)`. The error is `test_unicode_filename`.
- Working tree: `Ran 874 tests`, `FAILED (errors=1, skipped=1)`. Same error. The extra test is the new `test_validators_message_value`, which passes.
- `test_unicode_filename` fails with `UnicodeEncodeError: 'ascii' codec` inside `os.stat`. This is the environment's filesystem encoding, not validator code. I did not fix it; it isn't in scope and it isn't mine to change.

**Changes still in place**
- `django/core/validators.py`: validators pass `value` into `ValidationError` params, and the IDN URL retry reports the original input. Details are in my previous report.
- `tests/validators/tests.py`: new regression test for Email and URL messages.

**Not done**
- `FileExtensionValidator` still doesn't pass `value`, deliberately, because it receives a file object.
- `test_unicode_filename` still fails in this environment because of the filesystem encoding.

I removed the temporary worktree I used for the clean-HEAD comparison. `.rehearsal/` remains as the log.