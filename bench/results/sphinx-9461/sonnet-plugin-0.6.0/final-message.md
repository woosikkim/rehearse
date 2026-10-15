I swept the other places that use the code I changed. The only other consumer of `get_class_members` is autosummary. It now gets the underlying property for `classmethod_prop`, and its `can_document_member` check accepts it. The autosummary suite still passes (23 tests).

The change is complete. The related suites pass and `.rehearsal/` holds the log.