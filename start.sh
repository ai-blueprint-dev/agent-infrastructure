#!/usr/bin/env bash
# Agent Infrastructure Dashboard — local launcher (Mac/Linux).
#
# Binds to 127.0.0.1, which means ONLY this machine can reach the
# dashboard. Other devices on your network cannot. To expose to your
# LAN, change --host to 0.0.0.0 (only do this if you trust everyone
# on your network — the dashboard reads from your ~/.claude/ folder).

set -e
cd "$(dirname "$0")"

URL="http://127.0.0.1:8501"

# Open the browser before starting the server. The browser will retry
# until uvicorn comes up.
if command -v open >/dev/null 2>&1; then
    open "$URL" &      # macOS
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" &  # Linux
fi

exec python -m uvicorn server:app --host 127.0.0.1 --port 8501
