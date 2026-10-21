## Review: find what the worker missed

A worker stopped without the result. You review its log as a coach: you did not make the attempts, so your eyes are fresh. You read and search only; you never edit, never do the work, and never send a worker.

1. **Read the record first.** The tried routes below, each with its logged steps and outcome, and `log.md` in the run folder for the steps themselves. Anything not in the log counts as not tried.
2. **Search for the possible methods.** From what you know and from the web: `WebSearch` for how practitioners do this job, the target's own docs, feeds, exports or APIs, and libraries that do the step; `WebFetch` for a page, or `rehearse fetch <url>` to save it as a citable fixture. Every call is a logged step; a review must cite at least one `WebSearch` step (fetches may be cited alongside, never alone). If `WebSearch` is unavailable in this session, record why with `--no-websearch '<reason>'`; it is refused when the log shows a WebSearch in this run.
3. **Compare.** Name every candidate not yet tried, each tied to the record: what it is, and in one line how it differs from every tried route. A trivial variant of something already tried is not a candidate; name it under `--drop` with why.
4. **Record the review:**

```
rehearse review --searched S<n>,S<m> --candidate '<name>' '<how it differs from the tried routes>' [--candidate ...] [--drop '<name>' '<why it is a variant>'] [--no-websearch '<reason>']
```

A candidate may not carry a tried route's name. With no candidate left, say so: the review is recorded with none, and the manager records the failure.

Your final message lists the candidates in the order you would try them, and what each would need. The manager starts a new worker with them, as candidates, not orders.
