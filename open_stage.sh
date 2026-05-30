#!/usr/bin/env bash
# Mint a stage ticket against the local backend and open the listener URL in a browser.
# Usage: ./open_stage.sh [space]   (default space = "default")
#
# Env overrides:
#   CONCIERGE_API_URL  default http://127.0.0.1:8085
#   STAGE_API_KEY      required — no default; export it before running
set -euo pipefail

SPACE="${1:-default}"
API="${CONCIERGE_API_URL:-http://127.0.0.1:8085}"
KEY="${STAGE_API_KEY:?STAGE_API_KEY is required — export it before running open_stage.sh}"

# Mint ticket; pull stage_url out of the JSON.
RESP=$(curl -fsS -H "Authorization: Bearer $KEY" "$API/api/stage-ticket/$SPACE")
URL=$(printf '%s' "$RESP" | python3 -c 'import json,sys; print(json.load(sys.stdin)["stage_url"])')

echo "Stage URL: $URL"

# Try to open in default browser; fall back to printing only.
if   command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1 &
elif command -v open     >/dev/null 2>&1; then open "$URL" >/dev/null 2>&1 &
else echo "(no xdg-open/open found — copy the URL above into a browser)"
fi
