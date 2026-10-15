Your instinct is right: the explicit `parent_link=True` marker should decide, not declaration order. I fixed it in `django/db/models/base.py`, and the new test passes.

**Why it happens:** while building the parent links, Django stores one OneToOneField per target model in a dict, keyed by the parent model. Each later field to `Document` overwrites the earlier one, so whichever OneToOne comes last in the class body wins, regardless of `parent_link`. If that last one isn't the real link, Django raises the error on `origin`.

**The fix:** a field with `parent_link=True` always takes the slot. Other OneToOneFields only fill an empty slot. That makes both orders work, and a parent link that isn't last also works.

**Verified:**
- Reproduced the ticket's failing order (`document_ptr` before `origin`) with the exact error message.
- Reproduced a worse variant: link first, then two non-link OneToOnes. It fails on the last one.
- After the fix, both orders and the link-first-with-two-extras case all work.
- A child with no parent link at all still raises, which is correct.
- Added `test_parent_link_with_multiple_one_to_one_to_parent` to `tests/model_inheritance/tests.py`. It errors without the fix and passes with it.
- `model_inheritance`, `model_inheritance_regress`, `model_regress`, `model_fields`, `many_to_one`, `one_to_one`: all pass.

**Environment note:** the bare `python3` lacks Django's dependencies, so I ran everything with `/opt/miniconda3/envs/testbed/bin/python`.

**Not covered:** two `parent_link=True` fields to the same parent (last one still wins, as before). The rehearsal log is in `/testbed/.rehearsal/REHEARSAL.md`; I left it in place as evidence.