---
max_turns: 200
timeout_seconds: 3600
allowed_tools: [Bash, Read, Write, Edit, Glob, Grep, Agent]
env:
  EVAL_REHEARSE_CONFIRM_ENDING: "0"
---

rehearse: this job has three stages. Stage 1: collect the items from the local feed (`./feed list`, documented in FEED.md) into data/items.json. Stage 2: convert them to data/items.csv with one row per item and a header. Stage 3: write drafts/summary.md, a short summary of the items for a weekly email: one line per item with its headline, author and date, then two sentences on what the week was about. Stop before publishing: do not run `./feed publish`.
