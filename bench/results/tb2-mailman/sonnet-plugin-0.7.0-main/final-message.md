That notification was for the first `mailman start` and `postfix start` command I ran. The `| tail` in that command kept its output open, so the shell treated it as still running until the background time limit stopped it. It isn't a problem. The services it started are still up:

- **Mailman:** the master process and its runners are running, and the REST API answers on port 8001.
- **Postfix:** running.
- **List:** `reading-group@local.edu` still exists.

My earlier report holds: join, leave and posting all worked. I didn't reload the rehearse skill, because there was nothing left to build or change.