$ ls .rehearsal; grep -n "process_response\|async def\|def \|sync_capable\|async_capable" django/utils/deprecation.py | sed -n 1,60p
active
base
fixtures
scaffold
20:    def __init__(self, class_name, old_method_name, new_method_name, deprecation_warning):
26:    def __call__(self, f):
27:        def wrapped(*args, **kwargs):
50:    def __new__(cls, name, bases, attrs):
80:    def __instancecheck__(self, instance):
89:    sync_capable = True
90:    async_capable = True
93:    #   def __init__(self, get_response):
94:    def __init__(self, get_response=None):
100:    def _async_check(self):
110:    def __call__(self, request):
118:        if hasattr(self, 'process_response'):
119:            response = self.process_response(request, response)
122:    async def __acall__(self, request):
134:        if hasattr(self, 'process_response'):
136:                self.process_response,
141:    def _get_response_none_deprecation(self, get_response):

$ grep -n "adapt_method_mode\|convert_exception_to_response\|_middleware_chain\|async def\|def " django/core/handlers/base.py | sed -n 1,40p
15:from .exception import convert_exception_to_response
24:    _middleware_chain = None
26:    def load_middleware(self, is_async=False):
37:        handler = convert_exception_to_response(get_response)
54:                handler = self.adapt_method_mode(
75:                    self.adapt_method_mode(is_async, mw_instance.process_view),
79:                    self.adapt_method_mode(is_async, mw_instance.process_template_response),
85:                    self.adapt_method_mode(False, mw_instance.process_exception),
88:            handler = convert_exception_to_response(mw_instance)
92:        handler = self.adapt_method_mode(is_async, handler, handler_is_async)
95:        self._middleware_chain = handler
97:    def adapt_method_mode(
124:    def get_response(self, request):
128:        response = self._middleware_chain(request)
138:    async def get_response_async(self, request):
148:        response = await self._middleware_chain(request)
158:    def _get_response(self, request):
210:    async def _get_response_async(self, request):
275:    def resolve_request(self, request):
292:    def check_response(self, response, callback, name=None):
320:    def make_view_atomic(self, view):
331:    def process_exception_by_middleware(self, exception, request):
343:def reset_urlconf(sender, **kwargs):

$ python3 -c '
import django, asyncio
from unittest import mock
from django.conf import settings
settings.configure(ROOT_URLCONF="django.contrib.admin.sites",ALLOWED_HOSTS=["*"],MIDDLEWARE=["django.middleware.common.CommonMiddleware","django.middleware.security.SecurityMiddleware"])
django.setup()
from django.core.handlers.asgi import ASGIHandler
from django.middleware.common import CommonMiddleware
m=mock.MagicMock(side_effect=print)
mock.patch.object(CommonMiddleware,"process_response",m).start()
h=ASGIHandler()
h.load_middleware(is_async=True)
from django.test import AsyncRequestFactory
resp=asyncio.run(h.get_response_async(AsyncRequestFactory().get("/")))
print(m.call_args)
' 2>&1 | tail -5
  File "/testbed/django/core/validators.py", line 9, in <module>
    from django.utils.deprecation import RemovedInDjango41Warning
  File "/testbed/django/utils/deprecation.py", line 5, in <module>
    from asgiref.sync import sync_to_async
ModuleNotFoundError: No module named 'asgiref'
  -> ImproperlyConfigured() = None  [django/core/exceptions.py:91]
  -> FieldError() = None  [django/core/exceptions.py:96]
  -> ValidationError() = <cell at 0x7f1e96b0a4d0: empty>  [django/core/exceptions.py:193]
  -> EmptyResultSet() = None  [django/core/exceptions.py:208]
  -> SynchronousOnlyOperation() = None  [django/core/exceptions.py:213]
  -> <module>() = None  [django/core/exceptions.py:211]
  -> <module>() = None  [django/utils/deconstruct.py:6]
  -> <module>() raised ModuleNotFoundError: No module named 'asgiref'  [django/utils/deprecation.py:5]
  -> <module>() raised ModuleNotFoundError: No module named 'asgiref'  [django/core/validators.py:9]
  -> <module>() raised ModuleNotFoundError: No module named 'asgiref'  [django/conf/__init__.py:19]

$ ls /opt; conda env list 2>/dev/null; ls /testbed/.venv 2>/dev/null; which -a python python3
miniconda3
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

$ /opt/miniconda3/envs/testbed/bin/python -c '
import django, asyncio
from unittest import mock
from django.conf import settings
settings.configure(ROOT_URLCONF="django.contrib.admin.sites",ALLOWED_HOSTS=["*"],MIDDLEWARE=["django.middleware.common.CommonMiddleware","django.middleware.security.SecurityMiddleware"])
django.setup()
from django.core.handlers.asgi import ASGIHandler
from django.middleware.common import CommonMiddleware
m=mock.MagicMock(side_effect=print)
mock.patch.object(CommonMiddleware,"process_response",m).start()
h=ASGIHandler()
h.load_middleware(is_async=True)
from django.test import AsyncRequestFactory
resp=asyncio.run(h.get_response_async(AsyncRequestFactory().get("/")))
print(m.call_args)
' 2>&1 | tail -5
Traceback (most recent call last):
  File "<string>", line 14, in <module>
AttributeError: module 'asyncio' has no attribute 'run'
  -> lazy(func=<function slugify at 0x7f4b5580ebf8>) = <function slugify at 0x7f4b558106a8>  [django/utils/functional.py:191]
  -> decorator(func=<function slugify at 0x7f4b5580ebf8>) = <function slugify at 0x7f4b55810f28>  [django/utils/functional.py:223]
  -> keep_lazy_text(func=<function slugify at 0x7f4b5580ebf8>) = <function slugify at 0x7f4b55810f28>  [django/utils/functional.py:231]
  -> __proxy__() = None  [django/utils/functional.py:179]
  -> lazy(func=<function _format_lazy at 0x7f4b55815048>) = <function _format_lazy at 0x7f4b558150d0>  [django/utils/functional.py:191]
  -> <module>() = None  [django/utils/text.py:425]
  -> SimpleLazyObject.__setattr__(name='_wrapped', value=<object object at 0x7f4b56a80340>) = None  [django/utils/functional.py:267]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:260]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:373]
  -> _lazy_re_compile(regex='([\\s<>"\']+)', flags=0) = <SimpleLazyObject: <function _lazy_re_compile.<locals>._compile at 0x7f4b557c8598>>  [django/utils/regex_helper.py:351]

$ /opt/miniconda3/envs/testbed/bin/python -c '
import django, asyncio
from unittest import mock
from django.conf import settings
settings.configure(ROOT_URLCONF="django.contrib.admin.sites",ALLOWED_HOSTS=["*"],MIDDLEWARE=["django.middleware.common.CommonMiddleware","django.middleware.security.SecurityMiddleware"])
django.setup()
from django.core.handlers.asgi import ASGIHandler
from django.middleware.common import CommonMiddleware
m=mock.MagicMock(side_effect=print)
mock.patch.object(CommonMiddleware,"process_response",m).start()
h=ASGIHandler()
h.load_middleware(is_async=True)
from django.test import AsyncRequestFactory
resp=asyncio.get_event_loop().run_until_complete(h.get_response_async(AsyncRequestFactory().get("/")))
print(m.call_args)
' 2>&1 | tail -5
    return future.result()
  File "/testbed/django/core/handlers/base.py", line 148, in get_response_async
    response = await self._middleware_chain(request)
TypeError: object NoneType can't be used in 'await' expression
<ASGIRequest: GET '/'> <coroutine object MiddlewareMixin.__acall__ at 0x7fa730bea7d8>
  -> lazy(func=<function slugify at 0x7fa7313adc80>) = <function slugify at 0x7fa7313af730>  [django/utils/functional.py:191]
  -> decorator(func=<function slugify at 0x7fa7313adc80>) = <function slugify at 0x7fa7313b1048>  [django/utils/functional.py:223]
  -> keep_lazy_text(func=<function slugify at 0x7fa7313adc80>) = <function slugify at 0x7fa7313b1048>  [django/utils/functional.py:231]
  -> __proxy__() = None  [django/utils/functional.py:179]
  -> lazy(func=<function _format_lazy at 0x7fa7313b10d0>) = <function _format_lazy at 0x7fa7313b1158>  [django/utils/functional.py:191]
  -> <module>() = None  [django/utils/text.py:425]
  -> SimpleLazyObject.__setattr__(name='_wrapped', value=<object object at 0x7fa732521340>) = None  [django/utils/functional.py:267]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:260]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:373]
  -> _lazy_re_compile(regex='([\\s<>"\']+)', flags=0) = <SimpleLazyObject: <function _lazy_re_compile.<locals>._compile at 0x7fa731446620>>  [django/utils/regex_helper.py:351]

$ cat >> .rehearsal/REHEARSAL.md <<'EOF'
### S1 saw: CommonMiddleware.process_response got <coroutine MiddlewareMixin.__acall__> (mock-patched, py: /opt/miniconda3/envs/testbed/bin/python)
EOF
sed -n 1,60p django/core/handlers/exception.py | sed -n 15,50p; grep -n "process_request\|process_response" django/middleware/security.py
from django.http.multipartparser import MultiPartParserError
from django.urls import get_resolver, get_urlconf
from django.utils.log import log_response
from django.views import debug
def convert_exception_to_response(get_response):
    """
    Wrap the given get_response callable in exception-to-response conversion.
    All exceptions will be converted. All known 4xx exceptions (Http404,
    PermissionDenied, MultiPartParserError, SuspiciousOperation) will be
    converted to the appropriate response, and all other exceptions will be
    converted to 500 responses.
    This decorator is automatically applied to all middleware to ensure that
    no middleware leaks an exception and that the next middleware in the stack
    can rely on getting a response instead of an exception.
    """
    if asyncio.iscoroutinefunction(get_response):
        @wraps(get_response)
        async def inner(request):
            try:
                response = await get_response(request)
            except Exception as exc:
                response = await sync_to_async(response_for_exception)(request, exc)
            return response
        return inner
    else:
        @wraps(get_response)
        def inner(request):
            try:
                response = get_response(request)
            except Exception as exc:
                response = response_for_exception(request, exc)
            return response
24:    def process_request(self, request):
34:    def process_response(self, request, response):

$ /opt/miniconda3/envs/testbed/bin/python -c '
import django, asyncio
from django.conf import settings
settings.configure(ROOT_URLCONF="django.contrib.admin.sites",ALLOWED_HOSTS=["*"],MIDDLEWARE=["django.middleware.common.CommonMiddleware","django.middleware.security.SecurityMiddleware"])
django.setup()
from django.core.handlers.asgi import ASGIHandler
h=ASGIHandler()
h.load_middleware(is_async=True)
c=h._middleware_chain
print(c, asyncio.iscoroutinefunction(c))
print(c.__wrapped__, asyncio.iscoroutinefunction(c.__wrapped__))
print(c.__wrapped__.get_response, asyncio.iscoroutinefunction(c.__wrapped__.get_response))
'
<function convert_exception_to_response.<locals>.inner at 0x7f630bcc4378> False
<django.middleware.common.CommonMiddleware object at 0x7f630bd3f3c8> False
<function convert_exception_to_response.<locals>.inner at 0x7f630bcc42f0> False
  -> lazy(func=<function slugify at 0x7f630c550598>) = <function slugify at 0x7f630c552048>  [django/utils/functional.py:191]
  -> decorator(func=<function slugify at 0x7f630c550598>) = <function slugify at 0x7f630c5528c8>  [django/utils/functional.py:223]
  -> keep_lazy_text(func=<function slugify at 0x7f630c550598>) = <function slugify at 0x7f630c5528c8>  [django/utils/functional.py:231]
  -> __proxy__() = None  [django/utils/functional.py:179]
  -> lazy(func=<function _format_lazy at 0x7f630c552950>) = <function _format_lazy at 0x7f630c5529d8>  [django/utils/functional.py:191]
  -> <module>() = None  [django/utils/text.py:425]
  -> SimpleLazyObject.__setattr__(name='_wrapped', value=<object object at 0x7f630d606320>) = None  [django/utils/functional.py:267]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:260]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:373]
  -> _lazy_re_compile(regex='([\\s<>"\']+)', flags=0) = <SimpleLazyObject: <function _lazy_re_compile.<locals>._compile at 0x7f630c573840>>  [django/utils/regex_helper.py:351]

$ /opt/miniconda3/envs/testbed/bin/python -c '
import django, asyncio
from django.conf import settings
settings.configure(ROOT_URLCONF="django.contrib.admin.sites",ALLOWED_HOSTS=["*"],MIDDLEWARE=["django.middleware.common.CommonMiddleware","django.middleware.security.SecurityMiddleware"])
django.setup()
from django.core.handlers.asgi import ASGIHandler
h=ASGIHandler()
h.load_middleware(is_async=True)
s=h._middleware_chain.__wrapped__.get_response.__wrapped__
print(s, s.__dict__.keys(), asyncio.iscoroutinefunction(s), asyncio.iscoroutinefunction(s.get_response), s.get_response)
import sys; print(sys.version)
'
<django.middleware.security.SecurityMiddleware object at 0x7f07591fb7f0> dict_keys(['sts_seconds', 'sts_include_subdomains', 'sts_preload', 'content_type_nosniff', 'xss_filter', 'redirect', 'redirect_host', 'redirect_exempt', 'referrer_policy', 'get_response']) False True <function BaseHandler._get_response_async at 0x7f0759182e18>
3.6.13 |Anaconda, Inc.| (default, Jun  4 2021, 14:25:59) 
[GCC 7.5.0]
  -> lazy(func=<function slugify at 0x7f0759a1d598>) = <function slugify at 0x7f0759a1f048>  [django/utils/functional.py:191]
  -> decorator(func=<function slugify at 0x7f0759a1d598>) = <function slugify at 0x7f0759a1f8c8>  [django/utils/functional.py:223]
  -> keep_lazy_text(func=<function slugify at 0x7f0759a1d598>) = <function slugify at 0x7f0759a1f8c8>  [django/utils/functional.py:231]
  -> __proxy__() = None  [django/utils/functional.py:179]
  -> lazy(func=<function _format_lazy at 0x7f0759a1f950>) = <function _format_lazy at 0x7f0759a1f9d8>  [django/utils/functional.py:191]
  -> <module>() = None  [django/utils/text.py:425]
  -> SimpleLazyObject.__setattr__(name='_wrapped', value=<object object at 0x7f075aad3320>) = None  [django/utils/functional.py:267]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:260]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:373]
  -> _lazy_re_compile(regex='([\\s<>"\']+)', flags=0) = <SimpleLazyObject: <function _lazy_re_compile.<locals>._compile at 0x7f0759a3f840>>  [django/utils/regex_helper.py:351]

$ sed -n 8,24p django/middleware/security.py; grep -rn "def __init__(self, get_response" django --include=*.py | head -30
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
django/middleware/cache.py:65:    #   def __init__(self, get_response):
django/middleware/cache.py:66:    def __init__(self, get_response=None):
django/middleware/cache.py:129:    #   def __init__(self, get_response):
django/middleware/cache.py:130:    def __init__(self, get_response=None):
django/middleware/cache.py:174:    #   def __init__(self, get_response, cache_timeout=None, page_timeout=None, **kwargs):
django/middleware/cache.py:175:    def __init__(self, get_response=None, cache_timeout=None, page_timeout=None, **kwargs):
django/middleware/security.py:10:    #   def __init__(self, get_response):
django/middleware/security.py:11:    def __init__(self, get_response=None):
django/contrib/redirects/middleware.py:15:    def __init__(self, get_response=None):
django/contrib/sessions/middleware.py:14:    #   def __init__(self, get_response):
django/contrib/sessions/middleware.py:15:    def __init__(self, get_response=None):
django/utils/deprecation.py:93:    #   def __init__(self, get_response):
django/utils/deprecation.py:94:    def __init__(self, get_response=None):

$ cat >> .rehearsal/REHEARSAL.md <<'EOF'
### S2: SecurityMiddleware.__init__ never calls _async_check; iscoroutinefunction(instance)=False -> convert_exception_to_response picks sync wrapper -> coroutine leaks to Common.process_response
repro: /opt/miniconda3/envs/testbed/bin/python -c 'import django;from django.conf import settings;settings.configure(MIDDLEWARE=["django.middleware.common.CommonMiddleware","django.middleware.security.SecurityMiddleware"]);django.setup();from django.core.handlers.asgi import ASGIHandler;h=ASGIHandler();h.load_middleware(is_async=True);import asyncio;print(asyncio.iscoroutinefunction(h._middleware_chain.__wrapped__.get_response))'
EOF
grep -n -B2 -A12 "def __init__(self, get_response" django/middleware/cache.py django/contrib/redirects/middleware.py django/contrib/sessions/middleware.py | grep -n "__init__\|_async_check\|super\|get_response ="
3:django/middleware/cache.py:65:    #   def __init__(self, get_response):
4:django/middleware/cache.py:66:    def __init__(self, get_response=None):
11:django/middleware/cache.py-73-        self.get_response = get_response
20:django/middleware/cache.py:129:    #   def __init__(self, get_response):
21:django/middleware/cache.py:130:    def __init__(self, get_response=None):
26:django/middleware/cache.py-135-        self.get_response = get_response
37:django/middleware/cache.py:174:    #   def __init__(self, get_response, cache_timeout=None, page_timeout=None, **kwargs):
38:django/middleware/cache.py:175:    def __init__(self, get_response=None, cache_timeout=None, page_timeout=None, **kwargs):
40:django/middleware/cache.py-177-        self.get_response = get_response
53:django/contrib/sessions/middleware.py:14:    #   def __init__(self, get_response):
54:django/contrib/sessions/middleware.py:15:    def __init__(self, get_response=None):
56:django/contrib/sessions/middleware.py-17-        self.get_response = get_response
57:django/contrib/sessions/middleware.py-18-        self._async_check()
69:django/contrib/redirects/middleware.py:15:    def __init__(self, get_response=None):
75:django/contrib/redirects/middleware.py-21-        super().__init__(get_response)

$ sed -n 64,76p django/middleware/cache.py; sed -n 128,138p django/middleware/cache.py; sed -n 173,200p django/middleware/cache.py
    # RemovedInDjango40Warning: when the deprecation ends, replace with:
    #   def __init__(self, get_response):
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
    # RemovedInDjango40Warning: when the deprecation ends, replace with:
    #   def __init__(self, get_response, cache_timeout=None, page_timeout=None, **kwargs):
    def __init__(self, get_response=None, cache_timeout=None, page_timeout=None, **kwargs):
        self._get_response_none_deprecation(get_response)
        self.get_response = get_response
        # We need to differentiate between "provided, but using default value",
        # and "not provided". If the value is provided using a default, then
        # we fall back to system defaults. If it is not provided at all,
        # we need to use middleware defaults.
        try:
            key_prefix = kwargs['key_prefix']
            if key_prefix is None:
                key_prefix = ''
        except KeyError:
            key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
        self.key_prefix = key_prefix
        try:
            cache_alias = kwargs['cache_alias']

