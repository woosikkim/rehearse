`bad-name-rgxs` now accepts regexes with commas inside braces, so `(foo{1,3})` parses as one pattern instead of crashing. I ran `tests/config` and `tests/test_self.py` and they pass (213 passed, 1 skipped, 1 xfailed).

**Cause:** The option was split on every comma, so `(foo{1,3})` became `(foo{1` and `3)`, and compiling the first piece failed.

**Fix:**
- **New splitter:** I added `_check_regexp_csv` in `pylint/utils/utils.py`. It splits on commas only when they are outside `{...}`, so quantifiers like `{1,3}` survive. It is exported from `pylint/utils/__init__.py`.
- **Where it is used:** Both regex-list transformers in `pylint/config/argument.py` now call it. `--bad-names-rgx` and the regex-path option (`ignore-paths`) use it.

**Checked by hand:**
- Before the fix, `(foo{1,3})` raised the error from the report.
- After the fix, `(foo{1,3})` gives one pattern.
- After the fix, `(foo{1,3}),bar, a{2}` gives three patterns.

**Test change:** `test_csv_regex_error` in `tests/config/test_config.py` expected the mangled `(foo{1` error. I changed it to use a genuinely invalid regex, `(foo{1,3}`. I also added `test_csv_regex_comma_in_quantifier`, which checks that `(foo{1,3}),bar` is accepted.

**Not covered:**
- A comma inside a character class (`[a,b]`) or a group (`(a,b)`) is still split. The report asked for braces only, and there is no escape syntax for commas.
- I didn't run the whole test suite.

The rehearsal log is in `.rehearsal/REHEARSAL.md`.