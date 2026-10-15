#!/usr/bin/env bash
# Start the demo server (it stops itself after an hour) and leave only the wrong documentation in the workspace.
set -euo pipefail
server="$(cd "$(dirname "$0")/../../demos/mock-server" && pwd)/server.py"
setsid nohup timeout 3600 python3 "$server" >/dev/null 2>&1 < /dev/null &
cat > API.md <<'DOC'
# Shop API

- `GET http://localhost:8766/api/items` returns the items.
- Each item has a `name` and a `price` in dollars.
DOC
for i in 1 2 3 4 5 6 7 8 9 10; do
  python3 -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8766/api/v1/items", timeout=1)' 2>/dev/null && exit 0
  sleep 0.5
done
echo "mock server did not start" >&2
exit 1
