# Diagramming Feature — Implementation Plan

## Overview

Add a "Diagramming" button to the connected side panel. When clicked, it sends the accumulated meeting transcript to a backend endpoint, generates a D2 architecture diagram using Gemini Flash, renders it to SVG server-side using the `d2` CLI, and pushes it to the Meet main stage for all participants.

This is **Option 1 (snapshot)**: each click generates a fresh diagram from the full transcript at that moment. Stateless, no session management needed.

---

## File 1: `Dockerfile`

Install the `d2` v0.7.1 binary in the Python runtime stage.

Replace the Python stage with:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
# Install d2 binary
RUN apt-get update && apt-get install -y curl tar && \
    curl -fsSL https://github.com/terrastruct/d2/releases/download/v0.7.1/d2-v0.7.1-linux-amd64.tar.gz \
    | tar -xz --strip-components=2 -C /usr/local/bin d2-v0.7.1-linux-amd64/bin/d2 && \
    apt-get remove -y curl tar && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
COPY --from=frontend /app/dist ./dist
ENV PORT=8080
EXPOSE $PORT
CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT --timeout-keep-alive 3600
```

Verify installation works with: `RUN d2 --version`

---

## File 2: `main.py` additions

### 2a. Imports to add at the top
```python
import asyncio
import subprocess
import tempfile
import uuid as uuid_lib
```
(`asyncio` is already imported — only add the others)

### 2b. In-memory diagram store — add after `gemini_client = ...`

```python
# In-memory store: diagram_id → SVG bytes  (cleared on restart, fine for demo)
_diagram_store: dict[str, bytes] = {}
```

### 2c. D2 generation function — add after `fetch_url()` function

```python
DIAGRAM_MODEL = "gemini-2.5-flash"

D2_PROMPT = """You are an expert systems architect. Analyse the meeting transcript below and generate a D2 diagram that best represents the system, architecture, process, or concepts being discussed.

Rules:
- Output ONLY valid D2 code. No markdown fences, no backticks, no explanation.
- Start with this exact header (do not change it):
  direction: right
  vars: {
    d2-config: {
      layout-engine: elk
      sketch: true
    }
  }
- Add a title using this format (replace with a short title derived from the meeting context):
  title: |md
    # <Meeting Title>
  | {near: top-center}
- Use clear, readable node/edge names derived from what was discussed.
- Choose the most appropriate structure: component diagram for architecture, sequence for flows, class for data models, mindmap for broad topics.
- If the transcript contains no clear technical content, generate a simple mindmap of the key topics discussed.
- Keep it focused: max 15 nodes.

Meeting transcript:
{transcript}
"""

async def generate_diagram(transcript: str) -> tuple[str, bytes]:
    """Returns (diagram_id, svg_bytes). Raises on failure."""
    diagram_text_client = genai.Client(vertexai=True, project=PROJECT_ID, location=REGION)
    response = await asyncio.to_thread(
        lambda: diagram_text_client.models.generate_content(
            model=DIAGRAM_MODEL,
            contents=D2_PROMPT.format(transcript=transcript[:8000]),
        )
    )
    d2_code = response.text.strip()
    # Strip markdown fences if model added them despite instructions
    d2_code = re.sub(r'^```[a-z]*\n?', '', d2_code, flags=re.MULTILINE)
    d2_code = re.sub(r'```$', '', d2_code, flags=re.MULTILINE).strip()

    print(f"[diagram] generated D2 ({len(d2_code)} chars)", flush=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        d2_path = f"{tmpdir}/diagram.d2"
        svg_path = f"{tmpdir}/diagram.svg"
        with open(d2_path, "w") as f:
            f.write(d2_code)
        result = subprocess.run(
            ["d2", "-t", "0", d2_path, svg_path],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"[diagram] d2 error: {result.stderr}", flush=True)
            raise RuntimeError(f"d2 render failed: {result.stderr[:200]}")
        with open(svg_path, "rb") as f:
            svg_bytes = f.read()

    diagram_id = str(uuid_lib.uuid4())
    _diagram_store[diagram_id] = svg_bytes
    print(f"[diagram] stored id={diagram_id} size={len(svg_bytes)}", flush=True)
    return diagram_id, svg_bytes
```

### 2d. HTTP endpoints — add before the `@app.websocket("/ws")` line

```python
from fastapi import Body
from fastapi.responses import Response as FastAPIResponse

@app.post("/api/diagram")
async def api_diagram(payload: dict = Body(...)):
    transcript = payload.get("transcript", "").strip()
    if not transcript:
        return {"error": "No transcript provided"}, 400
    try:
        diagram_id, _ = await generate_diagram(transcript)
        return {"id": diagram_id}
    except Exception as e:
        print(f"[diagram] {type(e).__name__}: {e}", flush=True)
        return {"error": str(e)}

@app.get("/api/diagram/{diagram_id}.svg")
async def get_diagram_svg(diagram_id: str):
    svg = _diagram_store.get(diagram_id)
    if not svg:
        return FastAPIResponse(status_code=404, content="Not found")
    return FastAPIResponse(content=svg, media_type="image/svg+xml")
```

---

## File 3: `public/diagram_stage.html` (new file)

Create this file at `public/diagram_stage.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Meeting Diagram</title>
  <script src="https://www.gstatic.com/meetjs/addons/1.1.0/meet.addons.js"></script>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Google Sans', sans-serif;
      background: #1a1a2e;
      color: #fff;
      height: 100vh;
      display: flex;
      flex-direction: column;
    }
    .topbar {
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 20px;
      background: rgba(255,255,255,0.05);
      border-bottom: 1px solid rgba(255,255,255,0.1);
      flex-shrink: 0;
    }
    .topbar-title {
      font-size: 14px;
      font-weight: 600;
      color: rgba(255,255,255,0.9);
    }
    .topbar-badge {
      font-size: 11px;
      color: rgba(255,255,255,0.4);
    }
    .diagram-wrap {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
      overflow: auto;
    }
    .diagram-wrap svg {
      max-width: 100%;
      max-height: 100%;
      border-radius: 12px;
      background: #fff;
      padding: 16px;
    }
    .loading {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
      color: rgba(255,255,255,0.5);
      font-size: 14px;
    }
    .spinner {
      width: 36px; height: 36px;
      border: 3px solid rgba(155,109,255,0.2);
      border-top-color: #9B6DFF;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .error {
      color: #f3a59f;
      font-size: 13px;
      padding: 20px;
      text-align: center;
    }
  </style>
</head>
<body>
  <div class="topbar">
    <span class="topbar-title" id="title">Meeting Diagram</span>
    <span class="topbar-badge">Generated by Gemini · D2</span>
  </div>
  <div class="diagram-wrap" id="wrap">
    <div class="loading">
      <div class="spinner"></div>
      <span>Generating diagram...</span>
    </div>
  </div>

  <script>
    const params = new URLSearchParams(location.search);
    const diagramId = params.get('id') || '';
    const title = params.get('title') || 'Meeting Diagram';

    document.getElementById('title').textContent = title;

    async function loadDiagram() {
      if (!diagramId) {
        document.getElementById('wrap').innerHTML = '<div class="error">No diagram ID provided.</div>';
        return;
      }
      try {
        const resp = await fetch(`/api/diagram/${diagramId}.svg`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const svg = await resp.text();
        document.getElementById('wrap').innerHTML = svg;
        // Remove fixed width/height from SVG so it scales
        const svgEl = document.getElementById('wrap').querySelector('svg');
        if (svgEl) {
          svgEl.removeAttribute('width');
          svgEl.removeAttribute('height');
          svgEl.style.maxWidth = '100%';
          svgEl.style.maxHeight = 'calc(100vh - 80px)';
        }
      } catch (e) {
        document.getElementById('wrap').innerHTML = `<div class="error">Failed to load diagram: ${e.message}</div>`;
      }
    }

    // Init Meet SDK
    (async () => {
      try {
        const session = await meet.addon.createAddonSession({ cloudProjectNumber: '649226456677' });
        await session.createMainStageClient();
      } catch (e) { console.warn('Meet SDK init:', e); }
    })();

    loadDiagram();
  </script>
</body>
</html>
```

---

## File 4: `index.tsx` changes

### 4a. Add `@state() diagramming` flag after the existing `@state()` declarations

Find this block:
```typescript
  @state() actionLinks: Array<{url: string; label: string}> = [];
```

Add after it:
```typescript
  @state() diagramming = false;
```

### 4b. Add `generateDiagram()` method — add after `openInMainStage()` method

```typescript
  private async generateDiagram() {
    if (!this.transcript.trim()) {
      this.status = 'No transcript yet — speak first';
      return;
    }
    this.diagramming = true;
    this.status = 'Generating diagram...';
    try {
      const resp = await fetch('/api/diagram', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transcript: this.transcript }),
      });
      const data = await resp.json();
      if (data.error) throw new Error(data.error);

      const stageUrl = `${location.origin}/diagram_stage.html?id=${encodeURIComponent(data.id)}&title=${encodeURIComponent('Meeting Architecture')}`;
      console.log('[concierge] launching diagram stage:', stageUrl);

      if (this.sidePanelClient) {
        await this.sidePanelClient.startActivity({ mainStageUrl: stageUrl });
      }
      this.status = 'Diagram pushed to main stage';
    } catch (e: any) {
      console.error('[concierge] diagram error:', e);
      this.status = `Diagram failed: ${e.message || e}`;
    } finally {
      this.diagramming = false;
    }
  }
```

### 4c. Replace the controls-row in the connected render block

Find the existing controls-row (3 controls: Mic, Video, Wake). Replace with a 4-control grid adding Diagramming as the 4th button. The grid should change from `grid-template-columns: 1fr 1fr 1fr` to `1fr 1fr 1fr 1fr` — update the CSS or add an inline style override.

Replace the entire `<div class="section">` containing the `controls-row` with:

```typescript
        <div class="section">
          <div class="controls-row" style="grid-template-columns:1fr 1fr 1fr 1fr">
            <div class="ctrl" data-active="${this.audioEnabled}" @click=${() => this.toggleAudio()}>
              <div class="ctrl-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:15px;height:15px"><path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/></svg>
              </div>
              <span class="ctrl-label">Mic</span>
              <span class="ctrl-state">${this.audioEnabled ? 'On' : 'Muted'}</span>
            </div>
            <div class="ctrl" data-active="${this.videoEnabled}" @click=${() => this.toggleVideo()}>
              <div class="ctrl-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:15px;height:15px"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>
              </div>
              <span class="ctrl-label">Video</span>
              <span class="ctrl-state">${this.videoEnabled ? 'On' : 'Off'}</span>
            </div>
            <div class="ctrl" data-active="${this.wakeActive}"
                 @click=${() => this.wakeActive ? this.deactivateWakeWord() : this.activateWakeWord()}>
              <div class="ctrl-icon">
                <svg viewBox="0 0 28 28" style="width:15px;height:15px"><path d="M14 1C14 8.2 8.2 14 1 14C8.2 14 14 19.8 14 27C14 19.8 19.8 14 27 14C19.8 14 14 8.2 14 1Z" fill="currentColor"/></svg>
              </div>
              <span class="ctrl-label">Wake</span>
              <span class="ctrl-state">${this.wakeActive ? 'Active' : 'Standby'}</span>
            </div>
            <div class="ctrl" data-active="false"
                 style="${this.diagramming ? 'opacity:0.6;pointer-events:none' : ''}"
                 @click=${() => this.generateDiagram()}>
              <div class="ctrl-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:15px;height:15px">
                  <rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>
                  <rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>
                  <line x1="6.5" y1="10" x2="6.5" y2="14"/><line x1="17.5" y1="10" x2="17.5" y2="14"/>
                  <line x1="10" y1="17.5" x2="14" y2="17.5"/>
                </svg>
              </div>
              <span class="ctrl-label">Diagram</span>
              <span class="ctrl-state">${this.diagramming ? 'Generating' : 'Snapshot'}</span>
            </div>
          </div>
        </div>
```

---

## Deploy

After all changes:

```bash
cd /home/curtis/gemini/addons/meet-live-concierge
gcloud run deploy meet-live-concierge \
  --source . \
  --region us-central1 \
  --project master-engine-495207-j8 \
  --quiet
```

Then test by:
1. Connecting the concierge in a Meet session
2. Speaking a few sentences about a system or architecture
3. Clicking "Diagram" in the controls row
4. The main stage should open with the D2-rendered SVG

---

## Gotchas

- The `d2` binary tar structure changed between versions. For v0.7.1, the binary is at `d2-v0.7.1-linux-amd64/bin/d2` inside the tarball. The `--strip-components=2` and path `d2-v0.7.1-linux-amd64/bin/d2` in the tar extract command must match exactly. Verify with: `tar -tzf d2-v0.7.1-linux-amd64.tar.gz | grep bin/d2`
- `diagram_stage.html` uses `cloudProjectNumber: '649226456677'` (the Marketplace project, NOT the Cloud Run project `633006702698`).
- The `/api/diagram` and `/api/diagram/{id}.png` endpoints must be registered **before** the static files mount (`app.mount("/", StaticFiles(...))`) otherwise FastAPI won't route to them.
- `_diagram_store` is in-memory — diagrams are lost on Cloud Run instance restart. Fine for demo; not persistent.
- The Gemini call in `generate_diagram()` uses `asyncio.to_thread()` to avoid blocking the event loop since the `google-genai` SDK's non-Live calls are synchronous.
- `generate_diagram` uses `genai.Client` directly (not the Live client) — same `PROJECT_ID` and `REGION` config applies.
