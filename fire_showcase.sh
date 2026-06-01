#!/usr/bin/env bash
# fire_showcase.sh - Easily fire a slide from the new_atoms_showcase playbook
set -euo pipefail

SLIDE="${1:-cover}"
SPACE="${2:-default}"
TOKEN="${STAGE_API_KEY:-testkey}"
API="${CONCIERGE_API_URL:-http://127.0.0.1:8085}"

echo "Firing slide '$SLIDE' on space '$SPACE'..."
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  "$API/api/playbook/fire/new_atoms_showcase/$SLIDE/$SPACE"
echo ""
echo "Slide '$SLIDE' successfully pushed to stage."
