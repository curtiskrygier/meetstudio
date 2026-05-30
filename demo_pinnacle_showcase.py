#!/usr/bin/env python3
"""
Meet Live Concierge — Pinnacle Cinematic Showcase (Mermaid, HTML Sandbox, & Overlays)
===================================================================================
Orchestrates an ultra-premium, multi-phase demonstration of our next-generation 
Meet Main Stage features:
1. Client-Side Compiled Mermaid Flowcharts (gdm-mermaid-panel)
2. Sandbox-Isolated Custom HTML HUD Panels (gdm-html-panel)
3. Immersive, Glassmorphic Fullscreen Takeovers (overlay = True)

This script features interactive telemetry syncing (Nvidia/Google stocks via 212Trading/Yahoo,
Toulouse Velo Bike shares, OpenSky Airspace tracking), synchronized sound chimes, chyrons, 
emoji explosions, and high-fidelity narration transcripts.

Environment Variables:
    FAST_MODE: Set to "0" or "false" to slow down transitions for recording. Default: True.
    CONCIERGE_API_URL: Target FastAPI backend URL. Default: http://localhost:8000
    STAGE_API_KEY: Secure authorization token.
    MEET_SPACE_ID: Force target Google Meet space.
"""

import asyncio
import os
import sys
import glob
import random
import httpx
from types import ModuleType
from unittest.mock import MagicMock

# --- Auto-Resolve Local Virtualenv Site-Packages ---
_base_dir = os.path.dirname(os.path.abspath(__file__))
_venv_dirs = glob.glob(os.path.join(_base_dir, "venv", "lib", "python3.*", "site-packages"))
for _vd in _venv_dirs:
    if _vd not in sys.path:
        sys.path.insert(0, _vd)

# Setup dynamic dummy modules for google.adk to bypass ADK import failures in 212Trading backend
class AdkMockModule(ModuleType):
    def __init__(self, name):
        super().__init__(name)
        self.__path__ = []
    def __getattr__(self, name):
        mock_val = MagicMock()
        setattr(self, name, mock_val)
        return mock_val

class AdkMockFinder:
    def find_spec(self, fullname, path, target=None):
        if fullname.startswith("google.adk"):
            from importlib.machinery import ModuleSpec
            return ModuleSpec(fullname, AdkMockLoader())
        return None

class AdkMockLoader:
    def create_module(self, spec):
        mod = AdkMockModule(spec.name)
        sys.modules[spec.name] = mod
        return mod
    def exec_module(self, module):
        pass

sys.meta_path.insert(0, AdkMockFinder())

# --- 212Trading Backend Market Services Integration ---
_T212_LOADED = False
_GET_QUOTE_FN = None

try:
    t212_path = "/home/curtis/gemini/212Trading"
    if t212_path not in sys.path:
        sys.path.append(t212_path)
    
    if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
        adc_path = "/home/curtis/.config/gcloud/application_default_credentials.json"
        if os.path.exists(adc_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = adc_path
            
    try:
        from google.cloud import secretmanager
        sm_client = secretmanager.SecretManagerServiceClient()
        project_id = "431547562459"
        
        for s_name in ["T212_API_KEY", "T212_API_SECRET"]:
            if s_name not in os.environ:
                try:
                    name = f"projects/{project_id}/secrets/{s_name}/versions/latest"
                    val = sm_client.access_secret_version(request={"name": name}).payload.data.decode("UTF-8")
                    os.environ[s_name] = val
                except Exception:
                    pass
    except Exception:
        pass

    dummy_agent = ModuleType("backend.agent")
    dummy_agent.app = ModuleType("backend.agent.app")
    sys.modules["backend.agent"] = dummy_agent
    sys.modules["backend.agent.app"] = dummy_agent.app

    from backend.services.market_data import get_quote as t212_get_quote
    _GET_QUOTE_FN = t212_get_quote
    _T212_LOADED = True
    print("✨ Successfully integrated with 212Trading backend market services.", file=sys.stderr)
except Exception as e:
    print(f"⚠️ Could not load 212Trading backend market services: {e}", file=sys.stderr)

# --- Configuration & Environment Setup ---
API_URL = os.environ.get("CONCIERGE_API_URL", "CONCIERGE_API_URL_PLACEHOLDER")
KEY = os.environ.get("STAGE_API_KEY") or exit("STAGE_API_KEY required — export it before running this script")
FAST_MODE = os.environ.get("FAST_MODE", "true").lower() not in ("0", "false", "no")

# --- ANSI Terminal Colors for Premium Logging ---
CLR_CYAN = "\033[38;5;51m"
CLR_MAGENTA = "\033[38;5;201m"
CLR_GREEN = "\033[38;5;82m"
CLR_YELLOW = "\033[38;5;220m"
CLR_SLATE = "\033[38;5;244m"
CLR_RESET = "\033[0m"

def print_banner():
    print(f"\n{CLR_CYAN}  ==============================================================={CLR_RESET}")
    print(f"{CLR_CYAN}  ▲   P I N N A C L E   C I N E M A T I C   S H O W C A S E   ▲{CLR_RESET}")
    print(f"{CLR_CYAN}  ==============================================================={CLR_RESET}")
    print(f"  {CLR_SLATE}Features: Mermaid.js Flowcharts, Custom HTML HUDs, & Takeover Overlays{CLR_RESET}")
    print(f"  {CLR_SLATE}Deployment Server:{CLR_RESET} {CLR_CYAN}{API_URL}{CLR_RESET}\n")

# --- Utility Handlers & API Functions ---
async def get_active_space(client: httpx.AsyncClient) -> str:
    headers = {"Authorization": f"Bearer {KEY}"} if KEY else {}
    try:
        resp = await client.get(f"{API_URL}/api/dev/sessions", headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        listeners = data.get("stage_listeners", {})
        sessions = data.get("active_sessions", [])
        return sessions[0] if sessions else (list(listeners.keys())[0] if listeners else "")
    except Exception:
        return ""

async def post_endpoint(client: httpx.AsyncClient, endpoint: str, payload: dict):
    headers = {"Content-Type": "application/json"}
    if KEY:
        headers["Authorization"] = f"Bearer {KEY}"
    try:
        resp = await client.post(f"{API_URL}{endpoint}", headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  {CLR_MAGENTA}⚠️ Error calling {endpoint}: {e}{CLR_RESET}", file=sys.stderr)

async def call_mcp_tool(client: httpx.AsyncClient, tool_name: str, arguments: dict):
    headers = {"Content-Type": "application/json"}
    if KEY:
        headers["Authorization"] = f"Bearer {KEY}"
    payload = {
        "jsonrpc": "2.0",
        "id": "pinnacle-showcase-mcp",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    try:
        resp = await client.post(f"{API_URL}/mcp", headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        res = resp.json()
        if "error" in res:
            print(f"  {CLR_MAGENTA}❌ MCP Tool Error: {res['error'].get('message')}{CLR_RESET}", file=sys.stderr)
        else:
            txt = res.get("result", {}).get("content", [{}])[0].get("text", "")
            print(f"  {CLR_GREEN}⚡ [MCP Server] {txt}{CLR_RESET}")
    except Exception as e:
        print(f"  {CLR_MAGENTA}❌ MCP Call Failed to {tool_name}: {e}{CLR_RESET}", file=sys.stderr)

async def set_transcript(client: httpx.AsyncClient, space_id: str, text: str, label: str = "Gemini Concierge"):
    await post_endpoint(client, f"/api/transcript/{space_id}", {
        "role": "agent",
        "label": label,
        "text": text,
        "is_final": True
    })

async def launch_emoji_burst(client: httpx.AsyncClient, space_id: str, emojis: list[str]):
    for emo in emojis:
        await post_endpoint(client, f"/api/emoji/{space_id}", {"emoji": emo})
        await asyncio.sleep(0.12)

async def broadcast_chat_comment(client: httpx.AsyncClient, space_id: str, sender: str, text: str, avatar: str = ""):
    await post_endpoint(client, f"/api/chat/{space_id}", {
        "sender": sender,
        "text": text,
        "avatar": avatar,
    })

# --- Live Telemetry Data Fetchers ---
async def get_live_stock_price(client: httpx.AsyncClient, symbol: str, default: float) -> tuple[float, float]:
    ticker_map = {
        "GOOG": "GOOGL_US_EQ",
        "NVDA": "NVDA_US_EQ",
        "MSFT": "MSFT_US_EQ",
        "AAPL": "AAPL_US_EQ",
    }
    t212_ticker = ticker_map.get(symbol.upper(), f"{symbol.upper()}_US_EQ")

    if _T212_LOADED and _GET_QUOTE_FN:
        try:
            quote = await _GET_QUOTE_FN(t212_ticker)
            if quote:
                p = quote.get("price")
                prev = quote.get("prev_close") or p
                change_pct = quote.get("change_pct")
                if change_pct is None:
                    change_pct = ((p - prev) / prev * 100) if prev else 0.0
                return float(p), float(change_pct)
        except Exception as e:
            print(f"  {CLR_SLATE}⚠️ T212 query failed: {e}. Falling back...{CLR_RESET}", file=sys.stderr)
            
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        resp = await client.get(url, headers=headers, timeout=3)
        if resp.status_code == 200:
            meta = resp.json()["chart"]["result"][0]["meta"]
            p = float(meta["regularMarketPrice"])
            prev = float(meta.get("previousClose") or p)
            return p, ((p - prev) / prev) * 100
    except Exception:
        pass
    return default, random.uniform(-1.5, 3.5)

STATION_CACHE = {}
async def get_live_toulouse_bikes(client: httpx.AsyncClient) -> list[dict]:
    global STATION_CACHE
    try:
        if not STATION_CACHE:
            resp = await client.get("https://api.cyclocity.fr/contracts/toulouse/gbfs/v2/station_information.json", timeout=3)
            if resp.status_code == 200:
                stations = resp.json().get("data", {}).get("stations", [])
                for s in stations:
                    STATION_CACHE[str(s.get("station_id"))] = s.get("name", "Station").strip()

        resp = await client.get("https://api.cyclocity.fr/contracts/toulouse/gbfs/v2/station_status.json", timeout=3)
        if resp.status_code == 200:
            status_list = resp.json().get("data", {}).get("stations", [])
            active = []
            for s in status_list:
                s_id = str(s.get("station_id"))
                if s_id in STATION_CACHE:
                    active.append({
                        "name": STATION_CACHE[s_id],
                        "bikes": s.get("num_bikes_available", 0),
                        "stands": s.get("num_docks_available", 0)
                    })
                    if len(active) >= 6:
                        break
            if active:
                return active
    except Exception:
        pass
    return [
        {"name": "CAPITOLE", "bikes": random.randint(5, 15), "stands": random.randint(10, 20)},
        {"name": "JEANNE D'ARC", "bikes": random.randint(2, 10), "stands": random.randint(5, 18)},
        {"name": "GARE MATABIAU", "bikes": random.randint(8, 22), "stands": random.randint(4, 15)},
    ]

MS_TO_FPM = 196.85
async def get_live_toulouse_flights(client: httpx.AsyncClient, tick: int = 0) -> tuple[int, list[dict]]:
    try:
        # Toulouse Airport blagnac sector
        resp = await client.get("https://opensky-network.org/api/states/all?lamin=43.5&lomin=1.1&lamax=43.8&lomax=1.6", headers={"User-Agent": "Mozilla/5.0"}, timeout=4)
        if resp.status_code == 200:
            states = resp.json().get("states") or []
            flights = []
            for idx, s in enumerate(states):
                if s[8]:  # on ground
                    continue
                alt_m = s[7] if s[7] is not None else s[13]
                if alt_m is None:
                    continue
                callsign = s[1].strip() if s[1] else f"AFR{100+idx}"
                flights.append({
                    "callsign": callsign,
                    "altitude": int(alt_m),
                    "speed": int((s[9] or 0) * 3.6),
                    "vrate_fpm": int((s[11] or 0) * MS_TO_FPM)
                })
                if len(flights) >= 4:
                    break
            if flights:
                return len(states), flights
    except Exception:
        pass

    # Approach descent vector simulations
    sim = [
        {"callsign": "AFR6129", "altitude": max(700, 1500 - tick * 150), "speed": max(220, 310 - tick * 10), "vrate_fpm": -950},
        {"callsign": "BAW373", "altitude": max(1300, 2800 - tick * 180), "speed": max(260, 380 - tick * 12), "vrate_fpm": -1200},
        {"callsign": "EZY4218", "altitude": max(2100, 4200 - tick * 220), "speed": max(320, 450 - tick * 15), "vrate_fpm": -1500},
    ]
    return len(sim), sim

# --- High Fidelity SVG System Architecture Diagram (For Phase 2 Fullscreen Takeover) ---
architecture_svg = """<svg viewBox="0 0 700 350" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- Cyberpunk Glowing drop shadows -->
    <filter id="cyan-glow" x="-15%" y="-15%" width="130%" height="130%">
      <feGaussianBlur stdDeviation="5" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
    <filter id="magenta-glow" x="-15%" y="-15%" width="130%" height="130%">
      <feGaussianBlur stdDeviation="5" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
    <filter id="green-glow" x="-15%" y="-15%" width="130%" height="130%">
      <feGaussianBlur stdDeviation="5" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>

  <!-- Futuristic Glassmorphic Background Card -->
  <rect width="100%" height="100%" rx="18" fill="rgba(10, 12, 28, 0.95)" stroke="#00f2ff" stroke-width="2"/>
  
  <!-- Subtle High-tech dots array -->
  <pattern id="dot-pattern" width="24" height="24" patternUnits="userSpaceOnUse">
    <circle cx="2" cy="2" r="1.2" fill="rgba(0, 242, 255, 0.08)"/>
  </pattern>
  <rect width="100%" height="100%" rx="18" fill="url(#dot-pattern)"/>

  <!-- Left Header -->
  <text x="30" y="40" fill="#00f2ff" font-family="monospace" font-size="12" font-weight="bold">CONCIERGE MASTER ROUTING ENGINE // V2.0</text>
  <line x1="30" y1="48" x2="350" y2="48" stroke="rgba(0, 242, 255, 0.3)" stroke-width="1.5"/>

  <!-- NODE 1: User Voice & Client (Vite, Lit, WS) -->
  <g transform="translate(45, 95)">
    <rect width="160" height="90" rx="10" fill="rgba(24, 30, 54, 0.7)" stroke="#00f2ff" stroke-width="1.5" filter="url(#cyan-glow)" />
    <text x="80" y="32" fill="#ffffff" font-family="sans-serif" font-size="13" font-weight="bold" text-anchor="middle">🎙️ CLIENT STAGE</text>
    <text x="80" y="52" fill="#00f2ff" font-family="monospace" font-size="10" text-anchor="middle">Lit &amp; Lit-Html</text>
    <text x="80" y="68" fill="rgba(255,255,255,0.5)" font-family="sans-serif" font-size="9" text-anchor="middle">Secure WebSockets</text>
  </g>

  <!-- Connecting Path 1 -> 2 -->
  <path d="M 205 140 Q 240 140 255 140" stroke="#00f2ff" stroke-width="2" fill="none" stroke-dasharray="4, 4"/>
  <circle cx="255" cy="140" r="3" fill="#00f2ff"/>

  <!-- NODE 2: FastAPI Core App (Python, Starlette, Uvicorn) -->
  <g transform="translate(265, 75)">
    <rect width="190" height="130" rx="12" fill="rgba(42, 22, 68, 0.8)" stroke="#f000ff" stroke-width="2" filter="url(#magenta-glow)" />
    <text x="95" y="36" fill="#ffffff" font-family="sans-serif" font-size="14" font-weight="bold" text-anchor="middle">🧠 FastAPI BACKEND</text>
    <text x="95" y="60" fill="#f000ff" font-family="monospace" font-size="11" font-weight="bold" text-anchor="middle">Uvicorn &amp; Starlette</text>
    <rect x="18" y="76" width="154" height="34" rx="6" fill="rgba(10,10,15,0.4)" stroke="rgba(240,0,255,0.3)" stroke-width="1"/>
    <text x="95" y="90" fill="#00ff88" font-family="sans-serif" font-size="10" text-anchor="middle" font-weight="bold">Gemini 2.5 Flash API</text>
    <text x="95" y="102" fill="rgba(255,255,255,0.5)" font-family="sans-serif" font-size="8" text-anchor="middle">A2UI State &amp; MCP Router</text>
  </g>

  <!-- Connecting Path 2 -> 3 -->
  <path d="M 455 140 L 505 140" stroke="#f000ff" stroke-width="2" fill="none" stroke-dasharray="4, 4"/>
  <circle cx="505" cy="140" r="3" fill="#f000ff"/>

  <!-- NODE 3: Component Canvas (Web components, Mermaid, Sandbox HTML) -->
  <g transform="translate(515, 95)">
    <rect width="150" height="90" rx="10" fill="rgba(24, 30, 54, 0.7)" stroke="#00f2ff" stroke-width="1.5" filter="url(#cyan-glow)" />
    <text x="75" y="32" fill="#ffffff" font-family="sans-serif" font-size="13" font-weight="bold" text-anchor="middle">🎨 CANVAS HUD</text>
    <text x="75" y="52" fill="#00f2ff" font-family="monospace" font-size="10" text-anchor="middle">gdm-mermaid-panel</text>
    <text x="75" y="68" fill="#00ff88" font-family="monospace" font-size="10" text-anchor="middle">gdm-html-panel</text>
  </g>

  <!-- NODE 4: Connected Systems & Live Feeds (Bottom Core) -->
  <g transform="translate(180, 245)">
    <rect width="360" height="55" rx="8" fill="rgba(12, 34, 28, 0.7)" stroke="#00ff88" stroke-width="1.5" filter="url(#green-glow)"/>
    <text x="180" y="26" fill="#00ff88" font-family="monospace" font-size="11" font-weight="bold" text-anchor="middle">📡 EXTERNAL REAL-TIME INTEGRATIONS</text>
    <text x="180" y="42" fill="rgba(255,255,255,0.6)" font-family="sans-serif" font-size="9" text-anchor="middle">T212 Markets  |  OpenSky Airspace  |  Toulouse GBFS Bikes</text>
  </g>

  <!-- Connection Lines from Backend to Bottom Integrations -->
  <path d="M 360 205 L 360 245" stroke="#00ff88" stroke-width="1.5" stroke-dasharray="2, 3"/>
</svg>
"""

# --- Main Showcase Entrypoint ---
async def main():
    print_banner()
    
    async with httpx.AsyncClient(timeout=30) as client:
        # 0. Get Active Session / Space
        space = os.environ.get("MEET_SPACE_ID")
        if not space:
            print(f"  {CLR_SLATE}Scanning for active Google Meet side-panel connections...{CLR_RESET}")
            space = await get_active_space(client)
            
        if not space:
            print(f"\n{CLR_MAGENTA}❌ Error: No active Google Meet side-panel session detected.{CLR_RESET}")
            print(f"  Please open Google Meet, launch the Live Concierge add-on panel, and re-run.")
            sys.exit(1)
            
        print(f"  {CLR_GREEN}✅ Target Space Resolved:{CLR_RESET} {CLR_CYAN}{space}{CLR_RESET}")
        print(f"  {CLR_YELLOW}⚡ Fast Mode: {'ENABLED (Staccato Transitions)' if FAST_MODE else 'DISABLED (Production Timing)'}{CLR_RESET}\n")

        delay = 2.0 if FAST_MODE else 6.5
        ticks_count = 3 if FAST_MODE else 5
        tick_sleep = 0.5 if FAST_MODE else 2.0

        # ───────────────────────────────────────────────────────────
        # Phase 0: Standby Cinematic Intermission Countdown
        # ───────────────────────────────────────────────────────────
        print(f"{CLR_CYAN}🎬 [Phase 0] Launching Interactive Standby Countdown...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})
        countdown_secs = 5 if FAST_MODE else 7
        
        await post_endpoint(client, f"/api/standby/{space}", {
            "active": True,
            "duration": 0,
            "seconds": countdown_secs,
            "badge": "PINNACLE REEL WARM-UP",
            "title": "Google Meet x A2UI Cinematic Showcase",
            "description": "Orchestrating Live Mermaid.js, HTML Iframe HUDs, and Frosted Glass Takeovers"
        })
        await asyncio.sleep(float(countdown_secs))
        
        # Dismount standby
        await post_endpoint(client, f"/api/standby/{space}", {"active": False})
        await asyncio.sleep(0.3)

        # ───────────────────────────────────────────────────────────
        # Phase 1: Dual-Split Layout — Stock Telemetry & Mermaid.js Flowchart
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 1] Splitting Screen: Live Stocks & Client-Side Mermaid Flowchart...{CLR_RESET}")
        await set_transcript(
            client, space, 
            "Phase 1: Real-time telemetry paired with a client-side compiled Mermaid sequence diagram. Watch the grid adapt seamlessly to active updates.",
            label="Gemini Concierge"
        )
        await post_endpoint(client, f"/api/theme-config/{space}", {"theme": "glassmorphism"})

        mermaid_syntax = (
            "sequenceDiagram\n"
            "  autonumber\n"
            "  actor User as 👤 Voice Command\n"
            "  participant Concierge as 🤖 Concierge\n"
            "  participant T212 as 📈 212Trading\n"
            "  participant Stage as 🖥️ Main Stage\n"
            "  User->>Concierge: Speaks Order Intent\n"
            "  activate Concierge\n"
            "  Concierge->>T212: Verify NVDA Stock Price\n"
            "  T212-->>Concierge: Return Quote Price ($1,042.50)\n"
            "  Concierge->>Stage: Compile Neon Mermaid Flowchart\n"
            "  activate Stage\n"
            "  Note over Stage: Client-side CSS neon overrides injected\n"
            "  Stage-->>User: Renders Liquid Stage HUD (<100ms)\n"
            "  deactivate Stage\n"
            "  deactivate Concierge\n"
        )

        TABS_CONFIG = [
            {"id": "stk", "label": "AI MARKET"},
            {"id": "flt", "label": "FLIGHT VECTOR"},
            {"id": "re", "label": "VELO TOULOUSE"}
        ]

        stock_history = [45, 47, 46, 49, 48, 51, 50, 53, 52, 55, 54, 57, 56, 59]
        
        for tick in range(ticks_count):
            print(f"  📈 Updating Stock Telemetry (Tick {tick+1}/{ticks_count})...")
            nvda_p, nvda_c = await get_live_stock_price(client, "NVDA", 1042.50)
            goog_p, goog_c = await get_live_stock_price(client, "GOOG", 175.20)
            msft_p, msft_c = await get_live_stock_price(client, "MSFT", 432.10)
            aapl_p, aapl_c = await get_live_stock_price(client, "AAPL", 188.80)
            
            stock_history.append(int(max(10, min(95, 50 + nvda_c * 15))))
            
            await call_mcp_tool(client, "render_stage", {
                "space_id": space,
                "surfaceUpdate": {
                    "components": [
                        {
                            "id": "grid_layout",
                            "component": {
                                "gdm-stage-grid": {
                                    "layout": "split",
                                    "focusedPanel": 0,
                                    "children": {
                                        "explicitList": ["telemetry_dashboard", "mermaid_panel"]
                                    }
                                }
                            }
                        },
                        {
                            "id": "telemetry_dashboard",
                            "component": {
                                "gdm-telemetry-dashboard": {
                                    "tabs": TABS_CONFIG,
                                    "activeTabId": "stk",
                                    "title": "⚡ Megatech Stock Indices (Live Quote Feeds)",
                                    "metrics": [
                                        {"label": f"NVDA ({'+' if nvda_c >= 0 else ''}{nvda_c:.2f}%)", "value": f"${nvda_p:.2f} {'▲' if nvda_c >= 0 else '▼'}", "color": "#00ff88" if nvda_c >= 0 else "#ff3b30"},
                                        {"label": f"GOOG ({'+' if goog_c >= 0 else ''}{goog_c:.2f}%)", "value": f"${goog_p:.2f} {'▲' if goog_c >= 0 else '▼'}", "color": "#00ff88" if goog_c >= 0 else "#ff3b30"},
                                        {"label": f"MSFT ({'+' if msft_c >= 0 else ''}{msft_c:.2f}%)", "value": f"${msft_p:.2f} {'▲' if msft_c >= 0 else '▼'}", "color": "#00f2ff" if msft_c >= 0 else "#ff3b30"},
                                        {"label": f"AAPL ({'+' if aapl_c >= 0 else ''}{aapl_c:.2f}%)", "value": f"${aapl_p:.2f} {'▲' if aapl_c >= 0 else '▼'}", "color": "#00ff88" if aapl_c >= 0 else "#ff3b30"},
                                    ],
                                    "chart": stock_history[-14:]
                                }
                            }
                        },
                        {
                            "id": "mermaid_panel",
                            "component": {
                                "gdm-mermaid-panel": {
                                    "syntax": mermaid_syntax,
                                    "title": "🧜‍♀️ Live Transaction Processing Pipeline",
                                    "version": 1
                                }
                            }
                        }
                    ]
                },
                "root": "grid_layout"
            })
            await asyncio.sleep(tick_sleep)

        # Highlight Mermaid Panel
        await post_endpoint(client, f"/api/focus-panel/{space}", {"panel": 2})
        await launch_emoji_burst(client, space, ["🧜‍♀️", "⚡", "🔮"])
        await asyncio.sleep(delay)

        # ───────────────────────────────────────────────────────────
        # Phase 2: Full-Stage Glassmorphic Diagram Takeover (Overlay Mode)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 2] Projecting Fullscreen Glassmorphic Architecture Diagram Overlay...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})
        await set_transcript(
            client, space, 
            "Phase 2: Projecting the complete high-fidelity system architecture diagram as an immersive fullscreen glassmorphic overlay. Notice how the live telemetry continues running blurred behind it.",
            label="Gemini Architect"
        )
        
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {
                "components": [
                    # Retain background grid so it blurs elegantly underneath
                    {
                        "id": "grid_layout",
                        "component": {
                            "gdm-stage-grid": {
                                "layout": "split",
                                "children": {
                                    "explicitList": ["telemetry_dashboard", "mermaid_panel"]
                                }
                            }
                        }
                    },
                    {
                        "id": "telemetry_dashboard",
                        "component": {
                            "gdm-telemetry-dashboard": {
                                "tabs": TABS_CONFIG,
                                "activeTabId": "stk"
                            }
                        }
                    },
                    {
                        "id": "mermaid_panel",
                        "component": {
                            "gdm-mermaid-panel": {
                                "syntax": mermaid_syntax,
                                "title": "🧜‍♀️ Live Transaction Processing Pipeline"
                            }
                        }
                    },
                    # Overlay Component
                    {
                        "id": "architecture_overlay",
                        "component": {
                            "gdm-diagram-view": {
                                "diagId": "concierge_arch",
                                "svg": architecture_svg,
                                "version": 1,
                                "overlay": True
                            }
                        }
                    }
                ]
            },
            "root": "grid_layout"
        })
        
        await launch_emoji_burst(client, space, ["🔮", "📐", "💎"])
        await asyncio.sleep(delay + 1.5)

        # ───────────────────────────────────────────────────────────
        # Phase 3: Real-Time Airspace Vectors & Custom HTML Sandbox Table
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 3] Transitioning to OpenSky Flight Vectors & Custom HTML Latency Table...{CLR_RESET}")
        await set_transcript(
            client, space, 
            "Phase 3: Cleared the overlay. Re-splitting the stage. Left side is now tracking live commercial aircraft descent approach patterns over Toulouse blagnac airport. Right side is a fully customized latency status table running inside our isolated, custom-styled HTML sandbox.",
            label="Gemini Concierge"
        )

        html_latency_table = (
            '<style>'
            '  body { background: transparent; margin: 0; color: #fff; font-family: system-ui, -apple-system, sans-serif; }'
            '  .title-area { display: flex; justify-content: space-between; align-items: center; padding-bottom: 8px; border-bottom: 1px solid rgba(0, 242, 255, 0.25); margin-bottom: 12px; }'
            '  .title-area h3 { margin: 0; font-size: 14px; letter-spacing: 0.5px; color: #00f2ff; font-family: monospace; }'
            '  .pulse-dot { width: 8px; height: 8px; background-color: #00ff88; border-radius: 50%; box-shadow: 0 0 8px #00ff88; animation: pulse 1.8s infinite; }'
            '  @keyframes pulse { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }'
            '  table { width: 100%; border-collapse: collapse; font-size: 11px; }'
            '  th { text-align: left; padding: 8px; background: rgba(0, 242, 255, 0.06); color: #00f2ff; font-family: monospace; border-bottom: 1px solid rgba(0, 242, 255, 0.15); }'
            '  td { padding: 8px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); }'
            '  .status-badge { padding: 2px 6px; border-radius: 4px; font-size: 9px; font-weight: bold; text-transform: uppercase; }'
            '  .badge-green { background: rgba(0, 255, 136, 0.15); color: #00ff88; border: 1px solid rgba(0, 255, 136, 0.3); }'
            '  .badge-orange { background: rgba(255, 170, 0, 0.15); color: #ffaa00; border: 1px solid rgba(255, 170, 0, 0.3); }'
            '</style>'
            '<div class="title-area">'
            '  <h3>🌐 CONCIERGE SERVICE MESH STATUS</h3>'
            '  <div class="pulse-dot"></div>'
            '</div>'
            '<table>'
            '  <tr>'
            '    <th>Endpoint Service</th>'
            '    <th>RTT</th>'
            '    <th>Packet Jitter</th>'
            '    <th>Health</th>'
            '  </tr>'
            '  <tr>'
            '    <td>/ws/stage?meeting_id=meet_v2</td>'
            '    <td style="color:#00ff88; font-weight:bold;">14ms</td>'
            '    <td>1.1ms</td>'
            '    <td><span class="status-badge badge-green">Nominal</span></td>'
            '  </tr>'
            '  <tr>'
            '    <td>FastAPI /api/render-stage</td>'
            '    <td style="color:#00ff88; font-weight:bold;">38ms</td>'
            '    <td>2.4ms</td>'
            '    <td><span class="status-badge badge-green">Nominal</span></td>'
            '  </tr>'
            '  <tr>'
            '    <td>212Trading Real-Time Engine</td>'
            '    <td style="color:#00ff88; font-weight:bold;">42ms</td>'
            '    <td>3.1ms</td>'
            '    <td><span class="status-badge badge-green">Nominal</span></td>'
            '  </tr>'
            '  <tr>'
            '    <td>Vertex LLM Connector (Gemini-2.5)</td>'
            '    <td style="color:#ffaa00; font-weight:bold;">165ms</td>'
            '    <td>12.8ms</td>'
            '    <td><span class="status-badge badge-orange">Throttled</span></td>'
            '  </tr>'
            '</table>'
        )

        flight_history = [22, 25, 24, 27, 26, 29, 28, 31, 30, 33, 32, 35, 34, 37]

        # Reset focus to clean split layout
        await post_endpoint(client, f"/api/focus-panel/{space}", {"panel": 0})

        for tick in range(ticks_count):
            print(f"  ✈️ Updating Airspace Radar Telemetry (Tick {tick+1}/{ticks_count})...")
            active_flights_count, flights = await get_live_toulouse_flights(client, tick=tick)
            
            lead_alt = flights[0]["altitude"] if flights else 2000
            flight_history.append(int(max(10, min(95, lead_alt // 80 + 10))))
            
            metrics = []
            for f in flights:
                vrate = f["vrate_fpm"]
                color = "#00ff88" if vrate < -200 else ("#ffd60a" if vrate > 200 else "#00f2ff")
                metrics.append({
                    "label": f"Flight {f['callsign']}",
                    "value": f"Alt: {f['altitude']}m / Spd: {f['speed']}km/h / Vr: {vrate} fpm",
                    "color": color,
                    "data": {
                        "kind": "flight",
                        "callsign": f["callsign"],
                        "altitude": f["altitude"],
                        "speed": f["speed"],
                        "vrate": vrate,
                    }
                })
            while len(metrics) < 4:
                metrics.append({"label": "Monitoring Sector...", "value": "Scanning Radar Coordinates...", "color": "rgba(255,255,255,0.3)"})

            await call_mcp_tool(client, "render_stage", {
                "space_id": space,
                "surfaceUpdate": {
                    "components": [
                        {
                            "id": "grid_layout",
                            "component": {
                                "gdm-stage-grid": {
                                    "layout": "split",
                                    "children": {
                                        "explicitList": ["telemetry_dashboard", "html_panel"]
                                    }
                                }
                            }
                        },
                        {
                            "id": "telemetry_dashboard",
                            "component": {
                                "gdm-telemetry-dashboard": {
                                    "tabs": TABS_CONFIG,
                                    "activeTabId": "flt",
                                    "title": f"✈️ Live TLS Radar Vectors — Planes Sensed: {active_flights_count}",
                                    "metrics": metrics,
                                    "chart": flight_history[-14:]
                                }
                            }
                        },
                        {
                            "id": "html_panel",
                            "component": {
                                "gdm-html-panel": {
                                    "html": html_latency_table,
                                    "title": "🌐 Network Latency Node Map",
                                    "version": tick + 1,
                                    "overlay": False
                                }
                            }
                        }
                    ]
                },
                "root": "grid_layout"
            })
            await asyncio.sleep(tick_sleep)

        await post_endpoint(client, f"/api/focus-panel/{space}", {"panel": 2})
        await launch_emoji_burst(client, space, ["✈️", "🌐", "⚡"])
        await asyncio.sleep(delay)

        # ───────────────────────────────────────────────────────────
        # Phase 4: Full-Stage Immersive Executive KPI HUD Takeover (HTML Overlay Mode)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 4] Launching Fullscreen Glassmorphic Executive KPI HUD...{CLR_RESET}")
        await set_transcript(
            client, space, 
            "Phase 4: Expanding our isolated HTML panel into a fullscreen glassmorphic takeover. Highly customized HUD controls, charts, and metrics can float seamlessly above our active Meet call grid.",
            label="Gemini Architect"
        )

        html_hud_overlay = (
            '<style>'
            '  body { background: transparent; margin: 0; color: #fff; font-family: system-ui, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; }'
            '  .hud-container { width: 550px; background: rgba(8, 12, 28, 0.85); backdrop-filter: blur(12px); border: 2px solid #f000ff; border-radius: 16px; padding: 24px; box-shadow: 0 0 25px rgba(240, 0, 255, 0.4); text-align: center; }'
            '  h1 { font-family: monospace; font-size: 26px; color: #f000ff; margin: 0 0 10px 0; text-shadow: 0 0 10px rgba(240, 0, 255, 0.5); letter-spacing: 1px; }'
            '  p { font-size: 13px; color: rgba(255,255,255,0.7); margin: 0 0 24px 0; }'
            '  .kpi-row { display: flex; justify-content: space-around; gap: 16px; margin-bottom: 20px; }'
            '  .kpi-card { flex: 1; background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(0, 242, 255, 0.25); border-radius: 12px; padding: 14px 8px; text-align: center; box-shadow: inset 0 0 10px rgba(0, 242, 255, 0.05); }'
            '  .kpi-card h4 { font-size: 24px; margin: 0; font-family: monospace; color: #00ff88; }'
            '  .kpi-card.cyan h4 { color: #00f2ff; }'
            '  .kpi-card.orange h4 { color: #ffaa00; }'
            '  .kpi-card span { font-size: 9px; color: rgba(255,255,255,0.55); text-transform: uppercase; font-weight: bold; letter-spacing: 0.5px; }'
            '  .sys-badge { background: rgba(240, 0, 255, 0.15); border: 1px solid rgba(240, 0, 255, 0.3); padding: 6px 12px; border-radius: 6px; font-family: monospace; font-size: 10px; color: #f000ff; display: inline-block; letter-spacing: 0.5px; }'
            '</style>'
            '<div class="hud-container">'
            '  <h1>🚀 EXECUTIVE MISSION CONTROL HUD</h1>'
            '  <p>Immersive glassmorphic takeovers rendering customizable HTML5 layouts instantly on the Main Stage.</p>'
            '  <div class="kpi-row">'
            '    <div class="kpi-card">'
            '      <h4>99.98%</h4>'
            '      <span>SYSTEM HEALTH</span>'
            '    </div>'
            '    <div class="kpi-card cyan">'
            '      <h4>582 rps</h4>'
            '      <span>API THROUGHPUT</span>'
            '    </div>'
            '    <div class="kpi-card orange">'
            '      <h4>1,242</h4>'
            '      <span>ACTIVE USER NODES</span>'
            '    </div>'
            '  </div>'
            '  <div class="sys-badge">ACTIVE SHIELD STATE: SECURED</div>'
            '</div>'
        )

        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {
                "components": [
                    {
                        "id": "grid_layout",
                        "component": {
                            "gdm-stage-grid": {
                                "layout": "split",
                                "children": {
                                    "explicitList": ["telemetry_dashboard", "html_panel"]
                                }
                            }
                        }
                    },
                    {
                        "id": "telemetry_dashboard",
                        "component": {
                            "gdm-telemetry-dashboard": {
                                "tabs": TABS_CONFIG,
                                "activeTabId": "flt"
                            }
                        }
                    },
                    {
                        "id": "html_panel",
                        "component": {
                            "gdm-html-panel": {
                                "html": html_hud_overlay,
                                "title": "🚀 Mission Control Console",
                                "version": 20,
                                "overlay": True
                            }
                        }
                    }
                ]
            },
            "root": "grid_layout"
        })

        await launch_emoji_burst(client, space, ["🚀", "🔥", "🤩"])
        await asyncio.sleep(delay + 1.5)

        # ───────────────────────────────────────────────────────────
        # Phase 5: Concluding Reset & Animated Reaction Storm
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 5] Resetting Stage and Triggering Celebration Storm...{CLR_RESET}")
        await set_transcript(
            client, space, 
            "Phase 5: Concluding our Pinnacle Showcase. Restoring the Google Meet Main Stage layout back to default standby mode.",
            label="Gemini Concierge"
        )
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})

        # Clear active overlays
        await call_mcp_tool(client, "clear_stage", {"space_id": space})
        await asyncio.sleep(0.5)

        # Trigger quick simulated chats representing feedback
        chat_reaction_stream = [
            ("Librarian AI", "Incredible! Client-side compiled Mermaidsequence flows are absolute magic 🧜‍♀️"),
            ("Antoine — Dev", "Custom CSS scrollbars in the isolated HTML frame look super clean. Great visual fidelity! 💻"),
            ("Priya — Product", "The glassmorphic architectural diagram takeover overlay is stunning. Full marks on design! 🌌"),
            ("Sofia — Investor", "Airspace vectors tracking physical planes over Blagnac airport in real-time is next-level ✈️"),
            ("Dana K.", "/mainstage Those neon glow filters on the floating takeovers are spectacular! 🚀")
        ]

        comment_sleep = 0.5 if FAST_MODE else 1.8
        for idx, (user, chat_msg) in enumerate(chat_reaction_stream):
            print(f"  💬 Broadcasting chat from: {user}")
            await broadcast_chat_comment(client, space, user, chat_msg)
            if idx in (1, 3):
                await launch_emoji_burst(client, space, ["👏", "💯"])
            await asyncio.sleep(comment_sleep)

        # Final massive celebration sound & emoji storm
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "applause"})
        await launch_emoji_burst(client, space, ["🎉", "💯", "🚀", "✨", "🔥", "🤩", "👏", "👑", "🌌", "💎"])
        
    print(f"\n{CLR_GREEN}🎉 Pinnacle Cinematic Showcase script executed successfully!{CLR_RESET}\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{CLR_MAGENTA}Showcase interrupted by user.{CLR_RESET}")
        sys.exit(0)
