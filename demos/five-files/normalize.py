from datetime import datetime


def parse_date(text):
    try:
        return datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return None


def normalize_rows(rows):
    kept = []
    for row in rows:
        row["date"] = parse_date(row["date"])
        if row["date"] is None:
            continue
        kept.append(row)
    return kept
