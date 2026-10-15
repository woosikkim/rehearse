I've added direct ITRS ↔ AltAz and ITRS ↔ HADec transforms, using the code from your issue. A point 100 m straight above a site now comes out at alt 89°50′ instead of 8°55′ (the small offset from 90° is geodetic versus geocentric vertical).

In the `astropy/coordinates` tests, the same tests fail now as before my change, so no new failures. The leftover failures are the ones that already failed before: expired leap-second and IERS data, and `test_straight_overhead` when run alone. I did not run the rest of the astropy test suite.

- **What I added:** a new file, `astropy/coordinates/builtin_frames/itrs_observed_transforms.py`, with your code plus a docs changelog entry. It is imported in `builtin_frames/__init__.py` so the transforms register.
- **Before:** the old route returned alt 8°55′ for a point 100 m overhead at the same `obstime`, and −7°40′ when `obstime` was a day later. This is the problem described in the issue.
- **After:** the same point gives alt ≈ 89°50′ and HA 0, whatever `obstime` is. An AltAz → ITRS round trip returns the original position exactly.
- **Test changes:** `test_gcrs_altaz_bothroutes` now allows `rtol=1e-5` (and `atol=1 km` for the moon). The ICRS route applies aberration and the direct ITRS route doesn't, so the two now differ by about 1e-6 relative. I added `test_itrs_straight_overhead`, which checks alt = 90°, HA = 0, a round trip, and `obstime` values of `t`, `t + 1 day` and `None`.
- **Refraction:** not included, as in your draft.
- **`ITRS → ITRS` transform:** I left it unchanged.

Rehearsal log and the "before" fixture are in `.rehearsal/`. I left them in place.

Should I now open the pull request, or do you want to review the diff first?