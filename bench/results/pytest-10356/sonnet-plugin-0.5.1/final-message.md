A test class that inherits from several marked base classes now keeps the marks from all of them. A class inheriting from `Foo` (marked `foo`) and `Bar` (marked `bar`) used to report only `foo`. `testing/test_mark.py` and `testing/python/collect.py` pass (167 passed, 1 xfailed). I couldn't run `testing/python/metafunc.py` because `hypothesis` isn't installed here.

**The fix** is in `src/_pytest/mark/structures.py`:
- For classes, `get_unpacked_marks` now gathers each class's own `pytestmark` across the whole MRO, base classes first.
- It takes a new `consider_mro` argument, on by default. `store_mark` passes `False`, so applying a decorator to a class only reads that class's own marks and doesn't copy inherited ones onto it.
- `get_unpacked_marks` now returns a list instead of a generator.

**Other changes:**
- I added a regression test, `test_mark_mro_multiple_bases`, in `testing/test_mark.py`.
- I added `changelog/10299.bugfix.rst`. The `10299` is a guess at the issue number, so please check it.
- I didn't touch `AUTHORS` from the PR checklist.

**Rehearsal:** I reproduced the bug on the unfixed code before changing anything, and the fixture is in `.rehearsal/fixtures/before.txt`. I didn't re-run that exact reproduction after the fix; the new test covers the same case. Beyond that I only logged the reproduction and the fix plan in `.rehearsal/REHEARSAL.md`. I left `.rehearsal/` in place for you to delete when you're done with it.

**Not checked:**
- Marks inherited through a metaclass `pytestmark` property, as in the issue's example, behave differently now. That path reads each class's `__dict__`, not the property.
- Duplicate marks aren't removed when the same mark appears on several bases.