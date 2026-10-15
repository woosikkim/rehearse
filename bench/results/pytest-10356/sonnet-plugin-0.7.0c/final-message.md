Marks from every base class are now collected, so `TestDings(Foo, Bar)` carries both `foo` and `bar`.

The rehearsal log is in `.rehearsal/REHEARSAL.md` and I left it in place.

- **Reproduced first:** with the `Foo`/`Bar`/`TestDings` example, `-m bar` deselected the test and `-m foo` selected it. After the fix, `-m bar` collects it.
- **Fix:** in `src/_pytest/mark/structures.py`, `get_unpacked_marks` now walks the class's MRO and reads each class's own `pytestmark` from its `__dict__`. A new `consider_mro` argument (default `True`) turns that off. The marks come back as a list, base classes first.
- **`store_mark`:** it now passes `consider_mro=False`. Without that, applying `@pytest.mark.x` to a subclass would copy its parents' marks onto it.
- **Callers:** the two callers in `src/_pytest/python.py` get the new behaviour without changes. Function marks are unaffected because functions aren't classes.
- **Tests:** I added `test_mark_mro` to `testing/test_mark.py`, plus a changelog entry. The changelog file `changelog/10299.bugfix.rst` uses `10299` as a guessed issue number, so please check it. I haven't added an `AUTHORS` entry.
- **Test results:** `testing/test_mark.py`, `test_skipping.py` and `python/collect.py` give 259 passed, 1 xfailed.

`testing/python/metafunc.py` fails at collection, and it fails the same way with my change stashed, so I didn't investigate it. I didn't run the full test suite.