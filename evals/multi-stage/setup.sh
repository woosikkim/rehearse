#!/usr/bin/env bash
# A file-backed "feed" command: no server, no sockets, nothing outlives a Bash call (the eval sandbox allows none of those).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cp "$here/feed" "$here/FEED.md" "$here/items.json" .
chmod +x feed
git init -q
git add -A
git -c user.email=eval@rehearse -c user.name=eval commit -qm "feed scaffold"
