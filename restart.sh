#!/usr/bin/env bash
# Totally restart the Productivity Capital dashboard widget.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# refresh all data
python3 "$DIR/sync_all.py" >/tmp/productivity-capital-sync.log 2>&1 || true
# kill any running instance
pkill -f '[p]roductivity-capital-dashboard/widget.py' 2>/dev/null || true
sleep 1
# launch fresh, detached
nohup python3 "$DIR/widget.py" >/tmp/productivity-capital.log 2>&1 &
echo "restarted (pid $!)"
