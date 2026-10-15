Fast-delete queries on the same table are now combined into one `DELETE ... WHERE a IN (...) OR b IN (...)`. The `delete`, `delete_regress`, `many_to_many`, `many_to_one`, `generic_relations`, `signals`, `admin_views`, `admin_utils`, `proxy_models` and `model_inheritance` suites pass (664 tests) with the code change. After that I added a new test and its models; the `delete` and `delete_regress` suites (64 tests) pass with them. I didn't run flake8 because it isn't installed in the environment.

**What changed**
- **`django/db/models/deletion.py`:** `Collector.collect()` now groups the fast-deletable relations by related model. It issues one combined query per batch for each model, instead of one per foreign key.
- **Batching:** `get_del_batches` now takes a list of fields, so the connection's batch-size limit still holds when several fields are OR'd.
- **`related_objects()` signature:** it is now `related_objects(related_model, related_fields, objs)`. This is a signature change for anything that overrides it. I updated the one override in the repo, in `django/contrib/admin/utils.py`.
- **Test:** `FastDeleteCombineTests` in `tests/delete`, with new `EntryUser` and `Entry` models (two foreign keys to one model). Deleting the user takes two queries: one `DELETE` for the entries and one for the user.

My first attempt merged every batch into a single OR query. That defeated the batch-size limit and failed two query-count tests (`test_large_delete` and `test_large_delete_related`), so I reverted it and grouped within each batch instead.

- **Rehearsal:** the real tests ran before and after the change, and I checked by hand that OR-ing two querysets of one model gives a single `WHERE ... OR ...` query. The log in `.rehearsal/REHEARSAL.md` is short and is missing the later steps (the failed first attempt and the final fix).
- **Not run:** non-SQLite backends (their batch-size limits differ), and the full Django test suite.