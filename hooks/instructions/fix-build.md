## Build: fix, then rerun

The ending is registered and confirmed; edits are open. Read the log, the fixtures and the ending first: they hold what the look found.

Change the code where the value is first made wrong, and fix any chain link the same way. As soon as you have a candidate change, apply it to the project's real files, never to a copy, and run `rehearse run` when you expect it to pass. The ending runs on the project's files, so a change that exists only in a copy is not a fix. Keep chasing upstream only while the ending still fails.

**The stopping rule.** When `rehearse run` passes, stop chasing and stop working: say so in your final message. The manager starts the director. If a note says edits are locked again, stop at once and say what you learned; the next look starts from there. If the director's findings are listed below, address each one.
