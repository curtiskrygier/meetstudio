import os
import re
import google.genai as genai

PROJECT_ID = os.environ.get("GEMINI_PROJECT")
REGION = os.environ.get("REGION", "us-central1")
MODEL = "gemini-live-2.5-flash-native-audio"
VOICE = os.environ.get("KORE_VOICE", "Charon")
WORKSPACE_AGENT_ENGINE = os.environ.get("WORKSPACE_AGENT_ENGINE", "")

CLIENT_ID = os.environ.get("CLIENT_ID")
MARKETPLACE_CLIENT_ID = "649226456677-kg2d06f201h6narlrddgass1qs2ka3e1.apps.googleusercontent.com"

SYSTEM_PROMPT = os.environ.get(
    "SYSTEM_PROMPT",
    "You are an AI meeting concierge in Google Meet. Be concise and conversational.\n\n"
    "Mandatory Rules:\n"
    "- ARCHITECT MODE: When the user says 'start diagramming', 'let's draw', or 'architect mode', you MUST immediately call activate_architect_mode. Once active, listen and generate D2 diagrams based on their descriptions.\n"
    "- PRESENTING: When you create or find a Google Doc/Sheet/Slide that the user wants to see, use the present_on_main_stage tool to push it to the Meet main stage.\n"
    "- WORKSPACE: Use workspace_agent for all file operations (Docs, Drive, Sheets).\n"
    "- SEARCH: For current events, search first. Synthesise results before creating documents.\n"
    "- URLS: Use fetch_url for specific web content.\n\n"
    "D2 Visual Modes:\n"
    "You must support three distinct visual modes. When requested, wrap the D2 code in the corresponding configuration block:\n"
    "BLUEPRINT MODE: Use direction: right, layout: elk, and theme: 200. Best for structural clarity.\n"
    "SKETCH MODE: Use direction: down, layout: dagre, and sketch: true. Hand-drawn whiteboard feel.\n"
    "CYBER MODE: Use direction: right, layout: elk, and dark-theme: 200. stroke: '#00f2ff', fill: '#0b0e14'.\n\n"
    "Default to SKETCH visual style for diagrams unless the user requests otherwise."
)

if not PROJECT_ID:
    raise RuntimeError("GEMINI_PROJECT environment variable is required")

gemini_client = genai.Client(vertexai=True, project=PROJECT_ID, location=REGION)

# SVG processing limits
MAX_SVG_SIZE = 5 * 1024 * 1024  # 5MB safety limit

# Global In-memory stores
diagram_store: dict[str, bytes] = {}
diagram_version: dict[str, int] = {}
diagram_title: dict[str, str] = {}
meeting_name_cache: dict[str, str] = {}
meeting_folder_cache: dict[str, str] = {}
current_session: dict[str, str] = {}
current_view: dict[str, dict] = {}
stage_listeners: dict[str, set] = {} # set[WebSocket]

# D2 Prompt for diagram generation
D2_PROMPT = """You are a Master Systems Architect. Analyse the technical meeting context and generate a professional D2 architecture diagram.

CRITICAL RULE: NO HALLUCINATIONS.
Only include components, actors, and interactions that were EXPLICITLY discussed in the meeting transcript or chat provided below. 
- NEVER add "standard" components (like 'Load Balancer' or 'Auth Service') if they were not mentioned.
- If you are unsure about a connection, do not draw it.
- Every node and edge must be traceable to the provided context.

Rules:
- Output ONLY valid D2 code. No markdown, no backticks, no explanation.
- NO SYSTEM BLOCKS: Never output 'vars', 'style', 'classes', 'direction', 'theme', or 'layout' blocks. These are managed by the system.
- 16:9 LAYOUT: Design for a wide horizontal flow. Use three horizontal tiers: [Ingestion/Source] -> [Processing] -> [Storage/Output].
- DATA FLOW: Use sequence numbers (1), (2), (3)... as prefixes on ALL edge labels.
- MINIMALIST NODES: Keep node labels to 1-3 keywords max. Ensure labels stay within boxes.
- QUOTING: EVERY node name and EVERY edge label MUST be wrapped in double quotes (e.g., "User" -> "API": "1. Request").
- ICONS: Assign icons using absolute paths: "Node Name".icon: "/app/assets/icons/<name>.svg"
- Icons Available: meet.svg, docs.svg, sheets.svg, drive.svg, gemini.svg, cloud_run.svg, sql.svg, storage.svg, compute.svg, cloud.svg, vertex_ai.svg, load_balancer.svg
- Icon Selection: Use the icon that most closely matches the discussed component.
- SHAPES: Use 'square', 'circle', 'cloud', 'cylinder', 'rectangle', 'person'.

Example structure:
"Source Tier": {
  "User".class: person
  "Meet App".icon: "/app/assets/icons/meet.svg"
}
"Processing": {
  "Gemini AI".icon: "/app/assets/icons/gemini.svg"
  "FastAPI".icon: "/app/assets/icons/cloud_run.svg"
}
"Output Tier": {
  "Google Drive".icon: "/app/assets/icons/drive.svg"
}
"User" -> "Meet App": "1. Interacts"
"Meet App" -> "FastAPI": "2. Streams Audio"
"FastAPI" -> "Gemini AI": "3. Transcribes"
"Gemini AI" -> "Google Drive": "4. Archives"

STRICT: If context is empty or contains no architecture, output ONLY:
"Waiting for Architecture Description...".shape: rectangle

Meeting context:
{context}
"""

DIAGRAM_MODEL = "gemini-2.5-flash"
