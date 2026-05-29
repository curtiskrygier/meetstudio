#!/usr/bin/env bash
# Mint a stage ticket against the local backend and open the listener URL in a browser.
# Usage: ./open_stage.sh [space]   (default space = "default")
#
# Env overrides:
#   CONCIERGE_API_URL  default http://127.0.0.1:8085
#   STAGE_API_KEY      default matches render_showreel.py
set -euo pipefail

SPACE="${1:-default}"
API="${CONCIERGE_API_URL:-http://127.0.0.1:8085}"
KEY="${STAGE_API_KEY:-meet-live_STAGE_SECURE_v1_zG9fN8qL7vP2mX6tY9wK4jC5bS8xQ7hZ3uW0rA}"

# Mint ticket; pull stage_url out of the JSON.
RESP=$(curl -fsS -H "Authorization: Bearer $KEY" "$API/api/stage-ticket/$SPACE")
URL=$(printf '%s' "$RESP" | python3 -c 'import json,sys; print(json.load(sys.stdin)["stage_url"])')

echo "Stage URL: $URL"

# Try to open in default browser; fall back to printing only.
if   command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1 &
elif command -v open     >/dev/null 2>&1; then open "$URL" >/dev/null 2>&1 &
else echo "(no xdg-open/open found — copy the URL above into a browser)"
fi
