def to_amount(text):
    return float(text)


def line_total(row):
    return to_amount(row["price"]) * int(row["qty"])
