`source-read` still doesn't fire for text pulled in by `.. include::`. I added a new `include-read` event instead, which does. Your extension needs to connect to it as well as `source-read`. I haven't added a test or a changelog entry.

I reproduced the bug first. `source-read` fires for `index` and for `something-to-include` as its own page. It never fires for the included text, because docutils reads that file directly, bypassing Sphinx. That is why your replacement landed in the standalone page but not in `index.html`.

- **`sphinx/directives/other.py`:** `Include.run` now emits `include-read` with the included file's path, the parent docname and the file's text (`source`). It only does this when something is listening. A handler can rewrite the text the same way as in `source-read`.
- **`sphinx/events.py`:** registers the event.
- **`doc/extdev/appapi.rst`:** documents it. I wrote `versionadded:: 7.2.5`, which is a guess; change it to the real release.

I checked it on your repro project. With a handler on `include-read`, it fired once, with `/tmp/repro/something-to-include.rst`, `index` and the included text. I only printed the event arguments. I did not run your replace extension or inspect the final HTML. I also did not run the existing test suite.

The repro files and the log (`.rehearsal/REHEARSAL.md`) are left in place.

To fix your case, connect the same function to both events:

```python
app.connect('source-read', subst_vars_replace)
app.connect('include-read', lambda app, path, parent, source: subst_vars_replace(app, parent, source))
```