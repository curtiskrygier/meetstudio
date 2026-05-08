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

## Reference — Pierrick Voulet
`https://github.com/PierrickVoulet/meet-media-api-samples/tree/meet-live-agent/meet-live-agent`
Two patterns that unblocked the last mile: hidden audio element + AudioContext before `await`.
His implementation is a fixed pipeline (no agent layer). Ours is ADK-extensible.
