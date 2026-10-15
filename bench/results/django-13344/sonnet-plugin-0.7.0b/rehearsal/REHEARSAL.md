## Repro
SecurityMiddleware lacked _async_check(); chain was sync under is_async=True (False before fix, True after).
repro: /opt/miniconda3/envs/testbed/bin/python -c 'import asyncio; from django.conf import settings; settings.configure(SECRET_KEY="x", ROOT_URLCONF="tests.urls", MIDDLEWARE=["django.middleware.security.SecurityMiddleware"]); import django; django.setup(); from django.core.handlers.base import BaseHandler; h=BaseHandler(); h.load_middleware(is_async=True); print(asyncio.iscoroutinefunction(h._middleware_chain))'
