Sweep finished, and it found nothing else to fix.

- **Callers and siblings:** `grep -rn "insert_input\|BaseInclude\|note_included" sphinx` shows one `Include` directive and no other place that wraps docutils' include. `literalinclude` reads its file through its own code, so it isn't affected.
- **Nested includes:** I built a document that includes `a.inc`, which itself includes `b.inc`, with no handler connected. The text builder produced the content in the right order, with no stray marker lines.
- **Not exercised in that probe:** I didn't connect `include-read` in the nested build, so I haven't seen a handler fire on `b.inc`. The `<...>` standard-include form and the `:parser:` option don't use the new hook.