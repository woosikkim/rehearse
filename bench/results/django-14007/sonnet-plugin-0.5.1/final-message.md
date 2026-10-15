The failure the hook flagged was my deliberate check: I stashed the fix to confirm the new `test_create` fails without it. It did, as intended. It wasn't a regression from my change.

The fix is restored (`compiler.py` shows as modified) and the latest run of `custom_pk`, `from_db_value`, `bulk_create` and `basic` passes: 110 tests, OK, 10 skipped. The earlier broader run of 941 tests also passed.

The `bulk_create` regression test is skipped on SQLite, since it can't return rows from bulk insert. I haven't run it against PostgreSQL, MariaDB or Oracle.