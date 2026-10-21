# Live cases

Three headless runs of the plugin against local, harmless fixtures (brief section 11): a first route blocked and a second
that works, a check the data cannot meet, and an exhausted search. They call a model, so they are run by hand, never in CI.

    tests/live/run.sh blocked-route      # also: check-wrong, exhausted
    python3 tests/live/check.py <case> <workdir>   # re-check a finished run

`run.sh` copies the case's `fixture/` into a work folder, runs `claude -p` there with this repo as the plugin
(`--plugin-dir`), the installed rehearse off for that run, Claude Code's sandbox on (writes stay in the work folder) and
`REHEARSE_HEADLESS=1`, then runs `check.py`, which reads the job file's mirror (`.rehearsal/<run>/state.json`), the run
folder's log and `report.md`, prints the evidence and one PASS/FAIL line per condition.

Do not edit this repo while a run is in progress: the hooks are loaded from it on every call.
