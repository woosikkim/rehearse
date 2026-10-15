$ ls .rehearsal; grep -n "order_by\|def get_order_by\|combinator" django/db/models/sql/compiler.py | head -60
active
fixtures
scaffold
53:        order_by = self.get_order_by()
55:        extra_select = self.get_extra_select(order_by, self.select)
57:        group_by = self.get_group_by(self.select + extra_select, order_by)
58:        return extra_select, order_by, group_by
60:    def get_group_by(self, select, order_by):
91:        # refer some column outside of the wanted_cols, order_by, or even
112:        # set to group by. So, we need to add cols in select, order_by, and
118:        for expr, (sql, params, is_ref) in order_by:
254:    def get_order_by(self):
259:        The order_by clause can alter the select clause (for example it
263:        if self.query.extra_order_by:
264:            ordering = self.query.extra_order_by
266:            ordering = self.query.order_by
267:        elif self.query.order_by:
268:            ordering = self.query.order_by
279:        order_by = []
290:                order_by.append((field, False))
293:                order_by.append((OrderBy(Random()), False))
301:                order_by.append((
312:                order_by.append((OrderBy(expr, descending=descending), False))
316:                # This came in through an extra(order_by=...) addition. Pass it
319:                order_by.append((
329:                order_by.extend(self.find_ordering_name(
333:                    order_by.append((
337:                    order_by.append((
343:        for expr, is_ref in order_by:
345:            if self.query.combinator:
373:    def get_extra_select(self, order_by, select):
377:            for expr, (sql, params, is_ref) in order_by:
410:    def get_combinator_sql(self, combinator, all):
420:                if compiler.get_order_by():
436:                if compiler.query.combinator:
449:                if combinator == 'union' or (combinator == 'difference' and parts):
454:        combinator_sql = self.connection.ops.set_operators[combinator]
455:        if all and combinator == 'union':
456:            combinator_sql += ' ALL'
459:        result = [' {} '.format(combinator_sql).join(sql_parts)]

$ sed -n 408,450p django/db/models/sql/compiler.py; grep -n "combined_queries" django/db/models/sql/query.py django/db/models/query.py
        return sql, params
    def get_combinator_sql(self, combinator, all):
        features = self.connection.features
        compilers = [
            query.get_compiler(self.using, self.connection)
            for query in self.query.combined_queries if not query.is_empty()
        ]
        if not features.supports_slicing_ordering_in_compound:
            for query, compiler in zip(self.query.combined_queries, compilers):
                if query.low_mark or query.high_mark:
                    raise DatabaseError('LIMIT/OFFSET not allowed in subqueries of compound statements.')
                if compiler.get_order_by():
                    raise DatabaseError('ORDER BY not allowed in subqueries of compound statements.')
        parts = ()
        for compiler in compilers:
            try:
                # If the columns list is limited, then all combined queries
                # must have the same columns list. Set the selects defined on
                # the query on all combined queries, if not already set.
                if not compiler.query.values_select and self.query.values_select:
                    compiler.query = compiler.query.clone()
                    compiler.query.set_values((
                        *self.query.extra_select,
                        *self.query.values_select,
                        *self.query.annotation_select,
                    ))
                part_sql, part_args = compiler.as_sql()
                if compiler.query.combinator:
                    # Wrap in a subquery if wrapping in parentheses isn't
                    # supported.
                    if not features.supports_parentheses_in_compound:
                        part_sql = 'SELECT * FROM ({})'.format(part_sql)
                    # Add parentheses when combining with compound query if not
                    # already added for all compound queries.
                    elif not features.supports_slicing_ordering_in_compound:
                        part_sql = '({})'.format(part_sql)
                parts += ((part_sql, part_args),)
            except EmptyResultSet:
                # Omit the empty queryset with UNION and with DIFFERENCE if the
                # first queryset is nonempty.

$ sed -n 340,372p django/db/models/sql/compiler.py; grep -n "def test_union_with_values_list_and_order\b" -A12 tests/queries/test_qs_combinators.py
        result = []
        seen = set()
        for expr, is_ref in order_by:
            resolved = expr.resolve_expression(self.query, allow_joins=True, reuse=None)
            if self.query.combinator:
                src = resolved.get_source_expressions()[0]
                # Relabel order by columns to raw numbers if this is a combined
                # query; necessary since the columns can't be referenced by the
                # fully qualified name and the simple column names may collide.
                for idx, (sel_expr, _, col_alias) in enumerate(self.select):
                    if is_ref and col_alias == src.refs:
                        src = src.source
                    elif col_alias:
                        continue
                    if src == sel_expr:
                        resolved.set_source_expressions([RawSQL('%d' % (idx + 1), ())])
                        break
                else:
                    raise DatabaseError('ORDER BY term does not match any column in the result set.')
            sql, params = self.compile(resolved)
            # Don't add the same column twice, but the order direction is
            # not taken into account so we strip it. When this entire method
            # is refactored into expressions, then we can check each part as we
            # generate it.
            without_ordering = self.ordering_parts.search(sql).group(1)
            params_hash = make_hashable(params)
            if (without_ordering, params_hash) in seen:
                continue
            seen.add((without_ordering, params_hash))
            result.append((resolved, (sql, params, is_ref)))
        return result

$ python3 -c '
import django
from django.conf import settings
settings.configure(INSTALLED_APPS=["tests.queries"],DATABASES={"default":{"ENGINE":"django.db.backends.sqlite3","NAME":":memory:"}})
django.setup()
from django.core.management import call_command
call_command("migrate", run_syncdb=True, verbosity=0)
from tests.queries.models import ReservedName as R
R.objects.create(name="a",order=1); R.objects.create(name="b",order=2)
qs = R.objects.filter(pk__in=[1]).union(R.objects.filter(pk__in=[2])).order_by("order")
print(list(qs))
print(list(qs.order_by().values_list("pk",flat=True)))
print(qs.query.combined_queries[0].order_by, qs.query.order_by)
print(list(qs))
' 2>&1 | tail -8
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/testbed/django/forms/boundfield.py", line 3, in <module>
    from django.forms.utils import flatatt, pretty_name
  File "/testbed/django/forms/utils.py", line 6, in <module>
    from django.utils import timezone
  File "/testbed/django/utils/timezone.py", line 11, in <module>
    import pytz
ModuleNotFoundError: No module named 'pytz'
  -> <module>() raised ModuleNotFoundError: No module named 'pytz'  [django/core/serializers/__init__.py:23]
  -> <module>() raised ModuleNotFoundError: No module named 'pytz'  [django/http/response.py:15]
  -> <module>() raised ModuleNotFoundError: No module named 'pytz'  [django/http/__init__.py:5]
  -> <module>() raised ModuleNotFoundError: No module named 'pytz'  [django/urls/exceptions.py:1]
  -> <module>() raised ModuleNotFoundError: No module named 'pytz'  [django/urls/base.py:8]
  -> <module>() raised ModuleNotFoundError: No module named 'pytz'  [django/urls/__init__.py:1]
  -> setup(set_prefix=True) raised ModuleNotFoundError: No module named 'pytz'  [django/__init__.py:16]
  -> Signal._remove_receiver(receiver=None) = None  [django/dispatch/dispatcher.py:269]
  -> Signal._remove_receiver(receiver=None) = None  [django/dispatch/dispatcher.py:269]
  -> Signal._remove_receiver(receiver=None) = None  [django/dispatch/dispatcher.py:269]

$ ls /testbed/.venv/bin/python /opt 2>&1; which -a python python3; conda env list 2>&1 | head
ls: cannot access '/testbed/.venv/bin/python': No such file or directory
/opt:
miniconda3
/opt/miniconda3/bin/python
/usr/bin/python
/bin/python
/opt/miniconda3/bin/python3
/usr/bin/python3
/bin/python3
# conda environments:
#
base                     /opt/miniconda3
testbed               *  /opt/miniconda3/envs/testbed

$ /opt/miniconda3/envs/testbed/bin/python -c '
import django
from django.conf import settings
settings.configure(INSTALLED_APPS=["tests.queries"],DATABASES={"default":{"ENGINE":"django.db.backends.sqlite3","NAME":":memory:"}})
django.setup()
from django.core.management import call_command
call_command("migrate", run_syncdb=True, verbosity=0)
from tests.queries.models import ReservedName as R
R.objects.create(name="a",order=1); R.objects.create(name="b",order=2)
qs = R.objects.filter(pk__in=[1]).union(R.objects.filter(pk__in=[2])).order_by("order")
print(list(qs))
print(list(qs.order_by().values_list("pk",flat=True)))
print(qs.query.combined_queries[0].order_by, qs.query.order_by)
print(list(qs))
' 2>&1 | tail -8
[<ReservedName: a>, <ReservedName: b>]
[1, 2]
() ('order',)
[<ReservedName: a>, <ReservedName: b>]
  -> __proxy__.__init__(args=('Enter only digits separated by commas.',), kw={}) = None  [django/utils/functional.py:82]
  -> __wrapper__() = <__proxy__ instance at 0x7f85a8f97898>  [django/utils/functional.py:173]
  -> SimpleLazyObject.__setattr__(name='_wrapped', value=<object object at 0x7f85aa3871b0>) = None  [django/utils/functional.py:251]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:244]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:357]
  -> _lazy_re_compile(regex='^\\d+(?:\\,\\d+)*\\Z', flags=0) = <SimpleLazyObject: <function _lazy_re_compile.<locals>._compile at 0x7f85a8fa4d08>>  [django/core/validators.py:25]
  -> RegexValidator.__new__() = <django.core.validators.RegexValidator object at 0x7f85a8f979e8>  [django/utils/deconstruct.py:18]
  -> SimpleLazyObject.__setattr__(name='_wrapped', value=<object object at 0x7f85aa3871b0>) = None  [django/utils/functional.py:251]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:244]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:357]

$ /opt/miniconda3/envs/testbed/bin/python -c '
import django
from django.conf import settings
settings.configure(INSTALLED_APPS=["tests.queries"],DATABASES={"default":{"ENGINE":"django.db.backends.sqlite3","NAME":":memory:"}})
django.setup()
from django.core.management import call_command
call_command("migrate", run_syncdb=True, verbosity=0)
from tests.queries.models import ReservedName as R
R.objects.create(name="a",order=1); R.objects.create(name="b",order=2)
qs = R.objects.filter(pk__in=[1]).union(R.objects.filter(pk__in=[2]).order_by("order"))
print(list(qs))
print(list(qs.order_by().values_list("pk",flat=True)))
print(list(qs))
' 2>&1 | tail -4; cd /testbed; git log -3 --format=%h -- django/db/models/sql/compiler.py; sed -n 925,940p django/db/models/query.py
    result, params = self.get_combinator_sql(combinator, self.query.combinator_all)
  File "/testbed/django/db/models/sql/compiler.py", line 421, in get_combinator_sql
    raise DatabaseError('ORDER BY not allowed in subqueries of compound statements.')
django.db.utils.DatabaseError: ORDER BY not allowed in subqueries of compound statements.
14d026cccb
f6075fb333
f8b8b00f01
        else:
            return self._filter_or_exclude(None, **filter_obj)
    def _combinator_query(self, combinator, *other_qs, all=False):
        # Clone the query to inherit the select list and everything
        clone = self._chain()
        # Clear limits and ordering so they can be reapplied
        clone.query.clear_ordering(True)
        clone.query.clear_limits()
        clone.query.combined_queries = (self.query,) + tuple(qs.query for qs in other_qs)
        clone.query.combinator = combinator
        clone.query.combinator_all = all
        return clone
    def union(self, *other_qs, all=False):
        # If the query is an EmptyQuerySet, combine all nonempty querysets.
  -> __proxy__.__init__(args=('Enter only digits separated by commas.',), kw={}) = None  [django/utils/functional.py:82]
  -> __wrapper__() = <__proxy__ instance at 0x7f5a22f5df60>  [django/utils/functional.py:173]
  -> SimpleLazyObject.__setattr__(name='_wrapped', value=<object object at 0x7f5a242e71b0>) = None  [django/utils/functional.py:251]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:244]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:357]
  -> _lazy_re_compile(regex='^\\d+(?:\\,\\d+)*\\Z', flags=0) = <SimpleLazyObject: <function _lazy_re_compile.<locals>._compile at 0x7f5a22f61d08>>  [django/core/validators.py:25]
  -> RegexValidator.__new__() = <django.core.validators.RegexValidator object at 0x7f5a22f5dc50>  [django/utils/deconstruct.py:18]
  -> SimpleLazyObject.__setattr__(name='_wrapped', value=<object object at 0x7f5a242e71b0>) = None  [django/utils/functional.py:251]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:244]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:357]

$ /opt/miniconda3/envs/testbed/bin/python -c '
import django
from django.conf import settings
settings.configure(INSTALLED_APPS=["tests.queries"],DATABASES={"default":{"ENGINE":"django.db.backends.sqlite3","NAME":":memory:"}})
django.setup()
from django.core.management import call_command
call_command("migrate", run_syncdb=True, verbosity=0)
from tests.queries.models import ReservedName as R
R.objects.create(name="a",order=1); R.objects.create(name="b",order=2)
qs = R.objects.filter(pk__in=[1]).union(R.objects.filter(pk__in=[2])).order_by("order")
print(list(qs.values_list("pk",flat=True)))
print(list(qs))
print(qs.query.combined_queries[1].values_select, qs.query.combined_queries[1].select)
' 2>&1 | tail -4
    order_by = self.get_order_by()
  File "/testbed/django/db/models/sql/compiler.py", line 359, in get_order_by
    raise DatabaseError('ORDER BY term does not match any column in the result set.')
django.db.utils.DatabaseError: ORDER BY term does not match any column in the result set.
  -> __proxy__.__init__(args=('Enter only digits separated by commas.',), kw={}) = None  [django/utils/functional.py:82]
  -> __wrapper__() = <__proxy__ instance at 0x7eff5faddf60>  [django/utils/functional.py:173]
  -> SimpleLazyObject.__setattr__(name='_wrapped', value=<object object at 0x7eff60e621b0>) = None  [django/utils/functional.py:251]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:244]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:357]
  -> _lazy_re_compile(regex='^\\d+(?:\\,\\d+)*\\Z', flags=0) = <SimpleLazyObject: <function _lazy_re_compile.<locals>._compile at 0x7eff5fae1d08>>  [django/core/validators.py:25]
  -> RegexValidator.__new__() = <django.core.validators.RegexValidator object at 0x7eff5faddc50>  [django/utils/deconstruct.py:18]
  -> SimpleLazyObject.__setattr__(name='_wrapped', value=<object object at 0x7eff60e621b0>) = None  [django/utils/functional.py:251]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:244]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:357]

$ /opt/miniconda3/envs/testbed/bin/python -c '
import django
from django.conf import settings
settings.configure(INSTALLED_APPS=["tests.queries"],DATABASES={"default":{"ENGINE":"django.db.backends.sqlite3","NAME":":memory:"}})
django.setup()
from django.db import connection
connection.features.supports_slicing_ordering_in_compound=True
from tests.queries.models import ReservedName as R
qs = R.objects.filter(pk__in=[1]).union(R.objects.filter(pk__in=[2]).order_by("order"))
print(str(qs.query))
print(str(qs.order_by().values_list("pk",flat=True).query))
print(str(qs.query))
' 2>&1 | tail -4
(SELECT "queries_reservedname"."id", "queries_reservedname"."name", "queries_reservedname"."order" FROM "queries_reservedname" WHERE "queries_reservedname"."id" IN (1)) UNION (SELECT "queries_reservedname"."id", "queries_reservedname"."name", "queries_reservedname"."order" FROM "queries_reservedname" WHERE "queries_reservedname"."id" IN (2) ORDER BY "queries_reservedname"."order" ASC)
(SELECT "queries_reservedname"."id" FROM "queries_reservedname" WHERE "queries_reservedname"."id" IN (1)) UNION (SELECT "queries_reservedname"."id" FROM "queries_reservedname" WHERE "queries_reservedname"."id" IN (2) ORDER BY "queries_reservedname"."order" ASC)
(SELECT "queries_reservedname"."id", "queries_reservedname"."name", "queries_reservedname"."order" FROM "queries_reservedname" WHERE "queries_reservedname"."id" IN (1)) UNION (SELECT "queries_reservedname"."id", "queries_reservedname"."name", "queries_reservedname"."order" FROM "queries_reservedname" WHERE "queries_reservedname"."id" IN (2) ORDER BY "queries_reservedname"."order" ASC)
  -> __proxy__.__init__(args=('Enter only digits separated by commas.',), kw={}) = None  [django/utils/functional.py:82]
  -> __wrapper__() = <__proxy__ instance at 0x7fa233f1eef0>  [django/utils/functional.py:173]
  -> SimpleLazyObject.__setattr__(name='_wrapped', value=<object object at 0x7fa23527d1b0>) = None  [django/utils/functional.py:251]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:244]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:357]
  -> _lazy_re_compile(regex='^\\d+(?:\\,\\d+)*\\Z', flags=0) = <SimpleLazyObject: <function _lazy_re_compile.<locals>._compile at 0x7fa233f23d08>>  [django/core/validators.py:25]
  -> RegexValidator.__new__() = <django.core.validators.RegexValidator object at 0x7fa233f1eda0>  [django/utils/deconstruct.py:18]
  -> SimpleLazyObject.__setattr__(name='_wrapped', value=<object object at 0x7fa23527d1b0>) = None  [django/utils/functional.py:251]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:244]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:357]

$ /opt/miniconda3/envs/testbed/bin/python -c '
import django
from django.conf import settings
settings.configure(INSTALLED_APPS=["tests.queries"],DATABASES={"default":{"ENGINE":"django.db.backends.sqlite3","NAME":":memory:"}})
django.setup()
from django.db import connection
connection.features.supports_slicing_ordering_in_compound=True
from tests.queries.models import ReservedName as R
qs = R.objects.filter(pk__in=[1]).union(R.objects.filter(pk__in=[2])).order_by("order")
print(str(qs.query))
print(str(qs.order_by().values_list("pk",flat=True).query))
print(str(qs.query))
' 2>&1 | tail -4
(SELECT "queries_reservedname"."id", "queries_reservedname"."name", "queries_reservedname"."order" FROM "queries_reservedname" WHERE "queries_reservedname"."id" IN (1)) UNION (SELECT "queries_reservedname"."id", "queries_reservedname"."name", "queries_reservedname"."order" FROM "queries_reservedname" WHERE "queries_reservedname"."id" IN (2)) ORDER BY (3) ASC
(SELECT "queries_reservedname"."id" FROM "queries_reservedname" WHERE "queries_reservedname"."id" IN (1)) UNION (SELECT "queries_reservedname"."id" FROM "queries_reservedname" WHERE "queries_reservedname"."id" IN (2))
(SELECT "queries_reservedname"."id", "queries_reservedname"."name", "queries_reservedname"."order" FROM "queries_reservedname" WHERE "queries_reservedname"."id" IN (1)) UNION (SELECT "queries_reservedname"."id", "queries_reservedname"."name", "queries_reservedname"."order" FROM "queries_reservedname" WHERE "queries_reservedname"."id" IN (2)) ORDER BY (3) ASC
  -> __proxy__.__init__(args=('Enter only digits separated by commas.',), kw={}) = None  [django/utils/functional.py:82]
  -> __wrapper__() = <__proxy__ instance at 0x7ff38a4def60>  [django/utils/functional.py:173]
  -> SimpleLazyObject.__setattr__(name='_wrapped', value=<object object at 0x7ff38b8401b0>) = None  [django/utils/functional.py:251]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:244]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:357]
  -> _lazy_re_compile(regex='^\\d+(?:\\,\\d+)*\\Z', flags=0) = <SimpleLazyObject: <function _lazy_re_compile.<locals>._compile at 0x7ff38a4e3d08>>  [django/core/validators.py:25]
  -> RegexValidator.__new__() = <django.core.validators.RegexValidator object at 0x7ff38a4dec50>  [django/utils/deconstruct.py:18]
  -> SimpleLazyObject.__setattr__(name='_wrapped', value=<object object at 0x7ff38b8401b0>) = None  [django/utils/functional.py:251]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:244]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:357]

$ cd /testbed; grep -n "ordering" tests/queries/models.py | head; grep -n "OrderBy\|def resolve_expression" -n django/db/models/expressions.py | sed -n 1,30p
36:        ordering = ['name']
48:        ordering = ['note']
76:        ordering = ['info']
88:        ordering = ['name']
103:        ordering = ['-note', 'name']
126:        # A complex ordering specification. Should stress the system a bit.
127:        ordering = ('author__extra__note', 'author__name', 'rank')
138:        ordering = ['item']
159:        ordering = ['valid']
172:# Some models with a cycle in the default ordering. This would be bad if we
224:    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
351:        return OrderBy(self, **kwargs)
354:        return OrderBy(self, descending=True, **kwargs)
447:    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
513:    def resolve_expression(self, query=None, allow_joins=True, reuse=None,
518:        return OrderBy(self, **kwargs)
521:        return OrderBy(self, descending=True, **kwargs)
550:    def resolve_expression(self, query=None, allow_joins=True, reuse=None,
596:    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
666:    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
801:    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
886:    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
950:    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
1069:class OrderBy(BaseExpression):

$ /opt/miniconda3/envs/testbed/bin/python -c '
import django
from django.conf import settings
settings.configure(INSTALLED_APPS=["tests.queries"],DATABASES={"default":{"ENGINE":"django.db.backends.sqlite3","NAME":":memory:"}})
django.setup()
from django.db import connection
connection.features.supports_slicing_ordering_in_compound=True
from tests.queries.models import ReservedName as R
a = R.objects.filter(pk__in=[1]).union(R.objects.filter(pk__in=[2]))
qs = R.objects.filter(pk__in=[3]).union(a.order_by("order"))
print(str(qs.query))
print(str(qs.order_by().values_list("pk",flat=True).query))
print(str(qs.query))
' 2>&1 | tail -4
  File "/testbed/django/db/models/sql/compiler.py", line 359, in get_order_by
    raise DatabaseError('ORDER BY term does not match any column in the result set.')
django.db.utils.DatabaseError: ORDER BY term does not match any column in the result set.
(SELECT "queries_reservedname"."id", "queries_reservedname"."name", "queries_reservedname"."order" FROM "queries_reservedname" WHERE "queries_reservedname"."id" IN (3)) UNION (SELECT * FROM ((SELECT "queries_reservedname"."id", "queries_reservedname"."name", "queries_reservedname"."order" FROM "queries_reservedname" WHERE "queries_reservedname"."id" IN (1)) UNION (SELECT "queries_reservedname"."id
  -> __proxy__.__init__(args=('Enter only digits separated by commas.',), kw={}) = None  [django/utils/functional.py:82]
  -> __wrapper__() = <__proxy__ instance at 0x7f2695eddf28>  [django/utils/functional.py:173]
  -> SimpleLazyObject.__setattr__(name='_wrapped', value=<object object at 0x7f269725e1b0>) = None  [django/utils/functional.py:251]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:244]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:357]
  -> _lazy_re_compile(regex='^\\d+(?:\\,\\d+)*\\Z', flags=0) = <SimpleLazyObject: <function _lazy_re_compile.<locals>._compile at 0x7f2695ee1d08>>  [django/core/validators.py:25]
  -> RegexValidator.__new__() = <django.core.validators.RegexValidator object at 0x7f2695eddc18>  [django/utils/deconstruct.py:18]
  -> SimpleLazyObject.__setattr__(name='_wrapped', value=<object object at 0x7f269725e1b0>) = None  [django/utils/functional.py:251]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:244]
  -> SimpleLazyObject.__init__() = None  [django/utils/functional.py:357]

$ cd /testbed; grep -n "combin" django/db/models/sql/query.py django/db/models/query.py | head -30; grep -n "def clone" -A45 django/db/models/sql/query.py | head -70
django/db/models/query.py:319:        combined = self._chain()
django/db/models/query.py:320:        combined._merge_known_related_objects(other)
django/db/models/query.py:321:        combined.query.combine(other.query, sql.AND)
django/db/models/query.py:322:        return combined
django/db/models/query.py:331:        combined = query._chain()
django/db/models/query.py:332:        combined._merge_known_related_objects(other)
django/db/models/query.py:335:        combined.query.combine(other.query, sql.OR)
django/db/models/query.py:336:        return combined
django/db/models/query.py:928:    def _combinator_query(self, combinator, *other_qs, all=False):
django/db/models/query.py:934:        clone.query.combined_queries = (self.query,) + tuple(qs.query for qs in other_qs)
django/db/models/query.py:935:        clone.query.combinator = combinator
django/db/models/query.py:936:        clone.query.combinator_all = all
django/db/models/query.py:940:        # If the query is an EmptyQuerySet, combine all nonempty querysets.
django/db/models/query.py:943:            return qs[0]._combinator_query('union', *qs[1:], all=all) if qs else self
django/db/models/query.py:944:        return self._combinator_query('union', *other_qs, all=all)
django/db/models/query.py:953:        return self._combinator_query('intersection', *other_qs)
django/db/models/query.py:959:        return self._combinator_query('difference', *other_qs)
django/db/models/sql/query.py:212:        # Set combination attributes
django/db/models/sql/query.py:213:        self.combinator = None
django/db/models/sql/query.py:214:        self.combinator_all = False
django/db/models/sql/query.py:215:        self.combined_queries = ()
django/db/models/sql/query.py:434:                self.distinct or self.combinator):
django/db/models/sql/query.py:540:    def combine(self, rhs, connector):
django/db/models/sql/query.py:550:            "Cannot combine queries on two different base models."
django/db/models/sql/query.py:552:            "Cannot combine queries once a slice has been taken."
django/db/models/sql/query.py:554:            "Cannot combine a unique query with a non-unique query."
django/db/models/sql/query.py:556:            "Cannot combine queries with different distinct fields."
django/db/models/sql/query.py:562:        # Determine which existing joins can be reused. When combining the
django/db/models/sql/query.py:564:        # combining with OR we can reuse joins. The reason is that in AND
django/db/models/sql/query.py:595:            # combined query must have two joins, too.
95:    def clone(self, using):
96-        return RawQuery(self.sql, using, params=self.params)
97-
98-    def get_columns(self):
99-        if self.cursor is None:
100-            self._execute_query()
101-        converter = connections[self.using].introspection.identifier_converter
102-        return [converter(column_meta[0])
103-                for column_meta in self.cursor.description]
104-

$ cd /testbed; git show 14d026cccb --stat | tail -5; git show 14d026cccb -- django | head -40; sed -n 296,312p django/db/models/sql/compiler.py
    Fixed #30572 -- Prevented values()/values_list() on combined queryset from mutating the list of columns in querysets.
 django/db/models/sql/compiler.py     | 1 +
 tests/queries/test_qs_combinators.py | 3 +++
 2 files changed, 4 insertions(+)
commit 14d026cccb144c6877294ba4cd4e03ebf0842498
Author: Mariusz Felisiak <felisiak.mariusz@gmail.com>
Date:   Wed Jun 19 10:44:53 2019 +0200
    Fixed #30572 -- Prevented values()/values_list() on combined queryset from mutating the list of columns in querysets.
diff --git a/django/db/models/sql/compiler.py b/django/db/models/sql/compiler.py
index a44adfc760..a791908caf 100644
--- a/django/db/models/sql/compiler.py
+++ b/django/db/models/sql/compiler.py
@@ -426,6 +426,7 @@ class SQLCompiler:
                 # must have the same columns list. Set the selects defined on
                 # the query on all combined queries, if not already set.
                 if not compiler.query.values_select and self.query.values_select:
+                    compiler.query = compiler.query.clone()
                     compiler.query.set_values((
                         *self.query.extra_select,
                         *self.query.values_select,
            col, order = get_order_dir(field, asc)
            descending = order == 'DESC'
            if col in self.query.annotation_select:
                # Reference to expression in SELECT clause
                order_by.append((
                    OrderBy(Ref(col, self.query.annotation_select[col]), descending=descending),
                    True))
                continue
            if col in self.query.annotations:
                # References to an expression which is masked out of the SELECT
                # clause.
                expr = self.query.annotations[col]
                if isinstance(expr, Value):
                    # output_field must be resolved for constants.
                    expr = Cast(expr, expr.output_field)
                order_by.append((OrderBy(expr, descending=descending), False))

$ cd /testbed; sed -n 30,38p tests/queries/models.py; /opt/miniconda3/envs/testbed/bin/python -c '
import django
from django.conf import settings
settings.configure(INSTALLED_APPS=["tests.queries"],DATABASES={"default":{"ENGINE":"django.db.backends.sqlite3","NAME":":memory:"}})
django.setup()
from django.db import connection
connection.features.supports_slicing_ordering_in_compound=True
from tests.queries.models import Tag as R
qs = R.objects.filter(pk__in=[1]).union(R.objects.filter(pk__in=[2])).order_by("name")
print(str(qs.query))
print(str(qs.order_by().values_list("pk",flat=True).query))
print(str(qs.query))
' 2>&1 | tail -4
        blank=True, null=True,
        related_name='children',
    )
    category = models.ForeignKey(NamedCategory, models.SET_NULL, null=True, default=None)
    class Meta:
        ordering = ['name']
    def __str__(self):
(SELECT "queries_tag"."id", "queries_tag"."name", "queries_tag"."parent_id", "queries_tag"."category_id" FROM "queries_tag" WHERE "queries_tag"."id" IN (1) ORDER BY "queries_tag"."name" ASC) UNION (SELECT "queries_tag"."id", "queries_tag"."name", "queries_tag"."parent_id", "queries_tag"."category_id" FROM "queries_tag" WHERE "queries_tag"."id" IN (2) ORDER BY "queries_tag"."name" ASC) ORDER BY (2)
(SELECT "queries_tag"."id" FROM "queries_tag" WHERE "queries_tag"."id" IN (1) ORDER BY "queries_tag"."name" ASC) UNION (SELECT "queries_tag"."id" FROM "queries_tag" WHERE "queries_tag"."id" IN (2) ORDER BY "queries_tag"."name" ASC)
(SELECT "queries_tag"."id", "queries_tag"."name", "queries_tag"."parent_id", "queries_tag"."category_id" FROM "queries_tag" WHERE "queries_tag"."id" IN (1) ORDER BY "queries_tag"."name" ASC) UNION (SELECT "queries_tag"."id", "queries_tag"."name", "queries_tag"."parent_id", "queries_tag"."category_id" FROM "queries_tag" WHERE "queries_tag"."id" IN (2) ORDER BY "queries_tag"."name" ASC) ORDER BY (2)

$ cd /testbed; /opt/miniconda3/envs/testbed/bin/python -c '
import django
from django.conf import settings
settings.configure(INSTALLED_APPS=["tests.queries"],DATABASES={"default":{"ENGINE":"django.db.backends.sqlite3","NAME":":memory:"}})
django.setup()
from django.db import connection
connection.features.supports_slicing_ordering_in_compound=True
from tests.queries.models import ReservedName as R
a = R.objects.filter(pk__in=[1])
b = R.objects.filter(pk__in=[2])
qs = a.union(b).order_by("order")
print(str(qs[:3].query))
v = qs.order_by().values_list("pk",flat=True)
print(str(v[:3].query))
print(str(qs[:3].query))
print(str(a.query), str(b.query))
print(str(a.union(b).order_by("order").values_list("order",flat=True).query))
' 2>&1 | tail -5
(SELECT "queries_reservedname"."id", "queries_reservedname"."name", "queries_reservedname"."order" FROM "queries_reservedname" WHERE "queries_reservedname"."id" IN (1)) UNION (SELECT "queries_reservedname"."id", "queries_reservedname"."name", "queries_reservedname"."order" FROM "queries_reservedname" WHERE "queries_reservedname"."id" IN (2)) ORDER BY (3) ASC LIMIT 3
(SELECT "queries_reservedname"."id" FROM "queries_reservedname" WHERE "queries_reservedname"."id" IN (1)) UNION (SELECT "queries_reservedname"."id" FROM "queries_reservedname" WHERE "queries_reservedname"."id" IN (2)) LIMIT 3
(SELECT "queries_reservedname"."id", "queries_reservedname"."name", "queries_reservedname"."order" FROM "queries_reservedname" WHERE "queries_reservedname"."id" IN (1)) UNION (SELECT "queries_reservedname"."id", "queries_reservedname"."name", "queries_reservedname"."order" FROM "queries_reservedname" WHERE "queries_reservedname"."id" IN (2)) ORDER BY (3) ASC LIMIT 3
SELECT "queries_reservedname"."id", "queries_reservedname"."name", "queries_reservedname"."order" FROM "queries_reservedname" WHERE "queries_reservedname"."id" IN (1) SELECT "queries_reservedname"."id", "queries_reservedname"."name", "queries_reservedname"."order" FROM "queries_reservedname" WHERE "queries_reservedname"."id" IN (2)
(SELECT "queries_reservedname"."order" FROM "queries_reservedname" WHERE "queries_reservedname"."id" IN (1)) UNION (SELECT "queries_reservedname"."order" FROM "queries_reservedname" WHERE "queries_reservedname"."id" IN (2)) ORDER BY (1) ASC

$ cd /testbed; sed -n 1069,1100p django/db/models/expressions.py; sed -n 150,165p django/db/models/sql/compiler.py; grep -n "def set_values" -A28 django/db/models/sql/query.py
class OrderBy(BaseExpression):
    template = '%(expression)s %(ordering)s'
    def __init__(self, expression, descending=False, nulls_first=False, nulls_last=False):
        if nulls_first and nulls_last:
            raise ValueError('nulls_first and nulls_last are mutually exclusive')
        self.nulls_first = nulls_first
        self.nulls_last = nulls_last
        self.descending = descending
        if not hasattr(expression, 'resolve_expression'):
            raise ValueError('expression must be an expression type')
        self.expression = expression
    def __repr__(self):
        return "{}({}, descending={})".format(
            self.__class__.__name__, self.expression, self.descending)
    def set_source_expressions(self, exprs):
        self.expression = exprs[0]
    def get_source_expressions(self):
        return [self.expression]
    def as_sql(self, compiler, connection, template=None, **extra_context):
        if not template:
            if self.nulls_last:
                template = '%s NULLS LAST' % self.template
            elif self.nulls_first:
                template = '%s NULLS FIRST' % self.template
        connection.ops.check_expression_support(self)
        expression_sql, params = compiler.compile(self.expression)
        placeholders = {
                        getattr(expr, 'alias', None) == self.query.base_table):
                    pk = expr
                    break
            # If the main model's primary key is in the query, group by that
            # field, HAVING expressions, and expressions associated with tables
            # that don't have a primary key included in the grouped columns.
            if pk:
                pk_aliases = {
                    expr.alias for expr in expressions
                    if hasattr(expr, 'target') and expr.target.primary_key
                }
                expressions = [pk] + [
                    expr for expr in expressions

$ cd /testbed; /opt/miniconda3/envs/testbed/bin/python -c '
import django
from django.conf import settings
settings.configure(INSTALLED_APPS=["tests.queries"],DATABASES={"default":{"ENGINE":"django.db.backends.sqlite3","NAME":":memory:"}})
django.setup()
from django.core.management import call_command
call_command("migrate", run_syncdb=True, verbosity=0)
from tests.queries.models import ReservedName as R
R.objects.create(name="a",order=2); R.objects.create(name="b",order=1)
a = R.objects.filter(pk__in=[1])
b = R.objects.filter(pk__in=[2])
qs = a.union(b).order_by("order")
print(repr(qs))
print(repr(qs.order_by().values_list("pk",flat=True)))
print(repr(qs))
print(repr(qs.values_list("order",flat=True)))
print(repr(qs))
print(repr(a), repr(b))
' 2>&1 | tail -6
<QuerySet [<ReservedName: b>, <ReservedName: a>]>
<QuerySet [1, 2]>
<QuerySet [<ReservedName: b>, <ReservedName: a>]>
<QuerySet [1, 2]>
<QuerySet [<ReservedName: b>, <ReservedName: a>]>
<QuerySet [<ReservedName: a>]> <QuerySet [<ReservedName: b>]>

$ cd /testbed; /opt/miniconda3/envs/testbed/bin/python -c 'import psycopg2' 2>&1 | tail -1; which psql pg_ctl postgres mysqld 2>&1 | head -3; git log --oneline -3 -- django/db/models/sql/query.py
ModuleNotFoundError: No module named 'psycopg2'
6b736dd074 Fixed #30349 -- Fixed QuerySet.exclude() on FilteredRelation.
719b746620 Fixed #30412 -- Fixed crash when adding check constraints with OR'ed condition on Oracle and SQLite.
0cb4062482 Refs #23758 -- Used RecursionError instead of RuntimeError to raise nested subquery errors.

$ cd /testbed; /opt/miniconda3/envs/testbed/bin/python -c '
import django
from django.conf import settings
settings.configure(INSTALLED_APPS=["tests.queries"],DATABASES={"default":{"ENGINE":"django.db.backends.sqlite3","NAME":":memory:"}})
django.setup()
from django.core.management import call_command
call_command("migrate", run_syncdb=True, verbosity=0)
from tests.queries.models import ReservedName as R
R.objects.create(name="rn1",order=7); R.objects.create(name="rn2",order=5);R.objects.create(name="rn0",order=6);R.objects.create(name="rn9",order=-1)
u = R.objects.filter(order__gte=6).union(R.objects.filter(order__lte=5))
q = u.order_by("name","order")
print(list(q.values_list("order",flat=True)))
print(list(q.values_list("name",flat=True)))
' 2>&1 | tail -4
    order_by = self.get_order_by()
  File "/testbed/django/db/models/sql/compiler.py", line 359, in get_order_by
    raise DatabaseError('ORDER BY term does not match any column in the result set.')
django.db.utils.DatabaseError: ORDER BY term does not match any column in the result set.

$ cd /testbed; /opt/miniconda3/envs/testbed/bin/python -c '
import django
from django.conf import settings
settings.configure(INSTALLED_APPS=["tests.queries"],DATABASES={"default":{"ENGINE":"django.db.backends.sqlite3","NAME":":memory:"}})
django.setup()
from django.db.models import F
from tests.queries.models import ReservedName as R
u = R.objects.filter(order__gte=6).union(R.objects.filter(order__lte=5)).order_by(F("order").asc(), "name")
print(str(u.query))
print(str(u.query.order_by))
print(str(u.values_list("order","name").query))
print(str(u.query))
print(str(u.order_by().values_list("name").query))
print(str(u.query))
' 2>&1 | tail -8
SELECT "queries_reservedname"."id", "queries_reservedname"."name", "queries_reservedname"."order" FROM "queries_reservedname" WHERE "queries_reservedname"."order" >= 6 UNION SELECT "queries_reservedname"."id", "queries_reservedname"."name", "queries_reservedname"."order" FROM "queries_reservedname" WHERE "queries_reservedname"."order" <= 5 ORDER BY (3) ASC, (2) ASC
(OrderBy(F(order), descending=False), 'name')
SELECT "queries_reservedname"."order", "queries_reservedname"."name" FROM "queries_reservedname" WHERE "queries_reservedname"."order" >= 6 UNION SELECT "queries_reservedname"."order", "queries_reservedname"."name" FROM "queries_reservedname" WHERE "queries_reservedname"."order" <= 5 ORDER BY (1) ASC, (2) ASC
SELECT "queries_reservedname"."id", "queries_reservedname"."name", "queries_reservedname"."order" FROM "queries_reservedname" WHERE "queries_reservedname"."order" >= 6 UNION SELECT "queries_reservedname"."id", "queries_reservedname"."name", "queries_reservedname"."order" FROM "queries_reservedname" WHERE "queries_reservedname"."order" <= 5 ORDER BY (3) ASC, (2) ASC
SELECT "queries_reservedname"."name" FROM "queries_reservedname" WHERE "queries_reservedname"."order" >= 6 UNION SELECT "queries_reservedname"."name" FROM "queries_reservedname" WHERE "queries_reservedname"."order" <= 5
SELECT "queries_reservedname"."id", "queries_reservedname"."name", "queries_reservedname"."order" FROM "queries_reservedname" WHERE "queries_reservedname"."order" >= 6 UNION SELECT "queries_reservedname"."id", "queries_reservedname"."name", "queries_reservedname"."order" FROM "queries_reservedname" WHERE "queries_reservedname"."order" <= 5 ORDER BY (3) ASC, (2) ASC

