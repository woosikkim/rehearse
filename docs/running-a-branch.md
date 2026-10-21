# Running a branch of rehearse without a release

For the owner. How to run a real job (the library job's stages 3 and 4) on branch `v4` while the installed plugin stays as it is, with only one copy of the hooks firing, and how to go back afterwards.

## What is installed (since 2026-10-21)

- The marketplace `rehearse` points at the GitHub repo `woosikkim/rehearse`, with auto-update on. Everyday sessions get what is on GitHub `main` (3.2.0 now) and nothing else: work in the repo folder can never reach them, and a self-job (a rehearse job on this repo) is safe again. A new version reaches everyday sessions only when it is on `main` and a session starts after that.
- Until 2026-10-21 the marketplace pointed at the repo folder itself, and auto-update copied the working tree whenever the version in plugin.json changed. Step 1 of 4.0.0 bumped the version on the branch, so from 2026-10-20 16:39 everyday sessions ran a snapshot of the step-1 tree. No rehearse job was started between that moment and the switch, so no job result came from the snapshot.
- Switching the marketplace deleted the plugin's data folder (`~/.claude/plugins/data/rehearse-rehearse/`, where every job file lives). The job files were restored from their copies in each project's `.rehearsal/<run id>/state.json`; nothing else was in the folder. The copies are the backup: never delete a project's `.rehearsal` folder while its job file may still be wanted.

## Running stages 3 and 4 on the branch

The branch is loaded straight from the repo folder for one session, and the installed plugin is switched off for that session only. Nothing on disk changes, so there is nothing to switch back.

1. In the repo: `git status --short` prints nothing and `git log --oneline -1` shows the v4 commit you mean to validate. Do not edit, check out or pull in the repo while the job runs: the hooks are read from these files on every call.
2. Open a terminal in the scraper project and start Claude Code with the branch as the plugin and the installed copy off:

```
cd /mnt/d/Projects/scraper
claude --plugin-dir /mnt/d/Projects/rehearse --settings '{"enabledPlugins":{"rehearse@rehearse":false}}'
```

3. Check inside the session that exactly one rehearse is loaded: `/plugins` lists `rehearse` from the directory and `rehearse@rehearse` as disabled. If both show as enabled, stop the session and use the fallback below.
4. Run the job. The job file lands in that session's plugin data folder; the run folder is `.rehearsal/<run id>/` in the scraper project as always. `rehearse feedback` afterwards works from the scraper folder.
5. Afterwards, nothing to undo: a normal `claude` session loads the installed copy again.

Do not run `claude plugin update` or a marketplace change during the job: a plugin update replaces the installed copy, and a marketplace removal deletes the plugin's data folder with every job file in it.

## Fallback: switching the installed copy off persistently

If the per-session settings override does not take (the check in step 3 fails):

```
claude plugin disable rehearse@rehearse
claude --plugin-dir /mnt/d/Projects/rehearse        # the session for the job
claude plugin enable rehearse@rehearse              # afterwards
```

`disable` and `enable` write `enabledPlugins` in `~/.claude/settings.json`; other sessions started in between run without rehearse.

## After the release

Once 4.0.0 is on GitHub `main`, the next session start installs it by itself (auto-update), or `claude plugin update rehearse@rehearse` does it at once; the `--plugin-dir` session is no longer needed.
