from datetime import datetime


def parse_date(text):
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return None


def normalize_rows(rows):
    kept = []
    for row in rows:
        row["date"] = parse_date(row["date"])
        if row["date"] is None:
            continue
        kept.append(row)
    return kept
