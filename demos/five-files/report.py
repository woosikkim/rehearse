def monthly_totals(rows):
    totals = {}
    for row in rows:
        month = row["date"].strftime("%Y-%m")
        totals[month] = totals.get(month, 0) + row["total"]
    return dict(sorted(totals.items()))
