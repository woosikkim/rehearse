The Git server and both HTTPS endpoints are working. I ran your six test steps against it, and both URLs returned the right content. The one thing I haven't confirmed is a push into a completely fresh repo with the final hook, because I tested on a repo that already had both branches.

- **SSH:** a `git` user has the password `password`, and `git@localhost:/git/project` is a bare repo at `/git/project`. sshd is running with password authentication on.
- **Deploy:** the `post-receive` hook checks out `main` into `/var/www/main` and `dev` into `/var/www/dev`. A push took about 0.3 seconds, well inside your 3-second limit. The hook also resets the repo's HEAD to `main` after each push, so HEAD doesn't stay on `dev`.
- **HTTPS:** nginx listens on 8443 with a self-signed certificate for `localhost`. It serves `/var/www/main` at `/` and `/var/www/dev` at `/dev/`.
- **Checks:**
  - `https://localhost:8443/index.html` returned "main branch content".
  - `https://localhost:8443/dev/index.html` returned "dev branch content".
  - Pushes from a clone over SSH with the password worked.

- **Not restart-proof:** sshd and nginx were started by hand, so they won't come back after a container restart.
- **Extra package:** I installed `sshpass` so my tests could supply the password.
- **Branches:** the hook ignores any branch other than `main` and `dev`.
- **Rehearse skill:** I made no program code changes. The rehearsal log is in `/app/.rehearsal/`, though it only records the first environment check. The setup and the push tests ran after the guard blocked them, so the log doesn't cover them.