`/app/program.py` is written. In my two tests it produced `.DAT` files byte-identical to the ones the COBOL program produced.

I compiled `program.cbl` with `cobc` in a scratch copy under `/tmp` and ran both versions on the same starting data. The two tests were:
- **A normal sale:** buyer `U001`, seller `U002`, book `B001`, input `U001U002B001200`.
- **Buyer and seller the same account:** `U002U002B0020000000050`.

The COBOL behaves in some ways you might not expect, and the Python copies them:
- **Short amount:** `INPUT.DAT` is only 15 bytes, so the amount field is padded with spaces and read as zeros. `200` becomes 2000000000.
- **Balance arithmetic:** balances are unsigned 10-digit fields. A subtraction that goes negative stores the absolute value, and anything over ten digits is cut off.
- **Same buyer and seller:** the COBOL rewrites the account record twice in a row, which is a runtime error. The program aborts after the buyer's debit has been written. `BOOKS.DAT` and `TRANSACTIONS.DAT` are not touched, and the Python stops at the same point.
- **Failed validation:** if the buyer, seller, book or book owner doesn't check out, nothing is changed. The checked-in `INPUT.DAT` asks for book `B007`, which doesn't exist, so running `program.py` on it leaves the data unchanged.

I haven't tested an empty input file, duplicate account IDs, or non-numeric characters in the amount.

The scratch copies are in `/tmp`, and my notes are in `/app/.rehearsal/REHEARSAL.md`.