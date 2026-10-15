---
name: rehearse
description: Start a rehearse run for the task that follows - look by hand, register and confirm the ending, then fix or build, and have the director check it.
user-invocable: true
disable-model-invocation: true
---

# /rehearse

The task follows this command. Typing `/rehearse` started a rehearse run: the plugin's hook created the run and gave you its instructions, ending with the run id. Follow them from the top.

If you see no rehearse instructions and no run id, the hook could not start the run. Run `rehearse status` to see whether a run is active, and tell the user what it printed.

To stop at any time, the user types `rehearse stop`.
