I swept the siblings and callers of `get_unpacked_marks`. Nothing else needed fixing.

Each check was a by-hand call:
- **Subclass of a marked base** (`foo` on `B`, `bar` on `C(B)`): returns `[bar, foo]` with no duplicates. With `consider_mro=False` it returns `[bar]`.
- **Class whose `pytestmark` is a single mark rather than a list:** returns `[foo]`.
- **Plain function** (`len`): returns `[]`.
- **Other `pytestmark` uses in `src`:**
  - `terminal.py:1351` only looks at keywords.
  - `config/__init__.py:354` reads functions.
  - Neither is affected by the change.
- **Callers:** `python.py:314`, `python.py:1717` and `store_mark` all pass in the existing mark tests (463 passed).

I logged the sweep in `.rehearsal/REHEARSAL.md`.