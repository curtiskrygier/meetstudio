import asyncio
import base64
import json
import os
import re
from contextlib import asynccontextmanager

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
    "- For Google Cloud Next announcements: call fetch_url('https://cloud.google.com/blog/topics/google-cloud-next') "
    "then supplement with a search for 'Google Cloud Next 2025 announcements site:cloud.google.com'. "
    "Focus on Workspace, AI, and Gemini announcements.",
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
        system_instruction=types.Content(parts=[types.Part(text=SYSTEM_PROMPT)]),
        tools=[WORKSPACE_TOOL, FETCH_URL_TOOL, types.Tool(google_search=types.GoogleSearch())],
    )

    await websocket.send_text(json.dumps({"type": "status", "text": "Connecting to Gemini Live..."}))

    async with gemini_client.aio.live.connect(model=MODEL, config=config) as session:
        await websocket.send_text(json.dumps({"type": "status", "text": f"{VOICE} connected — listening"}))

        stop_event = asyncio.Event()
        workspace_user: list[str] = [""]  # mutable so browser_to_gemini can write it

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
                                print(f"[init] workspace user: {workspace_user[0]}", flush=True)
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
                    if response.tool_call:
                        responses = []
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
                                # Surface doc/drive links in the side panel
                                for url in re.findall(r'https://(?:docs|drive|sheets|slides)\.google\.com/[^\s\]\[\(\)<>"]+', result):
                                    clean_url = url.rstrip('.,)')
                                    label = "Open Spreadsheet" if "spreadsheets" in clean_url else "Open Document"
                                    print(f"[action_link] {clean_url}", flush=True)
                                    await websocket.send_text(json.dumps({
                                        "type": "action_link",
                                        "url": clean_url,
                                        "label": label,
                                    }))
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

                    if not response.server_content:
                        continue
                    sc = response.server_content

                    if hasattr(sc, "input_transcription") and sc.input_transcription:
                        t = getattr(sc.input_transcription, "text", "")
                        if t:
                            await websocket.send_text(
                                json.dumps({"type": "transcript", "role": "user", "text": t})
                            )

                    if sc.model_turn:
                        for part in sc.model_turn.parts:
                            if part.inline_data:
                                await websocket.send_bytes(part.inline_data.data)
                            if part.text:
                                await websocket.send_text(
                                    json.dumps({"type": "transcript", "role": "agent", "text": part.text})
                                )
        except Exception as e:
            print(f"[g2b] {type(e).__name__}: {e}", flush=True)
        finally:
            recv_task.cancel()
            timeout_task.cancel()


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

if os.path.isdir("dist"):
    app.mount("/", StaticFiles(directory="dist", html=True), name="static")
