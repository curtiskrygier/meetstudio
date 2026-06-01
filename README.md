# Google Meet Studio

A Google Meet add-on that renders an agent-driven live stage in the meeting. The agent (Gemini Live) listens, composes UI surfaces via the [A2UI v0.9](https://a2ui.org) protocol, and pushes them to a fullscreen main stage built from composable Lit web components.

**A2UI v0.9 reference implementation** — the public catalogue spec lives at [`catalog/gdm-v0.2.json`](catalog/gdm-v0.2.json).

---

## What it is

Three deployment modes, same primitives:

| Mode | Who controls it | Friction |
|---|---|---|
| **Live agent stage** | Gemini Live listens and decides in real time | High — AI is in the room |
| **Sidekick to traditional decks** | Presenter speaks, agent suggests | Medium |
| **Pre-prepped playbook** | Presenter fires slides via buttons | Zero — no listening, no recording indicator |

**Tech stack:**
- Backend: FastAPI on Cloud Run (`main.py`), connects to Gemini Live
- Frontend: Lit web components, Vite bundling
- Protocol: A2UI v0.9 — agent describes a component tree, server pushes via WebSocket, client materialises
- Catalogue: 45 `gdm-*` components — atoms, molecules, overlays — spec at [`catalog/gdm-v0.2.json`](catalog/gdm-v0.2.json)

---

## Prerequisites

> **Meet Media API access is invitation-only.** This add-on uses the [Google Meet Media API](https://developers.google.com/meet/media-api), which is in **Developer Preview** and requires explicit approval from Google. [Apply for access](https://developers.google.com/meet/media-api/guides/overview#apply_for_access) before deploying. Without it the side panel loads but audio capture is silently blocked.

- Google Cloud project with Cloud Run, Meet Media API (dev preview), and Workspace Marketplace SDK enabled
- A second GCP project (or the same) with Vertex AI API enabled for Gemini Live billing
- OAuth 2.0 Client ID (Web application) with the Meet scopes
- [clasp](https://github.com/google/clasp) installed and authenticated
- Node.js 18+ and Python 3.11+

---

## Running locally

```bash
# 1. Clone with submodules (includes the a2ui-catalogue)
git clone --recurse-submodules https://github.com/curtiskrygier/meet-studio.git
cd meet-studio

# Or if already cloned:
git submodule update --init

# 2. Install dependencies
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
npm install && npm run build

# 2. Set required env vars
export GEMINI_PROJECT=your-gcp-project-id
export STAGE_API_KEY=any-secret-string

# 3. Start the backend
uvicorn main:app --port 8085 --reload

# 4. Open the stage in a browser
./open_stage.sh              # mints a ticket, opens main_stage.html

# 5. Run a demo
python render_showreel.py    # 6-act showreel
python demo_a2ui_primitives.py
```

After `npm run build`, always hard-refresh the stage tab (Ctrl+Shift+R) — Vite uses hash-based filenames.

### Dev gotchas

- **`GEMINI_PROJECT` is required** even for showreel-only runs that don't touch Gemini Live
- **Catch-all routes must stay last in `main.py`** — `StaticFiles` mount and the SPA fallback must remain at the bottom; routes declared after them are shadowed
- **`gdm-container` needs `grow: 1`** when slotted into a `gdm-stage-grid` cell that should fill height

---

## Syncing the Component Catalogue (`a2ui-catalogue`)

The `curtiskrygier/meetstudio` repository depends on the component definitions and renderers from `curtiskrygier/a2ui-catalogue`, which is integrated as a Git submodule in the `catalogue/` directory.

Since the local development repository (`/home/curtis/a2ui-catalogue`) is often ahead of the submodule during active feature development (e.g. implementing premium data visualization atoms), you can use the synchronization script to align them seamlessly:

### 1. Dev Mode (Local Copy Only)
To quickly copy modified code (atoms, schemas, and python renderers) directly from your local `a2ui-catalogue` workspace into the local `meetstudio/catalogue` folder without committing or pushing:
```bash
./sync-catalogue.sh -d
```
This is ideal for immediate local testing, playbook verification, or local Docker container builds.

### 2. Release Mode (Full Git Synchronization)
When you are ready to publish your changes upstream:
```bash
./sync-catalogue.sh -r "feat: add premium donut stat and heatmap visualization atoms"
```
This will:
1. Stage, commit, and push your changes inside your local `/home/curtis/a2ui-catalogue` workspace to GitHub (`origin main`).
2. Pull the latest commits from GitHub inside your `meetstudio/catalogue` submodule.
3. Stage and commit the updated submodule commit pointer in `meetstudio`.

---

## Authoring playbooks (Mode C)

Playbooks are YAML files in `playbooks/`. Each slide maps to a template:

```yaml
- id: intro
  template: title
  headline: "Q3 Board Update"
  subheadline: "Revenue · Pipeline · Outlook"
  next_action: { text: "Begin", fires: revenue }

- id: revenue
  template: hero_stat
  badge: { text: "ARR", type: primary }
  label: "Annual Recurring Revenue"
  data:
    ARR: { source: literal, value: "$48.2M" }
  value: "{{ ARR }}"
  is_up: true
  next_action: { text: "Next", fires: close }

- id: close
  template: signoff
  lines:
    - { text: "Thank you", color: white }
```

Fire a slide:
```bash
curl -X POST http://localhost:8085/api/playbook/fire/my_deck/intro/default \
  -H "Authorization: Bearer $STAGE_API_KEY"
```

**Available templates:** `title`, `hero_stat`, `split_with_action`, `list_5`, `signoff`, `market_ticker`

**Data sources:** `literal`, `rest` (live HTTP/JSON with configurable refresh), `stooq` (market data) — `bigquery` planned for v0.3.

---

## Deploying to Cloud Run

```bash
# Create a Secret Manager secret for your STAGE_API_KEY first:
echo -n "your-secret-key" | gcloud secrets create stage-api-key \
  --data-file=- --project=YOUR_CLOUD_RUN_PROJECT

# Deploy
gcloud run deploy meetstudio \
  --source . \
  --region us-central1 \
  --project YOUR_CLOUD_RUN_PROJECT \
  --timeout=3600 \
  --session-affinity \
  --allow-unauthenticated \
  --set-build-env-vars="CLIENT_ID=YOUR_OAUTH_CLIENT_ID,CLOUD_PROJECT_NUMBER=YOUR_PROJECT_NUMBER" \
  --set-env-vars="GEMINI_PROJECT=YOUR_GEMINI_PROJECT,REGION=us-central1,KORE_VOICE=Charon,CLIENT_ID=YOUR_OAUTH_CLIENT_ID" \
  --set-secrets="STAGE_API_KEY=stage-api-key:latest"
```

Grant the Cloud Run service account access to Gemini:
```bash
gcloud projects add-iam-policy-binding YOUR_GEMINI_PROJECT \
  --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

---

## Registering the Apps Script add-on

```bash
cd appsscript

# First time only — create a standalone Apps Script project
clasp create --title "Meet Studio" --type standalone

# Substitute your Cloud Run URL in the manifest
sed -i 's|YOUR_CLOUD_RUN_URL|https://YOUR_SERVICE.us-central1.run.app|g' appsscript.json

clasp push --force
clasp deploy --description "v1"
```

Copy the deployment ID and enter it in:
**GCP Console → APIs & Services → Google Workspace Marketplace SDK → App Configuration**

Then use **Test Install** in the Marketplace SDK console and open Google Meet.

---

## Configuration

| Variable | Required | Description |
|---|---|---|
| `CLOUD_PROJECT_NUMBER` | Yes (build) | Numeric GCP project number for the Meet Add-on SDK |
| `CLIENT_ID` | Yes (build) | OAuth 2.0 client ID for the Meet scopes |
| `GEMINI_PROJECT` | Yes (runtime) | GCP project ID billed for Gemini Live API usage |
| `STAGE_API_KEY` | Yes (runtime) | Bearer token protecting producer endpoints; load from Secret Manager in production |
| `REGION` | No | Cloud Run / Vertex AI region (default: `us-central1`) |
| `KORE_VOICE` | No | Gemini Live voice name (default: `Charon`) |
| `WORKSPACE_AGENT_ENGINE` | Optional | Vertex AI Reasoning Engine resource ID for Workspace tasks (Docs/Sheets creation) |
| `SYSTEM_PROMPT` | No | Override the agent's system instruction |

> [!IMPORTANT]
> **`STAGE_API_KEY` Security vs. Dev Convenience:** This key acts as a static master token allowing developer scripts (such as `render_showreel.py` or `test_playbooks.sh`) to cycle and trigger slides without going through a Google OAuth flow. For development, a simple string is fine, but in production, **always use a long, cryptographically secure key loaded via Secret Manager** to lock down the endpoints against abuse.

---

## MCP Server

The backend exposes an MCP server at `/mcp` (Streamable HTTP transport).

| Tool | Description |
|---|---|
| `send_transcript` | Broadcast a subtitle line to the Meet main stage |
| `trigger_diagram` | Generate a D2 diagram and broadcast it to the stage |

Connect from Claude Code (`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "meetstudio": {
      "type": "sse",
      "url": "https://YOUR_SERVICE.us-central1.run.app/mcp",
      "headers": { "Authorization": "Bearer YOUR_STAGE_API_KEY" }
    }
  }
}
```

---

## GCP project structure

| Project | Purpose |
|---|---|
| **Cloud Run project** | Hosts the service, OAuth Client ID, Meet Media API dev preview access |
| **Gemini billing project** | Vertex AI API enabled here; all Gemini Live calls billed to this project (`GEMINI_PROJECT`) |
| **Workspace Agent project** *(optional)* | Vertex AI Reasoning Engine for Docs/Sheets tasks (`WORKSPACE_AGENT_ENGINE`) |

The three projects can be the same project if preferred.

---

## Architecture notes

**Why 100ms PCM batches?** The AudioWorklet fires at ~125Hz (128 samples at 16kHz). Sending every frame generates ~7,500 WebSocket messages/min. Batching to 1,600 samples (100ms) reduces this to ~600/min while staying within Gemini Live's latency budget.

**Why a hidden `<audio muted>` element per track?** Chrome's Opus decoder is lazy — it won't decode a `MediaStreamTrack` unless something is actively playing it. Without this, all Meet audio tracks deliver silence to the AudioWorklet.

**Why two AudioContexts created before any `await`?** Chrome's autoplay policy suspends AudioContexts created outside a user-gesture handler. Both the recording (16kHz) and playback (24kHz) contexts must be created synchronously at the start of the click handler.

---

## Gemini Live voices

| Voice | Character |
|---|---|
| Charon | Informative, neutral (default) |
| Kore | Firm, clear |
| Puck | Upbeat, expressive |
| Aoede | Breezy, easy |
| Fenrir | Excitable |
| Zephyr | Light, positive |


---

## Known Gaps & Roadmap (To-Dos)

While the core functionality and security posture are production-ready, the following architectural gaps are tracked as future improvements:

1. **Mode C Presenter Dashboard:** The presenter URL `/presenter/{space}` remains a future comment placeholder; slide trigger workflows currently rely on terminal scripts or direct API calls.
2. **Monolithic Backend:** `main.py` remains a monolithic ~3,600-line file handling all routers, states, and WebSockets.
3. **No Throttling/Rate Limiting:** No rate limiting is configured on paid model/trigger endpoints, exposing the system to potential billing spikes under spam.

---

## License

MIT

