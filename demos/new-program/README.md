# Demo: new program

A three-item shop on your own machine. The task is to write a script that reads it.

## Before the session

Start the server in a separate terminal. It blocks, so it must not be run from the agent's own shell.

```
cd demos/new-program && python3 -m http.server 8765 -d site
```

## Try it

Start the session inside this folder:

```
cd demos/new-program && claude --plugin-dir ../..
```

Prompt:

```
rehearse: write a script that lists every item's name and price from http://localhost:8765 as CSV
```

## Expected result

| Name         | Price   |
|--------------|---------|
| Blue Mug     | $19.99  |
| Sticker Pack | $5.49   |
| Desk Lamp    | $120.00 |

The dollar sign is optional in the CSV: `19.99` and `$19.99` both count as right.

## What a good run looks like

In `.rehearsal/<run id>/`:

- `log.md` shows a check for an existing tool before anything was built.
- `fixtures/` holds the three item pages, saved with `rehearse fetch`.
- The odd third item was noticed by hand, before any code: its price sits in a table cell, not in a `price` span like the other two.
- The ending expects all three rows, and `report.md` shows them matched, with the director's verdict.
