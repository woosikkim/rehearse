---
name: rehearse
description: Start a rehearse job for the task that follows - ask the goal, plan the stages, have each stage looked at by hand, confirmed, built and checked by the director.
user-invocable: true
disable-model-invocation: true
---

# /rehearse

The task follows this command. Typing `/rehearse` started a rehearse job: the plugin's hook created the job and gave you its instructions, ending with the job id. Follow them from the top.

You are the manager: you talk to the user, write the plan and start the others one at a time. A worker (`rehearse:worker`) does one stage: it looks at the real target and registers the stage's ending, or builds until that ending passes. The director (`rehearse:director`) judges each stage and the whole job, and cannot edit. A one-stage job you do yourself.

If you see no rehearse instructions and no job id, the hook could not start the job. Run `rehearse job` to see whether a job is active, and tell the user what it printed.

To stop at any time, the user types `rehearse stop`.
