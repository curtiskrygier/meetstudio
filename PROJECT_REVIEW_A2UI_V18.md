# A2UI Migration: Phase 3 Review Bundle

This bundle contains the complete source code for the **Meet Live Concierge** project following the Phase 3 migration to a fully Server-Driven UI (A2UI) architecture.

---

## 1. Backend: main.py
*Location: `/home/curtis/gemini/addons/meet-live-concierge/main.py`*

```python
import asyncio
import base64
import json
import os
import re
import uuid as uuid_lib
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, Depends, HTTPException
from fastapi.responses import FileResponse, Response as FastAPIResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import httpx
import traceback

import logging

# Basic logging setup to replace prints
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("concierge")

# Modular imports
from app.config import (
    PROJECT_ID, REGION, MODEL, VOICE, SYSTEM_PROMPT,
    gemini_client, diagram_store, diagram_version, diagram_title,
    current_session, current_view, stage_listeners, WORKSPACE_AGENT_ENGINE
)
from app.auth import validate_google_token
from app.utils import fetch_url, svg_to_png
from app.drive import (
    get_calendar_meeting_name, get_or_create_meeting_folder,
    save_diagram_to_drive, fetch_meeting_chat, save_doc_shortcut_to_drive
)
from app.diagrams import generate_diagram, render_d2

from google.genai import types

@asynccontextmanager
async def lifespan(app):
    # Cleanup task for expired tickets
    async def cleanup_tickets():
        while True:
            await asyncio.sleep(300) # every 5 mins
            now = datetime.now(timezone.utc)
            expired = [t for t, (tok, exp) in auth_tickets.items() if exp < now]
            for t in expired: auth_tickets.pop(t, None)
            if expired: logger.info(f"[auth] Purged {len(expired)} expired tickets")
    
    task = asyncio.create_task(cleanup_tickets())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)

class MeetFramingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "ALLOWALL"
        response.headers["Content-Security-Policy"] = (
            "frame-ancestors 'self' https://*.google.com https://*.googleusercontent.com; "
            "default-src 'self' 'unsafe-inline' https://*.google.com https://*.googleusercontent.com; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' blob: data: https://*.google.com https://*.gstatic.com https://*.googleapis.com https://*.googleusercontent.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://*.google.com; "
            "connect-src 'self' https://*.google.com https://*.googleapis.com https://*.google-analytics.com wss://* ws://* *; "
            "img-src * data: blob:; "
            "font-src 'self' data: https://fonts.gstatic.com https://*.google.com;"
        )
        return response

app.add_middleware(MeetFramingMiddleware)

import secrets

auth_tickets: dict[str, tuple[str, datetime]] = {}

async def get_token_from_header(request: Request) -> str:
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    return auth[7:]

async def token_required(token: str = Depends(get_token_from_header)):
    if not await validate_google_token(token):
        raise HTTPException(status_code=403, detail="Invalid or expired Google token")
    return token

async def broadcast_to_stage(meeting_id: str, message: dict):
    if not meeting_id: return
    if message.get("type") == "view_change":
        current_view[meeting_id] = message
    if meeting_id not in stage_listeners: return
    payload = json.dumps(message)
    for ws in list(stage_listeners[meeting_id]):
        try: await ws.send_text(payload)
        except Exception: pass

async def live_session(websocket: WebSocket, meeting_id: str):
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE)
            )
        ),
        input_audio_transcription=types.AudioTranscriptionConfig(),
        system_instruction=types.Content(parts=[types.Part(text=SYSTEM_PROMPT)]),
        tools=[
            types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="workspace_agent",
                    description="Call the Google Workspace AI agent to create documents or find files.",
                    parameters={
                        "type": "OBJECT",
                        "properties": {"query": {"type": "string", "description": "The task to perform."}},
                        "required": ["query"]
                    }
                ),
                types.FunctionDeclaration(
                    name="present_on_main_stage",
                    description="Push a document or file to the Meet main stage for everyone to see.",
                    parameters={
                        "type": "OBJECT",
                        "properties": {
                            "url": {"type": "string", "description": "The URL of the document."},
                            "label": {"type": "string", "description": "The title of the document."},
                            "content": {"type": "string", "description": "Optional: preview content or summary to display on the stage."}
                        },
                        "required": ["url", "label"]
                    }
                ),
                types.FunctionDeclaration(
                    name="update_interface",
                    description="Update the user interface of the add-on side panel and the Meet Main Stage.",
                    parameters={
                        "type": "OBJECT",
                        "properties": {
                            "diagram_mode": {"type": "boolean", "description": "Set to true if generating or discussing a diagram."},
                            "main_stage_view": {"type": "string", "enum": ["diagram", "doc", "placeholder"], "description": "What to show on the main stage."},
                            "status_text": {"type": "string", "description": "A short status message to display to the user in the side panel."}
                        }
                    }
                ),
                types.FunctionDeclaration(name="fetch_url", description="Get content of a URL.", parameters={
                    "type": "OBJECT", "properties": {"url": {"type": "string"}}, "required": ["url"]
                }),
            ]),
            types.Tool(google_search=types.GoogleSearch()),
        ],
    )

    ui_state = {
        "status_state": "connecting",
        "status_text": "Connecting to Gemini Live...",
        "authenticated": True,
        "audioEnabled": True,
        "videoEnabled": False,
        "diagramMode": False,
        "transcriptMode": False,
        "actionLinks": []
    }

    async def broadcast_a2ui():
        payload = {
            "type": "A2UI_STATE",
            "components": [
                {
                    "id": "hero_status",
                    "element": "gdm-status-view",
                    "props": { "state": ui_state["status_state"], "status": ui_state["status_text"], "authenticated": ui_state["authenticated"] }
                },
                {
                    "id": "control_bar",
                    "element": "gdm-controls-view",
                    "props": { "audioEnabled": ui_state["audioEnabled"], "videoEnabled": ui_state["videoEnabled"], "diagramMode": ui_state["diagramMode"], "transcriptMode": ui_state["transcriptMode"] }
                },
                {
                    "id": "workspace_links",
                    "element": "gdm-actions-view",
                    "props": { "actions": ui_state["actionLinks"] }
                }
            ]
        }
        try: await websocket.send_text(json.dumps(payload))
        except Exception as e: logger.error(f"[a2ui] Broadcast error: {e}")

    await broadcast_a2ui()

    async with gemini_client.aio.live.connect(model=MODEL, config=config) as session:
        ui_state["status_state"] = "listening"
        ui_state["status_text"] = "Assistant connected — listening"
        await broadcast_a2ui()

        stop_event = asyncio.Event()
        workspace_user = [""]
        session_token = [""]
        session_space = [meeting_id]
        current_turn = {"id": str(uuid_lib.uuid4()), "role": None}

        async def browser_to_gemini():
            try:
                while not stop_event.is_set():
                    msg = await websocket.receive()
                    raw = msg.get("bytes")
                    text = msg.get("text")
                    if raw:
                        await session.send_realtime_input(audio=types.Blob(data=raw, mime_type="audio/pcm;rate=16000"))
                    elif text:
                        data = json.loads(text)
                        if data.get("type") == "init":
                            workspace_user[0] = data.get("user_email", "")
                            session_token[0] = data.get("access_token", "")
                            if data.get("meeting_id"): session_space[0] = data.get("meeting_id")
                            logger.info(f"[ws] init user={workspace_user[0]} space={session_space[0]}")
                        elif data.get("type") == "diagram_mode":
                            ui_state["diagramMode"] = bool(data.get("active", False))
                            ui_state["status_text"] = "Gemini Agent Architect" if ui_state["diagramMode"] else "Assistant connected"
                            await broadcast_a2ui()
                        elif data.get("type") == "view_change":
                            await broadcast_to_stage(session_space[0], data)
            except Exception: stop_event.set()

        recv_task = asyncio.create_task(browser_to_gemini())

        try:
            while not stop_event.is_set():
                async for response in session.receive():
                    if stop_event.is_set(): break
                    if response.tool_call:
                        responses = []
                        for fc in response.tool_call.function_calls:
                            if fc.name == "workspace_agent":
                                res = await call_workspace_agent(fc.args.get("query", ""), user_id=workspace_user[0])
                                responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": res}))
                                for url in re.findall(r'https?://(?:docs|drive|sheets|slides)\.google\.com/[^\s)]+', res):
                                    clean_url = url.rstrip('.,)')
                                    label = "Open Spreadsheet" if "spreadsheets" in clean_url else "Open Document"
                                    ui_state["actionLinks"].append({"url": clean_url, "label": label, "content": res})
                                    await broadcast_a2ui()
                                    await broadcast_to_stage(session_space[0], {"type": "view_change", "mode": "doc", "url": clean_url, "label": label, "content": res})
                            elif fc.name == "update_interface":
                                if "diagram_mode" in fc.args: ui_state["diagramMode"] = fc.args["diagram_mode"]
                                if "status_text" in fc.args: ui_state["status_text"] = fc.args["status_text"]
                                await broadcast_a2ui()
                                stage_view = fc.args.get("main_stage_view")
                                if stage_view: await broadcast_to_stage(session_space[0], {"type": "view_change", "mode": stage_view})
                                responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": "UI updated"}))
                            elif fc.name == "fetch_url":
                                responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": await fetch_url(fc.args.get("url", ""))}))
                            else: responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": "ok"}))
                        if responses: await session.send_tool_response(function_responses=responses)
                        continue
                    # ... (transcript and audio piping logic)
        finally:
            stop_event.set()
            recv_task.cancel()

@app.get("/api/auth/ticket")
async def create_auth_ticket(token: str = Depends(token_required)):
    ticket = secrets.token_urlsafe(32)
    expiry = datetime.now(timezone.utc) + timedelta(minutes=5)
    auth_tickets[ticket] = (token, expiry)
    return {"ticket": ticket}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, meeting_id: str = "", token: str = ""):
    ticket_data = auth_tickets.get(token)
    if not ticket_data or ticket_data[1] < datetime.now(timezone.utc):
        await websocket.close(code=1008); return
    await websocket.accept()
    try: await live_session(websocket, meeting_id)
    except WebSocketDisconnect: pass

@app.websocket("/ws/stage")
async def ws_stage_endpoint(websocket: WebSocket, meeting_id: str = "", ticket: str = ""):
    ticket_data = auth_tickets.get(ticket)
    if not ticket_data or ticket_data[1] < datetime.now(timezone.utc):
        await websocket.close(code=1008); return
    await websocket.accept()
    # ... (stage listener registration logic)
```

---

## 2. Frontend: index.tsx
*Location: `/home/curtis/gemini/addons/meet-live-concierge/index.tsx`*
Modular "Dumb Renderer" using Server-Driven state.

```typescript
@customElement('gdm-architect-agent')
export class GdmArchitectAgent extends LitElement {
  @state() components: Array<{id: string; element: string; props: any}> = [];
  // ... (session properties)

  private renderComponent(comp: any) {
    switch(comp.element) {
      case 'gdm-status-view':
        return html`<gdm-status-view .state=${comp.props.state} .status=${comp.props.status} .authenticated=${comp.props.authenticated}></gdm-status-view>`;
      case 'gdm-controls-view':
        return html`<gdm-controls-view .audioEnabled=${comp.props.audioEnabled} .videoEnabled=${comp.props.videoEnabled} .diagramMode=${comp.props.diagramMode} .transcriptMode=${comp.props.transcriptMode} @toggle-audio=${()=>this.toggleAudio()} @toggle-video=${()=>this.toggleVideo()} @toggle-diagram=${()=>this.toggleDiagramMode()} @toggle-transcript=${()=>this.toggleTranscriptMode()}></gdm-controls-view>`;
      case 'gdm-actions-view':
        return html`<gdm-actions-view .actions=${comp.props.actions} @action-click=${(e: any)=>this.openInMainStage(e.detail.url, e.detail.label, e.detail.content)}></gdm-actions-view>`;
      default: return html``;
    }
  }

  render() {
    return html`
      <div class="body">
        ${this.connected ? html`
          ${this.components.map(comp => html`<div class="section">${this.renderComponent(comp)}</div>`)}
          <!-- ... (Transcript section) -->
        ` : html`<!-- ... (SignIn / Checklist) -->`}
      </div>`;
  }
}
```

---

## 3. Main Stage: main_stage.html
*Location: `/home/curtis/gemini/addons/meet-live-concierge/public/main_stage.html`*
Cinematic 16:9 layout with direct SVG streaming.

```html
<style>
    #content-layer {
      flex: 1; display: flex; align-items: center; justify-content: center;
      width: 100%; aspect-ratio: 16 / 9;
      max-height: calc(100vh - 48px - 140px);
      margin: 0 auto; background: #0c0d10;
    }
    #diagram-container svg {
      width: 100%; height: 100%; object-fit: contain;
    }
</style>
<script>
    function renderInlineSVG(base64) {
      const svg = atob(base64);
      const container = document.getElementById('diagram-container');
      container.innerHTML = svg;
    }
    // WebSocket listener for "svg" field in "view_change" message
</script>
```
