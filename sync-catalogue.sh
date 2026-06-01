#!/bin/bash
# sync-catalogue.sh - High-fidelity synchronization between curtiskrygier/a2ui-catalogue and meetstudio
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Paths
LOCAL_SRC="/home/curtis/a2ui-catalogue"
SUBMODULE_DIR="./catalogue"
SPEC_FILE="./catalog/gdm-v0.2.json"

show_help() {
    echo -e "${CYAN}A2UI Catalogue Synchronizer & Submodule Manager${NC}"
    echo -e "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -s, --src PATH      Override local a2ui-catalogue repository path (default: $LOCAL_SRC)"
    echo "  -d, --dev-only      Dev mode: Sync local files only (no git commits or pushes)"
    echo "  -r, --release MSG   Release mode: Sync, commit/push local a2ui-catalogue, and update submodule reference in meetstudio with MSG"
    echo "  -h, --help          Show this help message"
    echo ""
}

# Parse options
MODE="dev"
RELEASE_MSG=""
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -s|--src) LOCAL_SRC="$2"; shift ;;
        -d|--dev-only) MODE="dev" ;;
        -r|--release) MODE="release"; RELEASE_MSG="$2"; shift ;;
        -h|--help) show_help; exit 0 ;;
        *) echo -e "${RED}Unknown option: $1${NC}"; show_help; exit 1 ;;
    esac
    shift
done

echo -e "${BLUE}=== A2UI Sync Active ===${NC}"
echo -e "Local Source:     ${CYAN}$LOCAL_SRC${NC}"
echo -e "Submodule Target: ${CYAN}$SUBMODULE_DIR${NC}"
echo -e "Spec Source:      ${CYAN}$SPEC_FILE${NC}"
echo -e "Execution Mode:   ${YELLOW}${MODE}${NC}"

# Check directories
if [ ! -d "$LOCAL_SRC" ]; then
    echo -e "${RED}Error: Source directory '$LOCAL_SRC' does not exist.${NC}"
    exit 1
fi

if [ ! -d "$SUBMODULE_DIR" ]; then
    echo -e "${RED}Error: Submodule directory '$SUBMODULE_DIR' does not exist. Run git submodule update --init --recursive first.${NC}"
    exit 1
fi

# 1. Update/sync spec file (canonical json spec)
echo -e "${BLUE}[1/4] Syncing gdm-v0.2.json schema specification...${NC}"
if [ -f "$SPEC_FILE" ]; then
    # Copy from meetstudio/catalog to the submodule spec
    mkdir -p "$SUBMODULE_DIR/spec"
    cp "$SPEC_FILE" "$SUBMODULE_DIR/spec/gdm-v0.2.json"
    # Also keep the local development repository spec updated
    mkdir -p "$LOCAL_SRC/spec"
    cp "$SPEC_FILE" "$LOCAL_SRC/spec/gdm-v0.2.json"
    echo -e "${GREEN}✓ gdm-v0.2.json spec synchronized to both submodule and local source.${NC}"
else
    echo -e "${YELLOW}! Warning: $SPEC_FILE not found, skipping spec sync.${NC}"
fi

# 2. Sync local source repository changes into meetstudio's submodule folder
echo -e "${BLUE}[2/4] Pulling local changes from source repo ($LOCAL_SRC) to submodule ($SUBMODULE_DIR)...${NC}"

# Check for modified schema.yaml and renderers
if [ -d "$LOCAL_SRC/atoms" ] && [ -d "$LOCAL_SRC/renderers" ]; then
    # Sync schema.yaml
    mkdir -p "$SUBMODULE_DIR/atoms"
    cp -v "$LOCAL_SRC/atoms/schema.yaml" "$SUBMODULE_DIR/atoms/schema.yaml"
    # Sync renderers (using rsync if available, fallback to cp)
    mkdir -p "$SUBMODULE_DIR/renderers"
    if command -v rsync >/dev/null 2>&1; then
        rsync -av --exclude '__pycache__' "$LOCAL_SRC/renderers/" "$SUBMODULE_DIR/renderers/"
        if [ -d "$LOCAL_SRC/googlechat" ]; then
            mkdir -p "$SUBMODULE_DIR/googlechat"
            rsync -av --exclude '__pycache__' "$LOCAL_SRC/googlechat/" "$SUBMODULE_DIR/googlechat/"
        fi
    else
        cp -rv "$LOCAL_SRC/renderers/"* "$SUBMODULE_DIR/renderers/"
    fi
    echo -e "${GREEN}✓ Core engine renderers and atoms schema synchronized.${NC}"
else
    echo -e "${RED}Error: Source repo does not contain valid atoms or renderers directories.${NC}"
    exit 1
fi

if [ "$MODE" = "dev" ]; then
    echo -e "\n${GREEN}=== DEV SYNC COMPLETE ===${NC}"
    echo -e "Submodule directory files are fully updated for local testing & Docker builds."
    echo -e "Run with --release \"Commit Message\" when you are ready to push upstream."
    exit 0
fi

# 3. Release Mode: Git operations
echo -e "${BLUE}[3/4] Release Mode active: Pushing changes upstream to GitHub...${NC}"

if [ -z "$RELEASE_MSG" ]; then
    RELEASE_MSG="sync: upgrade data visualization atoms and renderer"
fi

# Commit and push in the source repo if there are changes
echo -e "${CYAN}--> Committing and pushing in source repository ($LOCAL_SRC)...${NC}"
cd "$LOCAL_SRC"
# Staging core changes
git add atoms/schema.yaml renderers/web_article.py spec/gdm-v0.2.json
if git diff --cached --quiet; then
    echo -e "${YELLOW}No changes to commit in source repo ($LOCAL_SRC)${NC}"
else
    git commit -m "$RELEASE_MSG"
    git push origin main
    echo -e "${GREEN}✓ Pushed to a2ui-catalogue repository on GitHub.${NC}"
fi
cd - > /dev/null

# Pull inside the meetstudio submodule
echo -e "${CYAN}--> Updating submodule ($SUBMODULE_DIR) pointer to latest upstream commit...${NC}"
cd "$SUBMODULE_DIR"
git fetch origin
git checkout main
git pull origin main
cd - > /dev/null

# 4. Commit the submodule pointer bump inside meetstudio
echo -e "${BLUE}[4/4] Bumping submodule pointer inside meetstudio...${NC}"
git add "$SUBMODULE_DIR"
if git diff --cached --quiet; then
    echo -e "${YELLOW}Submodule pointer already up-to-date in meetstudio.${NC}"
else
    git commit -m "chore: bump catalogue submodule to latest (synchronized)"
    echo -e "${GREEN}✓ Meetstudio submodule reference updated and committed.${NC}"
fi

echo -e "\n${GREEN}=== RELEASE SYNC COMPLETE ===${NC}"
echo -e "Upstream repositories are fully synchronized and submodule pointers bumped."
