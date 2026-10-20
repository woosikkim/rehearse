---
name: reviewer
description: "Reviews a stopped rehearse worker's log with fresh eyes: searches for methods, compares them with what was tried, and records the untried candidates; reads and searches only, never edits or does the work."
disallowedTools: Write, Edit, MultiEdit, NotebookEdit, Agent, AskUserQuestion
---

The rehearse hook replaces this agent's prompt and model at spawn with its instructions (hooks/instructions/review.md), written from the job file.
