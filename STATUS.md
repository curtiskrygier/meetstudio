# Meet Live Architect — Project Status
_Last updated: 2026-05-08_

---

## What's Working Today

| Component | Status | Notes |
|---|---|---|
| Meet Web Add-on (side panel) | ✅ Live | Deployed to Cloud Run |
| Gemini Live voice (Kore) | ✅ Working | gemini-live-2.5-flash-native-audio via Vertex AI |
| Audio in from Meet participants | ✅ Working | Hidden audio element fix (Opus decoder activation) |
| Audio playback in side panel | ✅ Working | Both AudioContexts created before any `await` |
| PCM batching (100ms) | ✅ Working | Prevents Gemini Live RPM quota breach |
| Video frame capture (1fps) | ✅ Working | Toggle on/off in UI |
| Audio send toggle | ✅ Working | |
| Apps Script manifest | ✅ Templated | `YOUR_CLOUD_RUN_URL` / `YOUR_APPS_SCRIPT_ID` placeholders |
| GitHub repo | ✅ Pushed | `curtiskrygier/google-meet-live-architect-add-on-` (private) |
| workspace-subagent (GE04) | ✅ Redeployed | `projects/828378723395/.../2432159852814925824` |
| Shared drive move fix | ✅ Deployed | `supportsAllDrives=True` added to move + create tools |
| Save to Drive | ⚠️ Broken | Investigating: token scopes vs shared drive visibility |

---

## Technical Analysis: "Save to Drive" Issues

### Current Flow
1. **Frontend (`index.tsx`)**: Requests OAuth token with `https://www.googleapis.com/auth/drive.file` scope.
2. **Handshake**: Token is sent to `main.py` via WebSocket `init` message.
3. **Trigger**: When the Workspace Agent returns a Doc URL, `save_doc_shortcut_to_drive()` is called.
4. **Folder Logic**: `get_or_create_meeting_folder()` looks for "Meet Recordings" in `root`.

### Potential Avenues to Explore
1. **Scope Conflicts**: `drive.file` only sees files created by *this* specific Client ID. If "Meet Recordings" was created by a previous app version or manually, the bot is blind to it and may fail during creation/retrieval.
    - *Action*: Try elevating scope to `https://www.googleapis.com/auth/drive` for debugging.
2. **Shared Drive Support**: The current Drive API calls in `main.py` lack the `supportsAllDrives=True` and `includeItemsFromAllDrives=True` parameters.
    - *Action*: Add these parameters to all `httpx` calls in `main.py`'s Drive logic.
3. **Token Expiry**: User tokens last 1 hour. Long meetings will result in `401 Unauthorized` without a refresh mechanism.
4. **Visibility**: If "Meet Recordings" is not in the user's My Drive (e.g., they are a guest), the `root` search will fail.

---

## Demo Vision — Meet Concierge

A voice-activated Workspace assistant embedded in Google Meet:

```
"Hey Gemini..." (wake word)
    → Web Speech API detects trigger
    → PCM stream opens to backend
    → Gemini Live understands intent
    → Calls workspace-subagent (GE04) as a tool
    → Agent creates/finds Google Docs, Drive files, etc.
    → Gemini Live responds by voice
    → Side panel shows clickable link to result
```

### Why it's compelling
- Entirely within Google Workspace — no external dependencies
- Voice-activated, hands-free during live meetings
- Backed by a production ADK agent (Gemini 2.5 Pro, 85 tools)
- Wake word means it's invisible until needed — meeting concierge model

---

## Demo To-Do List (Priority Order)

### 1. Wake word activation (Web Speech API)
- Add `SpeechRecognition` listener in `index.tsx`
- Trigger phrase: "Hey Gemini"
- Close phrase: "Thanks Gemini" or silence timeout
- UI state: idle → listening → responding

### 2. Wire workspace-subagent as a tool in the backend
- `main.py`: add `workspace_agent` tool function
- POST to `https://us-central1-aiplatform.googleapis.com/v1/projects/828378723395/locations/us-central1/reasoningEngines/2432159852814925824:streamQuery`
- Pass `user_id` and `session_id`, collect text response
- Return result to Gemini Live as tool output

### 3. Verify shared drive placement
- Re-test doc creation with `parent_folder_id=0ANY6w_Rgsa7gUk9PVA` after redeploy
- Confirm doc lands in correct shared drive for `curtis@krygier.fr`
- Add `ag@krygier.co.uk` to OAuth consent screen test users (Client ID: `828378723395-sthb2fq69k997j81atek0edkkl6eakkd`)

### 4. Side panel link rendering
- When workspace-subagent returns a doc URL, render a clickable button in the side panel
- `window.open(url, '_blank')` on button click (user gesture — won't be blocked)

### 5. Add `ag@krygier.co.uk` auth flow
- Visit `https://workspace-subagent-auth-828378723395.us-central1.run.app/auth` as `ag@krygier.co.uk`
- Confirm token stored in Secret Manager

---

## Longer-Term Project Ambitions

### Project 1 — Real-time Meeting Diagrammer
- Agent listens to meeting, identifies architectural/process themes
- Generates Mermaid or D2 diagrams in real time
- Renders in side panel as conversation evolves
- Original motivating use case

### Project 2 — GE Native Auth (librarian-native on GE05)
- Current blocker: `GcpAuthProviderScheme` + `AuthenticatedFunctionTool` pattern not confirmed working
- Auth resource: `projects/633006702698/locations/global/authorizations/librarian-native-v5`
- Plan: strip to one tool, confirm credential shape from `_to_google_creds()`, then rebuild
- Unlocks: no separate OAuth consent URL — user's GE session flows straight through
- This is the last mile that makes the Meet demo seamless for any GE user

---

## Key Technical Notes (Don't Forget)

| Topic | Note |
|---|---|
| Hidden `<audio muted>` element | Chrome's Opus decoder is lazy — MUST play each track or AudioWorklet gets silence |
| AudioContext before `await` | Both 16kHz + 24kHz contexts must be created before any async call in the click handler |
| PCM batch size | 1600 samples = 100ms = ~600 RPM. Un-batched = ~7500 RPM → quota breach |
| `session.receive()` loop | Must wrap in `while not stop_event.is_set()` — exhausts after one turn otherwise |
| Cross-project billing | Cloud Run SA `649226456677-compute@` needs `roles/aiplatform.user` on GE05 |
| Shared drives | All Drive API calls need `supportsAllDrives=True` to see/move shared drive files |
| workspace-subagent endpoint | `projects/828378723395/locations/us-central1/reasoningEngines/2432159852814925824` |
| GE04 auth service | `https://workspace-subagent-auth-828378723395.us-central1.run.app/auth` |

---

## Delta Analysis & Sharing Strategy ("Virgin" Copy)

To share a clean version of this project on GitHub without exposing private credentials or environment-specific IDs, follow this approach.

### 1. Identify the "Delta"
The delta is the unique logic added to the base Meet Add-on template. Key custom files:
- **`index.tsx`**: Custom orb animations, wake-word detection, and `openInMainStage` logic.
- **`main.py`**: Integration with GE04 reasoning engine and Drive shortcut automation.
- **`public/main_stage.html`**: Shared document previewer.

### 2. Sanitization Checklist (Creating the "Virgin" Copy)
Before pushing to a public repository, remove or genericize these files:
- **Environment**: Delete `.env` and `.env.production`. Replace with `sample.env` containing empty values.
- **Apps Script**: Delete `appsscript/.clasp.json` (contains script IDs).
- **Hardcoded IDs**: Replace `649226456677` and `633006702698` with `YOUR_IDENTITY_PROJECT` and `YOUR_HOSTING_PROJECT` in `index.tsx` and `appsscript.json`.
- **Reasoning Engine**: Genericize the `WORKSPACE_AGENT_ENGINE` project path in `main.py`.

### 3. GitHub Reference
- **Private Repo**: `curtiskrygier/google-meet-live-architect-add-on-` (Current source of truth).
- **Public Reference**: Use the [Pierrick Voulet Sample](https://github.com/PierrickVoulet/meet-media-api-samples) as the baseline for calculating the architectural delta.

### 4. Delta Calculation Command
To see exactly what has changed relative to the clean state:
```bash
# Compare current state against the initial commit (assuming clean template start)
git diff --stat $(git rev-list --max-parents=0 HEAD) HEAD
```

---

## Reference — Pierrick Voulet
`https://github.com/PierrickVoulet/meet-media-api-samples/tree/meet-live-agent/meet-live-agent`
Two patterns that unblocked the last mile: hidden audio element + AudioContext before `await`.
His implementation is a fixed pipeline (no agent layer). Ours is ADK-extensible.
