`Book.objects.annotate(Count('name')).count()` now runs a plain `SELECT COUNT(*) FROM "aggregation_book"`. Before, it ran a subquery with a `GROUP BY`. The existing suites I ran pass (1463 tests across aggregation, annotations, queries, expressions and related apps), and so do the 84 annotations tests.

The change is in `Query.get_count()` in `django/db/models/sql/query.py`. It drops the annotations before counting, and clears the aggregate `group_by`, unless one of these applies:

- **Sliced, distinct or combined queries:** these keep their annotations.
- **Explicit grouping:** a `values()` followed by `annotate()` keeps its annotations.
- **Aggregate or window filters:** a filter on an aggregate or window annotation (`HAVING` / window filters) keeps them.
- **Annotations over other tables:** if an annotation touches a table other than the base one, I leave the query alone. Stripping `Count("authors")` kept its `LEFT JOIN` on the many-to-many table, which inflated the count (10 instead of 9 in one test), so I skip that case.
- **Q-object annotations:** these have no `flatten()`, so I treat them as "keep".

I added two tests in `tests/annotations/tests.py`. One checks that the count SQL has no `GROUP BY` or annotation aggregate. The other checks that the count for a multi-valued annotation matches `Book.objects.count()`.

Annotations over related tables still get the old subquery, so those counts aren't sped up. Dropping the join would fix that, but it needs care with join reference counts. I haven't added a release note.

The rehearsal log is in `.rehearsal/REHEARSAL.md`, and I left it in place. I'm not committing anything unless you ask.