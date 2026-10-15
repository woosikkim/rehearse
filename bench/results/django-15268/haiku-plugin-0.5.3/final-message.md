The optimizer now collapses consecutive `AlterUniqueTogether` / `AlterIndexTogether` pairs on the same model. The ticket example reduces from four operations to `[AlterUniqueTogether({("col",)}), AlterIndexTogether({("col",)})]`. The migrations suite passes (633 tests).

**The cause:** `AlterTogetherOptionOperation` inherits `ModelOptionOperation.reduce`, which only merges operations of the same class. So `AlterIndexTogether` refused to let the optimizer pass through it to reach the second `AlterUniqueTogether`, and the pairs were never merged.

**The change** (`django/db/migrations/operations/models.py`): `AlterTogetherOptionOperation.reduce` returns `True` when the other operation is a different AlterTogether option on the same model. The model-name check is what keeps operations on other models out of this path. Same-option merging still goes through the existing logic.

**Tests:**
- Three autodetector tests asserted the old four-operation output (`test_foo_together_ordering`, `test_remove_field_and_foo_together`, `test_rename_field_and_foo_together`). They passed on the untouched code, so I updated their expectations to the two-operation form. Field operations keep their positions, and `RemoveField` / `RenameField` still come where they did.
- Three new optimizer tests: the ticket case, the reversed order (index first), and a case on a different model that must not reduce.

**Rehearsal notes:** I reproduced the bug, confirmed the blocker, and hand-derived the expected outputs before editing. After the change, the same probes matched those expectations. The log is in `.rehearsal/REHEARSAL.md`, and I left `.rehearsal/` in place as you'd want.

**Not verified:**
- I ran only Django's test suite, not the reordered SQL on real database backends.
- flake8 isn't installed in the `testbed` conda env, so I did not lint the changes.
- Interpreter used: `/opt/miniconda3/envs/testbed/bin/python`. The system `python3` lacks Django's dependencies.