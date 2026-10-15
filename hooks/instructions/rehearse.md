# rehearse is on

You are in a rehearse run. First decide the mode:

- **fix**: a program exists, runs now, and gives a wrong result or an error.
- **build**: everything else (a new program, or one that does not run yet).

Then read the instructions for that mode and follow them from the top:

- fix: `${CLAUDE_PLUGIN_ROOT}/hooks/instructions/fix.md`
- build: `${CLAUDE_PLUGIN_ROOT}/hooks/instructions/build.md`

The confirmation template both use is `${CLAUDE_PLUGIN_ROOT}/hooks/instructions/confirm.md`.
