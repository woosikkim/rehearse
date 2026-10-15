I found a command that gives different output before and after the fix, and it's saved as the `repro:` line in `.rehearsal/REHEARSAL.md`. It doesn't reproduce the original crash.

The command builds a union queryset and derives `qs.order_by().values_list("pk", flat=True)` from it. It then changes a part of the derived queryset and prints the SQL of the original `qs`.

- **Before the fix:** the original `qs` SQL showed only `id` in its first part, so changing the derived queryset also changed the original.
- **After the fix:** the original `qs` SQL keeps the full column list (`id`, `name`, `order`).

I couldn't reproduce the PostgreSQL error from the ticket on sqlite. What I confirmed is the root cause, that clones shared their part queries, and that `Query.clone()` now copies them.