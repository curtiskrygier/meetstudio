import asyncio
import os
import re
import subprocess
import tempfile
import uuid as uuid_lib
from google.genai import types
from app.config import PROJECT_ID, REGION, DIAGRAM_MODEL, D2_PROMPT, diagram_store, diagram_version, diagram_title

async def render_d2(d2_code: str, style: str = "cyber") -> bytes:
    """Renders raw D2 code to SVG bytes using the local d2 binary and system style headers."""
    # SYSTEM BLOCK REMOVAL: Model occasionally outputs direction or vars even when forbidden
    d2_code = re.sub(r'^(direction|vars|style|classes|theme|layout):\s*.*$', '', d2_code, flags=re.MULTILINE | re.IGNORECASE)
    d2_code = re.sub(r'^(vars|style|classes)\s*\{.*?\}\s*$', '', d2_code, flags=re.DOTALL | re.MULTILINE | re.IGNORECASE)
    
    # PREPEND STYLE WRAPPER
    classes = "classes: {user:{shape:person};infra:{shape:square};storage:{shape:cylinder};cloud:{shape:cloud};app:{shape:rectangle}}\n"
    style_header = "direction: right\n"
    global_style = "style: {\n  font-size: 14\n  stroke-width: 2\n}\n"
    
    d2_args = ["d2", "--bundle"]

    if style == "blueprint":
        d2_args.extend(["-l", "elk", "-t", "200"])
        style_header += global_style
    elif style == "sketch":
        style_header = "direction: down\n"
        style_header += global_style
        d2_args.extend(["-l", "dagre", "-t", "100", "--sketch"])
    elif style == "google":
        d2_args.extend(["-l", "elk", "-t", "200"])
        style_header += 'style: {\n  font-size: 14\n  stroke: "#4285F4"\n  stroke-width: 2\n}\n'
    else: # cyber (default)
        d2_args.extend(["-l", "elk", "-t", "200"])
        style_header += 'style: {\n  font-size: 14\n  stroke: "#00f2ff"\n  fill: "#0b0e14"\n  stroke-width: 2\n}\n'
    
    full_d2 = classes + style_header + "\n" + d2_code.strip()

    with tempfile.TemporaryDirectory() as tmpdir:
        d2_path = f"{tmpdir}/diag.d2"
        svg_path = f"{tmpdir}/diag.svg"
        with open(d2_path, "w") as f:
            f.write(full_d2)
        
        try:
            process = await asyncio.create_subprocess_exec(
                *d2_args, d2_path, svg_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                err_msg = stderr.decode()
                print(f"[d2] error: {err_msg}", flush=True)
                # Simple fallback
                fallback_code = 'direction: right\n"User" -> "System": "Architecting..."'
                with open(d2_path, "w") as f:
                    f.write(fallback_code)
                process = await asyncio.create_subprocess_exec(
                    "d2", d2_path, svg_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()

            if os.path.exists(svg_path):
                with open(svg_path, "rb") as f:
                    return f.read()
        except Exception as e:
            print(f"[d2] render exception: {e}", flush=True)
    return b""

async def generate_diagram(transcript: str, chat: str = "", space_id: str = "", access_token: str = "", meeting_name: str = "", session_id: str = "", style: str = "cyber") -> tuple[str, bytes, str]:
    """Uses Vertex AI to generate D2 code from a meeting context, then renders to SVG."""
    context_parts = []
    if transcript: context_parts.append(f"## Voice Transcript\n{transcript[:6000]}")
    if chat: context_parts.append(f"## Chat Messages\n{chat[:4000]}")
    if meeting_name: context_parts.append(f"## Meeting Topic\n{meeting_name}")

    full_context = "\n\n".join(context_parts)
    from app.config import gemini_client
    
    formatted_prompt = D2_PROMPT.replace("{context}", full_context if full_context else "No meeting context available.")
    
    response = await gemini_client.aio.models.generate_content(
        model=DIAGRAM_MODEL,
        contents=formatted_prompt,
        config=types.GenerateContentConfig(temperature=0.2)
    )
    
    raw_text = response.text or ""
    match = re.search(r'```(?:d2)?\s*\n?(.*?)```', raw_text, re.DOTALL)
    d2_code = match.group(1).strip() if match else raw_text.strip()
    
    print(f"[d2] generating style={style}...", flush=True)
    svg_bytes = await render_d2(d2_code, style=style)
    
    # Extract title
    title_match = re.search(r'title:\s*"([^"]+)"', d2_code)
    title = title_match.group(1) if title_match else "Architecture Diagram"

    if svg_bytes:
        diag_id = session_id or str(uuid_lib.uuid4())
        diagram_store[diag_id] = svg_bytes
        diagram_version[diag_id] = diagram_version.get(diag_id, 0) + 1
        diagram_title[diag_id] = title
        return diag_id, svg_bytes, title

    return "", b"", ""
