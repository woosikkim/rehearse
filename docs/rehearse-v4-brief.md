# rehearse 4.0.0: finish the work, ask less

The agreed design from three consultation rounds (2026-10-20). It replaces the strike count with a record of what was tried, adds an `auto` mode that asks everything up front and nothing after, and starts three records for later improvement. It builds on the v3 brief (`rehearse-v3-brief.md`); only what changes is written here. Version 4.0.0, because `max_strikes`, `rehearse stuck` and the `stuck` phase are removed and the `confirm_ending` setting is replaced.

## 1. Why

In the first four-stage real job, stage 2 passed 37 of 39 checks and got stuck twice. Neither stuck was exhaustion: one came from a result line cut by an output filter (fixed in 3.0.1), the other from a judgment hidden in a check (3.2.0). Each stuck asked the owner to decide, and "stop here" ended the job for stages 3 and 4. Nothing in the hook could tell "tried everything" from "tried three times". A count is never failure.

## 2. The agreed layers

- **A worker stops only when everything it found by search or thought of has been tried and recorded.** Before it stops without a pass, it finds methods by web search as well as from its own knowledge, tries them, and records each as a tried route. Its stop needs at least one logged search among its tried records. The brake (two failing runs in a row) still stops a worker at once for a re-look; that stop needs no search and is not a failure.
- **Then the manager reviews as a coach.** It reads the worker's log, searches for methods itself, compares the two, and names the untried candidates, each tied to the record. In a one-stage job, where the manager did the work, a fresh read-only review worker does the review: the reviewer never did the attempts. A review cites at least one logged search. Its candidates go to a new worker, as candidates, not orders. This repeats while a genuinely new candidate remains.
- **The stage fails only under gate two** (section 3). The user is asked only in four cases: that failure; evidence that a check or the goal is wrong; something only the user can give; the irreversible step. Every question comes with what was tried and the candidate solutions.

The manager's first dispatch stays result-only (the result to reach, never the steps). After a reported failure it hands over the untried candidates. The director is unchanged: it judges "done" claims and never failure claims.

**Look failures go through the same loop.** Walls such as logins are mostly met while looking. A look worker that stops without registering an ending is treated exactly like a build worker that stops without a pass: tried records with at least one logged search before it may stop, a review (by a fresh review worker in a one-stage job), candidates to a new look worker, and gate two before "failed". The old rule "two look workers without an ending is a strike" is replaced by nothing that counts: the loop ends only through gate two.

**Continue with the best route that works, in every mode.** When a better route needs something only the user can give, the work continues with the best route that works without them, and what the better route would need goes in the report. In ask mode too, this is not a reason to stop; it may be raised at the next natural question. Only when no route works without the user does the stage wait.

**Cost is not a decision factor by default.** Certainty comes before cost and time. No design is argued against on cost alone; cost and time are recorded (section 7), not decided on.

## 3. Failure records and gates

Three records, written by commands and checked by the hook the way an ending's citations are checked today (a cited step must exist in the command log):

| record | what it holds | what the hook checks |
|---|---|---|
| `rehearse tried --route '<name>' --steps S<n>,... --outcome '<what happened>'` | one route, the logged steps that tried it, the outcome | every step exists in the log; a route with no logged steps cannot be claimed |
| `rehearse review --searched S<n>,... --candidate '<name>' '<how it differs from the tried routes>' ... [--drop '<name>' '<why it is a variant>']` | the searches, the untried candidates, the dropped variants | at least one searched step is a logged `WebSearch` (a `WebFetch` or `rehearse fetch` step may be cited alongside, never alone; with no WebSearch in the session, a stated reason is recorded and refused once the log shows one); a candidate's name is not a tried route's; in a one-stage job only `rehearse:reviewer` records the review |
| `rehearse failed --needs '<the one thing>'` or `--exhausted`, with `--summary` | the stage's honest end | gate two below; both forms also require at least one tried route citing a logged WebSearch |

Gates:

- **Gate one.** After a worker stops without a pass (a build worker) or without an ending (a look worker), the next worker of that kind is refused until a review exists, made after that stop, with at least one untried candidate. The worker's prompt carries those candidates from the job file, as the director's findings are carried today. A worker whose tried records cite no logged WebSearch is refused at its stop with "search first", unless it stopped at the brake. A review must come from fresh eyes: an agent that made any of the stage's tried records may not review them; in a one-stage job only the review worker (`rehearse:reviewer`, read-only) may record a review.
- **Gate two.** `failed` is refused while any candidate of the latest review is neither tried nor dropped, and until at least one tried route cites a logged WebSearch.

Strikes (REWORK, a worker stopping without a pass, a relock) are recorded, shown in the report body and the Process section, and never trigger anything. A REWORK needs no review: the director's findings are the candidates and go to a new build worker. The relock stays as a forced re-look. The existing deferral on resuming a worker stays: candidates always go to a new worker.

WebSearch and WebFetch are logged by the hook, so searches are citable steps. Methods are found by search: only a `WebSearch` step satisfies the search rule; a fetch of the target is a step the worker made anyway.

## 4. The wait phase and the four questions

`wait` replaces `stuck`. It is entered only by a recorded `failed`, by a check proven wrong, or by an irreversible step without an up-front OK; never by a count. Entering it means a solution-ready report: the routes tried with their steps, why each failed, the one thing needed, and everything prepared. The user's options match the question types:

- give the thing and resume: `rehearse wait --resume --says '<the user's words>'`;
- correct the check in their words: `rehearse wait --correct --says '<words>'` (the 3.2.0 guards stay: words from an answer since the wait began, only the failing checks may change);
- redo the stage at their wish: `rehearse wait --change --confirmed`;
- stop, which ends the whole job and says so: `rehearse wait --stop-here`.

A check proven wrong by evidence is raised at once with `rehearse wrong --check '<requirement>' --evidence S<n> --propose '<value>'`, instead of retrying against a check that cannot pass. Headless runs end as "not fixed" wherever they would wait. Interactive runs wait indefinitely.

## 5. Auto mode

`rehearse auto <task>` confirms as much as possible up front, then runs without asking.

- **Up front:** the goal items are asked, not assumed. The plan, the stages and the job ending are confirmed. The pre-plan looks cover every stage's targets, not only the riskiest, so logins, keys, paid plans and foreseeable judgment calls are asked together at the start: the plan command takes calls, and the job confirmation is refused while any is unanswered. The irreversible step may be OK'd up front, in the user's own words, recorded with its stamp.
- **Mid-run:** a stage that passes moves on. Stage endings found later are accepted as registered and marked "not confirmed by a person". Judgment calls found later are taken as registered and recorded. Every decision taken goes into a decisions list (the options, the one taken, the reason), and the plugin writes a "chosen on your behalf" list from it right after the report's first line, so the user can undo just those.
- **Waiting:** as in every mode (section 2), the work continues with the best route that works without the user. Auto waits only when no such route exists, with the solution-ready report. A check proven wrong also waits, because auto cannot lower a check.
- **The irreversible step:** with the recorded OK, it runs once, through its own command, only after the final director's PASS; a second run is refused; it is never inside an ending command, because an ending runs on every check and every director rerun. Risks the owner accepts: the OK precedes the content, so the final PASS is the only guard on what goes out; a half-failed step is the user's to clean up; the recorded words decide what counts as the step.
- **Headless** (evals and scripts, where nobody can answer): goal items are recorded as assumed, confirmations are accepted at registration, and any wait ends the job as "not fixed". This is the old unattended behaviour, now one switch inside auto rather than a mode of its own.

## 6. Modes and settings

- A mode word is read only right after `rehearse` (or `/rehearse`): `auto`. The colon form, `rehearse: <task>`, reads no mode word and is the escape for a task that begins with that word. `max` is reserved: it is refused with a one-line message and starts no job.
- Setting `mode` (`ask` or `auto`, default `ask`) picks the default. `REHEARSE_HEADLESS=1` (or `EVAL_REHEARSE_HEADLESS` for the eval runner) marks a run as headless. The old `confirm_ending: false` and its variable spellings map to auto plus headless, so existing eval cases keep running unchanged.
- One helper reads the mode; "attended" and "unattended" disappear from the code and the instructions.

## 7. Three records

- **After-job feedback:** `rehearse feedback '<line>'`, optionally `--job <id>`, from any session on the machine. Lines accumulate with dates on the job's file in the plugin data folder, where every job of every project lives.
- **Tokens and time**, per stage and per role (manager, worker, director), read at each agent's stop from its transcript (per-turn token counts and the model) and for the manager from the session transcript at each stage end. No dollars and no price setting.
- **False-REWORK signal:** a digest of the spawn snapshot in every verdict record, and the count of config edits between verdicts; "REWORK, then PASS with the same digest and no config edit between" is computable. An optional one-line stop reason: `rehearse stop <reason>`, and `--says` on stop here.

## 8. Self-jobs

A rehearse job may run on the rehearse repo. Since 2026-10-21 the installed plugin comes from GitHub `main` (the marketplace points at the repo on GitHub, auto-update on), so edits in the repo folder never reach any session; the one condition left is no plugin update or marketplace change while a job runs in that session. (Before that the marketplace pointed at the repo folder and auto-update copied the working tree on every version change, which put the step-1 tree into everyday sessions on 2026-10-20.) The parser, the feedback command, the token record and the digest suit self-jobs, since each has an ending that fails now and passes after; the failure loop does not.

## 9. Removed

- The `stuck` phase, `rehearse stuck`, the four-option stuck question, and the strike count as a trigger.
- The `max_strikes` setting. A saved value is ignored.
- The `confirm_ending` setting, replaced by `mode` and the headless switch; the old variables still map.
- The "no ending twice is a strike" rule.
- The words "attended" and "unattended".

## 10. Steps and proofs

1. **Modes and the fold.** Parser, `mode` setting, headless switch, legacy mapping, one helper. Proved by the parser test against the awkward cases, hook tests for each mode, and one eval case run unchanged.
2. **The three failure records and the gates.** Proved by hook tests: a tried record with an unlogged step refused; a build worker refused until a review; a review without a logged search refused; a worker's no-pass stop without a search refused; `failed` refused while a candidate is untried; `needs` refused with nothing tried.
3. **The wait phase** and its command, with the 3.0.1 and 3.2.0 guards carried over, `rehearse wrong`, and the one-stage review worker. Proved by hook tests and the removal of the stuck tests.
4. **Auto's up-front part:** plan-level calls, the irreversible OK and its single-run command, the decisions list and the chosen list. Proved by hook tests, including a second run of the step refused and the step refused inside an ending.
5. **The records:** feedback, tokens, digest, stop reason. Proved by hook tests and by the false-REWORK signal computed on the first four-stage job's file.
6. **The three evals**, then the library job's stages 3 and 4 as the real validation: the earlier stuck points pass without a call, and any call comes with solutions.

## 11. The three evals

All local, harmless, run headless in auto.

- **First route blocked, second works.** A local server where the obvious endpoint answers "key required" and a plain export file holds the same data. Pass: no question asked, a tried record for the blocked route with its steps, a logged search, the ending built on the second route.
- **A check the data cannot meet.** The request says ten items a day; the fixture has six on some days. Pass: no relock, a `wrong` record naming the check with the evidence step and a proposed correction, and an honest "not fixed" that says so.
- **Exhausted.** Every endpoint needs a key and no export exists. Pass: at least two tried routes with a logged search, a review with every candidate tried or dropped, `failed` accepted, the report listing the routes and what would be needed.

## 12. Deferred

- **max** (find and try every method, then compare): decide again after this release has been tried; the failure loop gives most of what it was wanted for.
- **retro** (automatic detection of rehearse-side failures across jobs): after the records accumulate.

## 13. Decisions taken while building

Recorded here as they are made, for the owner's review.

- Step 1: headless is a switch inside auto, not a third mode, because the hook cannot tell a headless run from an interactive one by itself; evals and scripts set it. The old `confirm_ending: false` maps to auto plus headless. Eval case files are left on the old variable for this step, so the eval run proves the mapping; they move to the new variables in a later step.
- Step 1: the job file keeps the full prompt as the request (goal citations quote it), and records the mode words apart.
- Step 1: the version number is set to 4.0.0 on the branch from the first step, since the branch is the 4.0.0 line; nothing is released until the owner says so.
- Step 1: the mode is decided once, at activation, and written into the job file; every later check reads the job file. Before, the hook re-read the `confirm_ending` variable on every call, so a variable set mid-job changed behaviour. Five tests relied on that and were aligned: a run is headless only when activated headless.
- Step 1 gate: the eval proof could not run on the installed runner. On Claude Code 2.1.305 the plugin-eval sandbox makes the working directory read-only for Bash and gives each call a private `/tmp`, so the plugin's command cannot write its record file, the stage file, fixtures or the trace; on 2.1.302 it could. The owner rejected a stdout fallback (it would reopen the cut-line hole 3.0.1 closed) and chose to report the regression and run evals on 2.1.302 side by side. Step proofs stay with the hook tests when no runner is available; the library job's stages 3 and 4 remain the live validation.
- Step 2: the hook logs `WebSearch` and `WebFetch` calls as steps (with a `tool` field), so a tried record or a review can cite them by step id; a step that is not a search is refused as `--searched`. After the owner's step-2 review: only a `WebSearch` step satisfies the rule, at a worker's stop, in every review and for both forms of `failed`; `WebFetch` and `rehearse fetch` steps may be cited alongside. When WebSearch is unavailable in a session, the record carries `--no-websearch '<reason>'`, which the Process section counts ("without a web search, reason recorded") and which is refused whenever the run's log holds a WebSearch step, so the reason cannot stand in for a search that was available.
- Step 2: the reviewer is a new read-only agent (`rehearse:reviewer`), spawned by the manager and prompted by the hook from the job file like the director; its model is `REVIEWER_MODEL`, defaulting to the director's (opus). Fresh eyes is enforced by agent kind: a review from an agent that made one of the tried records is refused. In a one-stage job only the reviewer may record a review (owner's step-2 review, point 2; an earlier line here said the manager might, which contradicted gate one and was wrong); the reviewer is allowed only while a review is due or a tried record is newer than the last review.
- Step 2: gate one holds a worker's own stop as well as the next spawn. A worker that stops without the result and without a tried record citing a search is held with "search first"; the brake stop is exempt. A stop with such a record marks the review due, records a strike (counts only) and tells the manager to review before the next worker.
- Step 2: gate two: `rehearse failed --needs` requires a tried route; `--exhausted` requires the latest review to have every candidate tried or dropped. Both end with the user's question, which still lands in the interim `stuck` phase until step 3 replaces it with the wait phase; headless jobs end `not_fixed` there. The `max_strikes` setting and `rehearse stuck` stay in place until step 3 for the same reason; the counts no longer trigger anything.
- Step 2: the Process section gains one line: routes tried, reviews, candidates dropped, and the failure record if any. Jobs from before 4.0.0 show "not recorded".
- Step 3: the `wait` phase replaces `stuck`. It is entered by `rehearse failed`, by `rehearse wrong`, and (step 4) by an irreversible step without an OK; never by a count. The job file records where the wait began (`wait_from`), and `--resume` returns the stage there; `--resume` and `--correct` carry the user's words with the 3.2.0 guards (word for word, from an answer since the wait began; correct changes only the failing checks; change needs the second yes; stop here from any question; no director while waiting; after resume an ending that already passes goes straight to the director, the 3.0.1 rule). `try again` is gone: its one use, strikes reset, no longer exists.
- Step 3: strike counts are no longer reset by an answer. A count never decides anything, so a reset would only make the record lie; the Process section counts strikes by cause from the log as before.
- Step 3: `rehearse wrong --check --evidence --propose` is accepted in look or build, names a check the last run failed, and cites logged steps; it enters the wait with the proposed correction in the note, and a worker that raised it stops with "reported a check wrong" instead of being held for a search. Headless, it ends the job as not fixed with the record kept.
- Step 3: `rehearse stuck`, the stuck phase, the `max_strikes` setting and the "stuck in look after a blocked look worker" path (3.0.1) are removed. That path is covered by the loop: a look failure ends in `failed`, which waits. A job file from 3.1.0 to 3.2.0 still shows its stuck log under the waits line ("not recorded" where it has none).
- Step 3: the failing checks are those of the last run of the ending, and the registration run counts as a run (before, `correct` saw only a later `rehearse run`, so a check that failed at registration had "nothing to apply"). `wrong` and `correct` read the same list.
- Step 3 review: `--no-websearch` is accepted only when the job was activated with the `websearch` setting off (`REHEARSE_WEBSEARCH=0`, `EVAL_REHEARSE_WEBSEARCH=0` in evals); the job file records the setting at activation so the command and the hook read the same answer. The default is available, with the escape refused; the log guard (refused when a WebSearch is in the run) stays as a second check.
- Step 4: plan-level calls are `rehearse plan --call '<question>' '<answer taken when nobody can answer>'`. They are asked before the job confirmation (on a one-stage job, before the stage confirmation) word for word like an ending's calls, through the same recording; the confirmation is refused while one is open. Headless, the registered answer is taken and listed as chosen.
- Step 4: the irreversible step is `rehearse plan --irreversible '<what it does>' '<its exact command>'`, one per job. Its OK is a plan call of its own ("May the irreversible step run once after the final pass: ...? It cannot be undone."); only a plain yes (the confirmation words) is the OK, recorded word for word. With the OK, `rehearse irreversible` runs the command once in `done.passed`; the command refuses it before the pass, without the OK, and a second time (it also reads its own earlier records, so two calls in one shell cannot run it twice); the hook refuses an ending whose command or tests contain the command text, and any Bash call containing it other than `rehearse irreversible` and `rehearse plan`. The Stop is blocked in `done.passed` while an OK'd step has not run. The words recorded in the plan decide what counts as the step (the risk the owner accepted).
- Step 4: in interactive auto a one-stage job's first ending is confirmed up front (it is the job ending), after the plan's calls; before, auto accepted it at registration, which would have skipped the up-front questions. On that yes the job counts as confirmed. Later endings in auto are accepted as registered, as in step 1.
- Step 4: the decisions list (`decisions` in the job file) records every choice taken without the user: an assumed goal item, a plan call or an ending's call taken as registered, a stage or job ending accepted without a person, the irreversible step left for the user. The plugin writes the "Chosen on your behalf" list from it right after the report's first line when the job ends, and the Process section counts it and states the irreversible step's fate.
- Step 4 review: the live invocation is declared so that it differs from the dry run (the guard matches text), both are named in the building stage's plan line, which fixes the interface, and the endings exercise the dry run. The final director's prompt names the declared step (code: the prompt is written from the job file) and director.md tells it to check the program and the dry run before PASS (instructions). One mechanical guard was added as code: a final PASS whose declared program does not exist is recorded as REWORK with the finding, since a step that cannot run cannot be retried after its one run.
- Step 5: feedback lines are kept beside the job's file in the plugin data folder (`<run id>.feedback.jsonl`), not inside it, so the rule that the command never writes the job file stands; `rehearse feedback` needs no live job and finds the job by the newest run folder under the current directory or by `--job <id>` in the data folder.
- Step 5: tokens are read from each agent's transcript at its stop (assistant turns deduplicated by message id, since one message is written as several lines) and from the session transcript for the manager at each stage end and at the job end, as the difference since its last record. Time is the stop stamp minus the spawn stamp, and the stage end minus the stage start for the manager. A transcript that cannot be read prints "tokens not readable", never zero. No dollars.
- Step 5: every verdict records the digest of the snapshot the director saw and the count of config edits since the previous verdict. The false-REWORK signal counts a REWORK followed by a PASS on the same digest with no config edit between; pairs from before 4.0.0 have no digest and are counted apart as "cannot tell".
- Step 5: `rehearse stop <reason>` records the reason; `rehearse wait --stop-here --says '<words>'` records the user's words as the reason. The Process section shows both.
- Cleanup pass (before step 6): the gate checks on tried, review, failed, wait, wrong and irreversible now live once in `hooks/gates.py`, called by the command (so the agent sees the reason before anything runs) and by the hook (so a faked result line changes nothing); the hook now also checks that a tried record's steps are logged, which only the command did before, and the command now applies the structural "no answer since the question arose" guard, which only the hook did before. The strikes counter is gone (the log is the count; a file from before 3.1.0 still shows its counter). The `status` alias, the not-verified lines for calls (the decisions list is the record), the duplicated manager bullet and the v2 `guard.py` shim are removed. The by-text command count in the Process section is frozen at the 3.0.1 command set, since it counts only records from before 3.1.0. Readers for job files from before 3.1.0 are kept.
- Install switch (2026-10-21, owner's decision): the `rehearse` marketplace now points at GitHub `woosikkim/rehearse` instead of the repo folder; `rehearse@rehearse` is 3.2.0 from `main`, auto-update on, no saved options (none existed). `claude plugin marketplace remove` deleted the plugin's data folder with the job files; the four job files that had a mirror (`.rehearsal/<run id>/state.json` in their projects) were restored, and no other file had been in the folder. The 4.0.0 cache copy was kept on disk because running sessions still call its hook path.
