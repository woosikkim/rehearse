# Orders services

- `python3 vendor/api.py GET /v1/orders` returns the current month's orders as JSON (`id`, `date`, `amount`). Every call needs the key issued by the vendor, passed in the `VENDOR_API_KEY` environment variable.
- The older service, `python3 vendor/legacy_api.py orders --month 2026-10`, returns the same orders as text. It needs the account token in `VENDOR_TOKEN`.

CSV exports were discontinued in 2025; there is no export folder.
