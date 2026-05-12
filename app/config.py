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
D2_PROMPT = """You are a Master Systems Architect. Analyse the technical meeting context and generate an elite, professional D2 architecture diagram optimized for a 16:9 widescreen display.

Rules:
- Output ONLY valid D2 code. No markdown, no backticks, no explanation.
- NO SYSTEM BLOCKS: Never output 'vars', 'style', 'classes', 'direction', 'theme', or 'layout' blocks. These are managed by the system.
- 16:9 LAYOUT: Always design for a wide horizontal flow. Use three clear horizontal tiers: [Ingestion/Source] -> [AI Processing] -> [Storage/Output].
- ARCHITECTURAL LAYERS: Group all components into logical nested containers based on the 3-tier rule.
- AI HIGHLIGHT: Wrap all AI-related components (Gemini, LLM, Vertex) in a container named "AI Reasoning".
- DATA FLOW: Use sequence numbers (1), (2), (3)... as prefixes on ALL edge labels to show the order of operations clearly.
- MINIMALIST NODES: Keep node labels to 1-3 keywords max (e.g., "FastAPI", "Gemini API"). Ensure labels stay within boxes.
- DESCRIPTIVE EDGES: Use edge labels to explain the interaction (e.g., "1. Streams PCM Audio").
- CRITICAL: Wrap EVERY node name and EVERY edge label in double quotes.
- ICONS: Assign icons using absolute paths: "Node Name".icon: "/app/assets/icons/<name>.svg"
- Icons Available: meet.svg, docs.svg, sheets.svg, drive.svg, gemini.svg, cloud_run.svg, sql.svg, storage.svg, compute.svg, cloud.svg, vertex_ai.svg, load_balancer.svg
- Icon Selection:
  - "Main Stage", "Meet", "Browser", "Add-on": Use "meet.svg"
  - "Gemini", "LLM", "AI", "Multimodal": Use "gemini.svg"
  - "FastAPI", "Cloud Run", "Server", "Gateway": Use "cloud_run.svg"
  - "Drive", "Docs", "Sheets", "Archive": Use "drive.svg", "docs.svg", "sheets.svg"
- SHAPES: Use 'square', 'circle', 'cloud', 'cylinder', 'rectangle', 'person'. Ensure shapes reflect the component type.

Example:
"Source Tier": {
  "User".class: person
  "Meet".icon: "/app/assets/icons/meet.svg"
}
"AI Reasoning": {
  "Gemini".icon: "/app/assets/icons/gemini.svg"
}
"Output Tier": {
  "Drive".icon: "/app/assets/icons/drive.svg"
}
"User" -> "Meet": "1. Interacts"
"Meet" -> "Gemini": "2. Sends Audio"
"Gemini" -> "Drive": "3. Saves Result"

STRICT: If context is empty, output ONLY:
"Waiting for Architecture Description...".shape: rectangle

Meeting context:
{context}
"""

DIAGRAM_MODEL = "gemini-2.5-flash"
