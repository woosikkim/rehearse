# Orders service

`python3 vendor/api.py GET /v1/orders` returns the orders of the current month or of a month given as `?month=<year>-<month>` as JSON (`id`, `date`, `amount`).
Every call needs the key issued by the vendor, passed in the `VENDOR_API_KEY` environment variable.

A CSV export of the same orders is written to `exports/orders-<year>-<month>.csv` on the first day of the following month.
