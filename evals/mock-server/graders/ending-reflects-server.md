---
type: llm
focus: trace
---
The ending registered with `rehearse ending` is built from what the server really answered, not from API.md: its expected values come from a fetch of /api/v1/items (cited as a fixture or step), and its prices are 19.99, 5.49 and 120.00 converted from the server's price_cents field (1999, 549, 12000). An ending that uses /api/items or a "price" field fails.
