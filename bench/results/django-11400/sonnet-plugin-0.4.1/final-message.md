Both filters now order their choices correctly, and the existing tests pass. I did not add new tests for the ordering cases. I ran `admin_filters`, `model_fields`, `model_forms` and `admin_views.tests`, with 14 tests skipped.

- **`RelatedFieldListFilter`:** `Field.get_choices()` always called `.order_by(*ordering)`. With the default empty ordering, that cleared the related model's `Meta.ordering`. It now only reorders when an ordering is given, so `Meta.ordering` is the fallback.
- **`RelatedOnlyFieldListFilter`:** it never passed `ordering` at all. It now uses the related model's `ModelAdmin` ordering, falling back to `Meta.ordering`.
- **Shared helper:** I added `field_admin_ordering()` to `RelatedFieldListFilter` (`django/contrib/admin/filters.py`), and both filters use it.
- **Reverse relations:** I made the same change to `ForeignObjectRel.get_choices` in `reverse_related.py`, since it had the same unconditional `order_by`.

Before the change I could only confirm the baseline (`admin_filters` passing). I didn't reproduce the wrong ordering by hand. The diagnosis comes from reading the code.

The tests need the conda interpreter at `/opt/miniconda3/envs/testbed/bin/python`. The default `python3` doesn't have `asgiref`.