Both filters now order their choices. I changed `django/contrib/admin/filters.py`, and the 32 existing `admin_filters` tests pass.

- **`RelatedFieldListFilter`:** it still uses the related model's `ModelAdmin` ordering when one is defined. If there isn't one, it now falls back to the related model's `Meta.ordering`. Before, the empty ordering cleared `Meta.ordering`.
- **`RelatedOnlyFieldListFilter`:** it now passes the same ordering to `field.get_choices`. Before, it passed none, so it ignored even the admin's ordering.
- **Shared helper:** both use a new `field_admin_ordering()` method.

I didn't add a test for the new behaviour, so the fix itself isn't covered by one. My one attempt to run the ordering by hand failed on missing Django settings, and I didn't retry it. The cause comes from reading `get_choices`.

`.rehearsal/` is still in the repo, as the rehearse skill asks. Delete it when you like.