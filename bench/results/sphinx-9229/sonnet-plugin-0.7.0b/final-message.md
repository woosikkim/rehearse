I've updated the repro line in `.rehearsal/REHEARSAL.md`. It builds the scaffold and counts how many times `Bar alias doc` appears in the output. The earlier repro only wrote to a file, so the hook saw no difference in output. The new one prints that count.

On the fixed code the count is 1. I didn't rerun it on the original code this turn. The earlier check, before the fix, showed only `alias of "collections.OrderedDict"` for `Bar`, so the count there should be 0.

The fix itself is unchanged and is described in my previous message.