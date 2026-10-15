# Rehearsal: coroutine passed to first middleware process_response
### S1: read deprecation.py/base.py/exception.py/security.py
- saw: SecurityMiddleware.__init__ (and cache, redirects) override __init__ without get_response/_async_check, so no _is_coroutine marker; convert_exception_to_response wraps it as sync, so the middleware above gets a coroutine
- next: set get_response and call _async_check in those __init__s
