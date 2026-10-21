# Running a branch of rehearse without a release

For the owner. How to run a real job (the library job's stages 3 and 4) on branch `v4` while the installed plugin stays as it is, with only one copy of the hooks firing, and how to go back afterwards.

## What is installed today (checked 2026-10-21)

- The marketplace `rehearse` points at this repo folder, with auto-update on. At each session start Claude Code compares the version in `.claude-plugin/plugin.json` with the installed one and, when it differs, copies the **whole working tree** (uncommitted changes included) into `~/.claude/plugins/cache/rehearse/rehearse/<version>/`. That copy is what every session loads; repo edits never reach a session until the next copy.
- Because step 1 of 4.0.0 set the version to `4.0.0` on the branch, the install is **not 3.2.0**: `installed_plugins.json` points at `cache/rehearse/rehearse/4.0.0`, copied on 2026-10-20 at 16:39 local, the step-1 tree. The 3.2.0 copy still sits beside it. Later commits on the branch kept the version `4.0.0`, so no further copy was made: everyday sessions run the step-1 snapshot.

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

Do not run `claude plugin update` during the job: it would replace the installed copy from the working tree, and if that session loaded the installed copy it would change the hooks under a running job.

## Fallback: switching the installed copy off persistently

If the per-session settings override does not take (the check in step 3 fails):

```
claude plugin disable rehearse@rehearse
claude --plugin-dir /mnt/d/Projects/rehearse        # the session for the job
claude plugin enable rehearse@rehearse              # afterwards
```

`disable` and `enable` write `enabledPlugins` in `~/.claude/settings.json`; other sessions started in between run without rehearse.

## Putting the everyday install back on 3.2.0 (optional, before the job)

Only if you want everyday sessions on the released 3.2.0 instead of the step-1 snapshot:

```
cd /mnt/d/Projects/rehearse && git checkout main      # main is 3.2.0
claude plugin update rehearse@rehearse                 # copies the tree: the install becomes 3.2.0
git checkout v4                                        # back to the branch
```

Do this while no rehearse job runs anywhere, and never with uncommitted changes in the tree (they would be copied). The auto-update will copy the tree again at the next version change; if that is unwanted, set `autoUpdate` to `false` for the `rehearse` entry in `~/.claude/plugins/known_marketplaces.json`.

## After the release

`claude plugin update rehearse@rehearse` with the tagged commit checked out copies 4.0.0 into the cache for good, and the `--plugin-dir` session is no longer needed.
