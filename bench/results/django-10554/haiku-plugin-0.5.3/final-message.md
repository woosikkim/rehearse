I couldn't reproduce the ticket's failure on this checkout, so I made no code change and added no regression test.

**What I ran**
- **SQLite:** can't run ordered union operands at all, and forcing the compound-query flags doesn't get around it. The existing combinator tests pass (26 run, 2 skipped).
- **PostgreSQL:** I started a project-local server and ran the ticket's sequence with `Permission`, `Tag` and `ReservedName` (which has an `order` field). Each variant was re-evaluated after the derived `order_by().values_list(...)` call, including the sliced `qs[:21]` form `repr` uses. None raised an error, and the original queryset's query attributes and SQL were unchanged.

**What I ruled out**
- The shared-state mutation that the HEAD commit (#30572) fixes is present and handled.
- The ticket's `ORDER BY (4)` never appeared in any shape I tried, with or without a Meta ordering on the model.

**What would settle it**
- The ticket's exact `Dimension` model definition (its `Meta.ordering` and the `order` field), and the Django and PostgreSQL versions. The traceback is from Python 3.6, so the ticket predates this checkout. I believe the ticket is #30628, but I haven't verified that.
- With those, I can rerun the same sequence and either reproduce it and fix it with a regression test, or confirm it's already fixed.

**Left in place**
- `.rehearsal/` holds the log (`REHEARSAL.md`), a project-local venv with Django installed in editable mode, and the `pgdata` directory from the Postgres run. Nothing outside `.rehearsal/` changed. Delete `.rehearsal/` when you no longer need it.