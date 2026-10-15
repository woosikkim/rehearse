Fast-path deletes that target the same table are now combined into one `DELETE ... WHERE (a_id IN (...) OR b_id IN (...))`. For the `R`/`A` case I reproduced, four separate `DELETE FROM delete_a` statements became one.

**Size:** full. I ran the current queries by hand, then did the change.

**What changed**
- `django/db/models/deletion.py`:
  - `collect()` groups the fast-deletable related fields by related model and emits one queryset per batch for each group.
  - `related_objects()` takes the related model and a list of fields, and ORs their `__in` filters.
  - `get_del_batches()` takes a field list, so batch size accounts for the number of OR'ed fields. On SQLite, four fields batch at 249 rather than 500, which keeps the parameter count under the limit.
  - `can_fast_delete()` accepts a model class as well as an instance or queryset.
- `django/contrib/admin/utils.py`: `NestedObjects.related_objects` gets the same new signature so the admin collector keeps working.
- `tests/delete/tests.py`: new `test_fast_delete_combined_fields`. It fails without the change and passes with it.

**Verified**
- The ticket's self-referential M2M shape (`SelfRefer.references` / `related`) gives one OR'ed query per through table.
- Test suites: `delete`, `delete_regress`, `generic_relations`, `admin_utils`, `admin_views`, `model_formsets` (573 tests OK), and `many_to_one`, `many_to_many`, `one_to_one`, `proxy_models`, `model_inheritance` (+ `_regress`), `multiple_database`, `generic_relations_regress`, `contenttypes_tests`, `admin_inlines`, `admin_checks` (474 tests OK).

**Not verified**
- flake8 isn't installed in the `testbed` environment, so lint wasn't run.
- Only SQLite was tested. The batch-size path uses `bulk_batch_size`, which the other backends implement too, but I didn't run them.
- The full Django test suite was not run.

**Environment note:** the bare `python3` lacks Django's dependencies, so I used `/opt/miniconda3/envs/testbed/bin/python`.

The rehearsal log and fixtures are in `/testbed/.rehearsal/REHEARSAL.md`. I left them in place. Nothing is committed.