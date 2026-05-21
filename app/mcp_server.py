import asyncio
import base64
import logging
import uuid as uuid_lib

from fastapi import Request
from fastapi.responses import JSONResponse

from app.auth import check_producer_auth

logger = logging.getLogger("concierge")


_TOOLS = [
    {
        "name": "send_transcript",
        "description": (
            "Broadcast a line of transcript text to the Meet main stage. "
            "Appears as a live subtitle for all participants."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to display as a transcript line"
                },
                "space_id": {
                    "type": "string",
                    "description": "Google Meet space ID of the active session (e.g. spaces/abc123)"
                },
                "role": {
                    "type": "string",
                    "enum": ["user", "agent"],
                    "description": "Speaker role — 'user' for a participant, 'agent' for the AI. Defaults to 'user'."
                },
                "pause_before_ms": {
                    "type": "integer",
                    "description": "Milliseconds to wait before broadcasting. Use to pace subtitles naturally for demos (e.g. 2000). Capped at 10000.",
                    "default": 0
                }
            },
            "required": ["text", "space_id"]
        }
    },
    {
        "name": "trigger_diagram",
        "description": (
            "Generate a D2 architecture diagram from a description or meeting transcript "
            "and broadcast it live to the Meet main stage."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "transcript": {
                    "type": "string",
                    "description": "Architecture description or meeting transcript to convert into a D2 diagram"
                },
                "space_id": {
                    "type": "string",
                    "description": "Google Meet space ID of the active session"
                },
                "style": {
                    "type": "string",
                    "enum": ["cyber", "blueprint", "sketch", "google"],
                    "description": "Visual theme for the diagram. Defaults to 'cyber'."
                }
            },
            "required": ["transcript", "space_id"]
        }
    },
    {
        "name": "generate_image",
        "description": (
            "Generate an AI image from a text description using Imagen 4 and broadcast it "
            "live to the Meet main stage."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Detailed image description (e.g. 'A futuristic data center with neon blue lights')"
                },
                "space_id": {
                    "type": "string",
                    "description": "Google Meet space ID of the active session"
                }
            },
            "required": ["prompt", "space_id"]
        }
    },
    {
        "name": "send_emoji",
        "description": (
            "Launch floating emoji reactions on the Meet main stage — "
            "they rise from the bottom and fade out, like live stream reactions."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "space_id": {
                    "type": "string",
                    "description": "Google Meet space ID of the active session"
                },
                "emoji": {
                    "type": "string",
                    "description": "The emoji character(s) to float up the screen (e.g. '👏', '🔥', '💡')"
                },
                "repeat": {
                    "type": "integer",
                    "description": "Number of times to fire the burst (1-5). Defaults to 1.",
                    "default": 1
                }
            },
            "required": ["space_id", "emoji"]
        }
    }
]


def _ok(req_id, result: dict):
    return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": result})

def _tool_text(req_id, text: str):
    return _ok(req_id, {"content": [{"type": "text", "text": text}]})

def _tool_error(req_id, message: str):
    return _ok(req_id, {"content": [{"type": "text", "text": message}], "isError": True})

def _rpc_error(req_id, code: int, message: str):
    return JSONResponse({"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}})


async def handle_mcp(request: Request, broadcast_fn, generate_diagram_fn, generate_image_fn=None):
    try:
        check_producer_auth(request)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=getattr(e, "status_code", 401))

    try:
        body = await request.json()
    except Exception:
        return _rpc_error(None, -32700, "Parse error")

    method = body.get("method", "")
    req_id = body.get("id")
    params = body.get("params", {})

    # Notifications carry no id — acknowledge and return
    if req_id is None:
        return JSONResponse({}, status_code=202)

    if method == "initialize":
        return _ok(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "meet-live-concierge", "version": "1.0.0"}
        })

    if method == "tools/list":
        return _ok(req_id, {"tools": _TOOLS})

    if method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments", {})

        if name == "send_transcript":
            text = (args.get("text") or "").strip()
            space_id = (args.get("space_id") or "").strip()
            role = args.get("role", "user")
            if role not in ("user", "agent"):
                role = "user"

            if not text or not space_id:
                return _tool_error(req_id, "text and space_id are required")

            pause_ms = min(int(args.get("pause_before_ms") or 0), 10000)
            if pause_ms > 0:
                await asyncio.sleep(pause_ms / 1000)

            label = "Gemini Architect" if role == "agent" else "Speaker"
            await broadcast_fn(space_id, {
                "type": "transcript",
                "role": role,
                "label": label,
                "text": text,
                "turn_id": str(uuid_lib.uuid4()),
                "is_final": True
            })
            logger.info(f"[mcp] send_transcript to {space_id}: {text[:60]}")
            return _tool_text(req_id, f"Transcript line sent to {space_id}.")

        if name == "trigger_diagram":
            transcript = (args.get("transcript") or "").strip()
            space_id = (args.get("space_id") or "").strip()
            style = args.get("style", "cyber")
            if style not in ("cyber", "blueprint", "sketch", "google"):
                style = "cyber"

            if not transcript or not space_id:
                return _tool_error(req_id, "transcript and space_id are required")

            logger.info(f"[mcp] trigger_diagram for {space_id} (style={style}) — generating async")

            async def _generate_and_broadcast():
                try:
                    diag_id, svg_bytes, title = await generate_diagram_fn(
                        transcript=transcript,
                        session_id=space_id,
                        style=style
                    )
                    if not diag_id:
                        logger.error(f"[mcp] trigger_diagram failed for {space_id}")
                        return
                    from app.config import diagram_version
                    await broadcast_fn(space_id, {
                        "type": "view_change",
                        "mode": "diagram",
                        "diag_id": diag_id,
                        "version": diagram_version.get(diag_id, 1),
                        "svg": base64.b64encode(svg_bytes).decode("utf-8")
                    })
                    logger.info(f"[mcp] diagram broadcast complete for {space_id}")
                except Exception as e:
                    logger.error(f"[mcp] trigger_diagram error: {e}")

            asyncio.create_task(_generate_and_broadcast())
            return _tool_text(req_id, f"Diagram generation started for {space_id} — will appear when ready.")

        if name == "send_emoji":
            space_id = (args.get("space_id") or "").strip()
            emoji = (args.get("emoji") or "👏").strip()
            repeat = max(1, min(int(args.get("repeat") or 1), 5))

            if not space_id:
                return _tool_error(req_id, "space_id is required")

            for i in range(repeat):
                if i > 0:
                    await asyncio.sleep(0.6)
                await broadcast_fn(space_id, {"type": "emoji_reaction", "emoji": emoji})

            logger.info(f"[mcp] send_emoji {emoji} x{repeat} to {space_id}")
            return _tool_text(req_id, f"Emoji {emoji} fired x{repeat} to {space_id}.")

        if name == "generate_image":
            prompt = (args.get("prompt") or "").strip()
            space_id = (args.get("space_id") or "").strip()

            if not prompt or not space_id:
                return _tool_error(req_id, "prompt and space_id are required")

            if not generate_image_fn:
                return _tool_error(req_id, "Image generation not configured on this server.")

            logger.info(f"[mcp] generate_image for {space_id}: {prompt[:60]}")

            async def _generate_and_broadcast():
                try:
                    img_bytes = await generate_image_fn(prompt)
                    if not img_bytes:
                        logger.error(f"[mcp] generate_image returned no data for {space_id}")
                        return
                    await broadcast_fn(space_id, {
                        "type": "view_change",
                        "mode": "image",
                        "imageData": base64.b64encode(img_bytes).decode("utf-8")
                    })
                    logger.info(f"[mcp] image broadcast complete for {space_id}")
                except Exception as e:
                    logger.error(f"[mcp] generate_image error: {e}")

            asyncio.create_task(_generate_and_broadcast())
            return _tool_text(req_id, f"Image generation started for {space_id} — will appear when ready.")

        return _rpc_error(req_id, -32601, f"Unknown tool: {name}")

    return _rpc_error(req_id, -32601, f"Method not found: {method}")
