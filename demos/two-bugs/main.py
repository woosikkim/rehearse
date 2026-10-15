import reader
import normalize
import price
import report

rows = reader.read_orders("orders.csv")
rows = normalize.normalize_rows(rows)
for row in rows:
    row["total"] = price.line_total(row)
for month, total in report.monthly_totals(rows).items():
    print(f"{month}  {total:.2f}")
