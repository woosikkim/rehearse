The direct ITRS↔AltAz/HADec transform is in place and the rehearsed cases pass. One existing test now fails because of the intended change, and that needs your decision before a PR.

**What changed**
- New `astropy/coordinates/builtin_frames/itrs_observed_transforms.py`: your sketch, with the `PIOVER2` import pointed at the local `.utils` module and the comments tidied.
- Registered it in `builtin_frames/__init__.py`. The graph picks the direct edge over the two-hop ITRS→CIRS→AltAz path.
- Appended `test_itrs_straight_overhead_direct` to `test_intermediate_transformations.py`. It checks Alt=90° at the same obstime and one hour later, HADec dec = site latitude, and an exact round trip.

**What the rehearsal showed**
- The current ITRS→AltAz path is obstime-sensitive. For a point straight overhead, it gives 86°19' at the same time and −5°35' one hour later. The new path gives 90° at both, and at `obstime=None`.
- The matrix applied by hand to the topocentric vector gives x≈0, y≈0, z≈10 km, which matches the replay.

**Test results** (run with `/opt/miniconda3/envs/testbed/bin/python`; the system `python3` lacks `erfa`)
- Five new failures: `test_gcrs_altaz_bothroutes[testframe0..4]`. It asserts that the Sun via ICRS and the Sun via ITRS agree at `rtol=1e-7`. The new direct edge deliberately skips the CIRS route, and the max difference is 5.8e-7. The test's expectation is now a choice you need to make: loosen the tolerance, or change the test to compare against the new route. I have not changed it. The Moon half of that test never runs because the Sun assertion fails first.
- `test_straight_overhead` fails with or without my change: `Time - float` inside the IERS code. The bundled leap-second file has expired (today is 2026-10-15). This is environmental, not caused by this change.
- The other baseline failures and the 85 errors are unchanged.

**Not done**
- Refraction is not included, as in your sketch.
- I did not answer whether maintainers will be receptive; that's for the issue thread.
- I did not commit.

The rehearsal log is in `.rehearsal/REHEARSAL.md`, with probe output in `.rehearsal/fixtures/`. I left it in place.