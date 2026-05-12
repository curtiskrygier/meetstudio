import asyncio
import os
import sys
import re
from google.genai import types

PROJECT_ID = 'agent-archi'
REGION = 'us-central1'
DIAGRAM_MODEL = 'gemini-2.5-flash'

# Import current D2_PROMPT from app.config
sys.path.append(os.getcwd())
from app.config import D2_PROMPT

import google.genai as genai
gemini_client = genai.Client(vertexai=True, project=PROJECT_ID, location=REGION)

source_text = """Capture: The Google Meet Add-on uses the Media API to stream raw 16kHz audio from the meeting.
Orchestrate: A FastAPI gateway on Cloud Run captures these audio chunks and pipes them via WebSockets to the Gemini Multimodal Live API.
Transcribe: Gemini Live transcribes the technical discussion with near-zero latency, providing a real-time text stream.
Architect: The Architect Agent (Vertex AI / Gemini Flash) parses the transcript to generate structured D2 diagramming code.
Visualize: The D2 code is rendered into a live SVG and broadcast directly to the Meet Main Stage for all participants to see.
Archive: A permanent snapshot of the architecture is automatically exported to a Google Drive storage tier for post-meeting reference."""

async def generate():
    formatted_prompt = D2_PROMPT.replace('{context}', source_text)
    response = await gemini_client.aio.models.generate_content(
        model=DIAGRAM_MODEL,
        contents=formatted_prompt,
        config=types.GenerateContentConfig(temperature=0.2)
    )
    raw_text = response.text or ''
    match = re.search(r'```(?:d2)?\s*\n?(.*?)```', raw_text, re.DOTALL)
    d2_code = match.group(1).strip() if match else raw_text.strip()
    
    with open('iter_16_9.d2', 'w') as f:
        f.write(d2_code)
    print('Generated iter_16_9.d2')

if __name__ == '__main__':
    asyncio.run(generate())
