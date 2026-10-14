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

Start the session inside the folder so the paths resolve. Try each prompt in a fresh session:

- `rehearse: fix the missing March orders`
- `fix the missing March orders`

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

## What a good rehearsal log looks like

- A `### S` step that calls `normalize.parse_date` or `price.to_amount` by hand.
- A "Revealed by" note on the file-4 failure.
- A "What I'd change and why" section.
