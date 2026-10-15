I fixed it for aliases of classes. I couldn't run the exact `Dict[...]`/`Union[...]` module from your report. All 165 autodoc tests pass, including two new ones.

**Cause.** When an alias points at a class, autodoc builds its source analyzer from the class's own module. For `IntAlias = int` that module is `builtins`, so the comment next to the alias is never found and only `alias of …` shows. An alias of a class defined in the same module already worked.

**Fix.** In `ClassDocumenter.add_content` (`sphinx/ext/autodoc/__init__.py`), when the class is documented as an alias, I switch the analyzer to the module that defines the alias. The docstring is then shown above `alias of …`.

**Tests.** I added `OtherAlias` and `IntAlias` to `tests/roots/test-ext-autodoc/target/classes.py`. I also added two tests in `tests/test_ext_autodoc_autoclass.py`. `IntAlias` is the one that failed before the fix. `OtherAlias` already passed.

**Not verified.**
- I tested on Python 3.9, where `Dict[str, Any]` and `Union[...]` aren't classes. They go through a different code path, and the existing `#:` generic-alias test passes there. Your Python 3.6 environment treats them as classes, which is why this fix should apply to your case.
- I never ran your exact `file.py`. The rehearsal guard blocked me from writing a new test module by shell, so I used the repo's test fixtures instead.

The log and fixtures are in `.rehearsal/`.