#!/usr/bin/env bash
# Run one live case headless on the checked-out plugin, then check it.
#
#   tests/live/run.sh <case> [workdir]        cases: blocked-route, check-wrong, exhausted
#
# A real `claude -p` run: it calls a model and needs a signed-in Claude Code. Not part of CI.
# The plugin is loaded from this repo (--plugin-dir); the installed rehearse is switched off for the run;
# Claude Code's own sandbox keeps every write inside the work folder. Do not edit the repo while a run is in
# progress: the hooks are read from these files on every call.
set -u
REPO=$(cd "$(dirname "$0")/../.." && pwd)
CASE=${1:?case name}
SRC="$REPO/tests/live/cases/$CASE"
[ -d "$SRC" ] || { echo "no such case: $CASE"; exit 2; }
WORK=${2:-${TMPDIR:-/tmp}/rehearse-live/$CASE-$(date -u +%Y%m%dT%H%M%S)}
mkdir -p "$WORK" && cp -r "$SRC/fixture/." "$WORK/"
PROMPT="rehearse auto $(cat "$SRC/prompt.txt")"
echo "case $CASE in $WORK"
cd "$WORK" || exit 2
REHEARSE_HEADLESS=1 timeout "${LIVE_TIMEOUT:-3600}" claude -p \
    --permission-mode bypassPermissions \
    --plugin-dir "$REPO" \
    --settings '{"enabledPlugins":{"rehearse@rehearse":false},"sandbox":{"enabled":true,"autoAllowBashIfSandboxed":true}}' \
    --output-format json "$PROMPT" > "$WORK/claude.json" 2> "$WORK/claude.err"
echo "claude exit $? (output in $WORK/claude.json)"
python3 "$REPO/tests/live/check.py" "$CASE" "$WORK"
