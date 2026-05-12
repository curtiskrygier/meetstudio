import os
import re
import google.genai as genai

PROJECT_ID = os.environ.get("GEMINI_PROJECT")
REGION = os.environ.get("REGION", "us-central1")
MODEL = "gemini-live-2.5-flash-native-audio"
VOICE = os.environ.get("KORE_VOICE", "Charon")
WORKSPACE_AGENT_ENGINE = os.environ.get(
    "WORKSPACE_AGENT_ENGINE",
    "projects/828378723395/locations/us-central1/reasoningEngines/2432159852814925824",
)
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
    "Default to BLUEPRINT visual style for diagrams unless the user requests otherwise."
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
D2_PROMPT = """You are an expert systems architect. Analyse the meeting context below and generate a professional architecture diagram.

Rules:
- Output ONLY valid D2 code. No markdown, no backticks, no explanation.
- Start with EXACTLY this configuration block:
  direction: right
  vars: { d2-config: { layout-engine: elk; sketch: true } }
- ARCHITECTURAL LAYERS: Use nested containers with curly braces { } to group related components into logical layers (e.g. "Client Tier", "API Layer", "Data Persistence").
- SEQUENTIAL FLOW: Define nodes and connections in the order of the data flow or processing steps described.
- Add a Title at the top-center using this format:
  title: "Short Meeting Title"
- Define classes on ONE LINE:
  classes: {user:{shape:person};infra:{shape:square};storage:{shape:cylinder};cloud:{shape:cloud}}
- CRITICAL: EVERY node name and EVERY edge label MUST be wrapped in double quotes.
- NO RESERVED WORDS: Do NOT use D2 keywords (style, vars, classes, direction, layout) as node names or edge labels.
- Use DOT SYNTAX for attributes: "Node Name".class: infra
- Use ABSOLUTE PATHS for icons: "Node Name".icon: "/app/assets/icons/<name>.svg"
- Icons Available: meet.svg, docs.svg, sheets.svg, drive.svg, gemini.svg, cloud_run.svg, sql.svg, storage.svg, compute.svg, cloud.svg, vertex_ai.svg, load_balancer.svg
- Icon Rules:
  - "Main Stage" or "Google Meet": Use "meet.svg"
  - "Gemini" or "Virtual Architect": Use "gemini.svg"
  - "Database": Use "sql.svg" or "storage.svg"
  - "Reasoning Engine": Use "vertex_ai.svg"
- SHAPES: Use standard D2 shapes: square, circle, cloud, cylinder, rectangle, person. (Do NOT use 'file' or 'doc').

Example:
"Client Tier": {
  "User".class: user
  "Browser".icon: "/app/assets/icons/cloud.svg"
}
"Cloud Infrastructure": {
  "Web App".icon: "/app/assets/icons/cloud_run.svg"
  "Database".class: storage
}
"User" -> "Web App": "Requests"
"Web App" -> "Database": "Queries"

STRICT: If the "Meeting context" below says "No meeting context available" or is empty, output ONLY this:
"Waiting for architecture description...".shape: rectangle

Meeting context:
{context}
"""

DIAGRAM_MODEL = "gemini-2.5-flash"
