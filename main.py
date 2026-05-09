import asyncio
import base64
import json
import os
import re
import subprocess
import tempfile
import uuid as uuid_lib
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

import httpx

import google.genai as genai
from google.genai import types
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

PROJECT_ID = os.environ.get("GEMINI_PROJECT")
REGION = os.environ.get("REGION", "us-central1")
MODEL = "gemini-live-2.5-flash-native-audio"
VOICE = os.environ.get("KORE_VOICE", "Kore")
WORKSPACE_AGENT_ENGINE = os.environ.get(
    "WORKSPACE_AGENT_ENGINE",
    "projects/828378723395/locations/us-central1/reasoningEngines/2432159852814925824",
)

SYSTEM_PROMPT = os.environ.get(
    "SYSTEM_PROMPT",
    "You are an AI meeting concierge in Google Meet. Be concise and conversational. "
    "You can create/find Workspace files (use workspace_agent) and search the web (built-in). "
    "When a doc is created, say it's ready and the link is in the panel.\n\n"
    "Rules:\n"
    "- For current events or news, always search first — do not rely on training data.\n"
    "- To research AND create a doc: search → synthesise into Markdown → pass full Markdown to "
    "workspace_agent in one call ('Create a Google Doc titled X with this content: ...').\n"
    "- When asked to fetch or look up a specific URL, use fetch_url with that URL.",
)

if not PROJECT_ID:
    raise RuntimeError("GEMINI_PROJECT environment variable is required")


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
            "default-src * 'unsafe-inline' 'unsafe-eval'; "
            "script-src * 'unsafe-inline' 'unsafe-eval'; "
            "connect-src * 'unsafe-inline'; "
            "img-src * data: blob: 'unsafe-inline';"
        )
        return response


app.add_middleware(MeetFramingMiddleware)

gemini_client = genai.Client(vertexai=True, project=PROJECT_ID, location=REGION)

# In-memory store: diagram_id → SVG bytes / version counter
_diagram_store: dict[str, bytes] = {}
_diagram_version: dict[str, int] = {}

# Drive caches keyed by space_id
_meeting_name_cache: dict[str, str] = {}   # space_id → calendar event title
_meeting_folder_cache: dict[str, str] = {} # space_id → Drive folder ID

# Diagram title store
_diagram_title: dict[str, str] = {}        # diagram_id → title

# Current active diagram session per meeting
_current_session: dict[str, str] = {}      # meeting_id → diagram session_id


async def get_calendar_meeting_name(space_id: str, access_token: str) -> str:
    """Return the Calendar event title for this Meet space, '' if not found."""
    if space_id in _meeting_name_cache:
        return _meeting_name_cache[space_id]
    try:
        bare = re.sub(r'^spaces[_/]', '', space_id)
        now = datetime.now(timezone.utc)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                params={
                    "singleEvents": "true",
                    "timeMin": (now - timedelta(hours=3)).isoformat(),
                    "timeMax": (now + timedelta(hours=3)).isoformat(),
                    "fields": "items(summary,hangoutLink,conferenceData/conferenceId)",
                    "maxResults": "50",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if resp.status_code != 200:
            print(f"[calendar] {resp.status_code}: {resp.text[:200]}", flush=True)
            return ""
        for event in resp.json().get("items", []):
            hangout = event.get("hangoutLink", "")
            conf_id = (event.get("conferenceData") or {}).get("conferenceId", "")
            if bare and (bare in hangout or bare in conf_id):
                name = event.get("summary", "").strip()
                print(f"[calendar] matched '{name}' for {bare}", flush=True)
                _meeting_name_cache[space_id] = name
                return name
        print(f"[calendar] no event matched for {bare}", flush=True)
    except Exception as e:
        print(f"[calendar] {type(e).__name__}: {e}", flush=True)
    return ""


async def get_or_create_meeting_folder(space_id: str, access_token: str, meeting_name: str = "") -> str | None:
    """Return the Drive folder ID for this meeting, creating it if needed."""
    # If meeting_name is provided, it's a test/manual override, skip cache
    if space_id in _meeting_folder_cache and not meeting_name:
        return _meeting_folder_cache[space_id]
    
    if meeting_name:
        folder_name = re.sub(r'[^\w\s\-]', '', meeting_name).strip()[:50] or "Test Meeting"
    else:
        calendar_name = await get_calendar_meeting_name(space_id, access_token)
        bare = re.sub(r'^spaces[_/]', '', space_id) or "meeting"
        folder_name = re.sub(r'[^\w\s\-]', '', calendar_name).strip()[:50] if calendar_name else bare

    recordings_id = await _drive_get_or_create_folder("Meet Recordings", "root", access_token)
    if not recordings_id:
        print("[drive] could not get/create 'Meet Recordings'. Ensure Drive API is enabled: https://console.cloud.google.com/apis/library/drive.googleapis.com", flush=True)
        return None
    folder_id = await _drive_get_or_create_folder(folder_name, recordings_id, access_token)
    if folder_id and not meeting_name:
        _meeting_folder_cache[space_id] = folder_id
    
    print(f"[drive] using folder '{folder_name}' id={folder_id}", flush=True)
    return folder_id


async def fetch_meeting_chat(space_id: str, access_token: str) -> str:
    if not space_id or not access_token:
        return ""
    # Normalise: spaces_xxx → spaces/xxx, bare xxx → spaces/xxx
    space_id = re.sub(r'^spaces[_/]', '', space_id)
    space_id = f"spaces/{space_id}"
    try:
        url = f"https://chat.googleapis.com/v1/{space_id}/messages?pageSize=100&orderBy=createTime+asc"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
        if resp.status_code != 200:
            print(f"[chat] API {resp.status_code}: {resp.text[:200]}", flush=True)
            return ""
        messages = []
        for m in resp.json().get("messages", []):
            sender = m.get("sender", {}).get("displayName", "Unknown")
            text = m.get("text", m.get("formattedText", "")).strip()
            if text:
                messages.append(f"{sender}: {text}")
        result = "\n".join(messages)
        print(f"[chat] {len(messages)} messages ({len(result)} chars)", flush=True)
        return result
    except Exception as e:
        print(f"[chat] error: {type(e).__name__}: {e}", flush=True)
        return ""


async def fetch_url(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            text = resp.text
            # Strip HTML tags
            text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL)
            text = re.sub(r'<script[^>]*>.*?</script>', ' ', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'[ \t]+', ' ', text)
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = text.strip()
            print(f"[fetch_url] {url} — {len(text)} chars", flush=True)
            return text[:6000]  # cap at ~1.5k tokens
    except Exception as e:
        print(f"[fetch_url] error: {e}", flush=True)
        return f"Error fetching {url}: {e}"


DIAGRAM_MODEL = "gemini-2.5-flash"

D2_PROMPT = """You are an expert systems architect. Analyse the meeting context below and generate a D2 diagram that best represents the system, architecture, process, or concepts being discussed.

Rules:
- Output ONLY valid D2 code. No markdown fences, no backticks, no explanation.
- Start with this exact header:
  direction: right
- Add a title using this format:
  title: "Short Title Derived From Meeting"
- ICON USAGE: You MUST use icons for major technical components.
  Available Icon URLs:
  - Google Meet: https://www.gstatic.com/images/branding/product/2x/meet_2020q4_48dp.png
  - Cloud Run: https://raw.githubusercontent.com/mingrammer/diagrams/master/resources/gcp/compute/run.png
  - Vertex AI: https://raw.githubusercontent.com/mingrammer/diagrams/master/resources/gcp/ml/vertex-ai.png
  - FastAPI: https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png
  - Gemini: https://www.gstatic.com/lamda/images/gemini_sparkle_v2_60b73b22b163d0434.svg
  Usage syntax: Node Name.icon: https://path/to/icon.png
- STYLE:
  - Keep it focused: max 15 nodes.
  - ONLY use these shapes: rectangle, oval, circle, cylinder, cloud, queue, person.
  - DO NOT add comments (//) on the same line as code.
  - If the transcript is non-technical, use oval shapes.

Meeting context:
{context}
"""


async def generate_diagram(transcript: str, chat: str = "", space_id: str = "", access_token: str = "", meeting_name: str = "", session_id: str = "") -> tuple[str, bytes, str]:
    """Returns (diagram_id, svg_bytes, title). Raises on failure."""
    diagram_text_client = genai.Client(vertexai=True, project=PROJECT_ID, location=REGION)
    context_parts = []
    if transcript:
        context_parts.append(f"## Voice Transcript\n{transcript[:6000]}")
    if chat:
        context_parts.append(f"## Meeting Chat\n{chat[:2000]}")
    context = "\n\n".join(context_parts) if context_parts else "No meeting context available."

    response = await asyncio.to_thread(
        lambda: diagram_text_client.models.generate_content(
            model=DIAGRAM_MODEL,
            contents=D2_PROMPT.format(context=context),
        )
    )
    d2_code = response.text.strip()
    # Strip markdown fences
    d2_code = re.sub(r'^```[a-z]*\n?', '', d2_code, flags=re.MULTILINE)
    d2_code = re.sub(r'```$', '', d2_code, flags=re.MULTILINE).strip()
    
    print(f"[diagram] raw D2 produced:\n{d2_code}", flush=True)

    # Custom post-processing to ensure compatibility
    d2_code = re.sub(r'shape\s*:\s*mindmap', 'shape: oval', d2_code)
    d2_code = re.sub(r'shape\s*:\s*sequence_diagram', '', d2_code)
    d2_code = re.sub(r'shape\s*:\s*component', 'shape: rectangle', d2_code)
    # Remove inline comments that break D2 attributes
    d2_code = re.sub(r'shape\s*:\s*([a-z]+)\s*//.*$', r'shape: \1', d2_code, flags=re.MULTILINE)
    # Collapse runs of blank lines
    d2_code = re.sub(r'\n{3,}', '\n\n', d2_code).strip()

    print(f"[diagram] final D2 ({len(d2_code)} chars)", flush=True)

    def strip_icons(code: str) -> str:
        # Robustly remove any line containing the word 'icon' followed by a colon
        # Handles: 'node.icon: ...', '  icon: ...', 'icon: ...'
        lines = code.splitlines()
        clean = [l for l in lines if not re.search(r'\bicon\s*:', l, re.IGNORECASE)]
        return "\n".join(clean).strip()

    async def render_d2(code: str) -> bytes:
        with tempfile.TemporaryDirectory() as tmpdir:
            d2_path = f"{tmpdir}/diagram.d2"
            svg_path = f"{tmpdir}/diagram.svg"
            with open(d2_path, "w") as f:
                f.write(code)
            result = subprocess.run(
                ["d2", "-t", "0", "--sketch", d2_path, svg_path],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr)
            with open(svg_path, "rb") as f:
                return f.read()

    try:
        svg_bytes = await render_d2(d2_code)
    except Exception as e:
        print(f"[diagram] first render failed: {e}", flush=True)
        # Fallback: strip ALL icon definitions and retry
        d2_code_no_icons = strip_icons(d2_code)
        print(f"[diagram] retrying without icons. code size: {len(d2_code_no_icons)}", flush=True)
        try:
            svg_bytes = await render_d2(d2_code_no_icons)
        except Exception as e2:
            print(f"[diagram] fallback render failed: {e2}", flush=True)
            raise RuntimeError(f"d2 render failed: {str(e2)[:200]}")

    title_match = re.search(r'title:\s*"([^"]+)"', d2_code)
    diagram_title = title_match.group(1).strip()[:20] if title_match else "Meeting Diagram"

    # Use session_id if provided by frontend so main stage can find it
    diagram_id = session_id or str(uuid_lib.uuid4())
    _diagram_store[diagram_id] = svg_bytes
    _diagram_version[diagram_id] = _diagram_version.get(diagram_id, 0) + 1
    _diagram_title[diagram_id] = diagram_title
    print(f"[diagram] stored id={diagram_id} title='{diagram_title}'", flush=True)

    # Trigger background save to Drive if we have auth
    if access_token and space_id:
        asyncio.create_task(save_diagram_to_drive(svg_bytes, diagram_title, space_id, access_token, meeting_name=meeting_name))

    return diagram_id, svg_bytes, diagram_title


async def _drive_get_or_create_folder(name: str, parent_id: str, access_token: str) -> str | None:
    headers = {"Authorization": f"Bearer {access_token}"}
    # q is used for searching
    q = (f"name='{name}' and mimeType='application/vnd.google-apps.folder' "
         f"and '{parent_id}' in parents and trashed=false")
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Search for existing folder
        resp = await client.get(
            "https://www.googleapis.com/drive/v3/files",
            params={
                "q": q,
                "fields": "files(id)",
                "spaces": "drive",
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true"
            },
            headers=headers,
        )
        if resp.status_code == 200:
            files = resp.json().get("files", [])
            if files:
                return files[0]["id"]
        
        # Create if not found
        resp = await client.post(
            "https://www.googleapis.com/drive/v3/files",
            params={"supportsAllDrives": "true"},
            json={
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id] if parent_id != "root" else []
            },
            headers=headers,
        )
        if resp.status_code in (200, 201):
            return resp.json().get("id")
        else:
            print(f"[drive] folder create failed: {resp.status_code} {resp.text}", flush=True)
    return None


def _svg_to_png(svg_bytes: bytes, width: int = 1200) -> bytes | None:
    try:
        result = subprocess.run(
            ["rsvg-convert", "-w", str(width), "--format", "png"],
            input=svg_bytes, capture_output=True, timeout=15,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
        print(f"[drive] rsvg-convert failed: {result.stderr[:200]}", flush=True)
    except Exception as e:
        print(f"[drive] rsvg-convert error: {e}", flush=True)
    return None


async def save_diagram_to_drive(svg_bytes: bytes, title: str, space_id: str, access_token: str, meeting_name: str = ""):
    if not access_token or not space_id:
        return
    try:
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()[:20] or "Meeting Diagram"
        # Convert to PNG for clean Drive preview
        png_bytes = await asyncio.get_event_loop().run_in_executor(None, _svg_to_png, svg_bytes)
        if png_bytes:
            upload_bytes = png_bytes
            mime_type = "image/png"
            filename = f"{safe_title}.png"
        else:
            upload_bytes = svg_bytes
            mime_type = "image/svg+xml"
            filename = f"{safe_title}.svg"
        meeting_folder_id = await get_or_create_meeting_folder(space_id, access_token, meeting_name=meeting_name)
        if not meeting_folder_id:
            return
        boundary = "boundary_d2svg"
        metadata = json.dumps({"name": filename, "parents": [meeting_folder_id], "mimeType": mime_type})
        body = (
            f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
            + metadata
            + f"\r\n--{boundary}\r\nContent-Type: {mime_type}\r\n\r\n"
        ).encode() + upload_bytes + f"\r\n--{boundary}--".encode()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
                params={"supportsAllDrives": "true"},
                content=body,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": f"multipart/related; boundary={boundary}",
                },
            )
        if resp.status_code in (200, 201):
            file_id = resp.json().get("id")
            print(f"[drive] saved '{filename}' id={file_id}", flush=True)
            return file_id
        else:
            print(f"[drive] upload {resp.status_code}: {resp.text[:200]}", flush=True)
    except Exception as e:
        print(f"[drive] {type(e).__name__}: {e}", flush=True)
    return None


async def save_doc_shortcut_to_drive(doc_url: str, doc_title: str, space_id: str, access_token: str):
    """Create a Drive shortcut to a workspace doc in the meeting folder."""
    if not access_token or not space_id:
        return
    file_id_match = re.search(r'/d/([a-zA-Z0-9_-]+)', doc_url)
    if not file_id_match:
        return
    file_id = file_id_match.group(1)
    try:
        meeting_folder_id = await get_or_create_meeting_folder(space_id, access_token)
        if not meeting_folder_id:
            return
        safe_name = re.sub(r'[^\w\s-]', '', doc_title or "Document").strip()[:40] or "Document"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://www.googleapis.com/drive/v3/files",
                params={"supportsAllDrives": "true"},
                json={
                    "name": safe_name,
                    "mimeType": "application/vnd.google-apps.shortcut",
                    "parents": [meeting_folder_id],
                    "shortcutDetails": {"targetId": file_id},
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if resp.status_code in (200, 201):
            print(f"[drive] shortcut '{safe_name}' created", flush=True)
        else:
            print(f"[drive] shortcut {resp.status_code}: {resp.text[:200]}", flush=True)
    except Exception as e:
        print(f"[drive] shortcut {type(e).__name__}: {e}", flush=True)


FETCH_URL_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="fetch_url",
            description=(
                "Fetch the text content of a web page. Use this to retrieve specific URLs "
                "for up-to-date information, such as blog posts, announcement pages, or documentation."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "url": types.Schema(
                        type=types.Type.STRING,
                        description="The full URL to fetch, e.g. 'https://cloud.google.com/blog/topics/google-cloud-next'",
                    )
                },
                required=["url"],
            ),
        )
    ]
)


async def _get_access_token() -> str:
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
            headers={"Metadata-Flavor": "Google"},
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


async def call_workspace_agent(query: str, user_id: str = "") -> str:
    if not user_id:
        return "Workspace agent: no user identity available — user must connect first."
    try:
        token = await _get_access_token()
        url = f"https://us-central1-aiplatform.googleapis.com/v1/{WORKSPACE_AGENT_ENGINE}:streamQuery"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        body = {"input": {"message": query, "user_id": user_id}}

        texts: list[str] = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=body, headers=headers)
            if resp.status_code != 200:
                print(f"[workspace] HTTP {resp.status_code}: {resp.text[:200]}", flush=True)
                return f"Workspace agent HTTP error {resp.status_code}: {resp.text[:120]}"
            print(f"[workspace] raw ({len(resp.text)} bytes): {resp.text[:300]}", flush=True)
            # Response is application/json — may be single object or NDJSON
            for line in resp.text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    for part in chunk.get("content", {}).get("parts", []):
                        t = part.get("text", "").strip()
                        if t:
                            texts.append(t)
                    # Fallback: top-level "output" field
                    out = chunk.get("output", "")
                    if not texts and isinstance(out, str) and out.strip():
                        texts.append(out.strip())
                except Exception:
                    pass
        result = "\n".join(texts) if texts else "The workspace agent did not return a response."
        print(f"[workspace] result: {result[:500]}", flush=True)
        return result
    except Exception as e:
        print(f"[workspace] {type(e).__name__}: {e}", flush=True)
        return f"Workspace agent error: {e}"


WORKSPACE_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="workspace_agent",
            description=(
                "Call the Google Workspace AI agent to create documents, find files, "
                "or manage Google Drive content. Returns a text result which may include URLs."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(
                        type=types.Type.STRING,
                        description=(
                            "The task to perform, e.g. "
                            "'Create a document named Meeting Notes with a summary of today'"
                        ),
                    )
                },
                required=["query"],
            ),
        )
    ]
)


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
        tools=[WORKSPACE_TOOL, FETCH_URL_TOOL, types.Tool(google_search=types.GoogleSearch())],
    )

    await websocket.send_text(json.dumps({"type": "status", "text": "Connecting to Gemini Live..."}))

    async with gemini_client.aio.live.connect(model=MODEL, config=config) as session:
        await websocket.send_text(json.dumps({"type": "status", "text": f"{VOICE} connected — listening"}))

        stop_event = asyncio.Event()
        workspace_user: list[str] = [""]   # mutable so browser_to_gemini can write it
        session_token: list[str] = [""]    # user OAuth token (for Drive)
        session_space: list[str] = [meeting_id]  # meeting space_id
        diagram_mode: list[bool] = [False]  # suppress tool calls while diagramming

        async def browser_to_gemini():
            try:
                while not stop_event.is_set():
                    msg = await websocket.receive()
                    raw = msg.get("bytes")
                    text = msg.get("text")
                    if raw:
                        await session.send_realtime_input(
                            audio=types.Blob(data=raw, mime_type="audio/pcm;rate=16000")
                        )
                    elif text:
                        try:
                            data = json.loads(text)
                            if data.get("type") == "init":
                                workspace_user[0] = data.get("user_email", "")
                                session_token[0] = data.get("access_token", "")
                                if data.get("meeting_id"):
                                    session_space[0] = data.get("meeting_id", meeting_id)
                                print(f"[init] user={workspace_user[0]} space={session_space[0]}", flush=True)
                            elif data.get("type") == "diagram_mode":
                                diagram_mode[0] = bool(data.get("active", False))
                                print(f"[diagram_mode] active={diagram_mode[0]}", flush=True)
                            elif data.get("type") == "video_frame":
                                jpeg = base64.b64decode(data["data"])
                                await session.send_realtime_input(
                                    video=types.Blob(data=jpeg, mime_type="image/jpeg")
                                )
                        except Exception:
                            pass
            except WebSocketDisconnect:
                pass
            except Exception as e:
                print(f"[b2g] {type(e).__name__}: {e}", flush=True)
            finally:
                stop_event.set()

        recv_task = asyncio.create_task(browser_to_gemini())

        # Hard session timeout — 90 minutes
        async def session_timeout():
            await asyncio.sleep(90 * 60)
            print("[session] 90-minute timeout reached", flush=True)
            stop_event.set()
        timeout_task = asyncio.create_task(session_timeout())

        try:
            while not stop_event.is_set():
                async for response in session.receive():
                    if stop_event.is_set():
                        break

                    # Check for tool calls first
                    if response.tool_call:
                        responses = []
                        # In diagram mode, ack all tool calls without executing them
                        # to prevent Gemini from creating docs while the user describes architecture
                        if diagram_mode[0]:
                            for fc in response.tool_call.function_calls:
                                print(f"[tool] suppressed in diagram mode: {fc.name}", flush=True)
                                responses.append(types.FunctionResponse(
                                    id=fc.id, name=fc.name, response={"result": "ok"}
                                ))
                            await session.send_tool_response(function_responses=responses)
                            continue
                        for fc in response.tool_call.function_calls:
                            if fc.name in ("workspace_agent", "call_workspace_agent"):
                                print(f"[tool] workspace query: {fc.args} user: {workspace_user[0]}", flush=True)
                                await websocket.send_text(json.dumps({"type": "status", "text": "Working on it..."}))
                                result = await call_workspace_agent(
                                    fc.args.get("query", ""),
                                    user_id=workspace_user[0],
                                )
                                responses.append(types.FunctionResponse(
                                    id=fc.id,
                                    name=fc.name,
                                    response={"result": result},
                                ))
                                # Surface doc/drive links in the side panel + save shortcuts
                                for url in re.findall(r'https://(?:docs|drive|sheets|slides)\.google\.com/[^\s\]\[\(\)<>"]+', result):
                                    clean_url = url.rstrip('.,)')
                                    label = "Open Spreadsheet" if "spreadsheets" in clean_url else "Open Document"
                                    print(f"[action_link] {clean_url}", flush=True)
                                    await websocket.send_text(json.dumps({
                                        "type": "action_link",
                                        "url": clean_url,
                                        "label": label,
                                    }))
                                    if session_token[0] and session_space[0]:
                                        asyncio.create_task(save_doc_shortcut_to_drive(
                                            clean_url, label, session_space[0], session_token[0]
                                        ))
                                # Surface auth links if the agent needs re-authorisation
                                for url in re.findall(r'https://workspace-subagent-auth[^\s]+', result):
                                    await websocket.send_text(json.dumps({
                                        "type": "action_link",
                                        "url": url.rstrip('.,)'),
                                        "label": "Authorise Workspace Agent",
                                    }))
                            elif fc.name == "fetch_url":
                                url_to_fetch = fc.args.get("url", "")
                                print(f"[tool] fetch_url: {url_to_fetch}", flush=True)
                                await websocket.send_text(json.dumps({"type": "status", "text": "Fetching source..."}))
                                content = await fetch_url(url_to_fetch)
                                responses.append(types.FunctionResponse(
                                    id=fc.id,
                                    name=fc.name,
                                    response={"content": content},
                                ))
                            else:
                                # Unknown tool (e.g. google_search handled internally) — ack to avoid 1007
                                print(f"[tool] unhandled tool call: {fc.name}", flush=True)
                                responses.append(types.FunctionResponse(
                                    id=fc.id,
                                    name=fc.name,
                                    response={"result": "ok"},
                                ))
                        if responses:
                            await session.send_tool_response(function_responses=responses)
                        continue

                    # Process server content
                    sc = response.server_content
                    if not sc:
                        continue

                    # Robust transcript capture with debug logging
                    input_trans = getattr(sc, "input_transcription", None)
                    if input_trans:
                        text = getattr(input_trans, "text", "")
                        print(f"[debug] input_transcription: '{text}' final={getattr(input_trans, 'final', False)}", flush=True)
                        if text:
                            await websocket.send_text(
                                json.dumps({"type": "transcript", "role": "user", "text": text})
                            )

                    if sc.model_turn:
                        for part in sc.model_turn.parts:
                            if part.inline_data:
                                await websocket.send_bytes(part.inline_data.data)
                            if part.text:
                                print(f"[debug] agent_transcript: '{part.text}'", flush=True)
                                await websocket.send_text(
                                    json.dumps({"type": "transcript", "role": "agent", "text": part.text})
                                )
        except Exception as e:
            print(f"[g2b] {type(e).__name__}: {e}", flush=True)
        finally:
            recv_task.cancel()
            timeout_task.cancel()


from fastapi import Body
from fastapi.responses import Response as FastAPIResponse


@app.post("/api/diagram")
async def api_diagram(payload: dict = Body(...)):
    transcript = payload.get("transcript", "").strip()
    chat = payload.get("chat", "").strip()
    access_token = payload.get("access_token", "").strip()
    space_id = payload.get("space_id", "").strip()
    session_id = payload.get("session_id", "").strip()
    meeting_name = payload.get("meeting_name", "").strip()

    if not chat and access_token and space_id:
        chat = await fetch_meeting_chat(space_id, access_token)
    
    print(f"[diagram] request: transcript={len(transcript)}c session={session_id} auth={'yes' if access_token else 'no'}", flush=True)
    
    try:
        diagram_id, svg_bytes, title = await generate_diagram(
            transcript, chat, space_id, access_token, 
            meeting_name=meeting_name, session_id=session_id
        )
        
        drive_file_id = None
        drive_folder_id = None
        if access_token and space_id:
            drive_file_id = await save_diagram_to_drive(svg_bytes, title, space_id, access_token, meeting_name=meeting_name)
            drive_folder_id = await get_or_create_meeting_folder(space_id, access_token, meeting_name=meeting_name)

        return {
            "id": diagram_id, 
            "title": title, 
            "drive_file_id": drive_file_id,
            "drive_folder_id": drive_folder_id,
            "status": "success"
        }
    except Exception as e:
        print(f"[diagram] {type(e).__name__}: {e}", flush=True)
        return {"error": str(e)}


@app.get("/api/session/{meeting_id:path}")
async def get_current_session(meeting_id: str):
    return {"session_id": _current_session.get(meeting_id, "")}

@app.post("/api/session/{meeting_id:path}")
async def set_current_session(meeting_id: str, payload: dict = Body(...)):
    _current_session[meeting_id] = payload.get("session_id", "")
    return {"ok": True}


@app.get("/api/diagram/{diagram_id}/version")
async def get_diagram_version(diagram_id: str):
    return {"version": _diagram_version.get(diagram_id, 0)}

@app.post("/api/diagram/{diagram_id}/save")
async def save_diagram_endpoint(diagram_id: str, payload: dict = Body(...)):
    svg = _diagram_store.get(diagram_id)
    if not svg:
        return {"error": "Diagram not found — generate one first"}
    access_token = payload.get("access_token", "")
    space_id = payload.get("space_id", "")
    title = _diagram_title.get(diagram_id, "Meeting Diagram")
    if not access_token or not space_id:
        return {"error": "access_token and space_id required"}
    await save_diagram_to_drive(svg, title, space_id, access_token)
    return {"ok": True, "title": title}

@app.get("/api/diagram/{diagram_id}.svg")
async def get_diagram_svg(diagram_id: str):
    svg = _diagram_store.get(diagram_id)
    if not svg:
        return FastAPIResponse(status_code=404, content="Not found")
    return FastAPIResponse(content=svg, media_type="image/svg+xml")


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, meeting_id: str = ""):
    await websocket.accept()
    try:
        await live_session(websocket, meeting_id)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[ws] {type(e).__name__}: {e}", flush=True)
        try:
            await websocket.send_text(json.dumps({"type": "status", "text": f"Error: {e}"}))
        except Exception:
            pass


from fastapi.responses import FileResponse

@app.get("/", include_in_schema=False)
@app.get("/index.html", include_in_schema=False)
async def serve_index():
    response = FileResponse("dist/index.html", media_type="text/html")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response

@app.get("/diagram_stage.html", include_in_schema=False)
async def serve_diagram_stage():
    response = FileResponse("dist/diagram_stage.html", media_type="text/html")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response

if os.path.isdir("dist"):
    app.mount("/", StaticFiles(directory="dist", html=True), name="static")
