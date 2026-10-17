# rehearse: confirming with the user

Only the manager asks the user. Ask with AskUserQuestion when it is available; otherwise write the question and stop, and the user's next message is the answer. Each question goes once, in one call.

## A stage ending

**Ask in this shape.** A plain sentence first, then the details:

> When I run the report for March, it should show 162.50; right now it shows 80.00.
>
> Command: `python3 main.py`
> Right now: `2024-03  80.00`
> Expected: `2024-03  162.50` (from step S6)

- The sentence names what the user would see, in their words, with the expected value and today's value.
- Then the exact command, the output now, and each expected value with its source.
- **On a one-stage job** there was no job confirmation, so the same question also lists the four goal items (purpose, deliverable, done, out of scope) and every assumption.
- **After edits locked again or a change**, also list the look steps taken since then. If the ending already passes, say so: the director checks it next, with no build.

Options: `yes`, `no, the expected value is wrong`, `stop here and write the report`.

## The job (two or more stages)

One question with: the goal items (each marked from the request or assumed), the assumptions, the blockers, the stages with their plan lines (and whether they came from the request, with any merge you propose), the worker and director models, and the job ending's command and expectations.

Options: `yes`, `no, change the plan`, `stop here and write the report`.

## The stuck question

Say what blocked the stage in plain words, then ask: `stop here`, `try again`, or `change the stage`.

## After the answer

- `yes`: the next step opens (a build, or stage 1's look). A proposed merge applies only on this yes.
- Any other answer to a stage ending (`no`, a correction): the plugin moves the stage back to look and records the user's words. Start a look worker for the same stage and pass it the user's words; on a one-stage job, look again yourself, register the corrected ending, and ask again.
- Change the plan: run `rehearse plan` again (once a stage has passed, `rehearse plan --stage <n>` with exactly one `--stage-def` and no goal flags), or `rehearse ending --job` for the job ending, and ask again.
- `stop here`: write `report.md` starting with `not fixed`, saying what is known so far, and finish.
- `try again`: strikes reset, and the stage's last step runs again: a build worker, or a look worker if the stage was blocked while looking.
- `change the stage`: rewrite the stage with `rehearse plan --stage <n>`, exactly one `--stage-def` and no goal flags (in the final stage, register the job ending again instead), then a look worker.
