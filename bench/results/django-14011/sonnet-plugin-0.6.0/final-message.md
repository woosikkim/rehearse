The sweep is done. It found one sibling I left alone and no new failures in the code I changed.

- **Search:** `process_request_thread`, `daemon_threads` and `ThreadingMixIn` appear only in `django/core/servers/basehttp.py` and `django/test/testcases.py`. `ThreadedWSGIServer`'s only other user is `tests/servers/test_liveserverthread.py`, which passes.
- **Checked by hand:** `ThreadedWSGIServer.daemon_threads` is still `True`. `LiveServerThreadedWSGIServer.daemon_threads` is `False`, and `LiveServerThread` uses it. I also confirmed it inherits the new `process_request_thread` that closes connections.
- **Sibling left alone:** `basehttp.run(threading=True)`, which `runserver` uses, builds its own threaded class. That class doesn't get the connection-closing `process_request_thread`, so `runserver` request threads still don't close their connections. I left it because `runserver` is long-lived and isn't what the ticket is about. Say if you want it routed through `ThreadedWSGIServer` too.

The race still isn't reproduced on a database that enforces connection limits, such as Postgres. I haven't added a regression test either. The sweep is logged in `.rehearsal/REHEARSAL.md`.