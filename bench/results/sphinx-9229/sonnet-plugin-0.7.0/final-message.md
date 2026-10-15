I replaced the reproduction in `.rehearsal/REHEARSAL.md` with one that does show the bug. It forces a full rebuild (`-E -a`) into a fresh output directory and prints `index.txt`. The earlier command reused a stale `.rehearsal/out`, so both runs looked the same.

I ran it on the original code (via `git stash`) and on the fixed code:

- **Original code:** the output is only `alias of "pathlib.PurePath"` and `alias of "collections.OrderedDict"`.
- **Fixed code:** the output is `Alias doc.` and `Alias2 doc. More.`.

The fix is back in place. `git status` shows only `CHANGES` and `sphinx/ext/autodoc/__init__.py` modified, plus the untracked `.rehearsal/` folder.