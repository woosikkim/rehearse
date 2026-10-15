I wrote `/app/program.py`, and its output matches the COBOL program's on the two cases I compared.

- **Reused vs built:** I wrote the port by hand in plain Python. It reads and rewrites the fixed 34-byte records in place, with no libraries.
- **Verified:**
  - **Your `INPUT.DAT`:** it names book B007, which doesn't exist, so validation fails. The script prints a blank line and "Transaction failed due to validation errors" and leaves the `.DAT` files unchanged. I checked this on `/app/data`.
  - **Valid transaction:** on a short-amount input (`U001U002B001200`), the Python output matched the COBOL output byte for byte in all three `.DAT` files. I compiled and ran the COBOL in a scratch copy, so `/app/data` was never touched by it.
- **Behaviors copied from the COBOL:**
  - Spaces in the amount field count as zeros, so `200` followed by blanks becomes 2000000000.
  - A negative balance is stored as its absolute value.
  - Values wrap at 10 digits.
- **Not run:** I didn't run the COBOL on an empty `INPUT.DAT`, or on other cases such as the buyer being the seller. I also didn't run the Python on a valid input that includes a full 10-digit amount; I only compared the short-amount case.

The rehearsal log is in `/app/.rehearsal/REHEARSAL.md`.