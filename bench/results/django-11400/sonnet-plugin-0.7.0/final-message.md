I added two regression tests for the ordering bug. Both fail on the original code and pass with the fix.

Both are in `tests/admin_filters/tests.py`:
- `test_relatedonlyfieldlistfilter_uses_related_admin_ordering` checks that `RelatedOnlyFieldListFilter` follows the related `ModelAdmin`'s ordering.
- `test_relatedfieldlistfilter_falls_back_to_meta_ordering` checks that `RelatedFieldListFilter` falls back to the related model's `Meta.ordering` when no admin ordering is set. It uses a fresh `AdminSite` with no admin registered for `User`. On the shared test site, `User`'s own admin ordering takes precedence and hides the fallback.

With the changes in `django/` stashed, `admin_filters` shows 2 failures out of 34 tests. With the fix restored, all 34 pass.

I wrote the `repro:` line (the `admin_filters` test run) into `.rehearsal/REHEARSAL.md`. The earlier `.rehearsal/REHEARSAL.md` didn't exist, so that file now holds only that line, not a full log.