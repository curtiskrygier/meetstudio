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
    "You are an AI meeting concierge in Google Meet. Be concise and conversational. "
    "You can create/find Workspace files (use workspace_agent) and search the web (built-in). "
    "When a doc is created, say it's ready and the link is in the panel.\n\n"
    "Rules:\n"
    "- For current events or news, always search first — do not rely on training data.\n"
    "- To research AND create a doc: search → synthesise into Markdown → pass full Markdown to "
    "workspace_agent in one call ('Create a Google Doc titled X with this content: ...').\n"
    "- When asked to fetch or look up a specific URL, use fetch_url with that URL.",
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
- ICONS: Assign icons based on node type. 
  - Use ABSOLUTE PATHS for icons: "Node Name".icon: "/app/assets/icons/<name>.svg"
  - Icons Available: meet.svg, docs.svg, sheets.svg, drive.svg, gemini.svg, cloud_run.svg, sql.svg, storage.svg, compute.svg, cloud.svg, vertex_ai.svg, load_balancer.svg
  - "Main Stage" or "Google Meet": Use "meet.svg"
  - "Gemini", "AI", "Agent": Use "gemini.svg"
  - "Database", "Firestore", "SQL": Use "sql.svg" or "storage.svg"
  - "Cloud Run", "Function", "Server": Use "cloud_run.svg"
  - "Storage", "Bucket", "S3", "Drive": Use "drive.svg" or "storage.svg"
  - "Vertex AI", "LLM", "Model": Use "vertex_ai.svg"
  - "User", "Client", "Browser": Use class "user" (no icon needed)

Context follows.
"""

DIAGRAM_MODEL = "gemini-2.5-flash"
