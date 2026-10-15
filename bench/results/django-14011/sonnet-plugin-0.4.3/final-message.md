`ThreadedWSGIServer` now closes the database connections of each request thread, so they no longer pile up and block `destroy_test_db()`. I didn't reproduce the original "database is being accessed by other users" error. It's a race that mainly shows up on PostgreSQL. After the change, `servers`, `handlers` and `requests` pass (136 tests, 1 skipped), but no test checks the closing itself. I didn't add one.

- **Cause:** `LiveServerThread.run()` only closed the connections belonging to the server thread. The per-request threads that `ThreadingMixIn` spawns each opened their own connection and never closed it.
- **`django/core/servers/basehttp.py`:** `ThreadedWSGIServer` now takes a `connections_override` argument. It applies that override in `process_request_thread` and calls `connections.close_all()` in `close_request`.
- **`django/test/testcases.py`:** `LiveServerThread._create_server()` now takes `connections_override` and passes it to the server. `run()` no longer sets the override on the server thread itself.
- **Tests:** the two `_create_server` overrides in `tests/servers/tests.py` now accept the new argument.

Two behaviour changes to know about:

- A custom `server_class` that isn't a `ThreadedWSGIServer` subclass must now accept `connections_override`.
- A single-threaded server no longer gets the shared in-memory SQLite connections. The existing single-thread test doesn't touch the database, so it still passes.

I left `.rehearsal/` in place with the log.