The sweep found no problems, so I made no further edits.

**Callers:** `grep` shows `sanitize` and `clean_url` are used only inside `filter.py`. There are no other callers or sibling implementations in `/app`.

**Second sample (`.rehearsal/fixtures/sample2.html`):**
- **Uppercase tags and attributes:** `<SCRIPT>`, `ONCLICK` and `HREF` were all handled.
- **Scheme tricks:** `&#106;avascript:` and `java&#9;script:` had their `href` removed.
- **`data:` URLs:** `data:text/html` had its `href` removed. The inline `data:image/png` image was kept.
- **Other vectors:** the CSS `url(javascript:...)` style, the `<meta refresh>` to `javascript:`, svg `xlink:href` and the conditional-comment script were all removed.
- **Unclosed script:** a trailing `<script>` with no closing tag was dropped.
- **Preserved content:** the non-ASCII `value="é ünï"` came through intact, as did `autofocus`.

**Not run:** I did not test non-UTF-8 files or deeply malformed HTML, and there is still no `REHEARSAL.md` log. Nothing else is outstanding.