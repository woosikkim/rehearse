The CDS unit parser now reads composite units in the right order, so the reporter's table gives `1000 J / (kpc2 m s)` and `1e-07 J / (kpc2 s)`. The fix is in `astropy/units/format/cds.py`.

**Cause:** the division rule in the CDS grammar was right-recursive. `J/m/s/kpc2` was grouped as `J / (m / (s / kpc2))`, which is why the terms came out in the wrong place.

**Fix:** everything after the first `/` is now in the denominator, so `J/m/s/kpc2` is `J / (m s kpc2)`. The grammar change is a new `denominator_of_units` rule. `cds_parsetab.py` was regenerated because ply reuses a stale table when `optimize=True`.

**Verified:**
- The reporter's MRT file, read with `Table.read(..., format="ascii.cds")`, now gives the expected units.
- Hand-checked variants come out right: `J/s/kpc2`, `J.m/s/kpc2`, `J/m.s` (unchanged), `m/s/kg/K`, `J/s`.
- A CDS write-then-read round trip on a composite unit gives an equal unit.
- I added three cases to `test_cds_grammar` in `astropy/units/tests/test_format.py`.
- `test_format.py` and `test_cds.py` pass: 744 tests.

**Not fixed by me:** 17 tests in `test_quantity_array_methods.py` and `test_quantity_non_ufuncs.py` fail. They fail the same way on the untouched code, so they are pre-existing and unrelated to this change.

**Not done:** no changelog fragment, since I don't have the PR number. The rehearsal log is at `.rehearsal/REHEARSAL.md`, and the guard marker has been removed.