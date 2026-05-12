import asyncio
import os
import re
import subprocess
import tempfile
import uuid as uuid_lib
from google.genai import types
from app.config import PROJECT_ID, REGION, DIAGRAM_MODEL, D2_PROMPT, diagram_store, diagram_version, diagram_title

async def generate_diagram(transcript: str, chat: str = "", space_id: str = "", access_token: str = "", meeting_name: str = "", session_id: str = "", style: str = "cyber") -> tuple[str, bytes, str]:
    """Uses Vertex AI to generate D2 code from a meeting context, then renders to SVG with custom styles."""
    context_parts = []
    if transcript:
        context_parts.append(f"## Voice Transcript\n{transcript[:6000]}")
    if chat:
        context_parts.append(f"## Chat Messages\n{chat[:4000]}")
    if meeting_name:
        context_parts.append(f"## Meeting Topic\n{meeting_name}")

    full_context = "\n\n".join(context_parts)
    
    from app.config import gemini_client
    
    # Use .replace() instead of .format() to avoid KeyErrors from the D2 configuration curly braces
    formatted_prompt = D2_PROMPT.replace("{context}", full_context if full_context else "No meeting context available.")
    
    response = await gemini_client.aio.models.generate_content(
        model=DIAGRAM_MODEL,
        contents=formatted_prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
        )
    )
    
    raw_text = response.text or ""
    # Robustly strip markdown code blocks
    match = re.search(r'```(?:d2)?\s*\n?(.*?)```', raw_text, re.DOTALL)
    d2_code = match.group(1).strip() if match else raw_text.strip()
    
    # PREPEND STYLE WRAPPER (Overrides anything the model produced)
    style_header = ""
    if style == "blueprint":
        style_header = (
            "direction: right\n"
            "vars: { d2-config: { layout-engine: elk; sketch: false } }\n"
            "theme: 200\n"
        )
    elif style == "sketch":
        style_header = (
            "direction: down\n"
            "vars: { d2-config: { layout-engine: dagre; sketch: true } }\n"
            "theme: 100\n"
        )
    elif style == "google":
        style_header = (
            "direction: right\n"
            "vars: { d2-config: { layout-engine: elk; sketch: false } }\n"
            "theme: 200\n"
            "style: {\n  stroke: \"#4285F4\"\n  stroke-width: 2\n}\n"
        )
    else: # cyber (default)
        style_header = (
            "direction: right\n"
            "vars: { d2-config: { layout-engine: elk; sketch: false } }\n"
            "theme: 200\n"
            "style: {\n  stroke: \"#00f2ff\"\n  fill: \"#0b0e14\"\n  stroke-width: 2\n}\n"
        )
    
    # Remove any existing vars, direction, or theme from model to avoid conflicts
    d2_code = re.sub(r'^(direction|vars|style|classes|theme).*?(\n\n|\n[a-z])', '', d2_code, flags=re.DOTALL | re.MULTILINE | re.IGNORECASE)
    d2_code = style_header + "\n" + d2_code

    # Extract title from D2 code for storage/Drive
    title_match = re.search(r'title:\s*"([^"]+)"', d2_code)
    title = title_match.group(1) if title_match else "Architecture Diagram"

    # Render D2 to SVG using the local d2 binary
    with tempfile.TemporaryDirectory() as tmpdir:
        d2_path = f"{tmpdir}/diag.d2"
        svg_path = f"{tmpdir}/diag.svg"
        with open(d2_path, "w") as f:
            f.write(d2_code)
        
        try:
            # We MUST use --bundle to include icons
            process = await asyncio.create_subprocess_exec(
                "d2", "--bundle", d2_path, svg_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                err_msg = stderr.decode()
                print(f"[d2] error: {err_msg}", flush=True)
                # Fallback to extremely simple layout if complex one fails
                fallback_code = f'direction: right\ntitle: "{title}"\n"User" -> "System": "Interaction"'
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
                    svg_bytes = f.read()
                
                # Store in memory
                diag_id = session_id or str(uuid_lib.uuid4())
                diagram_store[diag_id] = svg_bytes
                diagram_version[diag_id] = diagram_version.get(diag_id, 0) + 1
                diagram_title[diag_id] = title
                
                print(f"[diagram] generated style={style} v{diagram_version[diag_id]} for {diag_id}", flush=True)
                return diag_id, svg_bytes, title
        except Exception as e:
            print(f"[d2] exception: {e}", flush=True)
            raise

    return "", b"", ""
