# Why plain-confirmation is a pattern, not a judge

On 2026-10-15 the judge version of this grader voted FAIL FAIL FAIL on all three runs of the full suite
(results 2026-10-15T19-58-00-320Z). The sentence it was asked to find was present in each run, before the
first edit and followed by the command:

- run 1: "When you run the report, March should show **162.50**; right now it shows **80.00**."
- run 2: "When I run the report, March should show **162.50**, but right now it shows **80.00**."
- run 3: "When you run the monthly report, March should show **162.50** with the three missing orders included. Right now it shows **80.00**."

The eval tool records only the vote tally, not the judge's reasoning, so the cause is unknown. The pattern
checks the same thing deterministically: the sentence shape with both values. The template in
hooks/instructions/confirm.md is unchanged.
