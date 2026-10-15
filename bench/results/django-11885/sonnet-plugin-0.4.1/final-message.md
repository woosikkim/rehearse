Fast-delete relations from the same table are now combined into one `DELETE ... WHERE a IN (...) OR b IN (...)` query. The delete, admin, inheritance, generic relations and many-to-many test suites pass (534 tests, 15 skipped). The Django `delete` suite also passes with the new test (45 tests, 1 skipped).

**What changed**
- **`django/db/models/deletion.py`:** during collection, relations that can be fast-deleted are grouped by related model. Each group becomes one queryset that ORs the per-field `__in` filters. Batching now takes every field in the group into account.
- **`related_objects()` signature:** it now takes `(related_model, related_fields, objs)`, so any external subclass that overrides it needs the same update.
- **`can_fast_delete()`:** it now also accepts a model class, so it can check the related model before any queryset is built.
- **`django/contrib/admin/utils.py`:** the admin's override of `related_objects()` was updated to match, and it now calls `select_related` on all the grouped fields.
- **`tests/delete/tests.py`:** I added `test_fast_delete_combined_relationships`. `SecondReferrer` has two foreign keys to `Referrer`, so deleting a referrer now takes 2 queries.

**Rehearsal**
I rehearsed one step only: the baseline test run before the change. The `.rehearsal` marker is removed. The rehearsal log is thin, but the change was checked by the test suites above.

The test runner has to be started with `/opt/miniconda3/envs/testbed/bin/python tests/runtests.py`. The default `python` has no `asgiref`, so it fails to import Django.

I did not run the full Django test suite or any database backend other than SQLite. Backends that have a lower batch limit for multi-field queries are the most likely place for a problem.