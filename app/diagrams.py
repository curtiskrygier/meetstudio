import asyncio
import os
import re
import tempfile
import uuid as uuid_lib
import logging
from google.genai import types
from app.config import PROJECT_ID, REGION, DIAGRAM_MODEL, D2_PROMPT, diagram_store, diagram_version, diagram_title

logger = logging.getLogger("concierge")

async def render_d2(d2_code: str, style: str = "cyber") -> tuple[bytes, str]:
    """Renders raw D2 code to SVG bytes using the local d2 binary and system style headers."""
    # SECURITY: Strip comments first to prevent bypasses
    d2_code = re.sub(r'#.*$', '', d2_code, flags=re.MULTILINE)
    
    # SECURITY: Block 'include' and '@' (which can be used for imports/exec)
    if re.search(r'\binclude\b', d2_code, re.IGNORECASE) or '@' in d2_code:
        logger.warning(f"D2 security violation: forbidden keyword or character detected.")
        return b"", "D2 security violation: 'include' and '@' are forbidden."

    # SYSTEM BLOCK REMOVAL: Model occasionally outputs direction or vars even when forbidden
    # We remove these to ensure our system styles (direction: right, etc.) take precedence
    forbidden_blocks = ['direction', 'vars', 'style', 'classes', 'theme', 'layout']
    for block in forbidden_blocks:
        d2_code = re.sub(rf'^{block}\s*:.*$', '', d2_code, flags=re.MULTILINE | re.IGNORECASE)
        d2_code = re.sub(rf'^{block}\s*\{{.*?\}}', '', d2_code, flags=re.DOTALL | re.MULTILINE | re.IGNORECASE)
    
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
        d2_args.extend(["-l", "dagre", "-t", "200", "--sketch"])
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
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                return b"", "D2 compilation timed out."
            
            if process.returncode != 0:
                err_msg = stderr.decode().strip()
                return b"", err_msg

            if os.path.exists(svg_path):
                with open(svg_path, "rb") as f:
                    return f.read(), ""
        except Exception as e:
            return b"", str(e)
            
    return b"", "Unknown error"

async def generate_diagram(transcript: str, chat: str = "", space_id: str = "", access_token: str = "", meeting_name: str = "", session_id: str = "", style: str = "cyber") -> tuple[str, bytes, str]:
    """Uses Vertex AI to generate D2 code from a meeting context, then renders to SVG with an auto-correction loop."""
    context_parts = []
    # Replace simple truncation with a more robust context window
    # By taking the LAST N characters instead of the FIRST N, we capture the most recent context
    # where the actual diagram request usually happens.
    if transcript: context_parts.append(f"## Voice Transcript\n{transcript[-8000:]}")
    if chat: context_parts.append(f"## Chat Messages\n{chat[-4000:]}")
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
    
    logger.info(f"Generating diagram (style={style})...")
    svg_bytes, err = await render_d2(d2_code, style=style)
    
    if err:
        logger.warning(f"D2 render failed: {err}. Attempting auto-correction.")
        retry_prompt = f"The D2 code you generated produced this error:\n{err}\n\nPlease correct the syntax and output ONLY the corrected D2 code."
        
        response = await gemini_client.aio.models.generate_content(
            model=DIAGRAM_MODEL,
            contents=[formatted_prompt, raw_text, retry_prompt],
            config=types.GenerateContentConfig(temperature=0.1)
        )
        raw_text = response.text or ""
        match = re.search(r'```(?:d2)?\s*\n?(.*?)```', raw_text, re.DOTALL)
        d2_code = match.group(1).strip() if match else raw_text.strip()
        svg_bytes, err = await render_d2(d2_code, style=style)
        
        if err:
            logger.error(f"D2 auto-correction failed: {err}")
            # Fallback
            fallback_code = 'direction: right\n"Error" -> "Fallback": "Failed to parse architecture"'
            svg_bytes, _ = await render_d2(fallback_code, style=style)

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
