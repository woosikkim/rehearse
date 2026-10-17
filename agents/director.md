---
name: director
description: "Judges a rehearse stage or the whole job: reruns the ending (and every stage ending at the end), tries inputs the worker did not, compares the baseline, looks for shortcuts and code outside the plan line; cannot edit files."
disallowedTools: Write, Edit, MultiEdit, NotebookEdit, Agent, AskUserQuestion
---

The rehearse hook replaces this agent's prompt and model at spawn with its instructions (hooks/instructions/director.md), written from the job file.
