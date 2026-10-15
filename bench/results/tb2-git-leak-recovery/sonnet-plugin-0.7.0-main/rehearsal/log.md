$ git -C /app/repo log --oneline --all
c6d9997 chore: init e665d1a2-04a7-4e61-b523-e897e231d9cc
7a2420e chore: init e665d1a2-04a7-4e61-b523-e897e231d9cc

$ cd /app/repo && grep -rnoE "secret\[[^]]*\]" . 2>/dev/null | head; git count-objects -v; git fsck --lost-found --no-reflogs 2>&1 | head
count: 9
size: 36
in-pack: 0
packs: 0
size-pack: 0
prune-packable: 0
garbage: 0
size-garbage: 0
dangling commit 6b4c75caa9a2aa9a630e16764007b0109b1f5c07

$ git -C /app/repo reflog; git -C /app/repo stash list; git -C /app/repo show --stat HEAD; ls -a /app/repo /app/repo/.git
c6d9997 HEAD@{0}: commit: chore: init e665d1a2-04a7-4e61-b523-e897e231d9cc
7a2420e HEAD@{1}: reset: moving to HEAD~1
6b4c75c HEAD@{2}: commit: feat: add scratch notes
7a2420e HEAD@{3}: commit (initial): chore: init e665d1a2-04a7-4e61-b523-e897e231d9cc
commit c6d99979c3ef74db39532137fb89516c2d707785
Author: TerminalBench <tb@example.com>
Date:   Tue Oct 28 22:02:30 2025 +0000
    chore: init e665d1a2-04a7-4e61-b523-e897e231d9cc
 README.md | 1 +
 1 file changed, 1 insertion(+)
/app/repo:
.
..
.git
README.md
/app/repo/.git:
.
..
COMMIT_EDITMSG
HEAD
ORIG_HEAD
branches
config
description
hooks
index
info
logs
lost-found
objects
refs

$ git show 6b4c75c; ls .git/lost-found; git show HEAD:README.md; git cat-file -p 6b4c75c | head -3
commit 6b4c75caa9a2aa9a630e16764007b0109b1f5c07
Author: TerminalBench <tb@example.com>
Date:   Tue Oct 28 22:02:30 2025 +0000
    feat: add scratch notes
diff --git a/secret.txt b/secret.txt
new file mode 100644
index 0000000..52d18a0
--- /dev/null
+++ b/secret.txt
@@ -0,0 +1 @@
+secret[lost_and_found_in_git]
commit
demo project
some changes
tree aa7dfd0c18e6582cdc8959609bc02653870cd96a
parent 7a2420e8b3537348565a4cd08f0810ad26756e73
author TerminalBench <tb@example.com> 1761688950 +0000

$ printf 'secret[lost_and_found_in_git]\n' > /app/secret.txt; cd /app/repo && git reflog expire --expire=now --all && git gc --prune=now -q; git count-objects -v | head -2; git fsck --lost-found --no-reflogs; grep -rl "lost_and_found" . ; git log --oneline --all; git status --short
count: 0
size: 0
c6d9997 chore: init e665d1a2-04a7-4e61-b523-e897e231d9cc
7a2420e chore: init e665d1a2-04a7-4e61-b523-e897e231d9cc

