The sweep found nothing else to fix.

- **Edge cases:** I checked three shapes by hand. A single non-list `pytestmark` on a base class is collected correctly. `store_mark` on a subclass stores only its own mark, so inherited marks aren't copied onto it. A non-class object (`len`) still returns `[]`.
- **Other `pytestmark` users in `src`:** `terminal.py` (lines 1345 and 1351) and `config/__init__.py:354` only read the attribute. They don't collect marks from base classes, so they don't need the same change.

The fix and tests stand as reported.