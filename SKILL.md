# meet-live-concierge — Component Reference

This add-on implements a voice-activated workspace assistant for Google Meet, evolving from a passive summarizer to an active A2UI orchestrator.

## Strategic Avenues of Exploration

### 🟢 Path A: A2UI (Agent-to-UI) — [Current Focus]
- **Concept**: A "Dumb Renderer" pattern where the backend Agent completely controls the UI structure, theme, and layout via JSON state broadcasts.
- **Key Files**: `index.tsx` (Dumb host), `main.py` (Centralized state), `internal/components/` (Modular registry).
- **Goal**: Perfect cinematic presentation (16:9) and low-latency interactive controls (Agendas, Polls, Action Items).

### 🔵 Path B: A2U Identity Proxy (Apps Script Bridge) — [Hardened Infrastructure]
- **Concept**: Bypassing the "Service Account Gap" in Apps Script by using a dedicated U2M OAuth bridge.
- **Key Files**: `appsscript-implementation-ge04/workspace-subagent-auth` (Source).
- **Goal**: Allow Gemini to execute existing enterprise logic in Apps Script using the user's real identity, ensuring full audit trails and permission compliance.

### 🔴 Path C: Headless Concierge (Puppeteer Driving) — [PRIORITY 1]
- **Concept**: Using a headless browser (Puppeteer) on the server to log in as the user (via A2U Proxy) and drive real web applications (Google Sheets, GCP Console) live on the Meet Main Stage.
- **Integration**: Uses the "Antigravity" / WebMCP pattern to pipe the virtual browser view into the Meet Add-on media stream.
- **Target**: Share a **real Google Sheet** on the Main Stage that Gemini can actually edit and scroll based on meeting conversation.

### 🟣 Path D: Meet Remote Control — [New Capability]
- **Concept**: A developer-first CLI and trigger-driven remote control suite for stage layouts, dynamic D2 diagrams, media injection, and speaker/mic-bypass.
- **Key Files**: `demo_driver.py` (CLI Client), `main.py` (Mute/Audio endpoints), `public/main_stage.js` (Iframe & View handlers).
- **Goal**: Perfect CLI automation of presentations, instantaneous drawing overlays, ad-hoc TTS narration, and YouTube embedding.

#### Implementation Breakdown (6-Part Framework)

##### 🛠️ Core Active Capabilities (Implemented)
- **Part 3: Smart Audio & Narration (Kore TTS)**:
  - Ad-Hoc 24kHz audio synthesis using Gemini 2.5 models (`api_speak` endpoint).
  - High-fidelity Web Audio soundboard synthesizer on-the-fly inside `main_stage.js` (`applause`, `drumroll`, `buzzer`, `ding`/`chimes`).
  - Active Gemini Live stream muting & speaker bypass to prevent duplicate loops or echo during TTS streaming.
- **Part 4: Interactive Live-Coding & Terminal Broadcast**:
  - Lossless command execution and real-time output stream mirror.
  - Active streaming container widget on the main stage synced with local terminal outputs.
- **Part 6: Session Dashboard & State Synchronization**:
  - Full active stage state query (`GET /api/stage-state/{space_id}`) mapping layout, listeners, dynamic diagrams, and playback.
  - Live D2 diagram rollback & chronological state versioning (`diagram_history` backend stack).

##### 📋 Remaining Capabilities (Planned / Future)
- **Part 1: Advanced Stage Layout & Window Management**:
  - Dynamic multi-view grid layouts & split-screens (e.g., side-by-side terminal + D2 diagram).
  - Target focus controls to maximize/minimize widgets on demand.
  - Custom stage styling and theme-swapping (Dark, Light, Glassmorphism, Cyberpunk).
- **Part 2: Live Interactive Elements**:
  - Virtual Laser Pointer streaming laser coordinate vector markers to stage viewers in real time.
  - Live drawing canvas layer for annotations, bounding boxes, or markup overlays on active diagrams.
  - Physics-based SVG floating emoji bursts responding to gravity.
- **Part 5: Rich Collaboration & Documents**:
  - Interactive live Markdown Notepad allowing CLI appends or edits on stage in real time.
  - Dynamic Web Asset embeddings (e.g., casting live code repos or staging portals directly).
- **Part 7: Platinum Experience (Next Gen)**:
  - **Stateful Collaborative Drawing**: Shared SVG/Canvas layer allowing participants to co-annotate and sketch on the main stage concurrently with the agent.
  - **Snapshotting & Version History**: Point-in-time state captures of the collaborative stage (D2 diagrams, markdown notes, drawings) for comparative review and rollback.
  - **Spatial Audio (Multi-person Presence)**: Integration of Web Audio PannerNodes to position participants' virtual avatars or sound effects in 3D space, enhancing the sense of presence.

## Core Patterns

### 1. Multi-Project Architecture

> ⚠️ **CRITICAL — NEVER CHANGE THESE VALUES. Mixing up these two project numbers is the most common source of OAuth and Meet SDK auth failures.**

| Role | Project ID | Project Number |
|---|---|---|
| **OAuth / Workspace registration** | `agent-archi` | `649226456677` |
| **Cloud Run / Vertex AI (production hosting)** | `centered-planet-497209-r5` | `431547562459` |

- **OAuth Client ID**: `649226456677-kg2d06f201h6narlrddgass1qs2ka3e1.apps.googleusercontent.com` — always from `agent-archi`
- **`CLOUD_PROJECT_NUMBER` in `.env.production`**: MUST be `649226456677` (the OAuth/identity project). This is what `createAddonSession` in `index.tsx` passes to the Meet SDK — Google Meet validates it against the registered add-on in `agent-archi`. Using `431547562459` here silently breaks the Meet SDK handshake.
- **`--project` flag in `gcloud run deploy`**: MUST be `centered-planet-497209-r5`. Never deploy to `agent-archi`.
- **`--set-build-env-vars CLOUD_PROJECT_NUMBER`**: MUST be `649226456677` (same as `.env.production`).
- **`appsscript/appsscript.json` `addOnOrigins`**: Must contain only `CONCIERGE_API_URL_PLACEHOLDER`. Never add URLs from other projects or regions.
- **Handshake**: `index.tsx` uses `CLOUD_PROJECT_NUMBER=649226456677` for `createAddonSession`. The Cloud Run hosting project (`431547562459`) is only relevant for `gcloud run deploy --project` and server-side `GEMINI_PROJECT`.

### 2. Frontend Deployment & Hosting Boundary
- **Vite Frontend (Cloud Run)**: The built React/Vite assets are hosted and served entirely by **Cloud Run** under `agent-archi`. They are NOT bundled or pushed via Apps Script or clasp.
- **Apps Script Manifest (clasp)**: Apps Script is strictly a metadata wrapper. Running `clasp push` uploads only `appsscript.json` and `Code.js` to register the sidebar's entry point URL (`sidePanelUrl`) and authorized origins pointing to the Cloud Run URL.

### 3. Audio Pipeline
- **Opus Decoder**: Chrome's decoder is lazy. We use a hidden `<audio muted>` element for every track to force decoding so `AudioWorklet` receives non-silent PCM.
- **Batching**: PCM chunks are batched into 100ms segments (1600 samples) before being sent to Gemini Live to prevent RPM quota breaches.

### 4. Workspace Agent Integration
- **Reasoning Engine**: The backend calls a delegated Vertex AI Reasoning Engine (GE04) to handle Workspace tasks (docs, drive, search).
- **Redirection**: Documents generated by the agent are automatically "pushed" to the Meet main stage via `sidePanelClient.startActivity`.

### 5. Remote Control Trigger Engine
- **Comment-Driven Triggers**: Scripts like `demo_driver.py` parse text files for dynamic triggers (e.g., `# [TRIGGER: image: <prompt>]` or `# [TRIGGER: video: <url>]`) to orchestrate visuals synchronously with audio playback.
- **Audio and Mic Bypassing**: When automated pitches are streamed via PCM injection, the backend mutes Gemini Live's audio output and drops browser microphone inputs to avoid double-talk and echo feedback.

## Deployment Commands

### Step 1 — Local Verification
Always test that the TypeScript frontend builds successfully locally before deploying:
```bash
npm run build
```

### Step 2 — Backend & Frontend Deploy (Cloud Run)
Deploy the updated container (which handles both server-side Python socket endpoints and serves static Vite assets under `/dist`):
```bash
gcloud run deploy meet-live-concierge \
  --source . \
  --region us-central1 \
  --timeout=3600 \
  --session-affinity \
  --allow-unauthenticated \
  --set-build-env-vars="CLIENT_ID=649226456677-kg2d06f201h6narlrddgabs1qs2ka3e1.apps.googleusercontent.com,CLOUD_PROJECT_NUMBER=431547562459" \
  --set-env-vars="GEMINI_PROJECT=centered-planet-497209-r5,REGION=us-central1,KORE_VOICE=Charon,CLIENT_ID=649226456677-kg2d06f201h6narlrddgabs1qs2ka3e1.apps.googleusercontent.com" \
  --project=centered-planet-497209-r5
```

### Step 3 — Manifest Deploy (clasp)
Push the lightweight Apps Script container to associate Google Meet with your live Cloud Run URL:
```bash
cd appsscript
clasp push --force
clasp deploy --description "v1"
```

---

## 🔮 Demo Preservation & Reset-Safe Knowledge Base

These findings represent hard-earned, non-obvious engineering constraints discovered during testing. If the agent session resets, **adhere strictly to these principles** to maintain a flawless demonstration:

### 1. YouTube Autoplay Bypass Pattern
- **Problem**: Modern browsers (Chrome, Safari) strictly block programmatic unmuting (`unMute()`, `setVolume()`) on start unless triggered by a genuine user click on the parent frame. programmaic play requests fail with security exceptions.
- **Solution**: Always initialize the YouTube frame in **muted mode** (`mute=1`). This allows the browser to bypass autoplay blocks and start rendering video immediately 100% of the time. Programmatic unmuting on launch must be avoided.

### 2. Vertex AI Tool-Binding Schema Constraint
- **Problem**: The `google.genai` SDK for Vertex AI does **not** natively support Python coroutines (`async def`) for automated tool-binding schema extraction.
- **Solution**: All tools bound to the model must be synchronous standard `def` blocks, utilizing synchronous client requests (`httpx.Client()` instead of `httpx.AsyncClient()`) for downstream HTTP calls.

### 3. Agent vs. Endpoint Execution Philosophy
- **Endpoints** act as *deterministic tools* (e.g., drawing layout coords, switching widgets, starting activities).
- **Agents** act as *planners* (utilizing Vertex/Gemini reasoning to decide *when* and *how* to sequence those deterministic endpoints based on high-level workspace directives).

### 4. Custom Demo Assets (Theme Alignment)
Do not use placeholder, generic, or randomly generated images. The following static premium dark-themed UI mockups have been generated and baked into the Vite public folder:
- **Sidebar UX Concept (Panel 1)**: `/panel1_a2ui.png` — Visualizes transcript feeds, AI suggestions, and sidebar controls.
- **A2A Architecture Blueprint (Panel 2)**: `/panel2_a2a.png` — Detailed neon-digital technical workflow of the multi-agent system.

### 6. Google Meet Bottom Bar Overlay (Captions & Lower-Thirds Layout)
- **Problem**: In an actual Google Meet integration, Meet's bottom control bar overlays the bottom ~80px to 100px of the addon main stage iframe. Any lower-third elements or captions styled with typical low-offset values (e.g. `bottom: 6px`) will be completely obscured or hidden from view.
- **Solution**: Always style lower-third components (such as `gdm-captions`) or floating overlay panels with a safe bottom margin of at least `96px` to `110px`. This ensures the floating components clear the native Google Meet overlay flawlessly while aligning cleanly with active stage chat widgets (which use `bottom: 90px`).

### 7. Running the Pristine Showcase
- **Active Meeting Space**: `spaces/iLtvhiN9xNwB`
- **Run non-recorded demo**:
  ```bash
  cd /home/curtis/gemini/addons/meet-live-concierge && python3 demo_a2ui_showcase.py
  ```
- **Run demo with headless recording**:
  ```bash
  cd /home/curtis/gemini/addons/meet-live-concierge && python3 record_stage.py
  ```
- **Output Artifact**: High-fidelity recording at `demo_recording.mp4`.



