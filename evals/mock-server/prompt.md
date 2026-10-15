---
max_turns: 150
timeout_seconds: 3600
allowed_tools: [Bash, Read, Write, Edit, Glob, Grep, Agent]
env:
  EVAL_REHEARSE_CONFIRM_ENDING: "0"
---

rehearse: build a script that lists item names and prices from the local API. The API is described in API.md.
