`_clean_fields()` and `changed_data` now read values through BoundField, and the per-field change logic lives in `BoundField._did_change()`. The forms, model_forms, admin_views, model_formsets, admin_inlines and admin_widgets suites pass.

**Rehearsal:** full size. I reproduced the inconsistency first. For a disabled `DateTimeField` with a callable initial, `cleaned_data` kept microseconds while `form["d"].initial` dropped them. I then checked by hand that cleaning the BoundField's initial gives the value the widget shows, and only then made the change.

**Changes:**
- `django/forms/boundfield.py`: new `BoundField._did_change()` with the old per-field logic from `changed_data`, including the `show_hidden_initial` branch. Imports `ValidationError`.
- `django/forms/forms.py`:
  - New `_bound_items()` helper that yields `(name, self[name])`.
  - `_clean_fields()` uses `bf.initial` for disabled fields and `bf.data` otherwise, and passes `bf.initial` to `FileField.clean`.
  - `changed_data` is now a one-line comprehension over `_bound_items()`.
- `tests/forms_tests/tests/test_forms.py`: `test_datetime_clean_initial_callable_disabled` expected the old value with microseconds. The ticket names this inconsistency as the bug, so I changed the expectation to the BoundField's initial and added an assertion that the two match. The code wasn't changed to fit the test.

**Choices to check:**
- I named the method `_did_change` (private) rather than the ticket's `did_change`, since it's an internal helper.
- The probe and rehearsal log are in `.rehearsal/` (uncommitted, left in place as the evidence trail).