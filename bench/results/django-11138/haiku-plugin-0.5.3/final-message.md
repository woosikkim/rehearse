I fixed the ticket's bug in the MySQL, SQLite and Oracle backends, but I only verified SQLite against a live database. MySQL and Oracle are checked only through the generated SQL, since no servers are available here.

**What was wrong:** the connection's `TIME_ZONE` was never read when converting stored datetimes for date lookups. MySQL and Oracle hardcoded `'UTC'` as the source zone, and SQLite treated stored values as UTC. So a `__date` lookup on a Paris-stored value near midnight gave the wrong date. Reproduced: SQLite returned `2017-07-07` for a stored `2017-07-06 23:30:00` in a Paris database.

**Changes:**
- **MySQL** (`django/db/backends/mysql/operations.py`): the source zone is now `self.connection.timezone_name`, and no `CONVERT_TZ` is emitted when source and target match. This is the ticket's second point, so no timezone tables are needed in that case.
- **SQLite** (`django/db/backends/sqlite3/base.py`, `operations.py`): the four `django_datetime_*` functions take the connection's zone as an extra argument and read stored naive values in it. I used `localize` rather than `replace` to avoid pytz's LMT offset.
- **Oracle** (`django/db/backends/oracle/operations.py`): `FROM_TZ` uses the connection's zone instead of `'0:00'`.

**Verification:**
- MySQL SQL generation for three zone combinations matches the hand-written expectations (e.g. `DATE(t.dt)` when both zones are Paris).
- SQLite functions return the corrected dates (`2017-07-06` for the Paris case, `2017-07-07` for a UTC database).
- Django suites `db_functions.datetime`, `annotations`, `expressions`, `lookup` and `aggregation_regress` pass on SQLite (346 tests).
- Four failures in `timezones` and `queries` also occur on the untouched code (checked with `git stash`), so I did not touch them.
- Not run: MySQL and Oracle against a live server. The Oracle change follows the same pattern as MySQL but is untested.

The rehearsal log and fixtures are in `.rehearsal/`. I left them in place; delete them when you're done with them. I did not commit anything.