You're right: rotating `SECRET_KEY` with the old value in `SECRET_KEY_FALLBACKS` logs out session users. The docs say the fallbacks cover sessions, and they don't.

**What I checked, by running the real code:**
- `salted_hmac` uses `settings.SECRET_KEY` unless you pass `secret=`.
- `AbstractBaseUser.get_session_auth_hash()` (`django/contrib/auth/base_user.py:134`) calls it without `secret=`, so the session hash depends only on the current key.
- With `SECRET_KEY="new"` and `SECRET_KEY_FALLBACKS=["old"]`, the session hash matches the new key and does not match the old one.
- `get_user()` (`django/contrib/auth/__init__.py:200-209`) compares the stored hash with the current `get_session_auth_hash()` only. A session created under the old key fails and is flushed.

**What does work with fallbacks:** password reset tokens (`tokens.py:32`) and signed cookie/signing data (`signing.py:197`). That's why the docs look right for those cases.

**So the docs are wrong for sessions.** The settings reference (`docs/ref/settings.txt`, around line 2305) says fallbacks cover "sessions, password reset tokens, and so on", and `docs/topics/auth/default.txt:964` says rotation keeps sessions valid. Neither holds for the auth session hash.

**Fix options (I haven't made any changes):**
1. **Code fix:** make `get_user()` and `login()` accept a hash computed with any key in `[SECRET_KEY, *SECRET_KEY_FALLBACKS]`. This is the behaviour the docs describe, but it changes core auth verification, so it needs a decision.
2. **Docs fix:** state that rotating `SECRET_KEY` still logs out session users, and that fallbacks don't cover that check. This is the smaller change and matches the current code.

Tell me which one you want and I'll make it. I'd lean towards the code fix, since the docs already promise it.

**Rehearsal notes:**
- The rehearsal log is at `.rehearsal/REHEARSAL.md`. The bare `python3` had no `asgiref`, so I created `.rehearsal/venv` with `asgiref` and `sqlparse`. It's in the repo as an untracked directory; delete it when you're done.
- I did not run a full request through `get_user()` with a live session store. The result rests on the source and the hash probe.