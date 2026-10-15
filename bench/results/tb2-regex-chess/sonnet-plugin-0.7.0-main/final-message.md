I ran the sweep: the only caller of `re.json` is `check.py`, and the only writer is `gen_re.py`. I also tried three positions by hand that the Opera Game doesn't reach.

| Position | Moves returned | Expected |
|---|---|---|
| Castling, both sides (`r3k2r/8/8/8/8/8/8/R3K2R`) | 26 | 26 |
| En passant (`4k3/8/8/3pP3/8/8/8/4K3 w - d6`) | 7 | 7 |
| Promotion (`4k3/P7/8/8/8/8/8/4K3`) | 6 | 6 |

The 26 is my own count, not a python-chess comparison. Castling is also covered by the 320-position random check.

The en passant case is 5 king moves, the pawn push and the capture. The promotion case is 5 king moves plus the single queen promotion. No fixes were needed.

`/app/re.json` is final and `.rehearsal/` is left in place as the evidence.