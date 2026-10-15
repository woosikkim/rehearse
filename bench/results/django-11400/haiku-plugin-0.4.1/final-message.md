Both filters now respect ordering. The regression test fails on the original code and passes with the fix.

**Root cause:** `Field.get_choices()` and `ManyToOneRel.get_choices()` always call `.order_by(*ordering)`. With an empty tuple, that becomes `order_by()`, which clears `Meta.ordering`. I confirmed this on `auth.Permission`: without `order_by`, the SQL has `ORDER BY app_label, model, codename`. With `order_by(*())`, the `ORDER BY` disappears.

**Changes:**
- `django/db/models/fields/__init__.py` and `reverse_related.py`: `get_choices` calls `order_by` only when `ordering` is non-empty. An empty ordering now keeps the related model's `Meta.ordering`. This fixes the `RelatedFieldListFilter` report.
- `django/contrib/admin/filters.py`: a new `field_admin_ordering()` helper on `RelatedFieldListFilter` reads the related `ModelAdmin.get_ordering()`. `field_choices` uses it, and `RelatedOnlyFieldListFilter.field_choices` now passes it through. This fixes the `RelatedOnlyFieldListFilter` report.
- `tests/admin_filters/tests.py`: new `test_relatedonlyfieldlistfilter_foreignkey_ordering`.

**Verified:** `tests/runtests.py --parallel 1 admin_filters model_fields model_forms admin_views model_regress` gives 847 tests, OK, 67 skipped. The new test fails on the original source and passes with the fix.

**Not verified:**
- `RelatedFieldListFilter` falling back to a related model's `Meta.ordering` has no test. The test models have no `Meta.ordering`, so I covered that path only by reading the code and the `Permission` check.
- The rehearsal log is in `/testbed/.rehearsal/REHEARSAL.md`, with fixtures alongside it. `.rehearsal/` is untracked, and it includes a local venv (`.rehearsal/venv`) that you may want to delete before committing.

I did not commit anything.