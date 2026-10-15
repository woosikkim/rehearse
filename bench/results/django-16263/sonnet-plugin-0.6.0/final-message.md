`count()` now drops annotations it doesn't need. `Book.objects.annotate(Count('chapters')).count()` no longer computes `Count('chapters')`. The affected test suites pass, including the new test.

The change is in `Query.get_count` (`django/db/models/sql/query.py`). I only checked the SQL on a few cases and didn't measure speed.

**When it applies:** annotations are cleared only when the query has no slice, `distinct()` or union. It must also have no `values()` grouping and no filter on an aggregate. In those cases they can change the result, so the annotations stay. I called the last two cases by hand: a `values().annotate()` query and a sliced one both keep their annotations.

**Grouping by primary key:** if an aggregate was dropped from a query that was grouped by default, the count now groups by the primary key explicitly. Without that, a filter across a multi-valued relation would count duplicate joined rows.

**Leftover join:** an unused `LEFT OUTER JOIN` to the related table can remain in the SQL after the aggregate is gone. I did not try to trim it.

**Tests:** I added `test_count_strips_unused_annotations` in `tests/aggregation/tests.py`.

**Other callers:** the forms, admin and `dumpdata` counts all go through `QuerySet.count()`, so they pick up the change. `aggregate()` with existing annotations is a separate path, and I left it alone.

The rehearsal log is at `.rehearsal/REHEARSAL.md`, and I left it in place.