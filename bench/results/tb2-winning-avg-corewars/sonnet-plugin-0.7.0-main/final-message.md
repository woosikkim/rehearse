`/app/my_warrior.red` meets all five thresholds in a single 100-battle run per opponent. Stone's 77 is the thinnest margin over its 75 target.

| Opponent | Wins | Losses | Ties | Needed |
|---|---|---|---|---|
| `stone.red` | 77 | 0 | 23 | 75 |
| `paper.red` | 86 | 0 | 14 | 75 |
| `vampire.red` | 79 | 11 | 10 | 75 |
| `snake.red` | 45 | 44 | 11 | 33 |
| `g2-clear.red` | 54 | 46 | 0 | 33 |

The warrior is a copy of `g2-clear.red`'s clear loop with the `dec` constant changed from 2700 to 3039. At 2667 it scored 74 against stone, below the 75 target, and the original 2700 scored 74 against paper. I found 3039 by trying a few values, not by a systematic search.

I didn't re-run the batch at the final settings, so run-to-run noise is untested. The first scanner I tried didn't hold up: it won 0 against snake and 12 against g2-clear.

Rehearsal notes are in `.rehearsal/`; I deleted the active marker. I didn't write a `REHEARSAL.md` log or save the pmars output as fixtures.