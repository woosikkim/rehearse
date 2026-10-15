I saved the query to `/app/solution.sparql`, but I haven't run it. This machine has no SPARQL engine (no rdflib, no pip), so I checked the logic by hand against the data.

- **Full professor:** the role must match `^Professor\b`. That excludes "Assistant Professor…" (Voulodimos, Mueller).
- **EU country:** an `EXISTS` filter checks that at least one of the professor's departments belongs to a university in one of the 27 EU member codes. Switzerland, the US and the UK don't count.
- **More than 10 current students:** a subquery counts distinct students per department across all courses taught there.
  - A student counts if their enrollment date is on or before 2025-08-16.
  - They also need no graduation date, or one after 2025-08-16.
- **Countries column:** the query lists every country the professor works in, not only the EU ones. If you want only EU countries in that column, the `?country` pattern needs a filter too.

By hand, the query should return these three professors:

| Professor | Countries | Why they qualify |
|---|---|---|
| Orfeas Menis | GR, US | Computer Science at NTUA has 12 students. |
| Pepe Attanasio | PT, GR | He also works in Computer Science at NTUA (12 students). |
| Aristotle Tympas | GR | History and Philosophy at NKUA has 12 students. |

The others are excluded:
- Marie Dubois: Sorbonne Mathematics has only 7 current students.
- John Smith: MIT is not in the EU.
- Voulodimos and Mueller: they are assistant professors.

I counted Aristotle Tympas's NKUA department at 12 by hand, which is just over the threshold. A one-student counting error would change that result.

One risk: the department-count subquery sits inside `FILTER EXISTS`. Some SPARQL engines handle that differently from the spec, so run it once on your engine to confirm the three rows above.