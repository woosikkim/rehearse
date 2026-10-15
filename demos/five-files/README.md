# Demo: five files

A tiny order report. One bug, spread across five files.

## The files

1. `main.py` runs everything: read, normalize, price, report.
2. `reader.py` turns `orders.csv` into a list of rows.
3. `normalize.py` cleans the dates. The planted bug is in this file.
4. `price.py` turns prices into numbers. A second problem hides in this file.
5. `report.py` adds up the totals per month.

## The bug report

> The March total is missing three orders.

## Try it

```
cd demos/five-files && claude --plugin-dir ../..
```

Start the session inside the folder so the paths resolve. Prompt:

```
rehearse: fix the missing March orders
```

Without the word `rehearse` the plugin stays out of the way, so `fix the missing March orders` shows what the agent does on its own.

## Expected story

File 3 drops the rows whose dates it cannot parse. Reviving them makes file 4 fail on a price written with a comma, so both get fixed, and the hand-computed March total is the expected value.

## Run it

```
python3 main.py
```

Before the fix:

```
2024-03  80.00
2024-04  115.00
```

After the fix:

```
2024-03  162.50
2024-04  115.00
```

March by hand: 80.00 from the four ISO-dated orders, plus 12.50 + 40.00 + 30.00 = 82.50 from the three missing ones.

## What a good run looks like

In `.rehearsal/<run id>/`:

- `log.md` has a step that calls `normalize.parse_date("04/03/2024")` by hand through the stage, and one that calls `price.to_amount("12,50")`.
- The comma price is logged as a chain link with "Revealed by" the date fix.
- Before the first edit, the agent asked in one plain sentence: "When I run the report, March should show 162.50; right now it shows 80.00."
- `report.md` starts with `fixed`, and its ending table shows 162.50 expected and matched, with the director's verdict.
