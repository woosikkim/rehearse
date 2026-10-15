# Benchmark notes

This folder holds everything needed to repeat the measurements quoted in the main README, plus the raw results of every run.

**Status:** the full write-up, version by version and failure by failure, is still being written. The numbers in the main README come from the files here and can be recomputed with the scripts below.

## What is here

| Path | What it is |
|---|---|
| `rehearse_agent.py` | The Harbor agent: Claude Code with this plugin loaded from GitHub inside each task container. |
| `prompt_rehearse.j2` | The prompt wrapper: `rehearse: <task instructions>`. |
| `collect.py` | Turns a finished Harbor job into one folder per task under `results/` and prints a summary table. |
| `swe-verified-over1h-order.txt` | The 45 SWE-bench Verified tasks rated over one hour for a human, in a fixed seeded order (seed 20261014). Batches were taken from the top. |
| `tb2-order.txt`, `tb2-sample10.txt` | The 89 Terminal-Bench 2.1 tasks in a fixed seeded order, and the first ten as the sample. |
| `results/<task>/<model>-plugin-<version>/` | For every run: the full Claude Code transcript (`transcript.stream.jsonl`), the verifier's verdict, the agent's final message, and a one-line summary. |

## How to repeat a run

Requirements: Docker, [Harbor](https://harborframework.com) (`uv tool install harbor`), and a Claude subscription token from `claude setup-token` saved in `subscription.token` (git-ignored, never commit it).

```
harbor datasets download swe-bench/swe-bench-verified -o tasks
PYTHONPATH=$PWD/.. harbor run -p tasks/swe-bench-verified/django__django-13344 \
  -a bench.rehearse_agent:RehearseClaudeCode -m anthropic/claude-sonnet-5-5 \
  --ak max_turns=150 --ak prompt_template_path=$PWD/prompt_rehearse.j2 \
  --ae CLAUDE_CODE_OAUTH_TOKEN="$(cat subscription.token)" \
  --agent-setup-timeout-multiplier 3 -n 1 -o jobs --job-name my-run -y
python3 collect.py jobs/my-run my-label
```

Set `REHEARSE_GIT_REF` to pin a plugin version (a tag or commit); the default is `main`.

## Honest caveats

- The plugin was improved using these very runs, so results across tasks mix plugin versions from 0.4.1 to 0.6.3. Each result folder is named with the version it ran on.
- A single run per task is noisy: rerunning the same 22 tasks on the same version swung the fixed count by three or four either way. The regression count was stable.
- "Fixed" means every hidden test the project's maintainers wrote for that bug passes and nothing that passed before fails. Some tasks' hidden tests check things the bug report never mentions; those are counted as failures anyway and marked as such in the write-up.
