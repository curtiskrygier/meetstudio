import asyncio
import base64
import inspect
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
import markdown
import bleach
import logging

# Security: HTML Sanitization Whitelist
ALLOWED_TAGS = [
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'hr',
    'ul', 'ol', 'li', 'strong', 'em', 'b', 'i', 'code', 'pre',
    'blockquote', 'a', 'span', 'div'
]
ALLOWED_ATTRS = {
    'a': ['href', 'title', 'target'],
    'span': ['class'],
    'div': ['class']
}

def sanitize_html(raw_html: str) -> str:
    """Strips dangerous tags/scripts from AI-generated HTML."""
    return bleach.clean(raw_html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS)

THEME_PRESETS = {
    "default":    {"--bg-0":"#0c0d10","--bg-1":"#131418","--fg":"#f2f3f5","--fg-2":"#b8bcc4","--gem-1":"#4285F4","--radius":"14px","--font":"'Plus Jakarta Sans',sans-serif"},
    "matrix":     {"--bg-0":"#000000","--bg-1":"#050a00","--fg":"#00ff41","--fg-2":"#00cc33","--gem-1":"#00ff41","--gem-2":"#008f11","--live":"#39ff14","--radius":"0px","--font":"'Courier New',monospace","--line":"#003b00"},
    "blueprint":  {"--bg-0":"#001b35","--bg-1":"#002548","--fg":"#4fc3f7","--gem-1":"#29b6f6","--radius":"4px","--font":"'Roboto Mono',monospace"},
    "corporate":  {"--bg-0":"#f8f9fa","--bg-1":"#ffffff","--fg":"#1a1a1a","--fg-2":"#5f6368","--gem-1":"#1a73e8","--radius":"8px","--font":"'Google Sans',sans-serif"},
    "neon":       {"--bg-0":"#0a0014","--bg-1":"#120020","--fg":"#e040fb","--gem-1":"#ea80fc","--gem-2":"#ff4081","--radius":"16px","--font":"system-ui"},
    "minimal":    {"--bg-0":"#ffffff","--fg":"#000000","--fg-2":"#333","--gem-1":"#000","--line":"#e0e0e0","--radius":"6px"},
    "red":        {"--bg-0":"#1a0505","--bg-1":"#2a0808","--fg":"#ffcccc","--fg-2":"#ff9999","--gem-1":"#ea4335","--gem-2":"#ff5252","--line":"#4a1a1a","--radius":"4px","--font":"system-ui"},
    "blue":       {"--bg-0":"#050a1a","--bg-1":"#08142a","--fg":"#ccd9ff","--fg-2":"#99b3ff","--gem-1":"#4285F4","--gem-2":"#6699ff","--line":"#1a2a4a","--radius":"4px","--font":"system-ui"},
}

# Allowlists for /api/ui-prompt — fields the LLM is permitted to set
_ALLOWED_UI_FIELDS = frozenset({
    "status_text", "diagram_mode", "main_stage_view",
    "theme_preset", "theme_tokens", "layout",
    "component_visibility", "stage_theme", "banner",
    "workspace_agent"
})
_ALLOWED_LAYOUTS = frozenset({"default", "focus", "minimal", "presentation", "split"})
_ALLOWED_STAGE_VIEWS = frozenset({"diagram", "doc", "placeholder", "browser", "image"})
_ALLOWED_VISIBILITY_KEYS = frozenset({"transcript", "action_links", "controls", "diagram_refiner"})

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
    current_session, current_view, stage_listeners, WORKSPACE_AGENT_ENGINE,
    UI_PROMPT_SYSTEM, active_sessions, video_queues,
    current_a2ui_surface, current_a2ui_datamodel, current_a2ui_root
)
from app.auth import validate_google_token, check_producer_auth
from app.utils import fetch_url, svg_to_png
from app.drive import (
    get_calendar_meeting_name, get_or_create_meeting_folder,
    save_diagram_to_drive, fetch_meeting_chat, save_doc_shortcut_to_drive
)
from app.diagrams import generate_diagram, render_d2
from app.images import generate_image, image_cache
from app.mcp_server import handle_mcp
from app.reactions import detect_emojis
from app.a2ui_catalog import A2UI_CATALOG, validate_a2ui_surface, validate_a2ui_surface_detailed

from google.genai import types

notepad_locks = {}  # meeting_id -> {"owner": owner_id, "expires_at": float}


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
        # Hardened CSP: Removed unsafe-inline and unsafe-eval
        response.headers["Content-Security-Policy"] = (
            "frame-ancestors 'self' https://*.google.com https://*.googleusercontent.com; "
            "default-src 'self' blob: data: https://*.google.com https://*.googleusercontent.com; "
            "script-src 'self' blob: data: https://*.google.com https://*.gstatic.com https://*.googleapis.com https://*.googleusercontent.com https://cdnjs.cloudflare.com; "
            # 'unsafe-inline' permits agent-driven dynamic styling of A2UI components
            # (style attributes / element.style). Style injection only — script-src stays strict.
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://*.google.com; "
            "connect-src 'self' https://*.google.com https://*.googleapis.com https://*.google-analytics.com wss://* ws://*; "
            "img-src * data: blob:; "
            "font-src 'self' data: https://fonts.gstatic.com https://*.google.com; "
            "frame-src https://www.youtube.com https://www.youtube-nocookie.com;"
        )
        return response

app.add_middleware(MeetFramingMiddleware)

import secrets
import time
from collections import defaultdict

# Ticket system for Stage WS to avoid raw tokens in URL params
# {ticket_id: (token, expiry)}
auth_tickets: dict[str, tuple[str, datetime]] = {}

# Simple in-memory rate limiter for /api/image (per token, max 5/min)
_image_rate: dict[str, list[float]] = defaultdict(list)
_IMAGE_RATE_LIMIT = 5

def _check_image_rate(token: str):
    now = time.time()
    window = [t for t in _image_rate[token] if now - t < 60]
    if len(window) >= _IMAGE_RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded — max 5 image requests per minute")
    window.append(now)
    _image_rate[token] = window

async def get_token_from_header(request: Request) -> str:
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    return auth[7:]

async def token_required(token: str = Depends(get_token_from_header)):
    if not await validate_google_token(token):
        raise HTTPException(status_code=403, detail="Invalid or expired Google token")
    return token

async def token_or_api_key_required(token: str = Depends(get_token_from_header)):
    stage_api_key = os.environ.get("STAGE_API_KEY", "")
    if stage_api_key and token == stage_api_key:
        return token
    if not await validate_google_token(token):
        raise HTTPException(status_code=403, detail="Invalid or expired Google token")
    return token

async def broadcast_to_stage(meeting_id: str, message: dict, exclude_ws: WebSocket = None):
    if not meeting_id: return
    
    # We can detect the key/type based on either the outer key or the "type" field
    msg_type = message.get("type") if isinstance(message, dict) else None
    if not msg_type and isinstance(message, dict) and message:
        # If there is no "type" field, the discriminator is the first key (v0.9 layout)
        msg_type = next(iter(message))

    if msg_type == "view_change":
        current_view[meeting_id] = message
    elif msg_type == "updateComponents":
        current_a2ui_surface[meeting_id] = message
    elif msg_type == "updateDataModel":
        current_a2ui_datamodel[meeting_id] = message
    elif msg_type == "createSurface":
        current_a2ui_root[meeting_id] = message
    elif msg_type == "deleteSurface":
        current_a2ui_surface.pop(meeting_id, None)
        current_a2ui_datamodel.pop(meeting_id, None)
        current_a2ui_root.pop(meeting_id, None)

    if meeting_id not in stage_listeners:
        logger.info(f"[stage_ws] No listeners for {meeting_id}")
        return
    payload = json.dumps(message)
    logger.info(f"[stage_ws] Broadcasting {msg_type} to {len(stage_listeners[meeting_id])} listeners")
    for ws in list(stage_listeners[meeting_id]):
        if ws == exclude_ws:
            continue
        try: await ws.send_text(payload)
        except Exception: pass

    if msg_type == "transcript" or (isinstance(message, dict) and message.get("type") == "transcript"):
        for emoji in detect_emojis(message.get("text", "") if isinstance(message, dict) else ""):
            await asyncio.sleep(0.4)
            emoji_payload = json.dumps({"type": "emoji_reaction", "emoji": emoji})
            for ws in list(stage_listeners.get(meeting_id, [])):
                try: await ws.send_text(emoji_payload)
                except Exception: pass

async def call_workspace_agent(query: str, user_id: str = "", user_token: str = "") -> str:
    if not user_id: return "Workspace agent: no user identity available."
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
                headers={"Metadata-Flavor": "Google"},
            )
            sa_token = resp.json()["access_token"]

        base_url = f"https://{REGION}-aiplatform.googleapis.com/v1/{WORKSPACE_AGENT_ENGINE}"
        headers = {"Authorization": f"Bearer {sa_token}", "Content-Type": "application/json"}

        # Create a per-call session injecting the user's OAuth token so all 85 workspace
        # tools act as the calling user rather than the service account.
        session_id = None
        if user_token:
            async with httpx.AsyncClient(timeout=10.0) as client:
                sess_resp = await client.post(
                    f"{base_url}/sessions",
                    json={"user_id": user_id, "session_state": {"temp:evergreen-drive-auth": user_token}},
                    headers=headers,
                )
                if sess_resp.status_code == 200:
                    resp_json = sess_resp.json()
                    # Session create returns an LRO; real session name is in response.name
                    raw_name = resp_json.get("response", {}).get("name") or resp_json.get("name", "")
                    # Strip /operations/... suffix if present
                    if "/operations/" in raw_name:
                        raw_name = raw_name[:raw_name.index("/operations/")]
                    session_id = raw_name.split("/")[-1] if raw_name else None
                    logger.info(f"[workspace] session created: {session_id}")
                else:
                    logger.warning(f"[workspace] session create failed {sess_resp.status_code}: {sess_resp.text[:200]}")

        body = {"input": {"message": query, "user_id": user_id}}
        if session_id:
            body["input"]["session_id"] = session_id

        texts = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{base_url}:streamQuery", json=body, headers=headers)
            if resp.status_code != 200:
                logger.error(f"[workspace] streamQuery failed {resp.status_code}: {resp.text[:500]}")
                return f"Workspace agent error: {resp.status_code}"
                
            for line in resp.text.splitlines():
                if not line.strip(): continue
                try:
                    chunk = json.loads(line)
                    if "output" in chunk: texts.append(str(chunk["output"]))
                    elif "content" in chunk:
                        for p in chunk["content"].get("parts", []): texts.append(p.get("text", ""))
                except: pass
        return "\n".join(texts) if texts else "No response from workspace agent."
    except Exception as e: return f"Workspace agent error: {e}"

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
                    description="Create a real Google Doc, Spreadsheet, or Slide in the user's Google Drive, or find existing files and emails. Use this when the user wants a permanent document created.",
                    parameters={
                        "type": "OBJECT",
                        "properties": {"query": {"type": "string", "description": "The specific command to execute (e.g. 'Create a Google Doc called Summary with this content...')"}},
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
                            "status_text": {"type": "string", "description": "A short status message to display to the user in the side panel."},
                            "doc_data": {
                                "type": "OBJECT",
                                "description": "If the user asks to read or display a specific document, provide the title and its raw markdown content here.",
                                "properties": {
                                    "title": {"type": "string"},
                                    "content": {"type": "string", "description": "The raw Markdown content of the document."}
                                },
                                "required": ["title", "content"]
                            },
                            "theme_preset": {"type": "string", "enum": ["default", "matrix", "blueprint", "corporate", "neon", "minimal"]},
                            "theme_tokens": {"type": "OBJECT", "description": "Raw CSS token overrides — use for custom colors not covered by presets"},
                            "layout": {"type": "string", "enum": ["default", "focus", "minimal", "presentation", "split"]},
                            "component_visibility": {
                                "type": "OBJECT",
                                "description": "Show/hide named components",
                                "properties": {
                                    "transcript": {"type": "boolean"},
                                    "action_links": {"type": "boolean"},
                                    "controls": {"type": "boolean"},
                                    "diagram_refiner": {"type": "boolean"},
                                }
                            },
                            "banner": {"type": "string", "description": "Temporary full-width announcement text, auto-clears after 8s"},
                            "stage_theme": {"type": "boolean", "description": "Apply same theme to main stage simultaneously"}
                        }
                    }
                ),
                types.FunctionDeclaration(name="fetch_url", description="Get content of a URL.", parameters={
                    "type": "OBJECT", "properties": {"url": {"type": "string"}}, "required": ["url"]
                }),
                types.FunctionDeclaration(
                    name="generate_image",
                    description="Generate an AI image from a description and display it on the Meet main stage.",
                    parameters={
                        "type": "OBJECT",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "A detailed description of the image to generate (e.g. 'A futuristic server room with glowing blue lights')"
                            },
                            "model": {
                                "type": "string",
                                "description": (
                                    "The specific Imagen model to use. "
                                    "Options: "
                                    "- 'imagen-4.0-fast-generate-001' (ultra-fast ~1.5s draft mode, use for rapid interactive conversation) "
                                    "- 'imagen-3.0-generate-002' (premium ~4.5s high-fidelity mode, use for polished final presentation slides). "
                                    "Defaults to the server-configured premium model if omitted."
                                ),
                                "enum": ["imagen-4.0-fast-generate-001", "imagen-3.0-generate-002"]
                            }
                        },
                        "required": ["prompt"]
                    }
                ),
                types.FunctionDeclaration(
                    name="render_stage",
                    description=(
                        "Render interactive A2UI component panels on the Meet main stage. "
                        "Use this to display grids, radar, telemetry, image panels, notepads, etc. "
                        "Always include a gdm-stage-grid as root with children referencing panel component IDs."
                    ),
                    parameters={
                        "type": "OBJECT",
                        "properties": {
                            "surfaceUpdate": {
                                "type": "OBJECT",
                                "description": "A2UI surfaceUpdate payload. Must contain a 'components' array where each entry has 'id' and 'component' fields."
                            },
                            "root": {
                                "type": "string",
                                "description": "ID of the root layout component (gdm-stage-grid). Defaults to the first component in the array if omitted."
                            },
                            "dataModelUpdate": {
                                "type": "OBJECT",
                                "description": "Optional A2UI dataModelUpdate for data binding."
                            }
                        },
                        "required": ["surfaceUpdate"]
                    }
                ),
                types.FunctionDeclaration(
                    name="clear_stage",
                    description="Clear all A2UI panels from the Meet main stage and return to the default view.",
                    parameters={"type": "OBJECT", "properties": {}}
                ),
            ]),
            types.Tool(google_search=types.GoogleSearch()),
        ],
    )

    # --- A2UI STATE MANAGER ---
    ui_state = {
        "status_state": "connecting",
        "status_text": "Connecting to Gemini Live...",
        "authenticated": True,
        "audioEnabled": True,
        "videoEnabled": False,
        "diagramMode": False,
        "transcriptMode": False,
        "actionLinks": [],
        "transcript": [],
        "theme": THEME_PRESETS["default"],
        "layout": "default",
        "visibility": {
            "transcript": True,
            "action_links": True,
            "controls": True,
            "diagram_refiner": True
        },
        "extra_components": []
    }

    async def broadcast_a2ui():
        """Generates the A2UI payload and sends it to the frontend."""
        vis = ui_state.get("visibility", {})
        components = []
        
        # 1. Status View (Always visible)
        components.append({
            "id": "hero_status",
            "element": "gdm-status-view",
            "props": {
                "state": ui_state["status_state"],
                "status": ui_state["status_text"],
                "authenticated": ui_state["authenticated"]
            }
        })
        
        # 2. Control Bar
        if vis.get("controls", True):
            components.append({
                "id": "control_bar",
                "element": "gdm-controls-view",
                "props": {
                    "audioEnabled": ui_state["audioEnabled"],
                    "videoEnabled": ui_state["videoEnabled"],
                    "diagramMode": ui_state["diagramMode"],
                    "transcriptMode": ui_state["transcriptMode"]
                }
            })
        
        # 3. Workspace Links
        if vis.get("action_links", True) and ui_state["actionLinks"]:
            components.append({
                "id": "workspace_links",
                "element": "gdm-actions-view",
                "props": {
                    "actions": ui_state["actionLinks"]
                }
            })
        
        # 4. Diagram Refiner
        if ui_state["diagramMode"] and vis.get("diagram_refiner", True):
            components.append({
                "id": "diagram_refiner",
                "element": "gdm-diagram-refiner",
                "props": {} 
            })

        # 5. Transcript View
        if vis.get("transcript", True):
            components.append({
                "id": "transcript_view",
                "element": "gdm-transcript-view",
                "props": {}
            })

        # Append server-injected extra components
        components.extend(ui_state.get("extra_components", []))

        payload = {
            "type": "A2UI_STATE",
            "components": components,
            "theme": ui_state["theme"],
            "layout": ui_state["layout"]
        }
        try:
            await websocket.send_text(json.dumps(payload))
        except Exception as e:
            logger.error(f"[a2ui] Broadcast error: {e}")

    # Inject queue: external audio (e.g. from /api/audio-inject) feeds here
    inject_queue: asyncio.Queue = asyncio.Queue()

    # Register session globally
    active_sessions[meeting_id] = {
        "ui_state": ui_state,
        "broadcast_fn": broadcast_a2ui,
        "audio_inject": inject_queue,
        "audio_muted": False,
    }

    # Initial broadcast
    await broadcast_a2ui()

    async with gemini_client.aio.live.connect(model=MODEL, config=config) as session:
        # Update state on successful connection
        ui_state["status_state"] = "listening"
        ui_state["status_text"] = "Assistant connected — listening"
        await broadcast_a2ui()
        active_sessions[meeting_id]["send_client_content_fn"] = session.send_client_content

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
                        if not active_sessions.get(session_space[0], {}).get("audio_muted"):
                            await session.send_realtime_input(audio=types.Blob(data=raw, mime_type="audio/pcm;rate=16000"))
                    elif text:
                        data = json.loads(text)
                        if data.get("type") == "init":
                            email = data.get("user_email", "")
                            token = data.get("access_token", "")
                            workspace_user[0] = email
                            session_token[0] = token
                            if data.get("meeting_id"): session_space[0] = data.get("meeting_id")
                            
                            # Update global session data with identity for API access
                            if session_space[0] in active_sessions:
                                active_sessions[session_space[0]]["user_email"] = email
                                active_sessions[session_space[0]]["access_token"] = token
                            
                            logger.info(f"[ws] init user={workspace_user[0]} space={session_space[0]}")
                            
                            # Initial Welcome Card for Main Stage if empty
                            if session_space[0] not in current_a2ui_surface:
                                welcome_components = make_composable_standby_components(
                                    badge="GETTING STARTED",
                                    title="🚀 Google Meet Studio",
                                    description="Welcome! The Gemini Agent Architect is ready to build with you. Click the \"Connect\" button in your side panel to start the AI collaboration.",
                                    remaining_seconds=0
                                )
                                await broadcast_to_stage(session_space[0], {
                                    "updateComponents": {
                                        "components": welcome_components
                                    }
                                })
                                await broadcast_to_stage(session_space[0], {
                                    "createSurface": {"catalogId": "gdm-v0.1", "theme": {}, "root": "stage_root_grid"}
                                })
                        
                        elif data.get("type") == "diagram_mode":
                            # Sync frontend button clicks back into backend state
                            ui_state["diagramMode"] = bool(data.get("active", False))
                            if ui_state["diagramMode"]:
                                ui_state["status_text"] = "Gemini Agent Architect — speak your architecture description"
                            else:
                                ui_state["status_text"] = "Assistant connected — listening"
                            await broadcast_a2ui()

                        elif data.get("type") == "toggle_audio":
                            ui_state["audioEnabled"] = not ui_state["audioEnabled"]
                            await broadcast_a2ui()

                        elif data.get("type") == "toggle_video":
                            ui_state["videoEnabled"] = not ui_state["videoEnabled"]
                            await broadcast_a2ui()
                            
                        elif data.get("type") in ("view_change", "sound_event", "layout_event", "focus_panel", "emoji_event", "studio_mode_event", "stage_camera_frame", "surfaceUpdate", "dataModelUpdate", "beginRendering", "deleteSurface"):
                            await broadcast_to_stage(session_space[0], data)
            except Exception:
                stop_event.set()

        recv_task = asyncio.create_task(browser_to_gemini())

        async def audio_injector():
            while not stop_event.is_set():
                try:
                    chunk = await asyncio.wait_for(inject_queue.get(), timeout=0.2)
                    await session.send_realtime_input(
                        audio=types.Blob(data=chunk, mime_type="audio/pcm;rate=16000")
                    )
                except asyncio.TimeoutError:
                    pass
                except Exception as e:
                    logger.error(f"[inject] send error: {e}")

        inject_task = asyncio.create_task(audio_injector())

        CHAT_POLL_INTERVAL = 8

        async def chat_poller():
            last_seen: set[str] = set()
            await asyncio.sleep(15)
            while not stop_event.is_set():
                try:
                    token = session_token[0]
                    space = session_space[0]
                    if token and space and not active_sessions.get(meeting_id, {}).get("audio_muted"):
                        raw = await fetch_meeting_chat(space, token)
                        if raw:
                            new_lines = [l for l in raw.splitlines() if l and l not in last_seen]
                            if new_lines:
                                for l in new_lines:
                                    last_seen.add(l)
                                if len(last_seen) > 200:
                                    last_seen = set(list(last_seen)[-200:])
                                batch = "\n".join(new_lines)
                                text = (
                                    f"[Meeting Chat — new messages]\n{batch}\n"
                                    "[End of chat. Respond to relevant questions at your discretion.]"
                                )
                                await session.send_client_content(
                                    turns=types.Content(role="user", parts=[types.Part(text=text)]),
                                    turn_complete=True,
                                )
                                logger.info(f"[chat_poll] injected {len(new_lines)} message(s) for {space}")
                except Exception as e:
                    logger.error(f"[chat_poll] error: {e}")
                await asyncio.sleep(CHAT_POLL_INTERVAL)

        chat_poll_task = asyncio.create_task(chat_poller())

        try:
            while not stop_event.is_set():
                async for response in session.receive():
                    if stop_event.is_set(): break

                    if response.tool_call:
                        responses = []
                        for fc in response.tool_call.function_calls:
                            # Use ui_state instead of diagram_mode[0] array
                            if ui_state["diagramMode"] and fc.name != "update_interface":
                                responses.append(types.FunctionResponse(
                                    id=fc.id, 
                                    name=fc.name, 
                                    response={"result": "Tool disabled while Architect Mode is active. Switch main_stage_view or disable diagram_mode first."}
                                ))
                                continue
                            
                            elif fc.name == "workspace_agent":
                                logger.info(f"[tool] workspace: {fc.args}")
                                ui_state["status_text"] = "Workspace agent: working..."
                                await broadcast_a2ui()
                                
                                res = await call_workspace_agent(fc.args.get("query", ""), user_id=workspace_user[0], user_token=session_token[0])
                                ui_state["status_text"] = "Assistant connected — listening"
                                await broadcast_a2ui()
                                
                                responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": res}))
                                
                                for url in re.findall(r'https?://(?:docs|drive|sheets|slides)\.google\.com/[^\s)]+', res):
                                    clean_url = url.rstrip('.,)')
                                    label = "Open Spreadsheet" if "spreadsheets" in clean_url else "Open Document"
                                    ui_state["actionLinks"].append({"url": clean_url, "label": label, "content": res})
                                    await broadcast_a2ui()
                                    await broadcast_to_stage(session_space[0], {
                                        "type": "view_change",
                                        "mode": "doc",
                                        "url": clean_url,
                                        "label": label,
                                        "content": res
                                    })
                                    if session_token[0] and session_space[0]:
                                        asyncio.create_task(save_doc_shortcut_to_drive(clean_url, label, session_space[0], session_token[0]))

                                # Surface auth link if workspace agent needs authorization
                                for url in re.findall(r'https?://workspace-subagent-auth[^\s)]+', res):
                                    clean_url = url.rstrip('.,)')
                                    ui_state["actionLinks"].append({"url": clean_url, "label": "Authorize Workspace Access", "content": res})
                                    await broadcast_a2ui()
                            
                            elif fc.name == "present_on_main_stage":
                                url = fc.args.get("url", "")
                                label = fc.args.get("label", "Document")
                                content = fc.args.get("content", "")
                                
                                # A2UI STATE UPDATE
                                ui_state["actionLinks"].append({"url": url, "label": label, "content": content})
                                await broadcast_a2ui()
                                
                                await broadcast_to_stage(session_space[0], {
                                    "type": "view_change",
                                    "mode": "doc",
                                    "url": url,
                                    "label": label,
                                    "content": content
                                })
                                responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": "Presented."}))
                            
                            elif fc.name == "update_interface":
                                # 1. Update Backend UI State
                                if "diagram_mode" in fc.args:
                                    ui_state["diagramMode"] = fc.args["diagram_mode"]
                                if "status_text" in fc.args:
                                    ui_state["status_text"] = fc.args["status_text"]
                                
                                # Theme logic
                                current_theme = ui_state.get("theme", THEME_PRESETS["default"]).copy()
                                if "theme_preset" in fc.args:
                                    preset = fc.args["theme_preset"]
                                    if preset in THEME_PRESETS:
                                        current_theme.update(THEME_PRESETS[preset])
                                if "theme_tokens" in fc.args:
                                    current_theme.update(fc.args["theme_tokens"])
                                ui_state["theme"] = current_theme

                                if "layout" in fc.args:
                                    ui_state["layout"] = fc.args["layout"]
                                    await broadcast_to_stage(session_space[0], {
                                        "type": "layout_event",
                                        "layout": fc.args["layout"]
                                    })
                                if "component_visibility" in fc.args:
                                    cv = fc.args["component_visibility"]
                                    ui_state.setdefault("visibility", {}).update(cv)
                                
                                if "doc_data" in fc.args:
                                    raw_md = fc.args["doc_data"]["content"]
                                    # Convert Markdown to HTML on the server
                                    raw_html = markdown.markdown(raw_md, extensions=['extra'])
                                    html_content = sanitize_html(raw_html)
                                    
                                    ui_state.setdefault("extra_components", [])
                                    if len(ui_state["extra_components"]) >= 5:
                                        ui_state["extra_components"].pop(0)
                                        
                                    ui_state["extra_components"].append({
                                        "id": f"doc_{uuid_lib.uuid4().hex[:6]}",
                                        "element": "gdm-doc-view",
                                        "props": {
                                            "title": fc.args["doc_data"]["title"],
                                            "htmlContent": html_content
                                        }
                                    })
                                
                                # 2. Broadcast Side Panel State
                                await broadcast_a2ui()
                                
                                # 3. Broadcast Main Stage State
                                stage_view = fc.args.get("main_stage_view")
                                if stage_view:
                                    msg = {"type": "view_change", "mode": stage_view}
                                    if stage_view == "doc" and "doc_data" in fc.args:
                                        msg["label"] = fc.args["doc_data"]["title"]
                                        raw_html = markdown.markdown(fc.args["doc_data"]["content"], extensions=['extra'])
                                        msg["htmlContent"] = sanitize_html(raw_html)
                                    await broadcast_to_stage(session_space[0], msg)
                                
                                if fc.args.get("stage_theme"):
                                    await broadcast_to_stage(session_space[0], {
                                        "type": "theme_change",
                                        "tokens": current_theme
                                    })
                                    
                                responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": "UI updated successfully."}))
                            
                            elif fc.name == "fetch_url":
                                responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": await fetch_url(fc.args.get("url", ""))}))

                            elif fc.name == "generate_image":
                                prompt = fc.args.get("prompt", "")
                                chosen_model = fc.args.get("model", None)
                                logger.info(f"[tool] generate_image: {prompt[:60]} (model={chosen_model})")
                                ui_state["status_text"] = "Generating image…"
                                await broadcast_a2ui()

                                async def _gen_broadcast(p=prompt, m=chosen_model, space=session_space[0]):
                                    try:
                                        img_bytes = await generate_image(p, model=m)
                                        if img_bytes:
                                            await broadcast_to_stage(space, {
                                                "type": "view_change",
                                                "mode": "image",
                                                "imageData": base64.b64encode(img_bytes).decode("utf-8")
                                            })
                                    except Exception as ex:
                                        logger.error(f"[tool] generate_image broadcast failed: {ex}")
                                    finally:
                                        ui_state["status_text"] = "Assistant connected — listening"
                                        await broadcast_a2ui()

                                asyncio.create_task(_gen_broadcast())
                                responses.append(types.FunctionResponse(
                                    id=fc.id, name=fc.name,
                                    response={"result": "Image generation started — will appear on stage when ready."}
                                ))

                            elif fc.name == "render_stage":
                                surface_update = fc.args.get("surfaceUpdate", {})
                                root_id = (fc.args.get("root") or "").strip()
                                data_model_update = fc.args.get("dataModelUpdate")
                                if not root_id:
                                    comps = surface_update.get("components", [])
                                    if comps:
                                        root_id = comps[0].get("id", "")
                                errors, warnings = validate_a2ui_surface_detailed(surface_update)
                                if errors:
                                    responses.append(types.FunctionResponse(
                                        id=fc.id, name=fc.name,
                                        response={"result": f"Validation failed: {', '.join(errors)}"}
                                    ))
                                else:
                                    await broadcast_to_stage(session_space[0], {"updateComponents": {"components": surface_update.get("components", [])}})
                                    if data_model_update:
                                        await broadcast_to_stage(session_space[0], {"updateDataModel": data_model_update})
                                    if root_id:
                                        await broadcast_to_stage(session_space[0], {"createSurface": {"catalogId": "gdm-v0.1", "theme": {}, "root": root_id}})
                                    if warnings:
                                        logger.warning(f"[tool] render_stage surface warnings: {'; '.join(warnings)}")
                                    logger.info(f"[tool] render_stage root={root_id} n={len(surface_update.get('components', []))}")
                                    result_msg = f"Stage rendered with root '{root_id}'."
                                    if warnings:
                                        result_msg += " Advisory (rendered anyway): " + "; ".join(warnings)
                                    responses.append(types.FunctionResponse(
                                        id=fc.id, name=fc.name,
                                        response={"result": result_msg}
                                    ))

                            elif fc.name == "clear_stage":
                                await broadcast_to_stage(session_space[0], {"deleteSurface": {}})
                                logger.info(f"[tool] clear_stage for {session_space[0]}")
                                responses.append(types.FunctionResponse(
                                    id=fc.id, name=fc.name,
                                    response={"result": "Stage cleared."}
                                ))

                            else:
                                responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": "ok"}))
                        if responses: await session.send_tool_response(function_responses=responses)
                        continue

                    sc = response.server_content
                    if not sc: continue

                    # Transcript logic remains unchanged
                    input_trans = getattr(sc, "input_transcription", None)
                    if input_trans:
                        t_text = getattr(input_trans, "text", "")
                        is_final = getattr(input_trans, "final", False)
                        if t_text:
                            if current_turn["role"] != "user":
                                current_turn.update({"id": str(uuid_lib.uuid4()), "role": "user"})
                            transcript_msg = {"type": "transcript", "role": "user", "label": "You", "text": t_text, "turn_id": current_turn["id"], "is_final": is_final}
                            await websocket.send_text(json.dumps(transcript_msg))
                            caption_surface = {"updateComponents": {"components": [{"id": "stage_captions", "component": "gdm-captions", "text": t_text, "speaker": "You", "active": True}]}}
                            await broadcast_to_stage(session_space[0], caption_surface)
                            await broadcast_to_stage(session_space[0], {"createSurface": {"catalogId": "gdm-v0.1", "theme": {}, "root": "stage_captions"}})
                            if is_final: current_turn["role"] = None

                    if sc.model_turn:
                        for part in sc.model_turn.parts:
                            if part.inline_data:
                                if not active_sessions.get(meeting_id, {}).get("audio_muted"):
                                    await websocket.send_bytes(part.inline_data.data)
                            if part.text:
                                if not active_sessions.get(meeting_id, {}).get("audio_muted"):
                                    if current_turn["role"] != "agent":
                                        current_turn.update({"id": str(uuid_lib.uuid4()), "role": "agent"})
                                    transcript_msg = {"type": "transcript", "role": "agent", "label": "Gemini Architect", "text": part.text, "turn_id": current_turn["id"], "is_final": False}
                                    await websocket.send_text(json.dumps(transcript_msg))
                                    caption_surface = {"updateComponents": {"components": [{"id": "stage_captions", "component": "gdm-captions", "text": part.text, "speaker": "Gemini Architect", "active": True}]}}
                                    await broadcast_to_stage(session_space[0], caption_surface)
                                    await broadcast_to_stage(session_space[0], {"createSurface": {"catalogId": "gdm-v0.1", "theme": {}, "root": "stage_captions"}})
                    
                    if sc.turn_complete: current_turn["role"] = None
        except Exception as e:
            logger.error(f"[ws] error: {e}")
            logger.debug(traceback.format_exc())
        finally:
            active_sessions.pop(meeting_id, None)
            stop_event.set()
            recv_task.cancel()
            inject_task.cancel()
            chat_poll_task.cancel()

@app.get("/api/auth/ticket")
async def create_auth_ticket(request: Request, token: str = Depends(token_required)):
    """Create a short-lived ticket to authenticate a secondary client (like the stage) without passing the raw token in the URL."""
    ticket = secrets.token_urlsafe(32)
    expiry = datetime.now(timezone.utc) + timedelta(minutes=5)
    auth_tickets[ticket] = (token, expiry)
    return {"ticket": ticket}


@app.get("/api/stage-ticket/{space_id:path}")
async def create_stage_ticket(space_id: str, request: Request):
    """
    Issue a stage WebSocket ticket authenticated by STAGE_API_KEY.
    Used by headless recording clients that don't have a Google OAuth token.
    Returns the full stage URL ready to open in a browser.
    """
    check_producer_auth(request)
    logger.info(f"[stage-ticket] issued for {space_id} from {request.client.host}")
    ticket = secrets.token_urlsafe(32)
    # 30-minute expiry — long enough for a full demo recording
    expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
    auth_tickets[ticket] = ("mcp-recording-client", expiry)
    stage_url = f"{request.base_url}main_stage.html?meeting={space_id}&ticket={ticket}"
    return {"ticket": ticket, "stage_url": stage_url}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, meeting_id: str = "", ticket: str = ""):
    # We use a backend-issued Ticket to authenticate the WebSocket handshake
    ticket_data = auth_tickets.pop(ticket, None)
    if not ticket_data or ticket_data[1] < datetime.now(timezone.utc):
        logger.warning(f"[ws] handshake rejected: invalid or expired ticket for meeting {meeting_id}")
        await websocket.close(code=1008)
        return
    await websocket.accept()
    try: await live_session(websocket, meeting_id)
    except WebSocketDisconnect: pass

A2UI_ACTION_CONTEXT: dict[str, dict] = {
    "target-lock": {
        "context_fn": lambda d: f"[Stage] A viewer locked focus on flight {d.get('callsign', '?')} on the radar display.",
        "dm_path": "radar/lockedCallsign",
        "dm_val_fn": lambda d: d.get("callsign", ""),
    },
    "zoom-change": {
        "context_fn": lambda d: f"[Stage] A viewer adjusted the radar zoom by {d.get('delta', 0):+} nm.",
        "dm_path": None,
        "dm_val_fn": None,
    },
    "poll-vote": {
        "context_fn": lambda d: f"[Stage] A viewer cast a poll vote for option index {d.get('optionIndex', 0)}.",
        "dm_path": "poll/lastVote",
        "dm_val_fn": lambda d: str(d.get("optionIndex", "")),
    },
    "tab-select": {
        "context_fn": lambda d: f"[Stage] A viewer selected the '{d.get('tabId', '?')}' tab on the telemetry dashboard.",
        "dm_path": None,
        "dm_val_fn": None,
    },
}

async def handle_tab_select_action(meeting_id: str, tab_id: str):
    logger.info(f"[interactive_tabs] Switching tab to '{tab_id}' for meeting {meeting_id}")
    
    stocks_metrics = [
        {"label": "NVDA (+2.50%)", "value": "$914.85 ▲", "color": "#00ff88"},
        {"label": "MSFT (-0.80%)", "value": "$421.90 ▼", "color": "#ff3b30"},
        {"label": "GOOG (+1.20%)", "value": "$173.50 ▲", "color": "#ff2af2"},
        {"label": "AAPL (+0.45%)", "value": "$189.30 ▲", "color": "#00f2ff"},
        {"label": "AMZN (+1.10%)", "value": "$180.20 ▲", "color": "#00ffaa"},
        {"label": "TSLA (-1.85%)", "value": "$175.40 ▼", "color": "#ff3b30"}
    ]

    bikes_metrics = [
        {"label": "JULES-GUESDE (60%)", "value": "12/20 Bikes ▲", "color": "#00ffaa"},
        {"label": "CAPITOLE (72%)", "value": "18/25 Bikes ▲", "color": "#00f2ff"},
        {"label": "JEAN-JAURÈS (16%)", "value": "3/18 Bikes ▼", "color": "#ffaa00"},
        {"label": "MARENGO (0%)", "value": "0/15 Empty ▼", "color": "#ff3b30"},
        {"label": "🚲 DAILY TRIPS", "value": "15.2k", "color": "#ff2af2"}
    ]

    metro_metrics = [
        {"label": "🚄 LINE A (HEADWAY)", "value": "1m15s NOMINAL ▲", "color": "#00ffaa"},
        {"label": "🚄 LINE B (HEADWAY)", "value": "1m30s NOMINAL ▲", "color": "#00f2ff"},
        {"label": "🚌 BUS CO2 SAVED", "value": "12.4 Tons ▲", "color": "#00ffaa"},
        {"label": "⚡ TRACTION POWER", "value": "4.8 MW ▼", "color": "#ffaa00"},
        {"label": "🟢 NETWORK STATUS", "value": "100% OPERATIVE", "color": "#00ffaa"}
    ]
    
    charts = {
        "stk": [40, 42, 41, 44, 43, 46, 45, 48, 47, 49, 50, 49, 51, 52, 53],
        "pwr": [60, 58, 62, 65, 70, 72, 68, 65, 58, 55, 52, 55, 60, 62, 64],
        "ac": [30, 32, 35, 38, 42, 45, 42, 40, 38, 35, 36, 38, 40, 41, 43]
    }
    
    surface = current_a2ui_surface.get(meeting_id)
    if not surface:
        logger.warning(f"[interactive_tabs] No surface cached for meeting {meeting_id}")
        return
        
    components = surface.get("updateComponents", {}).get("components", [])
    updated = False
    
    for comp in components:
        if comp.get("id") == "telemetry_dashboard":
            if comp.get("component") == "gdm-telemetry-dashboard":
                comp["activeTabId"] = tab_id
                if tab_id == "stk":
                    comp["metrics"] = stocks_metrics
                    comp["chartData"] = charts["stk"]
                elif tab_id == "pwr":
                    comp["metrics"] = bikes_metrics
                    comp["chartData"] = charts["pwr"]
                elif tab_id == "ac":
                    comp["metrics"] = metro_metrics
                    comp["chartData"] = charts["ac"]
                updated = True
                break
                
    if updated:
        logger.info(f"[interactive_tabs] Broadcasting updated surface to meeting {meeting_id}")
        await broadcast_to_stage(meeting_id, surface)
        # The A2UI engine only repaints on `beginRendering`; a bare surfaceUpdate
        # just buffers components. Re-emit the cached root so the swapped
        # metrics/chartData actually render on the stage.
        root_msg = current_a2ui_root.get(meeting_id)
        if root_msg:
            await broadcast_to_stage(meeting_id, root_msg)
        else:
            logger.warning(f"[interactive_tabs] No cached root for {meeting_id}; tab swap may not repaint")

@app.websocket("/ws/stage")
async def ws_stage_endpoint(websocket: WebSocket, meeting_id: str = "", ticket: str = ""):
    is_local = websocket.client and websocket.client.host in ("127.0.0.1", "localhost")
    ticket_data = auth_tickets.get(ticket)
    if not is_local and (not ticket_data or ticket_data[1] < datetime.now(timezone.utc)):
        logger.warning(f"[ws/stage] rejected: invalid or expired ticket")
        await websocket.close(code=1008)
        return
    
    await websocket.accept()
    if not meeting_id: await websocket.close(); return
    if meeting_id not in stage_listeners: stage_listeners[meeting_id] = set()
    stage_listeners[meeting_id].add(websocket)
    logger.info(f"[stage_ws] NEW listener for {meeting_id}. Total: {len(stage_listeners[meeting_id])}")
    
    # Replay cached legacy view state
    if meeting_id in current_view:
        await websocket.send_text(json.dumps(current_view[meeting_id]))

    # Replay cached A2UI layout protocol sequence
    if meeting_id in current_a2ui_surface:
        await websocket.send_text(json.dumps(current_a2ui_surface[meeting_id]))
    if meeting_id in current_a2ui_datamodel:
        await websocket.send_text(json.dumps(current_a2ui_datamodel[meeting_id]))
    if meeting_id in current_a2ui_root:
        await websocket.send_text(json.dumps(current_a2ui_root[meeting_id]))
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            if msg.get("type") == "video_ended":
                queue = video_queues.get(meeting_id, [])
                if queue:
                    next_item = queue.pop(0)
                    logger.info(f"[queue] video_ended — advancing to next ({len(queue)} remaining) for {meeting_id}")
                    await broadcast_to_stage(meeting_id, {
                        "type": "view_change", "mode": "video",
                        "url": next_item["url"], "label": next_item.get("label", "")
                    })
                else:
                    logger.info(f"[queue] video_ended — queue empty, returning to placeholder for {meeting_id}")
                    await broadcast_to_stage(meeting_id, {"type": "view_change", "mode": "placeholder"})
            elif msg.get("type") == "notepad_update":
                # Implement single-writer lock per meeting space to prevent clobbering
                import time
                now = time.time()
                lock = notepad_locks.get(meeting_id)
                owner_id = id(websocket)
                
                if lock and lock["expires_at"] > now and lock["owner"] != owner_id:
                    # Notepad is currently locked by another active typer
                    try:
                        await websocket.send_text(json.dumps({
                            "type": "notepad_locked",
                            "error": "Notepad is currently being edited by another user."
                        }))
                    except Exception:
                        pass
                else:
                    # Acquire or refresh the lock for 5 seconds
                    notepad_locks[meeting_id] = {"owner": owner_id, "expires_at": now + 5.0}
                    # Broadcast the live text updates to all OTHER connected clients
                    await broadcast_to_stage(meeting_id, {
                        "type": "notepad_event",
                        "action": "overwrite",
                        "text": msg.get("text", "")
                    }, exclude_ws=websocket)
            elif msg.get("type") == "stage_camera_frame":
                # Forward camera frames to all other connected stage clients
                await broadcast_to_stage(meeting_id, msg, exclude_ws=websocket)
            elif msg.get("type") == "a2ui_error":
                logger.error(f"[a2ui_error] Frontend A2UI Error in meeting {meeting_id}:\n  Context: {msg.get('context')}\n  Error: {msg.get('error')}\n  Stack: {msg.get('stack')}")
            elif msg.get("type") == "a2ui_action":
                action_name = msg.get("action")
                detail = msg.get("detail", {})
                logger.info(f"[a2ui_action] {action_name} in {meeting_id}: {detail}")
                if action_name == "tab-select":
                    tab_id = detail.get("tabId")
                    if tab_id:
                        await handle_tab_select_action(meeting_id, tab_id)
                action_spec = A2UI_ACTION_CONTEXT.get(action_name)
                if action_spec:
                    send_fn = active_sessions.get(meeting_id, {}).get("send_client_content_fn")
                    if send_fn:
                        context_text = action_spec["context_fn"](detail)
                        try:
                            await send_fn(
                                turns=types.Content(role="user", parts=[types.Part(text=context_text)]),
                                turn_complete=True,
                            )
                            logger.info(f"[a2ui_action] context injected: {context_text}")
                        except Exception as e:
                            logger.error(f"[a2ui_action] send_client_content failed: {e}")
                    if action_spec.get("dm_path") and action_spec.get("dm_val_fn"):
                        dm_val = action_spec["dm_val_fn"](detail)
                        dm_msg = {
                            "updateDataModel": {
                                "path": action_spec["dm_path"],
                                "contents": {action_spec["dm_path"].split("/")[-1]: dm_val}
                            }
                        }
                        await broadcast_to_stage(meeting_id, dm_msg, exclude_ws=websocket)
    except WebSocketDisconnect:
        if meeting_id in stage_listeners:
            stage_listeners[meeting_id].discard(websocket)
            logger.info(f"[stage_ws] REMOVED listener for {meeting_id}")
            if not stage_listeners[meeting_id]: del stage_listeners[meeting_id]

# To compute CPU percentage over intervals
last_cpu_time = [datetime.now().timestamp(), sum(os.times()[:2]) if hasattr(os, "times") else 0.0]

@app.get("/api/telemetry")
async def get_telemetry(request: Request):
    check_producer_auth(request)
    import resource
    import sys
    import time
    global last_cpu_time
    
    now = time.time()
    dt = now - last_cpu_time[0]
    
    # Process CPU time (user + system)
    current_cpu_times = sum(os.times()[:2]) if hasattr(os, "times") else 0.0
    cpu_diff = current_cpu_times - last_cpu_time[1]
    
    cpu_pct = 0.0
    if dt > 0.05:
        cpu_pct = min(100.0, (cpu_diff / dt) * 100.0)
        last_cpu_time = [now, current_cpu_times]
    else:
        try:
            load = os.getloadavg()[0] * 100.0 / (os.cpu_count() or 1)
            cpu_pct = min(100.0, load)
        except Exception:
            cpu_pct = 5.2  # baseline idle cpu percentage
            
    # Max RSS memory (in MB)
    max_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    mem_mb = max_rss / 1024.0
    if sys.platform == 'darwin':
        mem_mb = max_rss / (1024.0 * 1024.0)
        
    active_conns = sum(len(conns) for conns in stage_listeners.values())
    efficiency = 99.9 if active_conns > 0 else 100.0
    
    # Keep cpu_pct dynamically fluctuating naturally if it rounds to 0.0
    if cpu_pct < 0.1:
        import random
        cpu_pct = 1.0 + random.random() * 2.0
        
    return {
        "cpu": round(cpu_pct, 1),
        "memory_mb": round(mem_mb, 1),
        "active_connections": active_conns,
        "efficiency": efficiency,
        "latency_ms": round(dt * 1000.0, 1)
    }

@app.post("/api/ui-prompt")
async def ui_prompt(payload: dict = Body(...), token: str = Depends(token_required)):
    user_prompt = payload.get("prompt", "")
    space_id = payload.get("space_id", "")
    if not user_prompt or not space_id:
        return FastAPIResponse(status_code=400)

    session_data = active_sessions.get(space_id)
    if not session_data:
        return {"ok": False, "error": "No active session for this space"}

    try:
        # One-shot Gemini Flash call
        response = await gemini_client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(role="user", parts=[types.Part(text=f"User: {user_prompt}")])
            ],
            config=types.GenerateContentConfig(
                system_instruction=UI_PROMPT_SYSTEM,
                temperature=0.1
            )
        )
        
        raw_text = response.text or ""
        args = {}
        if "{" in raw_text:
            try:
                args = json.loads(raw_text[raw_text.find("{"):raw_text.rfind("}")+1])
            except: pass
        
        if args:
            ui_state = session_data["ui_state"]

            # Strip unknown fields and validate enums/types before touching ui_state
            args = {k: v for k, v in args.items() if k in _ALLOWED_UI_FIELDS}
            if "layout" in args and args["layout"] not in _ALLOWED_LAYOUTS:
                args.pop("layout")
            if "main_stage_view" in args and args["main_stage_view"] not in _ALLOWED_STAGE_VIEWS:
                args.pop("main_stage_view")
            if "theme_preset" in args and args["theme_preset"] not in THEME_PRESETS:
                args.pop("theme_preset")
            if "theme_tokens" in args:
                # Only allow CSS custom properties (--foo: value) to prevent arbitrary key injection
                args["theme_tokens"] = {
                    k: v for k, v in args["theme_tokens"].items()
                    if isinstance(k, str) and k.startswith("--") and isinstance(v, str)
                }
            if "component_visibility" in args:
                args["component_visibility"] = {
                    k: bool(v) for k, v in args["component_visibility"].items()
                    if k in _ALLOWED_VISIBILITY_KEYS
                }

            # Apply changes (mirroring update_interface logic)
            if "status_text" in args: ui_state["status_text"] = args["status_text"]
            if "diagram_mode" in args: ui_state["diagramMode"] = args["diagram_mode"]
            if "theme_preset" in args:
                ui_state["theme"].update(THEME_PRESETS[args["theme_preset"]])
            if "theme_tokens" in args: ui_state["theme"].update(args["theme_tokens"])
            if "layout" in args:
                ui_state["layout"] = args["layout"]
                await broadcast_to_stage(space_id, {
                    "type": "layout_event",
                    "layout": args["layout"]
                })
            if "component_visibility" in args:
                ui_state.setdefault("visibility", {}).update(args["component_visibility"])
            
            # Workspace Agent (Document Creation) via Text Prompt
            if "workspace_agent" in args:
                query = args["workspace_agent"].get("query")
                if query:
                    logger.info(f"[ui-prompt] workspace request: {query}")
                    ui_state["status_text"] = "Creating document..."
                    await session_data["broadcast_fn"]()
                    
                    # Extract identity from global session data
                    email = session_data.get("user_email", "")
                    token = session_data.get("access_token", "")
                    
                    async def run_workspace_task():
                        try:
                            res = await call_workspace_agent(query, user_id=email, user_token=token)
                            for url in re.findall(r'https?://(?:docs|drive|sheets|slides)\.google\.com/[^\s)]+', res):
                                clean_url = url.rstrip('.,)')
                                label = "Open Spreadsheet" if "spreadsheets" in clean_url else "Open Document"
                                ui_state["actionLinks"].append({"url": clean_url, "label": label, "content": res})
                                await broadcast_to_stage(space_id, {
                                    "type": "view_change", "mode": "doc", "url": clean_url, "label": label, "content": res
                                })
                                if token and space_id:
                                    asyncio.create_task(save_doc_shortcut_to_drive(clean_url, label, space_id, token))

                            # Surface auth link if workspace agent needs authorization
                            for url in re.findall(r'https?://workspace-subagent-auth[^\s)]+', res):
                                ui_state["actionLinks"].append({"url": url.rstrip('.,)'), "label": "Authorize Workspace Access", "content": res})

                            ui_state["status_text"] = "Document ready."
                            await session_data["broadcast_fn"]()
                        except Exception as e:
                            logger.error(f"[ui-prompt] Workspace task failed: {e}")
                            ui_state["status_text"] = "Document creation failed."
                            await session_data["broadcast_fn"]()
                    
                    asyncio.create_task(run_workspace_task())

            # Trigger Broadcast
            await session_data["broadcast_fn"]()
            
            # Sync to Stage if requested
            if args.get("stage_theme"):
                await broadcast_to_stage(space_id, {
                    "type": "theme_change",
                    "tokens": ui_state["theme"]
                })
            
            if "main_stage_view" in args:
                await broadcast_to_stage(space_id, {"type": "view_change", "mode": args["main_stage_view"]})

            return {"ok": True, "applied": args}
            
        return {"ok": False, "error": "Could not parse UI request"}
    except Exception as e:
        logger.error(f"[ui-prompt] error: {e}")
        return FastAPIResponse(status_code=500)

@app.get("/api/video-queue/{space_id:path}")
async def get_video_queue(space_id: str, request: Request):
    check_producer_auth(request)
    return {"queue": video_queues.get(space_id, []), "length": len(video_queues.get(space_id, []))}

@app.post("/api/video-queue/{space_id:path}")
async def add_to_video_queue(space_id: str, request: Request):
    """Add one or more videos to the queue. Starts playing immediately if queue was empty."""
    check_producer_auth(request)
    body = await request.json()
    items = body if isinstance(body, list) else [body]
    # Normalise: each item can be a string URL or {"url": ..., "label": ...}
    normalised = [{"url": i, "label": ""} if isinstance(i, str) else i for i in items]

    was_empty = space_id not in video_queues or len(video_queues[space_id]) == 0
    video_queues.setdefault(space_id, []).extend(normalised)

    if was_empty and video_queues[space_id]:
        first = video_queues[space_id].pop(0)
        logger.info(f"[queue] starting playback: {first['url']} for {space_id}")
        await broadcast_to_stage(space_id, {
            "type": "view_change", "mode": "video",
            "url": first["url"], "label": first.get("label", "")
        })

    return {"ok": True, "queued": len(normalised), "remaining": len(video_queues.get(space_id, []))}

@app.delete("/api/video-queue/{space_id:path}")
async def clear_video_queue(space_id: str, request: Request):
    check_producer_auth(request)
    video_queues.pop(space_id, None)
    await broadcast_to_stage(space_id, {"type": "view_change", "mode": "placeholder"})
    return {"ok": True}

@app.post("/api/video-queue/{space_id:path}/skip")
async def skip_video(space_id: str, request: Request):
    check_producer_auth(request)
    queue = video_queues.get(space_id, [])
    if queue:
        next_item = queue.pop(0)
        await broadcast_to_stage(space_id, {
            "type": "view_change", "mode": "video",
            "url": next_item["url"], "label": next_item.get("label", "")
        })
        return {"ok": True, "playing": next_item, "remaining": len(queue)}
    else:
        await broadcast_to_stage(space_id, {"type": "view_change", "mode": "placeholder"})
        return {"ok": True, "playing": None, "remaining": 0}

@app.post("/api/gemini-mute/{space_id:path}")
async def gemini_mute(space_id: str, request: Request):
    """Mute or unmute Gemini's audio response for a given session. Used during demos."""
    check_producer_auth(request)
    body = await request.json()
    muted = bool(body.get("muted", True))
    session_data = active_sessions.get(space_id)
    if not session_data:
        raise HTTPException(404, "No active session")
    session_data["audio_muted"] = muted
    logger.info(f"[gemini-mute] {space_id} audio_muted={muted}")
    return {"ok": True, "muted": muted}

@app.get("/api/session/{meeting_id:path}")
async def get_session(meeting_id: str, _=Depends(token_required)):
    return {"session_id": current_session.get(meeting_id, "")}

@app.post("/api/session/{meeting_id:path}")
async def set_session(meeting_id: str, data: dict, _=Depends(token_required)):
    session_id = data.get("session_id", "")
    purge_old = data.get("purge_old")
    current_session[meeting_id] = session_id
    if purge_old:
        diagram_store.pop(purge_old, None)
        diagram_version.pop(purge_old, None)
        diagram_title.pop(purge_old, None)
        logger.info(f"[session] Purged old session: {purge_old}")
    
    reset_msg = {"type": "view_change", "mode": "diagram", "diag_id": session_id, "version": 0}
    await broadcast_to_stage(meeting_id, reset_msg)
    return {"ok": True}

@app.get("/api/diagram/{diagram_id}/version")
async def get_version(diagram_id: str, _=Depends(token_required)): 
    return {"version": diagram_version.get(diagram_id, 0)}

@app.get("/api/diagram/{diagram_id}.png")
async def get_png(diagram_id: str, _=Depends(token_required)):
    svg = diagram_store.get(diagram_id)
    if not svg: return FastAPIResponse(status_code=404)
    png = await asyncio.get_event_loop().run_in_executor(None, svg_to_png, svg)
    return FastAPIResponse(content=png, media_type="image/png")

@app.post("/api/render")
async def api_render_d2(payload: dict, _=Depends(token_or_api_key_required)):
    d2_code = payload.get("d2", "")
    style = payload.get("style", "cyber")
    if not d2_code: return FastAPIResponse(status_code=400)
    svg, err = await render_d2(d2_code, style=style)
    if err:
        logger.warning(f"[api_render] D2 error: {err}")
        return FastAPIResponse(content=err, status_code=400, media_type="text/plain")
    return FastAPIResponse(content=svg, media_type="image/svg+xml")

@app.post("/api/transcript/export")
async def export_transcript(payload: dict = Body(...), token: str = Depends(token_required)):
    try:
        meeting_name = await get_calendar_meeting_name(payload["space_id"], token)
        folder_id = await get_or_create_meeting_folder(payload["space_id"], token, meeting_name=meeting_name)
        
        boundary = "-------314159265358979323846"
        metadata = {
            "name": f"Transcript: {meeting_name or payload['space_id']}",
            "mimeType": "application/vnd.google-apps.document",
            "parents": [folder_id] if folder_id else []
        }
        
        body = (
            f"--{boundary}\n"
            f"Content-Type: application/json; charset=UTF-8\n\n"
            f"{json.dumps(metadata)}\n"
            f"--{boundary}\n"
            f"Content-Type: text/plain\n\n"
            f"{payload['transcript']}\n"
            f"--{boundary}--"
        ).encode("utf-8")

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
                params={"supportsAllDrives": "true"},
                content=body,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": f"multipart/related; boundary={boundary}",
                }
            )
            resp.raise_for_status()
            file_id = resp.json()["id"]
            
        logger.info(f"[export] Created document {file_id}")
        return {"ok": True, "file_id": file_id}
    except Exception as e:
        logger.error(f"[export] error: {e}")
        return {"error": str(e)}

@app.post("/api/diagram")
async def api_diagram(payload: dict = Body(...), token: str = Depends(token_required)):
    try:
        meeting_name = await get_calendar_meeting_name(payload["space_id"], token)
        diag_id, svg, title = await generate_diagram(
            payload["transcript"], payload.get("chat", ""), 
            payload["space_id"], token, 
            meeting_name, payload["session_id"],
            style=payload.get("style", "cyber")
        )
        drive_file_id = await save_diagram_to_drive(svg, title, payload["space_id"], token, meeting_name=meeting_name)
        
        # Stream the SVG directly over WebSocket to bypass auth/latency bottlenecks
        svg_base64 = base64.b64encode(svg).decode('utf-8')
        await broadcast_to_stage(payload["space_id"], {
            "type": "view_change", 
            "mode": "diagram", 
            "diag_id": diag_id, 
            "version": diagram_version.get(diag_id, 1),
            "svg": svg_base64
        })
        return {"id": diag_id, "title": title, "drive_file_id": drive_file_id}
    except Exception as e:
        logger.error(f"[api_diagram] error: {e}")
        return {"error": str(e)}

@app.post("/api/diagram/{diagram_id}/save")
async def save_diagram(diagram_id: str, payload: dict = Body(...), token: str = Depends(token_required)):
    svg = diagram_store.get(diagram_id)
    if not svg: return {"error": "Not found"}
    file_id = await save_diagram_to_drive(svg, diagram_title.get(diagram_id, "Diagram"), payload["space_id"], token)
    return {"ok": True, "file_id": file_id}

@app.get("/api/dev/sessions")
async def dev_sessions(request: Request):
    check_producer_auth(request)
    return {
        "active_sessions": list(active_sessions.keys()),
        "stage_listeners": {k: len(v) for k, v in stage_listeners.items()}
    }


@app.post("/api/audio-inject/{space_id:path}")
async def audio_inject(space_id: str, request: Request):
    """
    Stream raw 16kHz 16-bit mono PCM audio into the active Gemini Live session
    for the given space. Gemini transcribes it live and captions appear on stage.

    Auth: Bearer <STAGE_API_KEY>
    Body: raw PCM bytes (audio/pcm) — use ffmpeg to convert:
        ffmpeg -i input.wav -ar 16000 -ac 1 -f s16le output.pcm
    """
    check_producer_auth(request)

    session_data = active_sessions.get(space_id)
    if not session_data or "audio_inject" not in session_data:
        raise HTTPException(status_code=404, detail="No active Gemini Live session for this space")

    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty body")

    inject_queue: asyncio.Queue = session_data["audio_inject"]
    chunk_size = 3200  # 100ms of 16kHz 16-bit mono
    for i in range(0, len(body), chunk_size):
        await inject_queue.put(body[i:i + chunk_size])

    logger.info(f"[inject] queued {len(body)} bytes ({len(body)//3200} chunks) for {space_id}")
    return {"ok": True, "bytes": len(body), "chunks": len(body) // chunk_size}


@app.post("/api/stage-audio/{space_id:path}")
async def stage_audio(space_id: str, request: Request):
    """
    Broadcast audio to all stage WebSocket listeners for a space.
    The stage page decodes and plays it via Web Audio API.
    No active Gemini session required — works whenever the stage is open.

    Auth: Bearer <STAGE_API_KEY>
    Body: any audio format (WAV recommended, max 15MB) — sent as base64 to all stage listeners.
    """
    check_producer_auth(request)
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty body")

    import base64
    await broadcast_to_stage(space_id, {
        "type": "audio",
        "data": base64.b64encode(body).decode("utf-8"),
    })
    return {"ok": True, "bytes": len(body)}


def wav_to_pcm(wav_bytes: bytes) -> bytes:
    """Extracts raw mono PCM bytes from a WAV buffer."""
    import io
    import wave
    if wav_bytes.startswith(b'RIFF'):
        try:
            with wave.open(io.BytesIO(wav_bytes), 'rb') as wav_obj:
                return wav_obj.readframes(wav_obj.getnframes())
        except Exception:
            return wav_bytes[44:]
    return wav_bytes

def downsample_24_to_16(pcm_bytes: bytes) -> bytes:
    """Downsamples 24kHz mono PCM to 16kHz using pure-Python 3:2 decimation."""
    out = bytearray()
    for i in range(0, len(pcm_bytes) - len(pcm_bytes) % 6, 6):
        out.extend(pcm_bytes[i : i + 4])
    return bytes(out)


@app.post("/api/speak/{space_id:path}")
async def api_speak(space_id: str, request: Request):
    """
    Synthesize high-fidelity Kore voice on-demand and inject into Gemini session.
    """
    check_producer_auth(request)
    body = await request.json()
    text = body.get("text", "")
    voice = body.get("voice", VOICE)
    
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")

    session_data = active_sessions.get(space_id)
    was_muted = False
    if session_data:
        was_muted = session_data.get("audio_muted", False)
        session_data["audio_muted"] = True
        logger.info(f"[speak] temporarily muting session {space_id}")

    try:
        response = await gemini_client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                    )
                )
            )
        )
        
        audio_bytes = b""
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                audio_bytes += part.inline_data.data
        
        if not audio_bytes:
            raise HTTPException(status_code=500, detail="No audio returned from Gemini")

        wav_bytes = audio_bytes
        if not wav_bytes.startswith(b'RIFF'):
            import io
            import wave
            wav_io = io.BytesIO()
            with wave.open(wav_io, 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(24000)
                wav.writeframes(audio_bytes)
            wav_bytes = wav_io.getvalue()

        # Send 24kHz WAV directly to stage
        await broadcast_to_stage(space_id, {
            "type": "audio",
            "data": base64.b64encode(wav_bytes).decode("utf-8"),
        })

        # Downsample and inject to Gemini Live for automatic captioning
        raw_pcm_24k = wav_to_pcm(wav_bytes)
        raw_pcm_16k = downsample_24_to_16(raw_pcm_24k)
        
        if session_data and "audio_inject" in session_data:
            inject_queue = session_data["audio_inject"]
            chunk_size = 3200
            for i in range(0, len(raw_pcm_16k), chunk_size):
                await inject_queue.put(raw_pcm_16k[i:i + chunk_size])
            logger.info(f"[speak] injected {len(raw_pcm_16k)} bytes of 16kHz PCM to {space_id}")
            
    except Exception as e:
        logger.error(f"[speak] error: {e}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if session_data:
            try:
                duration = len(audio_bytes) / 48000.0
            except Exception:
                duration = 2.0
            
            async def unmute_later(delay, s_data, orig_muted):
                await asyncio.sleep(delay + 0.5)
                s_data["audio_muted"] = orig_muted
                logger.info(f"[speak] restored audio_muted={orig_muted} for {space_id}")
            
            asyncio.create_task(unmute_later(duration, session_data, was_muted))

    return {"ok": True, "text": text, "voice": voice}


@app.post("/api/terminal-stream/{space_id:path}")
async def terminal_stream(space_id: str, request: Request):
    """
    Receives stdout chunk from CLI and broadcasts it to the stage terminal.
    """
    check_producer_auth(request)
    body = await request.json()
    data = body.get("data", "")
    append = bool(body.get("append", True))
    
    await broadcast_to_stage(space_id, {
        "type": "view_change",
        "mode": "terminal",
        "terminal_data": data,
        "append": append
    })
    return {"ok": True}


@app.post("/api/sound-event/{space_id:path}")
async def sound_event(space_id: str, request: Request):
    """
    Triggers a soundboard synthesized effect on the stage.
    """
    check_producer_auth(request)
    body = await request.json()
    sound = body.get("sound", "")
    if not sound:
        raise HTTPException(status_code=400, detail="Missing sound parameter")
    
    await broadcast_to_stage(space_id, {
        "type": "sound_event",
        "sound": sound
    })
    return {"ok": True, "sound": sound}


@app.post("/api/layout/{space_id:path}")
async def set_stage_layout(space_id: str, request: Request):
    """
    Switches active main stage view layout dynamically.
    """
    check_producer_auth(request)
    body = await request.json()
    view_mode = body.get("view", "placeholder")
    await broadcast_to_stage(space_id, {
        "type": "view_change",
        "mode": view_mode
    })
    return {"ok": True, "view": view_mode}


@app.post("/api/pointer/{space_id:path}")
async def set_stage_pointer(space_id: str, request: Request):
    """
    Triggers coordinate laser pointer dots on the main stage.
    """
    check_producer_auth(request)
    body = await request.json()
    await broadcast_to_stage(space_id, {
        "type": "pointer_event",
        "x": body.get("x", 50),
        "y": body.get("y", 50),
        "active": body.get("active", True)
    })
    return {"ok": True}


@app.post("/api/draw/{space_id:path}")
async def set_stage_draw(space_id: str, request: Request):
    """
    Renders lines, rectangles, text annotations, or clears the stage canvas overlay.
    """
    check_producer_auth(request)
    body = await request.json()
    payload = {"type": "draw_event", "action": body.get("action", "clear")}
    if "color" in body: payload["color"] = body["color"]
    if "lineWidth" in body: payload["lineWidth"] = body["lineWidth"]
    if "x1" in body: payload["x1"] = body["x1"]
    if "y1" in body: payload["y1"] = body["y1"]
    if "x2" in body: payload["x2"] = body["x2"]
    if "y2" in body: payload["y2"] = body["y2"]
    if "x" in body: payload["x"] = body["x"]
    if "y" in body: payload["y"] = body["y"]
    if "w" in body: payload["w"] = body["w"]
    if "h" in body: payload["h"] = body["h"]
    if "text" in body: payload["text"] = body["text"]
    if "font" in body: payload["font"] = body["font"]
    await broadcast_to_stage(space_id, payload)
    return {"ok": True}


@app.post("/api/notepad/{space_id:path}")
async def set_stage_notepad(space_id: str, request: Request):
    """
    Updates the collaborative live markdown notepad.
    """
    check_producer_auth(request)
    body = await request.json()
    await broadcast_to_stage(space_id, {
        "type": "notepad_event",
        "action": body.get("action", "overwrite"),
        "text": body.get("text", "")
    })
    return {"ok": True}


@app.post("/api/layout-config/{space_id:path}")
async def set_stage_layout_config(space_id: str, request: Request):
    """
    Sets advanced layouts (grid, split, single) on the main stage content layer.
    """
    check_producer_auth(request)
    body = await request.json()
    await broadcast_to_stage(space_id, {
        "type": "layout_event",
        "layout": body.get("layout", "single")
    })
    return {"ok": True}


@app.post("/api/theme-config/{space_id:path}")
async def set_stage_theme_config(space_id: str, request: Request):
    """
    Toggles pre-configured visual style themes dynamically.
    """
    check_producer_auth(request)
    body = await request.json()
    await broadcast_to_stage(space_id, {
        "type": "theme_event",
        "theme": body.get("theme", "darkflow")
    })
    return {"ok": True}


@app.post("/api/chat/{space_id:path}")
async def set_stage_chat(space_id: str, request: Request):
    """
    Broadcasts a custom chat comment card onto the stage.
    """
    check_producer_auth(request)
    body = await request.json()
    text = body.get("text", "")
    if text.strip().lower().startswith("/mainstage"):
        text = text.strip()[len("/mainstage"):].strip()
    await broadcast_to_stage(space_id, {
        "type": "chat_comment",
        "sender": body.get("sender", "Audience Member"),
        "text": text,
        "avatar": body.get("avatar", "")
    })
    return {"ok": True}


@app.post("/api/chat")
@app.post("/api/chat/")
async def set_stage_chat_fallback(request: Request):
    """
    Fallback when space_id is omitted. Broadcasts to all active stages or default.
    """
    check_producer_auth(request)
    body = await request.json()
    text = body.get("text", "")
    if text.strip().lower().startswith("/mainstage"):
        text = text.strip()[len("/mainstage"):].strip()
    payload = {
        "type": "chat_comment",
        "sender": body.get("sender", "Audience Member"),
        "text": text,
        "avatar": body.get("avatar", "")
    }
    active_spaces = list(stage_listeners.keys()) if stage_listeners else ["default"]
    for sp in active_spaces:
        await broadcast_to_stage(sp, payload)
    return {"ok": True}



@app.post("/api/transcript/{space_id:path}")
async def set_stage_transcript(space_id: str, request: Request):
    """
    Broadcasts a custom live transcript caption onto the stage.
    """
    check_producer_auth(request)
    body = await request.json()
    await broadcast_to_stage(space_id, {
        "type": "transcript",
        "role": body.get("role", "agent"),
        "label": body.get("label", "Gemini Architect"),
        "text": body.get("text", ""),
        "turn_id": body.get("turn_id", "demo-turn"),
        "is_final": body.get("is_final", True)
    })
    return {"ok": True}


@app.post("/api/emoji/{space_id:path}")
async def set_stage_emoji(space_id: str, request: Request):
    """
    Broadcasts a floating emoji reaction to all stage listeners.
    """
    check_producer_auth(request)
    body = await request.json()
    await broadcast_to_stage(space_id, {
        "type": "emoji_reaction",
        "emoji": body.get("emoji", "👏")
    })
    return {"ok": True}

active_standby_tasks = {}  # space_id -> asyncio.Task

def make_composable_standby_components(badge: str, title: str, description: str, remaining_seconds: int) -> list:
    """Generates a premium server-driven welcome/standby card composed entirely of atomic design primitives."""
    components = []
    
    # 1. Root Grid
    components.append({
        "id": "stage_root_grid",
        "component": {
            "gdm-stage-grid": {
                "layout": "single",
                "children": {
                    "explicitList": ["welcome_outer_container"]
                }
            }
        }
    })
    
    # 2. Outer Full-Stage Container
    components.append({
        "id": "welcome_outer_container",
        "component": {
            "gdm-container": {
                "direction": "column",
                "justify": "center",
                "align": "center",
                "width": "100%",
                "height": "100%",
                "background": "rgba(10, 15, 30, 0.45)", # Deep cinematic cyber backdrop
                "children": {
                    "explicitList": ["welcome_card"]
                }
            }
        }
    })
    
    # 3. Glassmorphic Welcome Card
    card_children = [
        "welcome_header_row",
        "welcome_divider",
        "welcome_title"
    ]
    if description:
        card_children.append("welcome_description")
    if remaining_seconds > 0:
        card_children.append("welcome_countdown")
        card_children.append("welcome_countdown_line")
    card_children.append("welcome_progress")
    card_children.append("welcome_status_row")
    
    components.append({
        "id": "welcome_card",
        "component": {
            "gdm-container": {
                "direction": "column",
                "justify": "center",
                "align": "center",
                "padding": "32px",
                "gap": "20px",
                "width": "500px",
                "glass": True,
                "borderRadius": "16px",
                "border": "1px solid rgba(255, 255, 255, 0.12)",
                "children": {
                    "explicitList": card_children
                }
            }
        }
    })
    
    # 4. Header Row
    components.append({
        "id": "welcome_header_row",
        "component": {
            "gdm-container": {
                "direction": "row",
                "justify": "space-between",
                "align": "center",
                "width": "100%",
                "children": {
                    "explicitList": ["welcome_icon", "welcome_badge"]
                }
            }
        }
    })
    
    components.append({
        "id": "welcome_icon",
        "component": {
            "gdm-icon": {
                "name": "sonar",
                "color": "cyan",
                "size": "32px"
            }
        }
    })
    
    components.append({
        "id": "welcome_badge",
        "component": {
            "gdm-badge": {
                "text": badge.upper(),
                "type": "cyan",
                "pulse": True
            }
        }
    })
    
    # 5. Divider
    components.append({
        "id": "welcome_divider",
        "component": {
            "gdm-divider": {
                "vertical": False,
                "color": "rgba(255, 255, 255, 0.15)",
                "thickness": "1px",
                "margin": "4px 0"
            }
        }
    })
    
    # 6. Title
    components.append({
        "id": "welcome_title",
        "component": {
            "gdm-text": {
                "content": title,
                "size": "h2",
                "color": "accent",
                "pulse": True,
                "uppercase": True,
                "font": "sans",
                "align": "center"
            }
        }
    })
    
    # 7. Description
    if description:
        components.append({
            "id": "welcome_description",
            "component": {
                "gdm-text": {
                    "content": description,
                    "size": "body",
                    "color": "white",
                    "align": "center"
                }
            }
        })
        
    # 8. Countdown Timer
    if remaining_seconds > 0:
        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60
        time_str = f"{minutes:02d}:{seconds:02d}"
        components.append({
            "id": "welcome_countdown",
            "component": {
                "gdm-text": {
                    "content": time_str,
                    "size": "64px",
                    "weight": "800",
                    "color": "accent",
                    "pulse": True,
                    "font": "mono",
                    "align": "center"
                }
            }
        })
        components.append({
            "id": "welcome_countdown_line",
            "component": {
                "gdm-divider": {
                    "vertical": False,
                    "color": "rgba(0, 242, 255, 0.4)",
                    "thickness": "2px",
                    "margin": "0 auto"
                }
            }
        })
        
    # 9. Progress Bar
    components.append({
        "id": "welcome_progress",
        "component": {
            "gdm-progress": {
                "value": 100.0,
                "color": "cyan",
                "height": "8px",
                "animated": True,
                "glow": True
            }
        }
    })
    
    # 10. Status Row
    components.append({
        "id": "welcome_status_row",
        "component": {
            "gdm-container": {
                "direction": "row",
                "justify": "space-between",
                "align": "center",
                "width": "100%",
                "children": {
                    "explicitList": ["welcome_status_lbl", "welcome_clock"]
                }
            }
        }
    })
    
    components.append({
        "id": "welcome_status_lbl",
        "component": {
            "gdm-text": {
                "content": "📡 Aligning WebSocket feeds..." if remaining_seconds > 0 else "🟢 Broadcast stage calibrated",
                "size": "caption",
                "color": "mute"
            }
        }
    })
    
    components.append({
        "id": "welcome_clock",
        "component": {
            "gdm-clock": {
                "showClock": True,
                "showDate": False,
                "format": "24h",
                "accentColor": "cyan"
            }
        }
    })
    
    return components


async def standby_countdown_task(space_id: str, badge: str, title: str, description: str, total_seconds: int):
    """Background task to broadcast decreasing countdown state for standby screens."""
    try:
        remaining = total_seconds
        while remaining >= 0:
            components = make_composable_standby_components(badge, title, description, remaining)
            # Send the components
            await broadcast_to_stage(space_id, {
                "updateComponents": {
                    "components": components
                }
            })
            await broadcast_to_stage(space_id, {
                "createSurface": {"catalogId": "gdm-v0.1", "theme": {}, "root": "stage_root_grid"}
            })
            if remaining == 0:
                break
            await asyncio.sleep(1.0)
            remaining -= 1
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"[standby] Countdown error for space {space_id}: {e}")
    finally:
        active_standby_tasks.pop(space_id, None)


@app.post("/api/standby/{space_id:path}")
async def set_stage_standby(space_id: str, request: Request):
    """
    Toggles a premium visual standby/intermission screen with an active countdown.
    Composed entirely of atomic primitives.
    """
    check_producer_auth(request)
    body = await request.json()
    active = body.get("active", False)
    
    # 1. Cancel any pre-existing task for this space
    existing_task = active_standby_tasks.get(space_id)
    if existing_task:
        existing_task.cancel()
        active_standby_tasks.pop(space_id, None)
        
    if active:
        # Calculate total seconds
        duration_mins = int(body.get("duration", 0))
        duration_secs = int(body.get("seconds", 3))
        total_seconds = duration_mins * 60 + duration_secs
        
        badge = body.get("badge", "STUDIO INTERMISSION")
        title = body.get("title", "Session Will Resume Shortly")
        description = body.get("description", "Preparing next showcase stage...")
        
        # Start new countdown background task
        task = asyncio.create_task(
            standby_countdown_task(space_id, badge, title, description, total_seconds)
        )
        active_standby_tasks[space_id] = task
    else:
        # Deactivating: clear the stage to restore default clean slate
        await broadcast_to_stage(space_id, {"deleteSurface": {}})
        logger.info(f"[standby] Deactivated standby for space {space_id}")
        
    return {"ok": True}


@app.post("/api/focus-panel/{space_id:path}")
async def set_stage_focus_panel(space_id: str, request: Request):
    """
    Sets advanced block focus highlighting on a specific panel.
    """
    check_producer_auth(request)
    body = await request.json()
    msg = {
        "type": "focus_panel",
        "panel": body.get("panel", 0)
    }
    # Optional layout switch (e.g. stretch to 'presentation', revert to 'grid')
    if body.get("layout"):
        msg["layout"] = body["layout"]
    await broadcast_to_stage(space_id, msg)
    return {"ok": True}


@app.post("/api/poll/{space_id:path}")
async def trigger_stage_poll(space_id: str, request: Request):
    """
    Triggers an interactive slide-in poll widget overlay on the main stage.
    """
    check_producer_auth(request)
    body = await request.json()
    await broadcast_to_stage(space_id, {
        "type": "poll_event",
        "active": body.get("active", False),
        "question": body.get("question"),
        "layout": body.get("layout", "rows"),
        "options": body.get("options"),
        "values": body.get("values"),
        "opt1": body.get("opt1"),
        "opt2": body.get("opt2"),
        "opt3": body.get("opt3"),
        "opt4": body.get("opt4"),
        "val1": body.get("val1", 0),
        "val2": body.get("val2", 0),
        "val3": body.get("val3", 0),
        "val4": body.get("val4", 0)
    })
    return {"ok": True}



@app.post("/api/render-stage/{space_id:path}")
async def render_stage(space_id: str, request: Request):
    """
    Emit an A2UI surfaceUpdate to the main stage — the agent-driveable render path.

    Body:
      surfaceUpdate: A2UI v0.8 surfaceUpdate payload
        { components: [{ id, component: { "gdm-stage-card": { title, text, accent } } }] }
      root: component id to use as the render root (default: first component's id)
      dataModelUpdate: optional A2UI v0.8 dataModelUpdate payload

    Validates component names against the catalog; rejects unknown elements.
    """
    check_producer_auth(request)
    body = await request.json()

    surface_update = body.get("surfaceUpdate", {})
    errors, warnings = validate_a2ui_surface_detailed(surface_update)

    components = surface_update.get("components", [])
    root_id = body.get("root") or (components[0]["id"] if components else None)

    import datetime
    if errors:
        await broadcast_to_stage(space_id, {
            "validationFailed": {
                "errors": errors,
                "surfaceId": root_id if 'root_id' in locals() else None,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            }
        })
        raise HTTPException(status_code=422, detail={"errors": errors})

    if warnings:
        logger.warning(f"[render-stage] surface warnings: {'; '.join(warnings)}")
    if not root_id:
        raise HTTPException(status_code=422, detail={"errors": ["No root component id"]})

    # Broadcast in A2UI protocol order: updateComponents → (optional) updateDataModel → createSurface
    await broadcast_to_stage(space_id, {"updateComponents": {"components": components}})

    data_model_update = body.get("dataModelUpdate")
    if data_model_update:
        await broadcast_to_stage(space_id, {"updateDataModel": data_model_update})

    await broadcast_to_stage(space_id, {"createSurface": {"catalogId": "gdm-v0.1", "theme": {}, "root": root_id}})

    logger.info(f"[render-stage] {space_id} root={root_id} components={len(components)}")
    resp = {"ok": True, "root": root_id, "components": len(components)}
    if warnings:
        resp["warnings"] = warnings
    return resp


@app.post("/api/render-stage-clear/{space_id:path}")
async def render_stage_clear(space_id: str, request: Request):
    """Clear the A2UI surface on the stage (deleteSurface)."""
    check_producer_auth(request)
    await broadcast_to_stage(space_id, {"deleteSurface": {}})
    logger.info(f"[render-stage] clear {space_id}")
    return {"ok": True}


@app.post("/api/dashboard/{space_id:path}")
async def set_stage_dashboard(space_id: str, request: Request):
    """
    Updates the live telemetry dashboard on Panel 3 with custom or preset use cases.
    """
    check_producer_auth(request)
    body = await request.json()
    payload = {
        "type": "dashboard_event",
        "mode": body.get("mode"),
        "activeTabId": body.get("activeTabId"),
        "tabs": body.get("tabs"),
        "title": body.get("title"),
        "metrics": body.get("metrics", [])
    }
    if "chart" in body:
        payload["chart"] = body["chart"]
    if "chartValue" in body:
        payload["chartValue"] = body["chartValue"]
        
    await broadcast_to_stage(space_id, payload)
    return {"ok": True}


@app.post("/api/diagram/{space_id:path}/rollback")
async def diagram_rollback(space_id: str, request: Request):
    """
    Rollback diagram state to a previous version in the active history.
    """
    check_producer_auth(request)
    body = await request.json()
    version = body.get("version")
    steps = body.get("steps")
    
    diag_id = current_session.get(space_id)
    if not diag_id:
        raise HTTPException(status_code=404, detail="No active diagram for this space")
        
    from app.config import diagram_history
    history = diagram_history.get(diag_id, [])
    if not history:
        raise HTTPException(status_code=404, detail="No history found for this diagram ID")
        
    target_item = None
    if version is not None:
        for item in history:
            if item["version"] == version:
                target_item = item
                break
    elif steps is not None:
        current_v = diagram_version.get(diag_id, 0)
        target_v = current_v - steps
        for item in history:
            if item["version"] == target_v:
                target_item = item
                break
    else:
        if len(history) >= 2:
            target_item = history[-2]
        else:
            raise HTTPException(status_code=400, detail="Not enough history to roll back")
            
    if not target_item:
        raise HTTPException(status_code=400, detail="Invalid version or rollback step specified")
        
    diagram_store[diag_id] = target_item["svg"]
    diagram_version[diag_id] = target_item["version"]
    diagram_title[diag_id] = target_item["title"]
    
    svg_base64 = base64.b64encode(target_item["svg"]).decode('utf-8')
    await broadcast_to_stage(space_id, {
        "type": "view_change", 
        "mode": "diagram", 
        "diag_id": diag_id, 
        "version": target_item["version"],
        "svg": svg_base64
    })
    
    return {"ok": True, "rolled_to": target_item["version"], "title": target_item["title"]}


@app.get("/api/stage-state/{space_id:path}")
async def get_stage_state(space_id: str, request: Request):
    """
    Query current active stage dashboard and layout properties.
    """
    check_producer_auth(request)
    
    listeners = stage_listeners.get(space_id, set())
    video_q = video_queues.get(space_id, [])
    diag_id = current_session.get(space_id)
    view = current_view.get(space_id, {})
    session_data = active_sessions.get(space_id)
    
    state = {
        "space_id": space_id,
        "listeners_count": len(listeners),
        "video_queue": video_q,
        "video_queue_length": len(video_q),
        "active_view": view.get("mode") if view else "placeholder",
        "current_view_details": view,
        "active_diagram_id": diag_id,
        "active_diagram_version": diagram_version.get(diag_id, 0) if diag_id else 0,
        "active_diagram_title": diagram_title.get(diag_id, "") if diag_id else "",
        "session_active": session_data is not None,
        "audio_muted": session_data.get("audio_muted", False) if session_data else False
    }
    return state


@app.post("/api/image")
async def api_image(payload: dict = Body(...), token: str = Depends(token_or_api_key_required)):
    prompt = (payload.get("prompt") or "").strip()
    if not (prompt.startswith("http://") or prompt.startswith("https://") or prompt.startswith("static:")):
        _check_image_rate(token)
    space_id = (payload.get("space_id") or "").strip()
    panel = payload.get("panel", 1)
    image_layout = payload.get("image_layout", "single")
    label = payload.get("label")
    autoplay = payload.get("autoplay")
    model = payload.get("model", "imagen-3.0-generate-002")
    
    if not prompt or not space_id:
        return FastAPIResponse(status_code=400)

    async def _gen_and_broadcast():
        try:
            if prompt.startswith("http://") or prompt.startswith("https://") or prompt.startswith("static:"):
                img_src = prompt[7:] if prompt.startswith("static:") else prompt
                msg_payload = {
                    "type": "view_change",
                    "mode": "image",
                    "imageData": img_src,
                    "panel": panel,
                    "imageLayout": image_layout,
                    "label": label
                }
                if autoplay is not None:
                    msg_payload["autoplay"] = autoplay
                await broadcast_to_stage(space_id, msg_payload)
                return

            img_bytes = await generate_image(prompt, model=model)
            if img_bytes:
                msg_payload = {
                    "type": "view_change",
                    "mode": "image",
                    "imageData": base64.b64encode(img_bytes).decode("utf-8"),
                    "panel": panel,
                    "imageLayout": image_layout,
                    "label": label
                }
                if autoplay is not None:
                    msg_payload["autoplay"] = autoplay
                await broadcast_to_stage(space_id, msg_payload)
        except Exception as e:
            logger.error(f"[api/image] error: {e}")

    asyncio.create_task(_gen_and_broadcast())
    return {"ok": True, "message": f"Image generation started using {model}"}


@app.post("/api/image/pre-generate")
async def api_image_pre_generate(payload: dict = Body(...), token: str = Depends(token_or_api_key_required)):
    model = payload.get("model", "imagen-3.0-generate-002")
    prompts = payload.get("prompts", [])
    if not isinstance(prompts, list):
        prompts = [prompts]

    sem = asyncio.Semaphore(3)

    async def _warm_cache(p):
        async with sem:
            try:
                if (p, model) not in image_cache:
                    logger.info(f"[pre-generate] warming cache with {model} for: {p[:55]}...")
                    await generate_image(p, model=model)
            except Exception as e:
                logger.error(f"[pre-generate] failed for {p[:50]} with model {model}: {e}")

    for p in prompts:
        p = p.strip()
        if p and not (p.startswith("http://") or p.startswith("https://") or p.startswith("static:")):
            asyncio.create_task(_warm_cache(p))

    return {"ok": True, "message": f"Pre-generation started using {model}"}


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    return await handle_mcp(request, broadcast_to_stage, generate_diagram, generate_image)

@app.get("/main_stage.html", include_in_schema=False)
async def serve_main_stage():
    response = FileResponse("dist/main_stage.html")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response

@app.get("/", include_in_schema=False)
async def serve_index():
    response = FileResponse("dist/index.html")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response
# NOTE: the @app.get("/{path:path}") catch-all SPA-fallback used to live here.
# Moved to the END of this file (next to the StaticFiles mount) so it doesn't
# intercept GET requests for /api/* endpoints registered below — being a
# greedy path:path matcher declared first means it wins for any GET it sees,
# including legitimate API endpoints whose declarations come later in source.
# Same problem class as the StaticFiles mount, same fix: catch-alls go LAST.

# NOTE: app.mount("/", StaticFiles(...)) used to live here. Moved to the END
# of this file so it doesn't intercept POST requests for routes registered
# below (e.g. /api/playbook/fire/...). A Starlette mount at "/" catches every
# path under that prefix and StaticFiles only serves GET/HEAD → POST 405.
# ═══════════════════════════════════════════════════════════════════════════
# STAGED FILE — destination: APPEND to main.py
#
# ## TODO before apply
#   - This is a CODE FRAGMENT to be PASTED at the bottom of main.py, NOT a
#     standalone module. The `app`, `broadcast_to_stage`, `logger`,
#     `HTTPException`, `Request` symbols must already be in scope from
#     main.py's existing imports — they are.
#   - The endpoint is currently UNAUTHED. This is fine for localhost PoC
#     because the audience stage's click should not carry STAGE_API_KEY (an
#     audience-side credential is a leak risk). Before deploying:
#         OPTION A: Mint a per-space "fire ticket" at stage-ticket time,
#                   embed in the rendered button's payload, require server-side
#                   on /api/playbook/fire/...
#         OPTION B: Only enable fire endpoint when a presenter ticket is
#                   active for the space (Mode C v0 separates presenter
#                   URL from audience URL — presenter URL holds the auth).
#     For PoC, the unauthed local endpoint is the right tradeoff.
#   - The `_ACTIVE_TICKS` dict is module-global. Cloud Run multi-instance
#     would need a different state model (Redis, Firestore, etc.) — fine
#     while you're on a single uvicorn process.
# ═══════════════════════════════════════════════════════════════════════════

import asyncio

# Active tick loops per space — cancelled when a new slide fires on the
# same space, so a previous slide's ticker doesn't keep painting under the
# new slide.
_ACTIVE_TICKS: dict[str, asyncio.Task] = {}


@app.post("/api/playbook/fire/{playbook_name}/{slide_id}/{space_id:path}")
async def fire_playbook_slide(playbook_name: str, slide_id: str, space_id: str,
                              request: Request):
    """Resolve a playbook slide, cancel any in-flight tick loop on this space,
    broadcast the new surface to the audience stage (full A2UI protocol order:
    surfaceUpdate → beginRendering), then optionally start a fresh tick loop.

    NOTE on auth: unauthed for localhost PoC. See TODO at top of staged file
    for the deployment auth options."""
    # Lazy import to avoid main.py↔playbooks circular-import issues at module
    # load time. By the time the endpoint is HIT, playbooks/__init__.py has
    # long-since registered everything.
    from playbooks.manager import playbook_manager

    # 1. Cancel any active tick loop on this space — one slide's ticker
    #    shouldn't keep ticking after the next slide takes the stage.
    existing = _ACTIVE_TICKS.pop(space_id, None)
    if existing is not None:
        existing.cancel()

    # 2. Resolve the slide.
    slide = playbook_manager.get_slide(playbook_name, slide_id)
    if not slide:
        raise HTTPException(
            status_code=404,
            detail=f"Slide '{slide_id}' not found in playbook '{playbook_name}'.")

    # 3. Build the surface. Calling convention: builder(space_id, tick=0).
    #    Tolerate both sync (demo_poc.py style) and async (yaml_loader style)
    #    builders, and both 1-arg and 2-arg signatures, during the PoC.
    b = slide.builder
    try:
        if inspect.iscoroutinefunction(b):
            try:
                components = await b(space_id, 0)
            except TypeError:
                components = await b(space_id)
        else:
            try:
                components = b(space_id, 0)
            except TypeError:
                components = b(space_id) if callable(b) else b
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Slide builder failed: {e}")

    if not components:
        raise HTTPException(status_code=500,
                            detail="Slide builder returned no components.")

    # 4. Broadcast in full A2UI protocol order. Bare surfaceUpdate populates
    #    the engine buffer but does not repaint — must follow with
    #    beginRendering. (This is the bug that bit the first draft.)
    root_id = components[0].get("id", "root")

    errors, warnings = validate_a2ui_surface_detailed({"components": components})
    import datetime
    if errors:
        await broadcast_to_stage(space_id, {
            "validationFailed": {
                "errors": errors,
                "surfaceId": root_id if 'root_id' in locals() else None,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            }
        })

    await broadcast_to_stage(space_id, {
        "updateComponents": {"components": components},
    })
    await broadcast_to_stage(space_id, {
        "createSurface": {"catalogId": "gdm-v0.1", "theme": {}, "root": root_id},
    })
    logger.info(f"[playbook] fired {playbook_name}/{slide_id} -> {space_id} "
                f"({len(components)} components, root={root_id})")

    # 5. If the slide ticks, start a fresh background loop. Each tick re-calls
    #    the builder with an incrementing tick number; the builder decides
    #    whether to return a full surface or just changed components.
    if getattr(slide, "ticks", False):
        hz = getattr(slide, "hz", 1) or 1
        delay = 1.0 / hz

        async def run_loop():
            tick = 1
            b = slide.builder
            is_coro = inspect.iscoroutinefunction(b)
            try:
                while True:
                    await asyncio.sleep(delay)
                    try:
                        if is_coro:
                            partial = await b(space_id, tick)
                        else:
                            partial = b(space_id, tick)
                    except TypeError:
                        # Builder doesn't accept a tick arg — bail cleanly
                        # rather than spin forever.
                        break
                    if partial:
                        await broadcast_to_stage(space_id, {
                            "updateComponents": {"components": partial},
                        })
                        await broadcast_to_stage(space_id, {
                            "createSurface": {"catalogId": "gdm-v0.1", "theme": {}, "root": root_id},
                        })
                    tick += 1
            except asyncio.CancelledError:
                pass  # Clean exit when the next slide fires.

        _ACTIVE_TICKS[space_id] = asyncio.create_task(run_loop())

    return {
        "status": "fired",
        "playbook": playbook_name,
        "slide": slide_id,
        "components": len(components),
        "ticks_active": space_id in _ACTIVE_TICKS,
    }


@app.get("/api/playbook/list/{playbook_name}")
async def list_playbook_slides(playbook_name: str):
    """List the slides in a playbook. Used by the future /presenter/{space}
    URL to populate its button strip."""
    from playbooks.manager import playbook_manager

    slides = playbook_manager.list_slides(playbook_name)
    if not slides:
        raise HTTPException(status_code=404,
                            detail=f"Playbook '{playbook_name}' not found or empty.")
    return {
        "playbook": playbook_name,
        "slides": [
            {"slide_id": s.slide_id, "label": s.label, "notes": s.notes,
             "ticks": s.ticks, "hz": s.hz}
            for s in slides
        ],
    }


# SPA-fallback GET catch-all — explicitly 404s any unmatched api/* path,
# otherwise serves the requested file from dist/ or falls back to index.html.
# Placed near the end so api/* GET endpoints registered above (e.g. the
# playbook list endpoint) win before this catch-all gets a chance.
@app.get("/{path:path}", include_in_schema=False)
async def serve_static(path: str):
    if path.startswith("api/") or path in ("mcp",):
        raise HTTPException(status_code=404)
    # Secure against directory traversal attacks by resolving absolute paths.
    base_dir = os.path.abspath("dist")
    target_path = os.path.abspath(os.path.join(base_dir, path))
    if not target_path.startswith(base_dir):
        raise HTTPException(status_code=400, detail="Invalid path")
    if os.path.exists(target_path) and os.path.isfile(target_path):
        return FileResponse(target_path)
    return FileResponse(os.path.join(base_dir, "index.html"))


# StaticFiles mount — placed LAST so it doesn't intercept the API routes
# defined above (notably the playbook fire/list endpoints).
if os.path.isdir("dist"): app.mount("/", StaticFiles(directory="dist", html=True), name="static")
