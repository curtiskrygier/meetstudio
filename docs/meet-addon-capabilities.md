# Google Meet Add-on Capabilities — Developer Runbook

Reference for what is and isn't possible when building Google Meet add-ons using the Meet Add-on SDK and Workspace Add-ons API.

---

## Architecture

```
Google Meet (browser)
├── Side Panel iframe        ← your web app (index.tsx / Cloud Run)
│   └── SidePanelClient      ← SDK object, one per user
├── Main Stage iframe        ← your web app (main_stage.html / Cloud Run)
│   └── MainStageClient      ← SDK object, active only during an activity
└── Meet UI                  ← Google's own UI, not accessible
```

Your add-on is a web app hosted externally (Cloud Run). Meet loads it in iframes. The SDK bridges communication between your iframes and Meet.

---

## Deployment Stack

| Layer | What it is | How configured |
|---|---|---|
| Apps Script project | Hosts the `appsscript.json` manifest | `clasp push` / `clasp deploy` |
| Marketplace SDK | Links the Marketplace listing to a deployment | GCP Console → Marketplace SDK |
| Workspace Add-ons API | Alternative deployment path for the add-on config | `gcloud workspace-add-ons deployments` |
| Cloud Run | Serves the actual web app (side panel + main stage) | `gcloud builds submit` from project root |

**Critical:** `gcloud builds submit` must be run from the project root (`meetstudio/`), not from a subdirectory like `appsscript/`.

---

## Side Panel

### Initialisation
```typescript
const session = await meet.addon.createAddonSession({ cloudProjectNumber });
const sidePanelClient = await session.createSidePanelClient();
const meetingInfo = await sidePanelClient.getMeetingInfo();
// meetingInfo.meetingId → "spaces/XXXXXXXXXXXXXXX" (NOT the vpp-xxxx-xxx code)
```

### What you get from getMeetingInfo()
- `meetingId` — the full resource name (`spaces/...`), same for all participants in a call
- Meeting title, conference ID
- **Not available:** participant list, other users' identities

### Key methods
| Method | What it does |
|---|---|
| `startActivity({ mainStageUrl, sidePanelUrl?, additionalData? })` | Pushes the main stage to all participants; shows "Join the activity" prompt to those who have the side panel open |
| `getFrameOpenReason()` | Returns `OPEN_ADDON`, `START_ACTIVITY`, or `JOIN_ACTIVITY` — use to auto-detect participant join |
| `getActivityStartingState()` | Returns `{ mainStageUrl, sidePanelUrl, additionalData }` set by the host |
| `setActivityStartingState(state)` | Update the activity state mid-session |
| `on('frameToFrameMessage', cb)` | Receive messages from the main stage frame |
| `sendMessage(payload)` | Send a message to the main stage frame |
| `closeAddon()` | Close the side panel |

### What is NOT possible from the side panel
- Getting participant names or emails without OAuth
- Listing who is in the call
- Seeing whether another user has the add-on open
- Programmatically clicking "Join the activity" for a participant (Meet UI only)
- Detecting when the presenter starts an activity in real-time (must poll or wait for JOIN_ACTIVITY)

---

## Main Stage / Activity

### How startActivity() works
- Only one activity can be running at a time per meeting
- Calling `startActivity()` from the **host** pushes the `mainStageUrl` to all participants
- Participants who have the add-on side panel open see a "Join the activity" prompt — **one click required**, cannot be bypassed
- Participants who do NOT have the side panel open see the stage automatically with no prompt
- The `sidePanelUrl` parameter specifies what the participant's side panel loads when they click "Join the activity"
- The `additionalData` string (max 4096 chars) is available to participants via `getActivityStartingState()`

### ActivityStartingState
```typescript
await sidePanelClient.startActivity({
  mainStageUrl: 'https://your-app/main_stage.html?join_session=spaces/XXX&ticket=YYY',
  sidePanelUrl: 'https://your-app/',        // what participant side panel loads on join
  additionalData: JSON.stringify({ session: meetingId })  // arbitrary data for participants
});
```

### Detecting JOIN_ACTIVITY
```typescript
const reason = await sidePanelClient.getFrameOpenReason();
// 'OPEN_ADDON'      — user opened add-on normally
// 'START_ACTIVITY'  — user started the activity
// 'JOIN_ACTIVITY'   — user clicked "Join the activity"
if (reason === 'JOIN_ACTIVITY') {
  // auto-skip to participant view, no role picker needed
}
```

### Main stage URL parameters
Pass state via query params in `mainStageUrl`. In `main_stage.html`:
- `?meeting=spaces/XXX` — presenter mode, stage listens on that space
- `?join_session=spaces/XXX` — participant mode, calls `/api/join/spaces/XXX` to create a private space
- `?ticket=XXX` — short-lived auth token for the stage WebSocket

---

## Frame-to-Frame Communication

```typescript
// Side panel → Main stage
sidePanelClient.sendMessage(JSON.stringify({ type: 'slide_change', slide: 3 }));

// Main stage → Side panel (via notifyMainStage or frameToFrameMessage)
mainStageClient.notifyMainStage(JSON.stringify({ type: 'feedback', data: '...' }));

// Side panel receives from main stage
sidePanelClient.on('frameToFrameMessage', (msg) => {
  const data = JSON.parse(msg.payload);
  // msg.originator = 'MAIN_STAGE' or 'SIDE_PANEL'
});
```

**Limitation:** Messages are only between your two iframes (side panel ↔ main stage). You cannot message other participants' frames directly.

---

## Participant Individual Targeting (MeetStudio pattern)

Since `startActivity()` sends one URL to everyone, individual targeting requires a server-side fan-out pattern:

```
Presenter fires slide to meetingId (spaces/XXX)
    ↓
broadcast_to_stage() on server fans out to:
    → spaces/XXX-pABC  (Participant A's private space)
    → spaces/XXX-pDEF  (Participant B's private space)
    → spaces/XXX-pGHI  (Participant C's private space)

Presenter fires to spaces/XXX-pABC only
    → Only Participant A sees it
```

Each participant's `main_stage.html?join_session=spaces/XXX` auto-calls `/api/join/spaces/XXX` which creates a unique private space and registers it under the session.

---

## OAuth & Permissions

The side panel runs in an iframe — standard OAuth flows via `google.accounts.oauth2` work. Required scopes for MeetStudio:
- `https://www.googleapis.com/auth/meetings.space.readonly` — read meeting info
- `https://www.googleapis.com/auth/chat.messages.readonly` — read chat
- `https://www.googleapis.com/auth/drive.file` — create/read Drive files
- `openid`, `email` — user identity

**Not available without extra approval:**
- Meet Media API (real-time audio/video streams) — requires separate GCP allowlist
- `meetings.space.created` or admin-level meeting data

---

## What IS Possible

- Custom side panel UI shown to all call participants who have the add-on installed
- Push content to the main stage for everyone simultaneously via `startActivity()`
- Individual targeting via server-side fan-out to per-participant WebSocket spaces
- Bi-directional messaging between side panel and main stage iframes
- Detecting join reason (`JOIN_ACTIVITY`) to auto-configure participant view
- Passing state to participants via `additionalData` in `ActivityStartingState`
- OAuth token acquisition in the side panel for Google APIs
- Real-time WebSocket connection to a Cloud Run backend
- Playbook/slide system: server fires pre-built A2UI surfaces to stage listeners
- Multiple participants registering names/identity via the side panel

## What is NOT Possible

- Force-joining a participant to an activity without their click (Meet enforces consent)
- Knowing which specific users are in the call (no participant roster API)
- Sending different `mainStageUrl` to different participants — one URL for all
- Programmatic "close side panel for this participant" from another user
- Reading audio/video streams without Meet Media API allowlist
- Cross-add-on communication
- Modifying Meet's own UI (mute buttons, tile layouts, etc.)
- Detecting when a specific participant leaves the call

---

## Known Gotchas

| Issue | Root cause | Fix |
|---|---|---|
| "Unable to find addon for Addon ID" | Marketplace listing not re-published after deployment ID change | Publish updated Store Listing in GCP Console |
| "Only a single instance of an activity can be in use at a time" | Normal Meet behaviour when participant opens side panel while activity runs | Expected — participant must click "Join the activity" |
| Bundle not updating after deploy | `gcloud builds submit` run from wrong directory (e.g. `appsscript/`) | Always run from project root `meetstudio/` |
| `startActivity()` fails with `ActivityIsOngoing` | Activity already running, calling again fails | Use `setActivityStartingState()` to update instead |
| `getFrameOpenReason()` returns `UNKNOWN` | Called before SDK fully initialised | Await after `createSidePanelClient()` |
| meetingId is `spaces/XXXXX` not `vpp-xxxx-xxx` | The human-readable room code ≠ SDK meeting ID | Use `getMeetingInfo().meetingId` |

---

## MeetStudio-Specific Endpoints

| Endpoint | Auth | Purpose |
|---|---|---|
| `GET /api/session/{id}/active` | None | Participants poll to detect session start |
| `GET /api/join/{session_id}?name=` | None | Create participant private space + ticket |
| `POST /api/join-code/{session_id}` | Producer | Create human-readable join code |
| `POST /api/playbook/fire/{playbook}/{slide}/{space}` | Producer | Fire a slide to a specific space |
| `POST /api/session/broadcast/{session_id}/{playbook}/{slide}` | Producer | Broadcast slide to all participants |
| `GET /api/session/participants/{session_id}` | Producer | List participants with name + connection status |
| `GET /presenter/{space_id}?ticket=` | API key | Standalone presenter control room |
| `GET /api/version` | None | Server build time for version badge |
