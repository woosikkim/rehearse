# rehearse: confirming the ending

Before any edit, the person who asked confirms that the ending says the right thing.

**Ask in this shape.** A plain sentence first, then the details:

> When I run the report for March, it should show 162.50; right now it shows 80.00.
>
> Command: `python3 main.py`
> Right now: `2024-03  80.00`
> Expected: `2024-03  162.50` (from step S6)

- The sentence names what the user would see, in their words, with the expected value and today's value.
- Then the exact command, the output before the fix, and each expected value with its source.

**How to ask.**

- When the AskUserQuestion tool is available, ask with it, with these options:
  - `yes`
  - `no, the expected value is wrong`
  - `stop here and write the report`
- When it is not available, write the sentence and the details, then stop. The user's next message is the answer.
- In an unattended run (the plugin's `confirm_ending` setting is off), still write the sentence and the details, then spawn `rehearse:director` with the Agent tool instead of asking. It reviews the ending against the request and either confirms it or lists what it does not cover; register those too, then spawn it again. After two reviews the plugin accepts the ending as it stands; the report lists what the review still found uncovered.

**After the answer.**

- `yes`: edits open. Go on to the fix or the build.
- The expected value is wrong: look again by hand, register a corrected ending, and ask again.
- `stop here and write the report`: write `report.md` starting with `not fixed`, saying what is known so far, and finish.
