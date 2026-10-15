I added direct ITRS↔AltAz and ITRS↔HADec transforms, and the new geometry test passes. The wider coordinates suite has 5 more failures than before my change, and I haven't worked out why.

**The bug:** a point 1 km along +z from an observer at latitude 30° came out at altitude 23°27′ through the old route. Geometry says 30°00′. With the new transforms it is exactly 30°00′00″.

**What changed:**
- **New transforms:** `astropy/coordinates/builtin_frames/itrs_observed_transforms.py` is your proposed code with an unused `erfa` import removed. It is registered in `builtin_frames/__init__.py`. There is no refraction yet, as in your draft.
- **New test:** `test_itrs_topocentric_overhead` covers the altitude check, time-invariance across obstimes, `dec` = 90° for HADec, and the round trip back to ITRS.
- **Loosened test:** in `test_gcrs_altaz_bothroutes` I loosened the Sun comparison to `rtol=1e-5`. The new topocentric route and the route through ICRS now differ by about 1.6e-6 relative. That is the geocentric-versus-topocentric aberration you describe, but the test itself fails on the IERS error below, so the loosened tolerance has not passed yet.

**Test results:**
- **Baseline:** the full `astropy/coordinates` suite has 5 failures and 85 errors before my change. These are IERS and environment problems.
- **With my change:** 10 failures and the same 85 errors. The 5 extra are all `test_gcrs_altaz_bothroutes[testframe0–4]`.
- **The error:** they fail with `TypeError: Time - float` inside the IERS lookup (`iers.py:271`), on the ICRS route at line 428, before the loosened comparison runs.
- **Unexplained:** on baseline, `testframe0` fails the same way but the other four pass. I don't know why my change makes all five fail. Outside pytest the same comparison runs fine and gives the 1.6e-6 difference.

I haven't investigated further. I can dig into why the extra four fail if you want.

**Not done:**
- No changelog entry or docs update.
- No check of the old geocentric `test_straight_overhead()` workaround. It lives in the same test file, and its result is part of the full-suite run above.

The rehearsal log is in `.rehearsal/REHEARSAL.md`.