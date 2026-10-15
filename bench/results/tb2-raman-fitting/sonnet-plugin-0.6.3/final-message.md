I searched the project for other readers or writers of `graphene.dat` and `results.json`. The only other hits were in the `.rehearsal/` logs, so there are no other callers or sibling code to fix.

I then read `/app/results.json` back. It parses as valid JSON, and its G and 2D x0 values (1580.33 and 2670.09 cm⁻¹) match the fit output.

The fit results are unchanged from my last message. The G peak is at 1580.33 cm⁻¹ and the 2D peak at 2670.09 cm⁻¹. Both are in cm⁻¹ after converting the file's first column with 1e7/x.