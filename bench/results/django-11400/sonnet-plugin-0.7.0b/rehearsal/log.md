$ ls .rehearsal; grep -n "ordering\|get_choices" django/contrib/admin/filters.py; grep -n "def get_choices" -A40 django/db/models/fields/__init__.py | grep -n "ordering\|def " 
active
fixtures
scaffold
197:        ordering = ()
200:            ordering = related_admin.get_ordering(request)
201:        return field.get_choices(include_blank=False, ordering=ordering)
422:        return field.get_choices(include_blank=False, limit_choices_to={'pk__in': pk_qs})
1:809:    def get_choices(self, include_blank=True, blank_choice=BLANK_CHOICE_DASH, limit_choices_to=None, ordering=()):
22:830-            for x in rel_model._default_manager.complex_filter(limit_choices_to).order_by(*ordering)
25:833-    def value_to_string(self, obj):
32:840-    def _get_flatchoices(self):

$ sed -n 190,202p django/contrib/admin/filters.py; sed -n 412,424p django/contrib/admin/filters.py; grep -n "ordering" django/db/models/fields/reverse_related.py; grep -n "def get_choices" -B3 -A22 django/db/models/fields/reverse_related.py
            extra = 0
        return len(self.lookup_choices) + extra > 1
    def expected_parameters(self):
        return [self.lookup_kwarg, self.lookup_kwarg_isnull]
    def field_choices(self, field, request, model_admin):
        ordering = ()
        related_admin = model_admin.admin_site._registry.get(field.remote_field.model)
        if related_admin is not None:
            ordering = related_admin.get_ordering(request)
        return field.get_choices(include_blank=False, ordering=ordering)
                'display': self.empty_value_display,
            }
FieldListFilter.register(lambda f: True, AllValuesFieldListFilter)
class RelatedOnlyFieldListFilter(RelatedFieldListFilter):
    def field_choices(self, field, request, model_admin):
        pk_qs = model_admin.get_queryset(request).distinct().values_list('%s__pk' % self.field_path, flat=True)
        return field.get_choices(include_blank=False, limit_choices_to={'pk__in': pk_qs})
117:    def get_choices(self, include_blank=True, blank_choice=BLANK_CHOICE_DASH, ordering=()):
126:            (x.pk, str(x)) for x in self.related_model._default_manager.order_by(*ordering)
114-            self.related_model._meta.model_name,
115-        )
116-
117:    def get_choices(self, include_blank=True, blank_choice=BLANK_CHOICE_DASH, ordering=()):
118-        """
119-        Return choices with a default blank choices included, for use
120-        as <select> choices for this field.
121-
122-        Analog of django.db.models.fields.Field.get_choices(), provided
123-        initially for utilization by RelatedFieldListFilter.
124-        """
125-        return (blank_choice if include_blank else []) + [
126-            (x.pk, str(x)) for x in self.related_model._default_manager.order_by(*ordering)
127-        ]
128-
129-    def is_hidden(self):
130-        """Should the related object be hidden?"""
131-        return bool(self.related_name) and self.related_name[-1] == '+'
132-
133-    def get_joining_columns(self):
134-        return self.field.get_reverse_joining_columns()

$ python3 -c '
import django
from django.conf import settings
settings.configure(INSTALLED_APPS=["django.contrib.contenttypes","django.contrib.auth"],DATABASES={"default":{"ENGINE":"django.db.backends.sqlite3","NAME":":memory:"}})
django.setup()
from django.contrib.auth.models import Permission
print(Permission.objects.all().query.order_by, Permission.objects.order_by(*()).query.order_by, Permission.objects.order_by(*()).query.default_ordering)'
Exit code 1
Traceback (most recent call last):
  File "<string>", line 5, in <module>
  File "/testbed/django/__init__.py", line 16, in setup
    from django.urls import set_script_prefix
  File "/testbed/django/urls/__init__.py", line 1, in <module>
    from .base import (
  File "/testbed/django/urls/base.py", line 3, in <module>
    from asgiref.local import Local
ModuleNotFoundError: No module named 'asgiref'
  -> <module>() = None  [django/utils/module_loading.py:82]
  -> AppConfig() = None  [django/apps/config.py:213]
  -> <module>() = None  [django/apps/config.py:10]
  -> Apps() = None  [django/apps/registry.py:417]
  -> Apps.__init__(installed_apps=None) = None  [django/apps/registry.py:58]
  -> <module>() = None  [django/apps/registry.py:427]
  -> <module>() = None  [django/apps/__init__.py:4]
  -> <module>() raised ModuleNotFoundError: No module named 'asgiref'  [django/urls/base.py:3]
  -> <module>() raised ModuleNotFoundError: No module named 'asgiref'  [django/urls/__init__.py:1]
  -> setup(set_prefix=True) raised ModuleNotFoundError: No module named 'asgiref'  [django/__init__.py:16]

$ ls -d .venv /opt/*/envs/* 2>/dev/null; conda env list 2>/dev/null; which -a python python3
/opt/miniconda3/envs/testbed
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

$ cat .rehearsal/REHEARSAL.md 2>/dev/null | head

$ /opt/miniconda3/envs/testbed/bin/python -c '
import django
from django.conf import settings
settings.configure(INSTALLED_APPS=["django.contrib.contenttypes","django.contrib.auth"],DATABASES={"default":{"ENGINE":"django.db.backends.sqlite3","NAME":":memory:"}})
django.setup()
from django.contrib.auth.models import Permission
print(Permission._meta.ordering, Permission.objects.order_by(*()).query.default_ordering, Permission.objects.order_by(*()).ordered, Permission.objects.all().ordered)'
('content_type__app_label', 'content_type__model', 'codename') False False True
  -> __wrapper__() = <__proxy__ instance at 0x7f03d38c3ba8>  [django/utils/functional.py:173]
  -> __proxy__.__init__(args=('Enter a valid IPv6 address.',), kw={}) = None  [django/utils/functional.py:82]
  -> __wrapper__() = <__proxy__ instance at 0x7f03d38c3e48>  [django/utils/functional.py:173]
  -> __proxy__.__init__(args=('Enter only digits separated by commas.',), kw={}) = None  [django/utils/functional.py:82]
  -> __wrapper__() = <__proxy__ instance at 0x7f03d38c3e10>  [django/utils/functional.py:173]
  -> SimpleLazyObject.__setattr__(name='_wrapped', value=<object object at 0x7f03d4a2f1b0>) = None  [django/utils/functional.py:251]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:244]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:357]
  -> _lazy_re_compile(regex='^\\d+(?:\\,\\d+)*\\Z', flags=0) = <SimpleLazyObject: <function _lazy_re_compile.<locals>._compile at 0x7f03d38c2488>>  [django/core/validators.py:26]
  -> RegexValidator.__new__() = <django.core.validators.RegexValidator object at 0x7f03d38c3fd0>  [django/utils/deconstruct.py:18]

