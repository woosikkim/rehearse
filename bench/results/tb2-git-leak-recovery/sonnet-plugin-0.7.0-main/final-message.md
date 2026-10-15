I recovered the secret and removed it from the repo.

1. **Recovery:** The secret was in a dangling commit, `6b4c75c` ("feat: add scratch notes"), which the history rewrite had left in the object store. It added a `secret.txt` containing `secret[lost_and_found_in_git]`. I wrote that string to `/app/secret.txt`.
2. **Cleanup:** I expired the reflog and ran `git gc --prune=now`, which deleted the unreachable commit and its objects. A search of the working tree finds no match for the secret, and `git fsck` reports no dangling objects.
3. **Untouched files:** `README.md` and the two existing commits (`7a2420e` and `c6d9997`, with their messages) are unchanged, and `git status` is clean.

I skipped the rehearse log and fixtures, since this task involved no code changes.

The cleanup is irreversible. The commit can no longer be recovered from this repo.