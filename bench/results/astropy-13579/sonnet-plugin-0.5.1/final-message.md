My change didn't cause the `test_time_cube` failure, so I'm keeping the fix.

- **Why it fails:** The test hits an expired leap-second file (`IERSStaleWarning`). The warning is turned into an error, and it happens with or without my change.
- **Baseline run:** The failing run the hook flagged was the one with my change stashed. The test failed on unmodified code.
- **With the fix:** The fix is back in place (`git diff` shows 3 insertions and 1 deletion in `sliced_wcs.py`). The `wcsapi` tests give 106 passed and 7 skipped, and `test_time_cube` is the only failure.

The sliced `world_to_pixel_values(0, 0)` for your example returns `(49.5, 12.)`, matching the full WCS.