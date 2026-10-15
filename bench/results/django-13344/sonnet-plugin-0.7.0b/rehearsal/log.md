$ ls .rehearsal; grep -n "process_response\|def adapt_method_mode\|_get_response_async\|convert_exception_to_response\|def load_middleware" -n django/core/handlers/base.py | head -40
active
fixtures
scaffold
15:from .exception import convert_exception_to_response
26:    def load_middleware(self, is_async=False):
36:        get_response = self._get_response_async if is_async else self._get_response
37:        handler = convert_exception_to_response(get_response)
88:            handler = convert_exception_to_response(mw_instance)
97:    def adapt_method_mode(
210:    async def _get_response_async(self, request):

$ grep -n "def convert_exception_to_response" -A40 django/core/handlers/exception.py
21:def convert_exception_to_response(get_response):
22-    """
23-    Wrap the given get_response callable in exception-to-response conversion.
24-
25-    All exceptions will be converted. All known 4xx exceptions (Http404,
26-    PermissionDenied, MultiPartParserError, SuspiciousOperation) will be
27-    converted to the appropriate response, and all other exceptions will be
28-    converted to 500 responses.
29-
30-    This decorator is automatically applied to all middleware to ensure that
31-    no middleware leaks an exception and that the next middleware in the stack
32-    can rely on getting a response instead of an exception.
33-    """
34-    if asyncio.iscoroutinefunction(get_response):
35-        @wraps(get_response)
36-        async def inner(request):
37-            try:
38-                response = await get_response(request)
39-            except Exception as exc:
40-                response = await sync_to_async(response_for_exception)(request, exc)
41-            return response
42-        return inner
43-    else:
44-        @wraps(get_response)
45-        def inner(request):
46-            try:
47-                response = get_response(request)
48-            except Exception as exc:
49-                response = response_for_exception(request, exc)
50-            return response
51-        return inner
52-
53-
54-def response_for_exception(request, exc):
55-    if isinstance(exc, Http404):
56-        if settings.DEBUG:
57-            response = debug.technical_404_response(request, exc)
58-        else:
59-            response = get_exception_response(request, get_resolver(get_urlconf()), 404, exc)
60-

$ cd /testbed/.rehearsal/scaffold && DJANGO_SETTINGS_MODULE=s python3 -c 'import asyncio, django; django.setup(); from django.test import AsyncClient; r=asyncio.run(AsyncClient().get("/")); print(r.status_code)' 2>&1 | tail -5
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'django'

$ cd /testbed && python3 - <<'EOF'
import asyncio
from unittest import mock
from django.conf import settings
settings.configure(SECRET_KEY='x',ROOT_URLCONF='tests.urls',ALLOWED_HOSTS=['*'],MIDDLEWARE=['django.middleware.common.CommonMiddleware','django.middleware.security.SecurityMiddleware'])
import django; django.setup()
from django.test import AsyncClient
from django.middleware.common import CommonMiddleware
p=mock.patch.object(CommonMiddleware,'process_response',autospec=True)
m=p.start()
r=asyncio.run(AsyncClient().get('/'))
print('ARGTYPE', type(m.call_args[0][2]))
EOF
echo; sed -n 97,140p django/core/handlers/base.py
Traceback (most recent call last):
  File "<stdin>", line 3, in <module>
  File "/testbed/django/conf/__init__.py", line 19, in <module>
    from django.core.validators import URLValidator
  File "/testbed/django/core/validators.py", line 9, in <module>
    from django.utils.deprecation import RemovedInDjango41Warning
  File "/testbed/django/utils/deprecation.py", line 5, in <module>
    from asgiref.sync import sync_to_async
ModuleNotFoundError: No module named 'asgiref'
    def adapt_method_mode(
        self, is_async, method, method_is_async=None, debug=False, name=None,
    ):
        """
        Adapt a method to be in the correct "mode":
        - If is_async is False:
          - Synchronous methods are left alone
          - Asynchronous methods are wrapped with async_to_sync
        - If is_async is True:
          - Synchronous methods are wrapped with sync_to_async()
          - Asynchronous methods are left alone
        """
        if method_is_async is None:
            method_is_async = asyncio.iscoroutinefunction(method)
        if debug and not name:
            name = name or 'method %s()' % method.__qualname__
        if is_async:
            if not method_is_async:
                if debug:
                    logger.debug('Synchronous %s adapted.', name)
                return sync_to_async(method, thread_sensitive=True)
        elif method_is_async:
            if debug:
                logger.debug('Asynchronous %s adapted.', name)
            return async_to_sync(method)
        return method
    def get_response(self, request):
        """Return an HttpResponse object for the given HttpRequest."""
        # Setup default url resolver for this thread
        set_urlconf(settings.ROOT_URLCONF)
        response = self._middleware_chain(request)

$ ls /opt/*/envs 2>/dev/null; conda env list 2>/dev/null; ls -d /testbed/.venv /opt/venv 2>/dev/null; which -a python python3
testbed
# conda environments:
#
base                     /opt/miniconda3
testbed               *  /opt/miniconda3/envs/testbed
/opt/miniconda3/bin/python
/usr/bin/python
/bin/python
/opt/miniconda3/bin/python3
/usr/bin/python3
/bin/python3

$ /opt/miniconda3/envs/testbed/bin/python - <<'EOF'
import asyncio
from unittest import mock
from django.conf import settings
settings.configure(SECRET_KEY='x',ROOT_URLCONF='tests.urls',ALLOWED_HOSTS=['*'],MIDDLEWARE=['django.middleware.common.CommonMiddleware','django.middleware.security.SecurityMiddleware'])
import django; django.setup()
from django.test import AsyncClient
from django.middleware.common import CommonMiddleware
p=mock.patch.object(CommonMiddleware,'process_response',autospec=True)
m=p.start()
r=asyncio.run(AsyncClient().get('/'))
print('ARGTYPE', type(m.call_args[0][2]))
EOF
Exit code 1
Traceback (most recent call last):
  File "<stdin>", line 10, in <module>
AttributeError: module 'asyncio' has no attribute 'run'
  -> keep_lazy() = <function keep_lazy.<locals>.decorator at 0x7f6eb1f08620>  [django/utils/functional.py:224]
  -> __proxy__() = None  [django/utils/functional.py:179]
  -> lazy(func=<function slugify at 0x7f6eb1f07bf8>) = <function slugify at 0x7f6eb1f086a8>  [django/utils/functional.py:191]
  -> decorator(func=<function slugify at 0x7f6eb1f07bf8>) = <function slugify at 0x7f6eb1f08f28>  [django/utils/functional.py:223]
  -> keep_lazy_text(func=<function slugify at 0x7f6eb1f07bf8>) = <function slugify at 0x7f6eb1f08f28>  [django/utils/functional.py:231]
  -> __proxy__() = None  [django/utils/functional.py:179]
  -> lazy(func=<function _format_lazy at 0x7f6eb1f0e048>) = <function _format_lazy at 0x7f6eb1f0e0d0>  [django/utils/functional.py:191]
  -> <module>() = None  [django/utils/text.py:425]
  -> SimpleLazyObject.__setattr__(name='_wrapped', value=<object object at 0x7f6eb3172340>) = None  [django/utils/functional.py:267]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:260]

$ /opt/miniconda3/envs/testbed/bin/python - <<'EOF'
import asyncio
from unittest import mock
from django.conf import settings
settings.configure(SECRET_KEY='x',ROOT_URLCONF='tests.urls',ALLOWED_HOSTS=['*'],MIDDLEWARE=['django.middleware.common.CommonMiddleware','django.middleware.security.SecurityMiddleware'])
import django; django.setup()
from django.test import AsyncClient
from django.middleware.common import CommonMiddleware
p=mock.patch.object(CommonMiddleware,'process_response',autospec=True)
m=p.start()
r=asyncio.get_event_loop().run_until_complete(AsyncClient().get('/'))
print('ARGTYPE', type(m.call_args[0][2]))
EOF
Exit code 1
Traceback (most recent call last):
  File "<stdin>", line 10, in <module>
  File "/opt/miniconda3/envs/testbed/lib/python3.6/asyncio/base_events.py", line 488, in run_until_complete
    return future.result()
  File "/testbed/django/test/client.py", line 897, in request
    response = await self.handler(scope)
  File "/testbed/django/test/client.py", line 192, in __call__
    response = await self.get_response_async(request)
  File "/testbed/django/core/handlers/base.py", line 148, in get_response_async
    response = await self._middleware_chain(request)
TypeError: object MagicMock can't be used in 'await' expression
  -> keep_lazy() = <function keep_lazy.<locals>.decorator at 0x7f41c65ee6a8>  [django/utils/functional.py:224]
  -> __proxy__() = None  [django/utils/functional.py:179]
  -> lazy(func=<function slugify at 0x7f41c65ecc80>) = <function slugify at 0x7f41c65ee730>  [django/utils/functional.py:191]
  -> decorator(func=<function slugify at 0x7f41c65ecc80>) = <function slugify at 0x7f41c65f0048>  [django/utils/functional.py:223]
  -> keep_lazy_text(func=<function slugify at 0x7f41c65ecc80>) = <function slugify at 0x7f41c65f0048>  [django/utils/functional.py:231]
  -> __proxy__() = None  [django/utils/functional.py:179]
  -> lazy(func=<function _format_lazy at 0x7f41c65f00d0>) = <function _format_lazy at 0x7f41c65f0158>  [django/utils/functional.py:191]
  -> <module>() = None  [django/utils/text.py:425]
  -> SimpleLazyObject.__setattr__(name='_wrapped', value=<object object at 0x7f41c7760340>) = None  [django/utils/functional.py:267]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:260]

$ /opt/miniconda3/envs/testbed/bin/python - <<'EOF' 2>&1 | tail -4
import asyncio
from unittest import mock
from django.conf import settings
settings.configure(SECRET_KEY='x',ROOT_URLCONF='tests.urls',ALLOWED_HOSTS=['*'],MIDDLEWARE=['django.middleware.common.CommonMiddleware','django.middleware.security.SecurityMiddleware'])
import django; django.setup()
from django.test import AsyncClient
from django.middleware.common import CommonMiddleware
mock.patch.object(CommonMiddleware,'process_response',new=print).start()
asyncio.get_event_loop().run_until_complete(AsyncClient().get('/'))
EOF
    response = await self.get_response_async(request)
  File "/testbed/django/core/handlers/base.py", line 148, in get_response_async
    response = await self._middleware_chain(request)
TypeError: object NoneType can't be used in 'await' expression
  -> keep_lazy() = <function keep_lazy.<locals>.decorator at 0x7f66da5ec6a8>  [django/utils/functional.py:224]
  -> __proxy__() = None  [django/utils/functional.py:179]
  -> lazy(func=<function slugify at 0x7f66da5eac80>) = <function slugify at 0x7f66da5ec730>  [django/utils/functional.py:191]
  -> decorator(func=<function slugify at 0x7f66da5eac80>) = <function slugify at 0x7f66da5ee048>  [django/utils/functional.py:223]
  -> keep_lazy_text(func=<function slugify at 0x7f66da5eac80>) = <function slugify at 0x7f66da5ee048>  [django/utils/functional.py:231]
  -> __proxy__() = None  [django/utils/functional.py:179]
  -> lazy(func=<function _format_lazy at 0x7f66da5ee0d0>) = <function _format_lazy at 0x7f66da5ee158>  [django/utils/functional.py:191]
  -> <module>() = None  [django/utils/text.py:425]
  -> SimpleLazyObject.__setattr__(name='_wrapped', value=<object object at 0x7f66db75f340>) = None  [django/utils/functional.py:267]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:260]

$ /opt/miniconda3/envs/testbed/bin/python - <<'EOF' 2>&1 | head -8
import asyncio
from unittest import mock
from django.conf import settings
settings.configure(SECRET_KEY='x',ROOT_URLCONF='tests.urls',ALLOWED_HOSTS=['*'],MIDDLEWARE=['django.middleware.common.CommonMiddleware','django.middleware.security.SecurityMiddleware'])
import django; django.setup()
from django.test import AsyncClient
from django.middleware.common import CommonMiddleware
mock.patch.object(CommonMiddleware,'process_response',new=print).start()
asyncio.get_event_loop().run_until_complete(AsyncClient().get('/'))
EOF
/testbed/django/utils/deprecation.py:119: RuntimeWarning: coroutine 'MiddlewareMixin.__acall__' was never awaited
  response = self.process_response(request, response)
<ASGIRequest: GET '/'> <coroutine object MiddlewareMixin.__acall__ at 0x7fbede2bf8e0>
Traceback (most recent call last):
  File "<stdin>", line 9, in <module>
  File "/opt/miniconda3/envs/testbed/lib/python3.6/asyncio/base_events.py", line 488, in run_until_complete
    return future.result()
  File "/testbed/django/test/client.py", line 897, in request
  -> keep_lazy() = <function keep_lazy.<locals>.decorator at 0x7fbedf5b46a8>  [django/utils/functional.py:224]
  -> __proxy__() = None  [django/utils/functional.py:179]
  -> lazy(func=<function slugify at 0x7fbedf5b2c80>) = <function slugify at 0x7fbedf5b4730>  [django/utils/functional.py:191]
  -> decorator(func=<function slugify at 0x7fbedf5b2c80>) = <function slugify at 0x7fbedf5b6048>  [django/utils/functional.py:223]
  -> keep_lazy_text(func=<function slugify at 0x7fbedf5b2c80>) = <function slugify at 0x7fbedf5b6048>  [django/utils/functional.py:231]
  -> __proxy__() = None  [django/utils/functional.py:179]
  -> lazy(func=<function _format_lazy at 0x7fbedf5b60d0>) = <function _format_lazy at 0x7fbedf5b6158>  [django/utils/functional.py:191]
  -> <module>() = None  [django/utils/text.py:425]
  -> SimpleLazyObject.__setattr__(name='_wrapped', value=<object object at 0x7fbee0727340>) = None  [django/utils/functional.py:267]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:260]

$ /opt/miniconda3/envs/testbed/bin/python - <<'EOF' 2>&1 | head -8
import asyncio
from django.conf import settings
settings.configure(SECRET_KEY='x',ROOT_URLCONF='tests.urls',ALLOWED_HOSTS=['*'],MIDDLEWARE=['django.middleware.common.CommonMiddleware','django.middleware.security.SecurityMiddleware'])
import django; django.setup()
from django.core.handlers.base import BaseHandler
h=BaseHandler()
h.load_middleware(is_async=True)
print(asyncio.iscoroutinefunction(h._middleware_chain), asyncio.iscoroutinefunction(h._middleware_chain.__wrapped__.get_response), type(h._middleware_chain.__wrapped__.get_response))
EOF
sed -n 1,60p django/core/handlers/exception.py | grep -n "wraps\|import"
False False <class 'function'>
1:import asyncio
2:import logging
3:import sys
4:from functools import wraps
6:from asgiref.sync import sync_to_async
8:from django.conf import settings
9:from django.core import signals
10:from django.core.exceptions import (
14:from django.http import Http404
15:from django.http.multipartparser import MultiPartParserError
16:from django.urls import get_resolver, get_urlconf
17:from django.utils.log import log_response
18:from django.views import debug
35:        @wraps(get_response)
44:        @wraps(get_response)
  -> keep_lazy() = <function keep_lazy.<locals>.decorator at 0x7f29686a5ea0>  [django/utils/functional.py:224]
  -> __proxy__() = None  [django/utils/functional.py:179]
  -> lazy(func=<function slugify at 0x7f29686a5510>) = <function slugify at 0x7f29686a5f28>  [django/utils/functional.py:191]
  -> decorator(func=<function slugify at 0x7f29686a5510>) = <function slugify at 0x7f29686a7840>  [django/utils/functional.py:223]
  -> keep_lazy_text(func=<function slugify at 0x7f29686a5510>) = <function slugify at 0x7f29686a7840>  [django/utils/functional.py:231]
  -> __proxy__() = None  [django/utils/functional.py:179]
  -> lazy(func=<function _format_lazy at 0x7f29686a78c8>) = <function _format_lazy at 0x7f29686a7950>  [django/utils/functional.py:191]
  -> <module>() = None  [django/utils/text.py:425]
  -> SimpleLazyObject.__setattr__(name='_wrapped', value=<object object at 0x7f296975a320>) = None  [django/utils/functional.py:267]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:260]

$ /opt/miniconda3/envs/testbed/bin/python - <<'EOF' 2>&1 | head -8
import asyncio
from django.conf import settings
settings.configure(SECRET_KEY='x',ROOT_URLCONF='tests.urls',ALLOWED_HOSTS=['*'],MIDDLEWARE=['django.middleware.security.SecurityMiddleware'])
import django; django.setup()
from django.core.handlers.base import BaseHandler
h=BaseHandler()
h.load_middleware(is_async=True)
print(asyncio.iscoroutinefunction(h._middleware_chain), type(h._middleware_chain))
print(asyncio.iscoroutinefunction(h._get_response_async))
EOF
False <class 'function'>
True
  -> keep_lazy() = <function keep_lazy.<locals>.decorator at 0x7f0ad14f2f28>  [django/utils/functional.py:224]
  -> __proxy__() = None  [django/utils/functional.py:179]
  -> lazy(func=<function slugify at 0x7f0ad14f2598>) = <function slugify at 0x7f0ad14f4048>  [django/utils/functional.py:191]
  -> decorator(func=<function slugify at 0x7f0ad14f2598>) = <function slugify at 0x7f0ad14f48c8>  [django/utils/functional.py:223]
  -> keep_lazy_text(func=<function slugify at 0x7f0ad14f2598>) = <function slugify at 0x7f0ad14f48c8>  [django/utils/functional.py:231]
  -> __proxy__() = None  [django/utils/functional.py:179]
  -> lazy(func=<function _format_lazy at 0x7f0ad14f4950>) = <function _format_lazy at 0x7f0ad14f49d8>  [django/utils/functional.py:191]
  -> <module>() = None  [django/utils/text.py:425]
  -> SimpleLazyObject.__setattr__(name='_wrapped', value=<object object at 0x7f0ad25a7320>) = None  [django/utils/functional.py:267]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:260]

$ sed -n 1,30p django/middleware/security.py
import re
from django.conf import settings
from django.http import HttpResponsePermanentRedirect
from django.utils.deprecation import MiddlewareMixin
class SecurityMiddleware(MiddlewareMixin):
    # RemovedInDjango40Warning: when the deprecation ends, replace with:
    #   def __init__(self, get_response):
    def __init__(self, get_response=None):
        self._get_response_none_deprecation(get_response)
        self.sts_seconds = settings.SECURE_HSTS_SECONDS
        self.sts_include_subdomains = settings.SECURE_HSTS_INCLUDE_SUBDOMAINS
        self.sts_preload = settings.SECURE_HSTS_PRELOAD
        self.content_type_nosniff = settings.SECURE_CONTENT_TYPE_NOSNIFF
        self.xss_filter = settings.SECURE_BROWSER_XSS_FILTER
        self.redirect = settings.SECURE_SSL_REDIRECT
        self.redirect_host = settings.SECURE_SSL_HOST
        self.redirect_exempt = [re.compile(r) for r in settings.SECURE_REDIRECT_EXEMPT]
        self.referrer_policy = settings.SECURE_REFERRER_POLICY
        self.get_response = get_response
    def process_request(self, request):
        path = request.path.lstrip("/")
        if (self.redirect and not request.is_secure() and
                not any(pattern.search(path)
                        for pattern in self.redirect_exempt)):
            host = self.redirect_host or request.get_host()
            return HttpResponsePermanentRedirect(

$ grep -rn "self.get_response = get_response\|super().__init__(get_response)" django | grep -v "deprecation.py"
django/middleware/security.py:22:        self.get_response = get_response
django/middleware/cache.py:73:        self.get_response = get_response
django/middleware/cache.py:135:        self.get_response = get_response
django/middleware/cache.py:177:        self.get_response = get_response
django/contrib/redirects/middleware.py:21:        super().__init__(get_response)
django/contrib/sessions/middleware.py:17:        self.get_response = get_response

$ sed -n 66,76p django/middleware/cache.py; sed -n 128,138p django/middleware/cache.py; sed -n 168,182p django/middleware/cache.py; sed -n 10,20p django/contrib/sessions/middleware.py
    def __init__(self, get_response=None):
        self._get_response_none_deprecation(get_response)
        self.cache_timeout = settings.CACHE_MIDDLEWARE_SECONDS
        self.page_timeout = None
        self.key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
        self.cache_alias = settings.CACHE_MIDDLEWARE_ALIAS
        self.cache = caches[self.cache_alias]
        self.get_response = get_response
    def _should_update_cache(self, request, response):
        return hasattr(request, '_cache_update_cache') and request._cache_update_cache
    # RemovedInDjango40Warning: when the deprecation ends, replace with:
    #   def __init__(self, get_response):
    def __init__(self, get_response=None):
        self._get_response_none_deprecation(get_response)
        self.key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
        self.cache_alias = settings.CACHE_MIDDLEWARE_ALIAS
        self.cache = caches[self.cache_alias]
        self.get_response = get_response
    def process_request(self, request):
        """
    Cache middleware that provides basic behavior for many simple sites.
    Also used as the hook point for the cache decorator, which is generated
    using the decorator-from-middleware utility.
    """
    # RemovedInDjango40Warning: when the deprecation ends, replace with:
    #   def __init__(self, get_response, cache_timeout=None, page_timeout=None, **kwargs):
    def __init__(self, get_response=None, cache_timeout=None, page_timeout=None, **kwargs):
        self._get_response_none_deprecation(get_response)
        self.get_response = get_response
        # We need to differentiate between "provided, but using default value",
        # and "not provided". If the value is provided using a default, then
        # we fall back to system defaults. If it is not provided at all,
        # we need to use middleware defaults.
class SessionMiddleware(MiddlewareMixin):
    # RemovedInDjango40Warning: when the deprecation ends, replace with:
    #   def __init__(self, get_response):
    def __init__(self, get_response=None):
        self._get_response_none_deprecation(get_response)
        self.get_response = get_response
        self._async_check()

