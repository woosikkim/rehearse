The sweep is done and found nothing to fix. The only file that refers to the gBlock is `/app/gblock.txt` itself, so nothing else depends on it.

I re-checked the file by hand:
- It is one line, and it starts with the FLAG codons `GAC TAT AAG GAT GAT GAT GAC AAA`.
- It ends with the last MGMT codons `…CTG GGT AAA CGT`, with no stop codon.
- Translating in frame, the earlier check found no stop codon (`'*'` absent). A raw grep for `TAA`, `TAG` or `TGA` finds 90 hits, but those are in other reading frames, so they don't matter.