`autodoc` with `:inherited-members:` now documents attributes that a base class documents with a `#:` comment. I checked it with a new test. The existing autodoc tests pass except `test_autodoc`, which fails with and without my change.

**Cause:** `autodoc` looked up attribute comments by `(current class, attribute name)`. A subclass never matched the key `(Base, attr)` where the comment lives.

**Fix** (`sphinx/ext/autodoc/__init__.py`):
- A new helper, `get_inherited_attr_doc`, searches the base classes of a class for the attribute's comment. It reads each base class's own module.
- `filter_members` uses it when `inherited-members` is set, so the attribute is kept.
- `add_content` uses it when the attribute isn't in the class itself, so the comment text is rendered.

**Tests:**
- I added `inheritedattr` to `Base` in the `test-ext-autodoc` test files.
- I added `test_autodoc_inherited_attribute_docs`, which passes.
- I updated two expected outputs that now include the new attribute.

**Not covered:**
- **Unverified variations:** I didn't test private attributes, attributes that a subclass redefines, or base classes from another module.
- **Behaviour change:** a subclass attribute with no comment of its own now picks up the base class's comment.
- **Log:** the helper guard limited my probes, so `.rehearsal/REHEARSAL.md` holds a single hand-run step. It showed `("ReferenceRole","name")` missing from `attr_docs` while `("SphinxRole","name")` is present.

I haven't committed anything.