The admin related filters now order their choices. `RelatedFieldListFilter` uses the related ModelAdmin's ordering and falls back to the related model's `Meta.ordering`. `RelatedOnlyFieldListFilter` now does the same, where before it ignored ordering entirely.

The `admin_filters` and `admin_views.tests.AdminViewBasicTest` tests pass (89 tests). I didn't add a test for the ordering, run the full suite, or try a live admin page.

**Cause:** the filter's default ordering was an empty tuple, and `order_by(*())` is the same as `order_by()`, which drops the model's default ordering. I confirmed this on `auth.Permission`, where `.all()` has an `ORDER BY` and `order_by()` does not.

**Fix** (`django/contrib/admin/filters.py`): I added `field_admin_ordering()`, which returns the ModelAdmin ordering, then `Meta.ordering`, then `()`. Both filters' `field_choices()` call it, and `RelatedOnlyFieldListFilter` now passes `ordering` to `get_choices`.

**Sweep:**
- **Callers:** the only other callers of `get_choices` and `field_choices` are the form-field paths in `options.py` and `fields/__init__.py`. They don't pass `ordering`, so they keep the model's default ordering.
- **Reverse relations:** these also go through the filter, and `ForeignObjectRel.get_choices` has the same `order_by(*ordering)` pattern. I called it by hand with the fallback ordering on `ContentType.permission`. It produced the expected `ORDER BY app_label, model, codename`, so no extra change was needed.