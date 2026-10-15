# Demo: two bugs

The same tiny order report as the five-files demo, with a different trap. The wrong number shows up in one file, the cause sits in another file upstream, and right next to the wrong number is a second, real bug that looks guilty but is not the cause.

## The files

1. `main.py` runs everything: read, normalize, price, report.
2. `reader.py` turns `orders.csv` into a list of rows.
3. `normalize.py` reads the dates. **The cause is here**: it reads `04/03/2024` as April 3 (month first), but the file means 4 March (day first).
4. `price.py` turns prices into numbers.
5. `report.py` adds up the totals per month. **The symptom shows here**, and so does the decoy: `money()` cuts a total to two decimals instead of rounding it, so 1.15 becomes 1.14. That is a real bug, but it does not change any total in this file.

## The bug report

> The March total is wrong.

## Try it

```
cd demos/two-bugs && claude --plugin-dir ../..
```

Prompt:

```
rehearse: fix the March total in the report, it is wrong
```

## Run it

```
python3 main.py
```

Before the fix:

```
2024-03  80.00
2024-04  127.50
2024-07  40.00
2024-12  30.00
```

After the fix:

```
2024-03  162.50
2024-04  115.00
```

March by hand: 80.00 from the four dashed dates, plus 12.50 + 40.00 + 30.00 = 82.50 from the three slashed ones.

## Expected story

The agent sees March at 80.00 in the report, and the three slashed orders turning up in April, July and December. It is tempted by `money()` in `report.py`, which really is wrong. But calling it by hand shows it returns 80.0 for 80.0: it is not why March is short. Chasing the value upstream, it calls `normalize.parse_date("04/03/2024")` and gets April 3. That is where the value is first made wrong, so the fix goes in `normalize.py`.

A good run:

- changes `normalize.py` to read day first;
- names the rounding bug in `report.py` in the report, or fixes it too, without calling it the cause;
- does not patch `report.py` alone.
