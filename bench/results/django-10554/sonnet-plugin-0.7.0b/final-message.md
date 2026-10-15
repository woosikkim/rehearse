I couldn't reproduce the reported crash on this checkout, so I haven't changed any code. I need a decision from you before going further.

**What I ran** (SQLite, `tests.queries` models, real evaluation plus `str(qs.query)` with the compound-ordering flag flipped to mimic PostgreSQL):
- The ticket's sequence works: `A.union(B).order_by('order')`, then `qs.order_by().values_list('pk', flat=True)`, then `qs` again. I also tried it with slicing (what `repr` does), with `F('order').asc()` ordering, with `Meta.ordering` models, and with ordered operands. The SQL, `qs.query.order_by` and each `combined_queries[i]` are the same before and after the `values_list` call.
- A mutation like the one in the ticket (parts losing columns while the outer `ORDER BY (4)` stays) is what `14d026cccb` fixed. That commit is already in HEAD: "Prevented values()/values_list() on combined queryset from mutating the list of columns". It clones the part query before calling `set_values`.

**A related failure that does still occur.** This raises `DatabaseError: ORDER BY term does not match any column in the result set`:
```python
u = R.objects.filter(order__gte=6).union(R.objects.filter(order__lte=5))
list(u.order_by('name', 'order').values_list('order', flat=True))
```
`name` isn't in the `values_list` select, so `get_order_by` (`compiler.py:359`) rejects it. This may be what the ticket is really about: ordering on derived querysets. I haven't confirmed that.

**Not covered:** I couldn't test PostgreSQL. There is no `psycopg2` or server here, and SQLite rejects `ORDER BY` inside compound parts, so I can't run the ticket's exact SQL.

**Decision for you:** should I treat the `values_list`-with-ordering failure above as the bug and fix it in `get_order_by`? If you have a PostgreSQL setup, or the exact model definition and a failing test, that would let me reproduce the original traceback instead.

The rehearsal log and fixtures are in `.rehearsal/`; the guard marker is removed.