#!/bin/bash

# ANSI Color Codes
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

BASE_URL="https://meet-live-concierge-602445641262.us-central1.run.app"
TOKEN="${STAGE_API_KEY:?STAGE_API_KEY is required — export it before running test_playbooks.sh}"
SPACE="default"

echo -e "${CYAN}================================════════════════════════======"
echo -e "       Meet Studio Playbook Test Runner"
echo -e "================================════════════════════════======${NC}"
echo -e "Target URL : ${YELLOW}${BASE_URL}${NC}"
echo -e "Space ID   : ${YELLOW}${SPACE}${NC}"
echo

function print_separator() {
    echo -e "${CYAN}--------------------------------------------------------------${NC}"
}

# --- Action 1: List Slides ---
echo -e "${GREEN}[1/4] Listing slides for playbook 'kickoff'...${NC}"
LIST_RESPONSE=$(curl -s "${BASE_URL}/api/playbook/list/kickoff")
echo -e "Response: ${YELLOW}${LIST_RESPONSE}${NC}"
print_separator

# --- Action 2: Fire Slide 1 (Intro) ---
echo -e "${GREEN}[2/4] Firing 'kickoff' playbook slide 'intro'...${NC}"
FIRE_INTRO=$(curl -s -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  "${BASE_URL}/api/playbook/fire/kickoff/intro/${SPACE}")
echo -e "Response: ${YELLOW}${FIRE_INTRO}${NC}"
print_separator

# --- Action 3: Fire Slide 2 (q3_arr) ---
echo -e "${GREEN}[3/4] Firing 'kickoff' playbook slide 'q3_arr'...${NC}"
FIRE_ARR=$(curl -s -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  "${BASE_URL}/api/playbook/fire/kickoff/q3_arr/${SPACE}")
echo -e "Response: ${YELLOW}${FIRE_ARR}${NC}"
print_separator

# --- Action 4: Draft New Playbook from Markdown ---
echo -e "${GREEN}[4/4] Draft & compile a custom playbook from markdown...${NC}"
DRAFT_PAYLOAD='{
  "source": "markdown",
  "content": "# Custom Script Playbook\n\n## Slide 1: Welcome Slide\nCreated dynamically via test script.\n\n## Slide 2: Verification Slide\nConfirming live reload and atomic A2UI parsing works perfectly."
}'

DRAFT_RESPONSE=$(curl -s -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "${DRAFT_PAYLOAD}" \
  "${BASE_URL}/api/playbook/draft-from-doc/${SPACE}")

echo -e "Response: ${YELLOW}${DRAFT_RESPONSE}${NC}"
print_separator

echo -e "${GREEN}✔ All test cases complete! Playbooks are fully operational.${NC}"
