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

**Judgment calls first.** When the ending rests on a borderline call (is X a tool? does Y count?), the look worker registered it with `--call`, and the plugin's note lists each one. Put each to the user as its own question, **word for word as registered**, before the confirmation, never as one line among dozens of checks. The plugin records the answer against the check it decides, and **refuses the confirmation while any call has no recorded answer**, naming the call to ask. With the question tool, a question that does not contain the registered wording is not matched and is refused. Without the question tool, ask the calls one per message in the registered order: the next message answers the first open call. If an answer changes a check, do not ask the confirmation: run `rehearse ending` again with the corrected value (cite `request`: the user's words are now part of it); the answers carry over. Only when every call is settled, ask the confirmation.

## The job (two or more stages)

One question with: the goal items (each marked from the request, from the user's answers, or assumed), the assumptions, the blockers, the stages with their plan lines (and whether they came from the request, with any merge you propose), the worker and director models, and the job ending's command and expectations.

Options: `yes`, `no, change the plan`, `stop here and write the report`.

## The wait question

The stage waits only after a recorded failure, a check proven wrong, or an irreversible step without an OK. Give a solution-ready report first: the routes tried with their logged steps, why each failed, the one thing needed, and everything prepared so that the user's answer is the last missing piece. Name the checks that fail (the plugin's note lists them) and what the director found. Then offer exactly these four options, each with what it does and what it costs, and say which one applies:

- `give what is needed` (a key, a login, a file, a decision): the stage resumes where it waited with their answer; an ending that already passes goes straight to the director. Costs what remained of the stage.
- `these checks are wrong`: the failing checks encode a judgment the user disagrees with, or a check the target cannot meet (the plugin's note names the proposed correction when a `wrong` record raised it). The work stays; only the ending changes to match their answer, then the director judges. Costs one director run.
- `redo this stage`: the stage is looked at again and rebuilt: a look worker, the ending registered and confirmed again, the build, the director. Costs a whole stage again. Needs a second, explicit yes.
- `stop here`: **ends the whole rehearse job now**, not just this stage: `report.md` says `not fixed`, and every remaining stage runs without rehearse. Nothing more is checked.

Never frame this as "how do you want to accept" or "continue?": one option ends the job, and the user must see that. A question from the user is not a decision: answer it, then ask again. The plugin never reads the decision from the user's words; only `rehearse wait` records it, and the stage waits until it runs.

## After the answer

- `yes`: the next step opens (a build, or stage 1's look). A proposed merge applies only on this yes.
- Any other answer to a stage ending (`no`, a correction): the plugin moves the stage back to look and records the user's words. Start a look worker for the same stage and pass it the user's words; on a one-stage job, look again yourself, register the corrected ending, and ask again.
- Change the plan: run `rehearse plan` again (once a stage has passed, `rehearse plan --stage <n>` with exactly one `--stage-def` and no goal flags), or `rehearse ending --job` for the job ending, and ask again.
- `stop here` (at any question): run `rehearse wait --stop-here`, write `report.md` starting with `not fixed`, saying what is known so far, and finish.
- `give what is needed`: run `rehearse wait --resume --says '<the user's words>'`. The words must be theirs, word for word, from an answer since the wait began; a paraphrase is refused. Follow the next step it prints: a worker, or the director when the ending already passes.
- `these checks are wrong`: run `rehearse wait --correct --says '<the user's words>'`. The words must be theirs, word for word, from an answer since the wait began; a paraphrase is refused. Then register the ending again yourself (`rehearse ending`, no look step needed): the same command and tests, and only the checks that were failing may change, citing `request` for a value from their words; any other check added, removed or changed is refused. Then ask the confirmation. If it already passes, the director judges next; the report lists every corrected check with the user's words.
- `redo this stage`: ask once more, yes or no: "Redo stage <n> from the look? Its ending gets registered and confirmed again, then it is built and judged again." Only after a yes: `rehearse wait --change --confirmed`, then rewrite the stage with `rehearse plan --stage <n>`, exactly one `--stage-def` and no goal flags (in the final stage, register the job ending again instead), then a look worker.
