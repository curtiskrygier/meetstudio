import asyncio
import base64
import json
import os
import uuid as uuid_lib
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import FileResponse, Response as FastAPIResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import httpx

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
    save_diagram_to_drive, fetch_meeting_chat
)
from app.diagrams import generate_diagram

from google.genai import types

@asynccontextmanager
async def lifespan(app):
    yield

app = FastAPI(lifespan=lifespan)

class MeetFramingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "ALLOWALL"
        response.headers["Content-Security-Policy"] = (
            "frame-ancestors 'self' https://*.google.com https://*.googleusercontent.com; "
            "default-src 'self' https://*.google.com https://*.googleusercontent.com https://*.gstatic.com; "
            "script-src 'self' https://*.google.com https://accounts.google.com https://*.gstatic.com 'unsafe-inline' 'unsafe-eval'; "
            "connect-src 'self' https: wss: ws://localhost:* https://*.googleapis.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://*.gstatic.com; "
            "img-src 'self' data: blob: https://*.googleusercontent.com https://*.google.com https://*.gstatic.com;"
        )
        return response

app.add_middleware(MeetFramingMiddleware)

async def broadcast_to_stage(meeting_id: str, message: dict):
    """Send a JSON message to all Main Stage listeners for this meeting."""
    if not meeting_id:
        return
    if message.get("type") == "view_change":
        current_view[meeting_id] = message
    if meeting_id not in stage_listeners:
        return
    payload = json.dumps(message)
    for ws in list(stage_listeners[meeting_id]):
        try:
            await ws.send_text(payload)
        except Exception:
            pass

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
                    description="Access Google Workspace (Docs, Sheets, Drive).",
                    parameters={
                        "type": "OBJECT",
                        "properties": {
                            "prompt": {"type": "string", "description": "The request for the agent."},
                        },
                        "required": ["prompt"]
                    }
                )
            ]),
            types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="fetch_url",
                    description="Get content of a URL.",
                    parameters={
                        "type": "OBJECT",
                        "properties": {
                            "url": {"type": "string", "description": "The URL to fetch."},
                        },
                        "required": ["url"]
                    }
                )
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
                    if msg.get("bytes"):
                        await session.send_realtime_input(audio=types.Blob(data=msg["bytes"], mime_type="audio/pcm;rate=16000"))
                    elif msg.get("text"):
                        data = json.loads(msg["text"])
                        if data.get("type") == "init":
                            token = data.get("access_token", "")
                            if not await validate_google_token(token):
                                await websocket.send_text(json.dumps({"type": "status", "text": "Auth failed: session rejected"}))
                                stop_event.set(); break
                            workspace_user[0] = data.get("user_email", "")
                            session_token[0] = token
                            if data.get("meeting_id"): session_space[0] = data.get("meeting_id")
                        elif data.get("type") == "diagram_mode":
                            diagram_mode[0] = bool(data.get("active", False))
                        elif data.get("type") == "broadcast_view":
                            await broadcast_to_stage(session_space[0], {
                                "type": "view_change",
                                "mode": data.get("mode"),
                                "url": data.get("url"),
                                "label": data.get("label"),
                                "diag_id": data.get("diag_id"),
                                "version": diagram_version.get(data.get("diag_id", ""), 1)
                            })
            except Exception: stop_event.set()

        async def gemini_to_browser():
            try:
                async for response in session.receive():
                    if response.server_content:
                        model_turn = response.server_content.model_turn
                        if model_turn:
                            for part in model_turn.parts:
                                if part.inline_data:
                                    await websocket.send_bytes(part.inline_data.data)
                                elif part.text:
                                    if current_turn["role"] != "agent":
                                        current_turn.update({"id": str(uuid_lib.uuid4()), "role": "agent"})
                                    await websocket.send_text(json.dumps({
                                        "type": "transcript", "role": "agent", "text": part.text, "turn_id": current_turn["id"]
                                    }))
                                    await broadcast_to_stage(session_space[0], {
                                        "type": "transcript", "role": "agent", "text": part.text, "turn_id": current_turn["id"]
                                    })
                        if response.server_content.turn_complete:
                            current_turn.update({"id": str(uuid_lib.uuid4()), "role": None})

                    if response.tool_call:
                        for call in response.tool_call.function_calls:
                            if call.name == "workspace_agent" and not diagram_mode[0]:
                                prompt = call.args["prompt"]
                                print(f"[tool] workspace_agent: {prompt}", flush=True)
                                from app.config import WORKSPACE_AGENT_ENGINE
                                engine_resp = await gemini_client.aio.models.generate_content(
                                    model=WORKSPACE_AGENT_ENGINE,
                                    contents=f"User: {workspace_user[0]}\nSpace: {session_space[0]}\nToken: {session_token[0]}\nRequest: {prompt}",
                                )
                                res_text = engine_resp.text
                                await session.send_tool_response(config=types.LiveConnectConfig(), tool_outputs=[
                                    types.FunctionResponse(name=call.name, id=call.id, response={"result": res_text})
                                ])
                                match = re.search(r'https?://docs\.google\.com/[^\s)]+', res_text)
                                if match:
                                    url = match.group(0)
                                    await websocket.send_text(json.dumps({"type": "action_link", "url": url, "label": "New Document"}))
                            elif call.name == "fetch_url":
                                url = call.args["url"]
                                content = await fetch_url(url)
                                await session.send_tool_response(config=types.LiveConnectConfig(), tool_outputs=[
                                    types.FunctionResponse(name=call.name, id=call.id, response={"result": content})
                                ])
            except Exception: stop_event.set()

        await asyncio.gather(browser_to_gemini(), gemini_to_browser())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, meeting_id: str = ""):
    await websocket.accept()
    try:
        await live_session(websocket, meeting_id)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[ws] error: {e}", flush=True)

@app.websocket("/ws/stage")
async def ws_stage_endpoint(websocket: WebSocket, meeting_id: str = ""):
    await websocket.accept()
    if not meeting_id:
        await websocket.close(); return
    if meeting_id not in stage_listeners: stage_listeners[meeting_id] = set()
    stage_listeners[meeting_id].add(websocket)
    
    if meeting_id in current_view:
        await websocket.send_text(json.dumps(current_view[meeting_id]))
        
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        stage_listeners[meeting_id].remove(websocket)
        if not stage_listeners[meeting_id]: del stage_listeners[meeting_id]

@app.get("/api/session/{meeting_id}")
async def get_session(meeting_id: str):
    return {"session_id": current_session.get(meeting_id)}

@app.post("/api/session/{meeting_id}")
async def set_session(meeting_id: str, data: dict):
    current_session[meeting_id] = data.get("session_id")
    return {"ok": True}

@app.get("/api/diagram/{diagram_id}/version")
async def get_diagram_version(diagram_id: str):
    return {"version": diagram_version.get(diagram_id, 0)}

@app.get("/api/diagram/{diagram_id}.png")
async def get_diagram_png(diagram_id: str):
    svg = diagram_store.get(diagram_id)
    if not svg: return FastAPIResponse(status_code=404, content="Not found")
    png = await asyncio.get_event_loop().run_in_executor(None, svg_to_png, svg)
    if not png: return FastAPIResponse(status_code=500, content="PNG conversion failed")
    return FastAPIResponse(content=png, media_type="image/png")

@app.post("/api/transcript/export")
async def export_transcript(payload: dict = Body(...)):
    transcript, access_token, space_id = payload.get("transcript", "").strip(), payload.get("access_token", "").strip(), payload.get("space_id", "").strip()
    if not transcript or not access_token or not space_id: return {"error": "Missing fields"}
    if not await validate_google_token(access_token): return {"error": "Unauthorized"}, 401
    try:
        meeting_name = await get_calendar_meeting_name(space_id, access_token)
        folder_id = await get_or_create_meeting_folder(space_id, access_token, meeting_name=meeting_name)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post("https://www.googleapis.com/drive/v3/files", 
                json={"name": f"Transcript: {meeting_name or space_id}", "mimeType": "application/vnd.google-apps.document", "parents": [folder_id] if folder_id else []},
                headers={"Authorization": f"Bearer {access_token}"})
            resp.raise_for_status()
            file_id = resp.json()["id"]
            await client.patch(f"https://www.googleapis.com/drive/v3/files/{file_id}?uploadType=media",
                content=transcript.encode("utf-8"), headers={"Authorization": f"Bearer {access_token}", "Content-Type": "text/plain"})
        return {"ok": True, "file_id": file_id}
    except Exception as e: return {"error": str(e)}

@app.post("/api/diagram")
async def api_diagram(payload: dict = Body(...)):
    transcript, chat, access_token, space_id, session_id = payload.get("transcript", "").strip(), payload.get("chat", "").strip(), payload.get("access_token", "").strip(), payload.get("space_id", "").strip(), payload.get("session_id", "").strip()
    if not await validate_google_token(access_token): return {"error": "Unauthorized"}, 401
    try:
        meeting_name = await get_calendar_meeting_name(space_id, access_token)
        diag_id, svg_bytes, title = await generate_diagram(transcript, chat, space_id, access_token, meeting_name, session_id)
        if space_id:
            await broadcast_to_stage(space_id, {"type": "view_change", "mode": "diagram", "diag_id": diag_id, "version": diagram_version.get(diag_id, 1)})
        return {"id": diag_id, "title": title}
    except Exception as e: return {"error": str(e)}

@app.post("/api/diagram/{diagram_id}/save")
async def save_diagram_endpoint(diagram_id: str, payload: dict = Body(...)):
    access_token, space_id = payload.get("access_token", ""), payload.get("space_id", "")
    if not await validate_google_token(access_token): return {"error": "Unauthorized"}, 401
    svg = diagram_store.get(diagram_id)
    if not svg: return {"error": "Not found"}
    file_id = await save_diagram_to_drive(svg, diagram_title.get(diagram_id, "Diagram"), space_id, access_token)
    return {"ok": True, "file_id": file_id}

@app.get("/", include_in_schema=False)
async def serve_index(): return FileResponse("dist/index.html")
@app.get("/main_stage.html", include_in_schema=False)
async def serve_main_stage(): return FileResponse("dist/main_stage.html")
@app.get("/diagram_stage.html", include_in_schema=False)
async def serve_diagram_stage(): return FileResponse("dist/diagram_stage.html")
@app.get("/transcript_stage.html", include_in_schema=False)
async def serve_transcript_stage(): return FileResponse("dist/transcript_stage.html")

if os.path.isdir("dist"): app.mount("/", StaticFiles(directory="dist", html=True), name="static")
