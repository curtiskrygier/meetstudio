import asyncio
import base64
import json
import os
import re
import uuid as uuid_lib
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import FileResponse, Response as FastAPIResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import httpx
import traceback

# Modular imports
from app.config import (
    PROJECT_ID, REGION, MODEL, VOICE, SYSTEM_PROMPT,
    gemini_client, diagram_store, diagram_version, diagram_title,
    current_session, current_view, stage_listeners
)
from app.auth import validate_google_token
from app.utils import fetch_url, svg_to_png
from app.drive import (
    get_calendar_meeting_name, get_or_create_meeting_folder,
    save_diagram_to_drive, fetch_meeting_chat, save_doc_shortcut_to_drive
)
from app.diagrams import generate_diagram

from google.genai import types

WORKSPACE_AGENT_ENGINE = os.environ.get(
    "WORKSPACE_AGENT_ENGINE",
    "projects/828378723395/locations/us-central1/reasoningEngines/2432159852814925824",
)

@asynccontextmanager
async def lifespan(app):
    yield

app = FastAPI(lifespan=lifespan)

class MeetFramingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "ALLOWALL"
        # Restored permissive CSP from 2d74378
        response.headers["Content-Security-Policy"] = (
            "frame-ancestors 'self' https://*.google.com https://*.googleusercontent.com; "
            "default-src * 'unsafe-inline' 'unsafe-eval'; "
            "script-src * 'unsafe-inline' 'unsafe-eval'; "
            "connect-src * 'unsafe-inline'; "
            "img-src * data: blob: 'unsafe-inline';"
        )
        return response

app.add_middleware(MeetFramingMiddleware)

async def broadcast_to_stage(meeting_id: str, message: dict):
    if not meeting_id: return
    if message.get("type") == "view_change":
        current_view[meeting_id] = message
    if meeting_id not in stage_listeners: return
    payload = json.dumps(message)
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
                types.FunctionDeclaration(name="activate_architect_mode", description="Turn on diagramming mode.", parameters={"type": "OBJECT", "properties": {}}),
                types.FunctionDeclaration(name="deactivate_architect_mode", description="Turn off diagramming mode.", parameters={"type": "OBJECT", "properties": {}}),
                types.FunctionDeclaration(name="fetch_url", description="Get content of a URL.", parameters={
                    "type": "OBJECT", "properties": {"url": {"type": "string"}}, "required": ["url"]
                }),
            ]),
            types.Tool(google_search=types.GoogleSearch()),
        ],
    )

    await websocket.send_text(json.dumps({"type": "status", "text": "Connecting to Gemini Live..."}))

    async with gemini_client.aio.live.connect(model=MODEL, config=config) as session:
        await websocket.send_text(json.dumps({"type": "status", "text": f"Assistant connected — listening"}))

        stop_event = asyncio.Event()
        workspace_user = [""]
        session_token = [""]
        session_space = [meeting_id]
        diagram_mode = [False]
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
                            print(f"[ws] init {workspace_user[0]}", flush=True)
                        elif data.get("type") == "diagram_mode":
                            diagram_mode[0] = bool(data.get("active", False))
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
                            if diagram_mode[0]:
                                responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": "ok"}))
                                continue
                            
                            if fc.name == "workspace_agent":
                                print(f"[tool] workspace: {fc.args}", flush=True)
                                res = await call_workspace_agent(fc.args.get("query", ""), user_id=workspace_user[0])
                                responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": res}))
                                for url in re.findall(r'https?://(?:docs|drive|sheets|slides)\.google\.com/[^\s)]+', res):
                                    clean_url = url.rstrip('.,)')
                                    label = "Open Spreadsheet" if "spreadsheets" in clean_url else "Open Document"
                                    await websocket.send_text(json.dumps({"type": "action_link", "url": clean_url, "label": label}))
                                    # Broadcast to main stage
                                    await broadcast_to_stage(session_space[0], {
                                        "type": "view_change",
                                        "mode": "doc",
                                        "url": clean_url,
                                        "label": label,
                                        "content": res # Preview
                                    })
                                    if session_token[0] and session_space[0]:
                                        asyncio.create_task(save_doc_shortcut_to_drive(clean_url, label, session_space[0], session_token[0]))
                            elif fc.name == "present_on_main_stage":
                                url = fc.args.get("url", "")
                                label = fc.args.get("label", "Document")
                                content = fc.args.get("content", "")
                                await broadcast_to_stage(session_space[0], {
                                    "type": "view_change",
                                    "mode": "doc",
                                    "url": url,
                                    "label": label,
                                    "content": content
                                })
                                await websocket.send_text(json.dumps({"type": "action_link", "url": url, "label": label}))
                                responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": "Presented."}))
                            elif fc.name == "activate_architect_mode":
                                await websocket.send_text(json.dumps({"type": "set_diagram_mode", "active": True}))
                                responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": "ok"}))
                            elif fc.name == "deactivate_architect_mode":
                                await websocket.send_text(json.dumps({"type": "set_diagram_mode", "active": False}))
                                responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": "ok"}))
                            elif fc.name == "fetch_url":
                                responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": await fetch_url(fc.args.get("url", ""))}))
                            else:
                                responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": "ok"}))
                        if responses: await session.send_tool_response(function_responses=responses)
                        continue

                    sc = response.server_content
                    if not sc: continue

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
        except Exception as e: print(f"[ws] error: {e}", flush=True)
        finally:
            stop_event.set()
            recv_task.cancel()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, meeting_id: str = ""):
    await websocket.accept()
    try: await live_session(websocket, meeting_id)
    except WebSocketDisconnect: pass

@app.websocket("/ws/stage")
async def ws_stage_endpoint(websocket: WebSocket, meeting_id: str = ""):
    await websocket.accept()
    if not meeting_id: await websocket.close(); return
    if meeting_id not in stage_listeners: stage_listeners[meeting_id] = set()
    stage_listeners[meeting_id].add(websocket)
    if meeting_id in current_view: await websocket.send_text(json.dumps(current_view[meeting_id]))
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        if meeting_id in stage_listeners:
            stage_listeners[meeting_id].discard(websocket)
            if not stage_listeners[meeting_id]: del stage_listeners[meeting_id]

@app.get("/api/session/{meeting_id:path}")
async def get_session(meeting_id: str): return {"session_id": current_session.get(meeting_id, "")}
@app.post("/api/session/{meeting_id:path}")
async def set_session(meeting_id: str, data: dict):
    session_id = data.get("session_id", "")
    purge_old = data.get("purge_old")
    current_session[meeting_id] = session_id
    
    # Force purge of old session data if requested
    if purge_old:
        diagram_store.pop(purge_old, None)
        diagram_version.pop(purge_old, None)
        diagram_title.pop(purge_old, None)
        print(f"[session] Purged old session: {purge_old}", flush=True)

    # Clear stale view and notify all listeners to show placeholder
    reset_msg = {"type": "view_change", "mode": "diagram", "diag_id": session_id, "version": 0}
    await broadcast_to_stage(meeting_id, reset_msg)
    return {"ok": True}

@app.get("/api/diagram/{diagram_id}/version")
async def get_version(diagram_id: str): return {"version": diagram_version.get(diagram_id, 0)}
@app.get("/api/diagram/{diagram_id}.png")
async def get_png(diagram_id: str):
    svg = diagram_store.get(diagram_id)
    if not svg: return FastAPIResponse(status_code=404)
    png = await asyncio.get_event_loop().run_in_executor(None, svg_to_png, svg)
    return FastAPIResponse(content=png, media_type="image/png")

@app.post("/api/transcript/export")
async def export_transcript(payload: dict = Body(...)):
    # ... (keeping simplified export logic for now)
    try:
        meeting_name = await get_calendar_meeting_name(payload["space_id"], payload["access_token"])
        folder_id = await get_or_create_meeting_folder(payload["space_id"], payload["access_token"], meeting_name=meeting_name)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post("https://www.googleapis.com/drive/v3/files", params={"supportsAllDrives": "true"},
                json={"name": f"Transcript: {meeting_name or payload['space_id']}", "mimeType": "application/vnd.google-apps.document", "parents": [folder_id] if folder_id else []},
                headers={"Authorization": f"Bearer {payload['access_token']}"})
            file_id = resp.json()["id"]
            await client.patch(f"https://www.googleapis.com/drive/v3/files/{file_id}?uploadType=media", params={"supportsAllDrives": "true"},
                content=payload["transcript"].encode("utf-8"), headers={"Authorization": f"Bearer {payload['access_token']}", "Content-Type": "text/plain"})
        return {"ok": True, "file_id": file_id}
    except Exception as e: return {"error": str(e)}

@app.post("/api/diagram")
async def api_diagram(payload: dict = Body(...)):
    try:
        meeting_name = await get_calendar_meeting_name(payload["space_id"], payload["access_token"])
        diag_id, svg, title = await generate_diagram(
            payload["transcript"], payload.get("chat", ""), 
            payload["space_id"], payload["access_token"], 
            meeting_name, payload["session_id"],
            style=payload.get("style", "cyber")
        )
        
        # Upload to Drive to match v17 stable behavior
        drive_file_id = await save_diagram_to_drive(svg, title, payload["space_id"], payload["access_token"], meeting_name=meeting_name)
        
        await broadcast_to_stage(payload["space_id"], {"type": "view_change", "mode": "diagram", "diag_id": diag_id, "version": diagram_version.get(diag_id, 1)})
        return {"id": diag_id, "title": title, "drive_file_id": drive_file_id}
    except Exception as e:
        print(f"[api_diagram] error: {e}", flush=True)
        traceback.print_exc()
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
