I'm stuck on a guard problem, not a code problem, so I'm stopping to ask.

**What I found.** Running the repro by hand showed the bug. When a class is documented under another name, as in `Alias = Path` followed by a `"""docstring"""`, the docstring is dropped. Only `alias of "pathlib.Path"` is shown. This happens when the class lives in a different module from the alias. On the Python 3.6 in the report, typing generics like `Dict[...]` are classes, so they hit this path. Aliases of a class from the same module work. `Dict[str, Any]` and `Union[str, None]` aliases also work on this repo's Python 3.9.

**The cause.** `ClassDocumenter.add_content` (`sphinx/ext/autodoc/__init__.py`, about line 1724) has two problems:
- It reads doc comments from the analyzer for the class's real module (`typing` or `pathlib`), not the module where the alias is defined.
- It always replaces the content with `alias of ...`.

**The planned fix.**
- When `doc_as_attr` is set and `self.modname != self.get_real_modname()`, build the analyzer from `self.modname`.
- Add the `alias of` text only if no variable comment exists. A small `get_variable_comment()` helper would do the lookup.

**The blocker.** The rehearse guard rejects my edit to `sphinx/ext/autodoc/__init__.py`. It says "nothing has been run yet", even after I raised the marker, ran a `python3 -c` call against the existing code, and removed the marker. I did that twice. The log (`.rehearsal/log.md`) stopped recording calls after the early ones. I haven't tried to get around the guard through the shell.

Which should I do?
1. Delete `.rehearsal/` as the guard suggests, then edit and verify with the same scaffold repro. This throws away the rehearsal log and fixtures.
2. Leave the guard alone while you check why it isn't logging.

I'd pick option 1.