Sweep results:

- **Callers:** the only ones are `src/_pytest/python.py:314` (classes and modules) and `:1717` (functions). Both read `self.obj`. Modules and functions still use the old path.
- **By-hand calls with non-class inputs:** `get_unpacked_marks(int)`, `get_unpacked_marks(len)` and `get_unpacked_marks(None)` all return `[]`, so the new class branch breaks nothing.
- **Real-collection check:** on the scaffold, `-m foo` still selects `TestDings::test_dings`. `-m bar` selected it after the fix.
- **Siblings:** `config/__init__.py:354` reads `method.pytestmark` directly, but only on functions to detect already-known marks, so MRO doesn't apply there. `terminal.py:1351` only looks at keyword names.

I found nothing else that needs fixing. The fix is complete and the earlier test results stand. I left `.rehearsal/` in place.