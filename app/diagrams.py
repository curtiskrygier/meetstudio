import asyncio
import os
import re
import subprocess
import tempfile
import uuid as uuid_lib
from google.genai import types
from app.config import PROJECT_ID, REGION, DIAGRAM_MODEL, D2_PROMPT, diagram_store, diagram_version, diagram_title

async def generate_diagram(transcript: str, chat: str = "", space_id: str = "", access_token: str = "", meeting_name: str = "", session_id: str = "") -> tuple[str, bytes, str]:
    """Uses Vertex AI to generate D2 code from a meeting context, then renders to SVG."""
    context_parts = []
    if transcript:
        context_parts.append(f"## Voice Transcript\n{transcript[:6000]}")
    if chat:
        context_parts.append(f"## Chat Messages\n{chat[:4000]}")
    if meeting_name:
        context_parts.append(f"## Meeting Topic\n{meeting_name}")

    full_context = "\n\n".join(context_parts)
    
    from app.config import gemini_client
    
    response = await gemini_client.aio.models.generate_content(
        model=DIAGRAM_MODEL,
        contents=full_context,
        config=types.GenerateContentConfig(
            system_instruction=D2_PROMPT,
            temperature=0.2,
        )
    )
    
    raw_text = response.text.strip()
    # Strip markdown code blocks if present
    d2_code = re.sub(r'^```d2\s*', '', raw_text)
    d2_code = re.sub(r'\s*```$', '', d2_code)
    
    # Simple sanitisation: ensures we have a valid D2 start if model hallucinated
    if "direction:" not in d2_code:
        d2_code = "direction: right\n" + d2_code

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
            # Use layout-engine elk for professional look
            process = await asyncio.create_subprocess_exec(
                "d2", "--layout", "elk", "--sketch", d2_path, svg_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                print(f"[d2] error: {stderr.decode()}", flush=True)
                # Fallback to simple layout if elk fails
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
                
                print(f"[diagram] generated v{diagram_version[diag_id]} for {diag_id}", flush=True)
                return diag_id, svg_bytes, title
        except Exception as e:
            print(f"[d2] exception: {e}", flush=True)
            raise

    return "", b"", ""
