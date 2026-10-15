def money(value):
    """Keep two decimals for the report."""
    return int(value * 100) / 100


def monthly_totals(rows):
    totals = {}
    for row in rows:
        month = row["date"].strftime("%Y-%m")
        totals[month] = money(totals.get(month, 0) + row["total"])
    return dict(sorted(totals.items()))
