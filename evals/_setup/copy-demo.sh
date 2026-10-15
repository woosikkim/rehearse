#!/usr/bin/env bash
# Copy a demo's program files (not its README, which tells the story) into the eval workspace and commit them.
# Usage from a case's setup.sh: bash "$(dirname "$0")/../_setup/copy-demo.sh" <demo name>
set -euo pipefail
demo="$(cd "$(dirname "$0")/../../demos/$1" && pwd)"
cp "$demo"/*.py "$demo"/*.csv .
git init -q
git add -A
git -c user.email=eval@rehearse -c user.name=eval commit -qm "demo $1"
