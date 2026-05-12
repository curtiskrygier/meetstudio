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
import markdown
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
        # Expanding CSP to ensure no internal Google signaling is blocked
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

# Ticket system for Stage WS to avoid raw tokens in URL params
# {ticket_id: (token, expiry)}
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
    if meeting_id not in stage_listeners:
        logger.info(f"[stage_ws] No listeners for {meeting_id}")
        return
    payload = json.dumps(message)
    logger.info(f"[stage_ws] Broadcasting {message.get('type')} to {len(stage_listeners[meeting_id])} listeners")
    for ws in list(stage_listeners[meeting_id]):
        try: await ws.send_text(payload)
        except Exception: pass

async def call_workspace_agent(query: str, user_id: str = "") -> str:
    if not user_id: return "Workspace agent: no user identity available."
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
                headers={"Metadata-Flavor": "Google"},
            )
            token = resp.json()["access_token"]
        
        url = f"https://{REGION}-aiplatform.googleapis.com/v1/{WORKSPACE_AGENT_ENGINE}:streamQuery"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        body = {"input": {"message": query, "user_id": user_id}}

        texts = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=body, headers=headers)
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
                            "status_text": {"type": "string", "description": "A short status message to display to the user in the side panel."},
                            "doc_data": {
                                "type": "OBJECT",
                                "description": "If the user asks to read or display a specific document, provide the title and its raw markdown content here.",
                                "properties": {
                                    "title": {"type": "string"},
                                    "content": {"type": "string", "description": "The raw Markdown content of the document."}
                                },
                                "required": ["title", "content"]
                            }
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
        "extra_components": []
    }

    async def broadcast_a2ui():
        """Generates the A2UI payload and sends it to the frontend."""
        components = [
            {
                "id": "hero_status",
                "element": "gdm-status-view",
                "props": {
                    "state": ui_state["status_state"],
                    "status": ui_state["status_text"],
                    "authenticated": ui_state["authenticated"]
                }
            },
            {
                "id": "control_bar",
                "element": "gdm-controls-view",
                "props": {
                    "audioEnabled": ui_state["audioEnabled"],
                    "videoEnabled": ui_state["videoEnabled"],
                    "diagramMode": ui_state["diagramMode"],
                    "transcriptMode": ui_state["transcriptMode"]
                }
            },
            {
                "id": "workspace_links",
                "element": "gdm-actions-view",
                "props": {
                    "actions": ui_state["actionLinks"]
                }
            }
        ]
        # Append server-injected extra components
        components.extend(ui_state.get("extra_components", []))

        payload = {
            "type": "A2UI_STATE",
            "components": components
        }
        try:
            await websocket.send_text(json.dumps(payload))
        except Exception as e:
            logger.error(f"[a2ui] Broadcast error: {e}")

    # Initial broadcast
    await broadcast_a2ui()

    async with gemini_client.aio.live.connect(model=MODEL, config=config) as session:
        # Update state on successful connection
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
                            # Sync frontend button clicks back into backend state
                            ui_state["diagramMode"] = bool(data.get("active", False))
                            if ui_state["diagramMode"]:
                                ui_state["status_text"] = "Gemini Agent Architect — speak your architecture description"
                            else:
                                ui_state["status_text"] = "Assistant connected — listening"
                            await broadcast_a2ui()
                            
                        elif data.get("type") == "view_change":
                            await broadcast_to_stage(session_space[0], data)
            except Exception:
                stop_event.set()

        recv_task = asyncio.create_task(browser_to_gemini())

        try:
            while not stop_event.is_set():
                async for response in session.receive():
                    if stop_event.is_set(): break

                    if response.tool_call:
                        responses = []
                        for fc in response.tool_call.function_calls:
                            # Use ui_state instead of diagram_mode[0] array
                            if ui_state["diagramMode"]:
                                responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": "ok"}))
                                continue
                            
                            elif fc.name == "workspace_agent":
                                logger.info(f"[tool] workspace: {fc.args}")
                                res = await call_workspace_agent(fc.args.get("query", ""), user_id=workspace_user[0])
                                responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": res}))
                                
                                for url in re.findall(r'https?://(?:docs|drive|sheets|slides)\.google\.com/[^\s)]+', res):
                                    clean_url = url.rstrip('.,)')
                                    label = "Open Spreadsheet" if "spreadsheets" in clean_url else "Open Document"
                                    
                                    # A2UI STATE UPDATE
                                    ui_state["actionLinks"].append({"url": clean_url, "label": label, "content": res})
                                    await broadcast_a2ui()
                                    
                                    # Broadcast to main stage
                                    await broadcast_to_stage(session_space[0], {
                                        "type": "view_change",
                                        "mode": "doc",
                                        "url": clean_url,
                                        "label": label,
                                        "content": res
                                    })
                                    if session_token[0] and session_space[0]:
                                        asyncio.create_task(save_doc_shortcut_to_drive(clean_url, label, session_space[0], session_token[0]))
                            
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
                                
                                if "doc_data" in fc.args:
                                    raw_md = fc.args["doc_data"]["content"]
                                    # Convert Markdown to HTML on the server
                                    html_content = markdown.markdown(raw_md, extensions=['extra'])
                                    
                                    # Use ui_state['actionLinks'] as the place for extra components or separate array
                                    # Brief says: ui_state.setdefault("extra_components", [])
                                    # But broadcast_a2ui doesn't have extra_components yet.
                                    # I will update ui_state and broadcast_a2ui as well.
                                    ui_state.setdefault("extra_components", [])
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
                                    # If it's a doc, we might need to send htmlContent to the stage too
                                    msg = {"type": "view_change", "mode": stage_view}
                                    if stage_view == "doc" and "doc_data" in fc.args:
                                        msg["label"] = fc.args["doc_data"]["title"]
                                        msg["htmlContent"] = markdown.markdown(fc.args["doc_data"]["content"], extensions=['extra'])
                                    await broadcast_to_stage(session_space[0], msg)
                                    
                                responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": "UI updated successfully."}))
                            
                            elif fc.name == "fetch_url":
                                responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": await fetch_url(fc.args.get("url", ""))}))
                            
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
                            msg = {"type": "transcript", "role": "user", "text": t_text, "turn_id": current_turn["id"], "is_final": is_final}
                            await websocket.send_text(json.dumps(msg))
                            await broadcast_to_stage(session_space[0], msg)
                            if is_final: current_turn["role"] = None

                    if sc.model_turn:
                        for part in sc.model_turn.parts:
                            if part.inline_data:
                                await websocket.send_bytes(part.inline_data.data)
                            if part.text:
                                if current_turn["role"] != "agent":
                                    current_turn.update({"id": str(uuid_lib.uuid4()), "role": "agent"})
                                msg = {"type": "transcript", "role": "agent", "text": part.text, "turn_id": current_turn["id"], "is_final": False}
                                await websocket.send_text(json.dumps(msg))
                                await broadcast_to_stage(session_space[0], msg)
                    
                    if sc.turn_complete: current_turn["role"] = None
        except Exception as e:
            logger.error(f"[ws] error: {e}")
            logger.debug(traceback.format_exc())
        finally:
            stop_event.set()
            recv_task.cancel()

@app.get("/api/auth/ticket")
async def create_auth_ticket(token: str = Depends(token_required)):
    """Create a short-lived ticket to authenticate a secondary client (like the stage) without passing the raw token in the URL."""
    ticket = secrets.token_urlsafe(32)
    expiry = datetime.now(timezone.utc) + timedelta(minutes=5)
    auth_tickets[ticket] = (token, expiry)
    return {"ticket": ticket}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, meeting_id: str = "", token: str = ""):
    # We use the 'token' param name for compatibility with index.tsx but it now expects a Ticket
    ticket_data = auth_tickets.get(token)
    if not ticket_data or ticket_data[1] < datetime.now(timezone.utc):
        logger.warning(f"[ws] handshake rejected: invalid or expired ticket for meeting {meeting_id}")
        await websocket.close(code=1008)
        return
    await websocket.accept()
    try: await live_session(websocket, meeting_id)
    except WebSocketDisconnect: pass

@app.websocket("/ws/stage")
async def ws_stage_endpoint(websocket: WebSocket, meeting_id: str = "", ticket: str = ""):
    # Stage client uses short-lived ticket
    ticket_data = auth_tickets.get(ticket)
    if not ticket_data or ticket_data[1] < datetime.now(timezone.utc):
        logger.warning(f"[ws/stage] rejected: invalid or expired ticket")
        await websocket.close(code=1008)
        return
    
    await websocket.accept()
    if not meeting_id: await websocket.close(); return
    if meeting_id not in stage_listeners: stage_listeners[meeting_id] = set()
    stage_listeners[meeting_id].add(websocket)
    logger.info(f"[stage_ws] NEW listener for {meeting_id}. Total: {len(stage_listeners[meeting_id])}")
    if meeting_id in current_view: await websocket.send_text(json.dumps(current_view[meeting_id]))
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        if meeting_id in stage_listeners:
            stage_listeners[meeting_id].discard(websocket)
            logger.info(f"[stage_ws] REMOVED listener for {meeting_id}")
            if not stage_listeners[meeting_id]: del stage_listeners[meeting_id]

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
async def api_render_d2(payload: dict, _=Depends(token_required)):
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
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post("https://www.googleapis.com/drive/v3/files", params={"supportsAllDrives": "true"},
                json={"name": f"Transcript: {meeting_name or payload['space_id']}", "mimeType": "application/vnd.google-apps.document", "parents": [folder_id] if folder_id else []},
                headers={"Authorization": f"Bearer {token}"})
            file_id = resp.json()["id"]
            await client.patch(f"https://www.googleapis.com/drive/v3/files/{file_id}?uploadType=media", params={"supportsAllDrives": "true"},
                content=payload["transcript"].encode("utf-8"), headers={"Authorization": f"Bearer {token}", "Content-Type": "text/plain"})
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
async def save_diagram(diagram_id: str, payload: dict = Body(...)):
    svg = diagram_store.get(diagram_id)
    if not svg: return {"error": "Not found"}
    file_id = await save_diagram_to_drive(svg, diagram_title.get(diagram_id, "Diagram"), payload["space_id"], payload["access_token"])
    return {"ok": True, "file_id": file_id}

@app.get("/", include_in_schema=False)
async def serve_index(): return FileResponse("dist/index.html")
@app.get("/{path:path}", include_in_schema=False)
async def serve_static(path: str):
    if os.path.exists(f"dist/{path}"): return FileResponse(f"dist/{path}")
    return FileResponse("dist/index.html")

if os.path.isdir("dist"): app.mount("/", StaticFiles(directory="dist", html=True), name="static")
