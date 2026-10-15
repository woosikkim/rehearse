"""Harbor agent: Claude Code with the rehearse plugin loaded.

Identical to Harbor's built-in ``claude-code`` agent except that each task
container also gets a clone of the rehearse repo and Claude Code starts with
``--plugin-dir`` pointing at it, so the skill, the guard hooks and the
rehearser helper are all active. Everything else (model, auth, turn limits,
trajectory and cost parsing) is inherited unchanged.

Run (from this repo):

    harbor run -d swe-bench/swe-bench-verified -i "<task glob>" \
        -a bench.rehearse_agent:RehearseClaudeCode -m anthropic/claude-sonnet-5-5 \
        --ae CLAUDE_CODE_OAUTH_TOKEN="$(cat bench/subscription.token)" --ae CLAUDE_FORCE_OAUTH=1

Set REHEARSE_GIT_URL / REHEARSE_GIT_REF to pin a different source or commit.
"""
import os
import shlex

from harbor.agents.installed.claude_code import ClaudeCode
from harbor.environments.base import BaseEnvironment

REPO_URL = os.environ.get("REHEARSE_GIT_URL", "https://github.com/woosikkim/rehearse")
REPO_REF = os.environ.get("REHEARSE_GIT_REF", "main")
PLUGIN_DIR = "$HOME/rehearse-plugin"


class RehearseClaudeCode(ClaudeCode):
    @staticmethod
    def name() -> str:
        return "claude-code-rehearse"

    async def install(self, environment: BaseEnvironment) -> None:
        await super().install(environment)
        await self.ensure_system_dependencies(environment, ("git", "python3"))
        await self.exec_as_agent(
            environment,
            command=(
                f"rm -rf {PLUGIN_DIR} && "
                f"git clone --quiet --depth 1 --branch {shlex.quote(REPO_REF)} "
                f"{shlex.quote(REPO_URL)} {PLUGIN_DIR} && "
                f"python3 {PLUGIN_DIR}/tests/test_guard.py"
            ),
        )

    def build_cli_flags(self) -> str:
        flags = super().build_cli_flags()
        return f"{flags} --plugin-dir {PLUGIN_DIR}".strip()

    def _resolve_auth_env(self) -> dict[str, str]:
        # Prefer the subscription token when one is given. Setting this here
        # instead of via `--ae CLAUDE_FORCE_OAUTH=1` matters: Harbor masks every
        # occurrence of a sensitive --ae value in its logs, and masking the
        # digit "1" everywhere turns the JSON transcripts unparsable.
        env = super()._resolve_auth_env()
        if env.get("CLAUDE_CODE_OAUTH_TOKEN") and "CLAUDE_FORCE_OAUTH" not in env:
            env["CLAUDE_FORCE_OAUTH"] = "1"
            env.pop("ANTHROPIC_API_KEY", None)
        return env
