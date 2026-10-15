Rehearse: full, because this was a reported behaviour change with code to run before any edit. Both reported bugs are fixed and the tests pass.

**Cause (confirmed by running it):** `Field.get_choices` calls `order_by(*ordering)`. With the empty tuple the filter passes, that becomes a bare `order_by()`, which clears `Meta.ordering`. The SQL for `Permission` shows no `ORDER BY` with `ordering=()`, but the expected `ORDER BY` with the model's `Meta.ordering`. `RelatedOnlyFieldListFilter` never passed `ordering` at all, so it had the same problem and also ignored the related ModelAdmin's ordering.

**Changes in `django/contrib/admin/filters.py`:**
- `RelatedFieldListFilter` has a new `get_related_ordering()` helper. It uses the related ModelAdmin's ordering, and falls back to the related model's `Meta.ordering` when that is empty.
- `field_choices` uses the helper.
- `RelatedOnlyFieldListFilter.field_choices` uses it too, and passes `ordering` to `get_choices`.

I left `Field.get_choices` alone. Its behaviour of clearing `Meta.ordering` for an explicit empty ordering is what other callers may rely on.

**Tests in `tests/admin_filters/tests.py`:** two regression tests.
- `test_relatedfieldlistfilter_foreignkey_ordering_meta` patches `Employee._meta.ordering` and checks the fallback.
- `test_relatedonlyfieldlistfilter_foreignkey_ordering` checks that the related ModelAdmin's ordering is applied.

Both fail without the fix and pass with it. I used ascending `name` ordering because the employees are created in pk order, and the default order would otherwise already match.

**Verification:**
- `admin_filters`: 34 tests, OK.
- `admin_views` and `admin_changelist`: 410 tests, OK (16 skipped).
- flake8 and isort are not installed in the project environment, so I did not run them.

**Choices I made:**
- The fallback lives in a helper, not in `Field.get_choices`, to keep the change inside the admin filters.
- Reverse relations are covered by the same fallback. I checked that `remote_field.model` and `related_model` both point to the same model for reverse relations.

The rehearsal log and probe output are in `.rehearsal/`, which I left in place as the skill asks. Not verified: a `Meta.ordering` that joins across relations (such as `content_type__app_label`) was checked only in SQL, not through an admin page.