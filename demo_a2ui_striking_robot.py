#!/usr/bin/env python3
"""
Meet Live Concierge — Cinematic AI Robot Host Demonstration Stage (A2UI v0.8)
=============================================================================
Orchestrates an ultra-premium, multi-phase demonstration of our Google Meet Main Stage.
Nexus, our autonomous AI robot host, guides the audience through the stage's 
visual features using scrolling tickers, lower-third chyrons, synchronized subtitle
captions, dynamic grid layouts, live D2 diagrams, and interactive audience polls.

Phases:
0. Setup & Stage Warm-up (5s Standby Countdown + Laser Sweep)
1. Welcome & Introduction by Nexus (Split Layout with Video / Image fallback)
2. Live Architecture Explainer (Direct D2 SVG rendering side-by-side with Nexus)
3. Fullscreen Glassmorphic Diagram Takeover (Frosted Glass Overlay + Emoji Burst)
4. Interactive Audience Engagement (Real-time Sliding Poll voting tally)
5. Control Center & Tech Telemetry (Futuristic Neon HTML Iframe Dashboard HUD)
6. Celebration Storm & Audience Feedback (Beeps, Applause, Chat feed reactions)

Features:
- Dynamic top scrolling stock & telemetry ticker band (gdm-ticker)
- Sliding lower-third credit chyrons (gdm-chyron)
- Cinematic movie-style translucent bottom caption overlays (gdm-captions)
- Seamless fallbacks from MP4 video to high-fidelity static images of Nexus
- Live stock indices (Yahoo Finance fallback + 212Trading support)
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
    print(f"⚠️ Could not load 212Trading backend market services: {e}. Using Yahoo Finance fallback.", file=sys.stderr)

# --- Configuration & Environment Setup ---
API_URL = os.environ.get("CONCIERGE_API_URL", "CONCIERGE_API_URL_PLACEHOLDER")
KEY = os.environ.get("STAGE_API_KEY", "meet-live_STAGE_SECURE_v1_zG9fN8qL7vP2mX6tY9wK4jC5bS8xQ7hZ3uW0rA")
FAST_MODE = os.environ.get("FAST_MODE", "false").lower() not in ("0", "false", "no")

# --- ANSI Terminal Colors for Premium Logging ---
CLR_CYAN = "\033[38;5;51m"
CLR_MAGENTA = "\033[38;5;201m"
CLR_GREEN = "\033[38;5;82m"
CLR_YELLOW = "\033[38;5;220m"
CLR_SLATE = "\033[38;5;244m"
CLR_RESET = "\033[0m"

def print_banner():
    print(f"\n{CLR_CYAN}  ==============================================================={CLR_RESET}")
    print(f"{CLR_CYAN}  ▲   C I N E M A T I C   A I   R O B O T   H O S T   D E M O   ▲{CLR_RESET}")
    print(f"{CLR_CYAN}  ==============================================================={CLR_RESET}")
    print(f"  {CLR_SLATE}Features: Ticker Band, Sliding Chyrons, Subtitle Captions, & Interaction{CLR_RESET}")
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
        "id": "robot-showcase-mcp",
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
            print(f"  {CLR_GREEN}⚡ [MCP Tool] {txt}{CLR_RESET}")
    except Exception as e:
        print(f"  {CLR_MAGENTA}❌ MCP Call Failed to {tool_name}: {e}{CLR_RESET}", file=sys.stderr)

async def launch_emoji_burst(client: httpx.AsyncClient, space_id: str, emojis: list[str]):
    for emo in emojis:
        await post_endpoint(client, f"/api/emoji/{space_id}", {"emoji": emo})
        await asyncio.sleep(0.12)

async def broadcast_chat_comment(client: httpx.AsyncClient, space_id: str, sender: str, text: str):
    await post_endpoint(client, f"/api/chat/{space_id}", {
        "sender": sender,
        "text": text,
        "avatar": ""
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
            pass
            
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
    return default, random.uniform(-1.0, 2.5)

# --- Spoken Narration Caption Sync Helper ---
async def speak_narrator_caption(client: httpx.AsyncClient, space_id: str, root_id: str, text: str, delay_seconds: float = 4.0):
    """
    Submits a gorgeous translucent caption pill overlay (gdm-captions) on the stage.
    Simulates speech by splitting lines and keeping them active.
    """
    print(f"  🎙️ [Nexus Speech] \"{text}\"")
    
    # Send gdm-captions overlay component inside the stage update
    await call_mcp_tool(client, "render_stage", {
        "space_id": space_id,
        "surfaceUpdate": {
            "components": [
                {
                    "id": "live_captions_overlay",
                    "component": {
                        "gdm-captions": {
                            "text": text,
                            "speaker": "NEXUS // CONCIERGE HOST",
                            "active": True,
                            "accentColor": "#00f2ff"
                        }
                    }
                }
            ]
        },
        "root": root_id
    })
    await asyncio.sleep(delay_seconds)

async def clear_captions_overlay(client: httpx.AsyncClient, space_id: str, root_id: str):
    await call_mcp_tool(client, "render_stage", {
        "space_id": space_id,
        "surfaceUpdate": {
            "components": [
                {
                    "id": "live_captions_overlay",
                    "component": {
                        "gdm-captions": {
                            "active": False,
                            "text": ""
                        }
                    }
                }
            ]
        },
        "root": root_id
    })

# --- Premium Cyberpunk SVG System Diagram Code ---
architecture_svg = """<svg viewBox="0 0 700 350" xmlns="http://www.w3.org/2000/svg">
  <defs>
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

  <rect width="100%" height="100%" rx="18" fill="rgba(10, 12, 28, 0.95)" stroke="#00f2ff" stroke-width="2"/>
  
  <pattern id="dot-pattern" width="24" height="24" patternUnits="userSpaceOnUse">
    <circle cx="2" cy="2" r="1.2" fill="rgba(0, 242, 255, 0.08)"/>
  </pattern>
  <rect width="100%" height="100%" rx="18" fill="url(#dot-pattern)"/>

  <text x="30" y="40" fill="#00f2ff" font-family="monospace" font-size="12" font-weight="bold">CONCIERGE REAL-TIME ROUTING MESH // V2.5</text>
  <line x1="30" y1="48" x2="350" y2="48" stroke="rgba(0, 242, 255, 0.3)" stroke-width="1.5"/>

  <!-- NODE 1: User Voice & Client -->
  <g transform="translate(45, 95)">
    <rect width="160" height="90" rx="10" fill="rgba(24, 30, 54, 0.7)" stroke="#00f2ff" stroke-width="1.5" filter="url(#cyan-glow)" />
    <text x="80" y="32" fill="#ffffff" font-family="sans-serif" font-size="13" font-weight="bold" text-anchor="middle">🎙️ CLIENT STAGE</text>
    <text x="80" y="52" fill="#00f2ff" font-family="monospace" font-size="10" text-anchor="middle">Lit &amp; Web Components</text>
    <text x="80" y="68" fill="rgba(255,255,255,0.5)" font-family="sans-serif" font-size="9" text-anchor="middle">Secure WebSockets</text>
  </g>

  <!-- Connecting Path 1 -> 2 -->
  <path d="M 205 140 L 255 140" stroke="#00f2ff" stroke-width="2" fill="none" stroke-dasharray="4, 4"/>
  <circle cx="255" cy="140" r="3" fill="#00f2ff"/>

  <!-- NODE 2: FastAPI Core App -->
  <g transform="translate(265, 75)">
    <rect width="190" height="130" rx="12" fill="rgba(42, 22, 68, 0.8)" stroke="#f000ff" stroke-width="2" filter="url(#magenta-glow)" />
    <text x="95" y="36" fill="#ffffff" font-family="sans-serif" font-size="14" font-weight="bold" text-anchor="middle">🧠 FastAPI CORE App</text>
    <text x="95" y="60" fill="#f000ff" font-family="monospace" font-size="11" font-weight="bold" text-anchor="middle">Uvicorn &amp; WS Router</text>
    <rect x="18" y="76" width="154" height="34" rx="6" fill="rgba(10,10,15,0.4)" stroke="rgba(240,0,255,0.3)" stroke-width="1"/>
    <text x="95" y="90" fill="#00ff88" font-family="sans-serif" font-size="10" text-anchor="middle" font-weight="bold">Gemini 2.5 Flash LLM</text>
    <text x="95" y="102" fill="rgba(255,255,255,0.5)" font-family="sans-serif" font-size="8" text-anchor="middle">A2UI Declarative Compiler</text>
  </g>

  <!-- Connecting Path 2 -> 3 -->
  <path d="M 455 140 L 505 140" stroke="#f000ff" stroke-width="2" fill="none" stroke-dasharray="4, 4"/>
  <circle cx="505" cy="140" r="3" fill="#f000ff"/>

  <!-- NODE 3: Component Canvas -->
  <g transform="translate(515, 95)">
    <rect width="150" height="90" rx="10" fill="rgba(24, 30, 54, 0.7)" stroke="#00f2ff" stroke-width="1.5" filter="url(#cyan-glow)" />
    <text x="75" y="32" fill="#ffffff" font-family="sans-serif" font-size="13" font-weight="bold" text-anchor="middle">🎨 CANVAS HUD</text>
    <text x="75" y="52" fill="#00f2ff" font-family="monospace" font-size="10" text-anchor="middle">gdm-ticker &amp; chyrons</text>
    <text x="75" y="68" fill="#00ff88" font-family="monospace" font-size="10" text-anchor="middle">gdm-captions</text>
  </g>

  <!-- NODE 4: Connected Systems & Live Feeds -->
  <g transform="translate(180, 245)">
    <rect width="360" height="55" rx="8" fill="rgba(12, 34, 28, 0.7)" stroke="#00ff88" stroke-width="1.5" filter="url(#green-glow)"/>
    <text x="180" y="26" fill="#00ff88" font-family="monospace" font-size="11" font-weight="bold" text-anchor="middle">📡 EXTERNAL REAL-TIME INTEGRATIONS</text>
    <text x="180" y="42" fill="rgba(255,255,255,0.6)" font-family="sans-serif" font-size="9" text-anchor="middle">212Trading Markets  |  Live Ticker Scrollers  |  Interactive Polls</text>
  </g>

  <!-- Connection Lines from Backend to Bottom Integrations -->
  <path d="M 360 205 L 360 245" stroke="#00ff88" stroke-width="1.5" stroke-dasharray="2, 3"/>
</svg>
"""

# --- Main Cinematic Showcase Run ---
async def main():
    print_banner()
    
    # 1. Initialize HTTP Client
    async with httpx.AsyncClient(timeout=30) as client:
        
        # 2. Get Space ID
        space = os.environ.get("MEET_SPACE_ID")
        if not space:
            print(f"  {CLR_SLATE}Detecting active Google Meet side-panel staging session...{CLR_RESET}")
            space = await get_active_space(client)
            
        if not space or space == "default":
            print(f"\n{CLR_MAGENTA}❌ Error: No active Google Meet side-panel session detected.{CLR_RESET}")
            print(f"  Please open Google Meet, launch the Live Concierge add-on panel, and re-run.")
            sys.exit(1)
            
        print(f"  {CLR_GREEN}✅ Target Space Resolved:{CLR_RESET} {CLR_CYAN}{space}{CLR_RESET}")
        print(f"  {CLR_YELLOW}⚡ Warm-up beginning in 1.5 seconds...{CLR_RESET}\n")
        await asyncio.sleep(1.5)

        # Base pacing durations
        t_base = 5.0 if FAST_MODE else 9.0
        t_short = 2.0 if FAST_MODE else 4.0

        # ───────────────────────────────────────────────────────────
        # Phase 0: Standby Cinematic Intermission Countdown (Setup)
        # ───────────────────────────────────────────────────────────
        print(f"{CLR_CYAN}🎬 [Phase 0] Setup & Stage Warm-up (5s Intermission Slate)...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})
        
        # Deploy high-fidelity standby slate count down
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {
                "components": [
                    {
                        "id": "countdown_slate",
                        "component": {
                            "gdm-standby-slate": {
                                "badge": "CINEMATIC SHOWCASE PREPARATION",
                                "title": "Google Meet x A2UI Cinematic Stage",
                                "description": "Nexus, the autonomous AI Robot, is taking over the stage. Synced with real-time stock tickers, lower-third chyrons, and interactive voting overlays.",
                                "seconds": 5,
                                "active": True
                            }
                        }
                    }
                ]
            },
            "root": "countdown_slate"
        })
        await asyncio.sleep(5.0)
        
        # Clear countdown slate
        await call_mcp_tool(client, "clear_stage", {"space_id": space})
        await asyncio.sleep(0.5)

        # ───────────────────────────────────────────────────────────
        # Phase 1: Welcome & Introductions by AI Host Nexus (Split Grid)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 1] Splitting Screen: Welcome & Intro by AI Host Nexus...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})
        await post_endpoint(client, f"/api/theme-config/{space}", {"theme": "glassmorphism"})
        
        # Try to locate the local video file. If not generated yet, it will fallback to the image perfectly.
        # Video component accepts direct paths relative to public.
        video_src_intro = "/public/robot_video_intro.mp4"
        image_src_fallback = "/public/robot_news_anchor.png"
        
        # Determine if video file is physically there, else display the static image fallback.
        # Since Lit components render image fallback natively if video src fails or we use image-panel:
        # We will use image-panel with robot_news_anchor.png since it is beautiful, and falls back gracefully.
        video_exists = os.path.exists(os.path.join(_base_dir, "public", "robot_video_intro.mp4"))
        nexus_panel_id = "nexus_intro_panel"
        
        if video_exists:
            print(f"  {CLR_GREEN}🎥 Found intro video! Using direct video stream...{CLR_RESET}")
            nexus_component = {
                "id": nexus_panel_id,
                "component": {
                    "gdm-video-panel": {
                        "src": video_src_intro,
                        "autoplay": True,
                        "panel": 1
                    }
                }
            }
        else:
            print(f"  {CLR_SLATE}⚠️ Video '/public/robot_video_intro.mp4' not found. Falling back to high-fidelity static image of Nexus...{CLR_RESET}")
            nexus_component = {
                "id": nexus_panel_id,
                "component": {
                    "gdm-image-panel": {
                        "src": image_src_fallback,
                        "label": "🤖 NEXUS COGNITIVE CORE",
                        "panel": 1
                    }
                }
            }

        # Build Phase 1 initial grid components
        ticker_text_p1 = "NEXUS NARRATOR ACTIVE • HIGH-FIDELITY WEB COMPONENTS ENGAGED • WEBSOCKET STATUS: ONLINE • "
        ticker_component = {
            "id": "top_stage_ticker",
            "component": {
                "gdm-ticker": {
                    "text": ticker_text_p1,
                    "active": True,
                    "badgeText": "NEXUS LIVE",
                    "badgeColor": "#00f2ff",
                    "scrollSpeed": 35,
                    "height": 56
                }
            }
        }
        
        chyron_p1 = {
            "id": "presenter_chyron",
            "component": {
                "gdm-chyron": {
                    "title": "NEXUS AI CONCIERGE",
                    "subtitle": "Your Autonomous Stage Host",
                    "active": True,
                    "accentColor": "#ff007f",
                    "bottom": 56,
                    "left": 40
                }
            }
        }

        # Render Phase 1 split stage initial view
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {
                "components": [
                    {
                        "id": "p1_split_grid",
                        "component": {
                            "gdm-stage-grid": {
                                "layout": "split",
                                "focusedPanel": 0,
                                "children": {
                                    "explicitList": [nexus_panel_id, "p1_blueprint_panel"]
                                }
                            }
                        }
                    },
                    nexus_component,
                    {
                        "id": "p1_blueprint_panel",
                        "component": {
                            "gdm-image-panel": {
                                "src": "/public/workspace_sketch.png",
                                "label": "📐 Workspace Drafting Board",
                                "panel": 2
                            }
                        }
                    },
                    ticker_component,
                    chyron_p1
                ]
            },
            "root": "p1_split_grid"
        })
        
        # Speaches streaming synced with caption overlay
        await speak_narrator_caption(
            client, space, "p1_split_grid", 
            "Hello and welcome to Google Meet Main Stage! I am Nexus, your autonomous robot host.", 
            delay_seconds=t_short
        )
        await speak_narrator_caption(
            client, space, "p1_split_grid", 
            "Today, I am taking you through our ultra-premium A2UI custom-rendered layout engine.", 
            delay_seconds=t_short
        )
        await speak_narrator_caption(
            client, space, "p1_split_grid", 
            "Notice how the top stock ticker and lower third captions render seamlessly over active Workspace streams!", 
            delay_seconds=t_base
        )
        
        # Turn off Phase 1 presenter chyron
        chyron_p1_off = {
            "id": "presenter_chyron",
            "component": {"gdm-chyron": {"active": False, "title": "", "subtitle": ""}}
        }
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {"components": [chyron_p1_off]},
            "root": "p1_split_grid"
        })

        # ───────────────────────────────────────────────────────────
        # Phase 2: Technical Architecture Explainer (Split Grid + D2 Diagram)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 2] Technical Architecture Explainer (Nexus + Dynamic D2 Diagram)...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})
        
        video_src_tech = "/public/robot_video_tech.mp4"
        video_tech_exists = os.path.exists(os.path.join(_base_dir, "public", "robot_video_tech.mp4"))
        nexus_p2_id = "nexus_tech_panel"
        
        if video_tech_exists:
            print(f"  {CLR_GREEN}🎥 Found tech video! Streaming...{CLR_RESET}")
            nexus_component_p2 = {
                "id": nexus_p2_id,
                "component": {
                    "gdm-video-panel": {
                        "src": video_src_tech,
                        "autoplay": True,
                        "panel": 1
                    }
                }
            }
        else:
            nexus_component_p2 = {
                "id": nexus_p2_id,
                "component": {
                    "gdm-image-panel": {
                        "src": image_src_fallback,
                        "label": "🤖 NEXUS SYSTEM LECTURE",
                        "panel": 1
                    }
                }
            }

        chyron_p2 = {
            "id": "tech_chyron",
            "component": {
                "gdm-chyron": {
                    "title": "WEBSOCKET SERVICE MESH",
                    "subtitle": "High-Frequency Component Exchange Pipeline",
                    "active": True,
                    "accentColor": "#00ff88",
                    "bottom": 56,
                    "left": 40
                }
            }
        }
        
        ticker_text_p2 = "COMPILING D2 SCHEMATIC SOURCE... PARSING REAL-TIME WEBSOCKET COMMUNICATOR... PORT 8000 OPEN... "
        ticker_component["component"]["gdm-ticker"]["text"] = ticker_text_p2
        ticker_component["component"]["gdm-ticker"]["badgeText"] = "COMPILE ACTIVE"
        ticker_component["component"]["gdm-ticker"]["badgeColor"] = "#00ff88"

        # Render Phase 2 split stage with Nexus lecture and D2 Mermaid / Diagram panel
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {
                "components": [
                    {
                        "id": "p2_split_grid",
                        "component": {
                            "gdm-stage-grid": {
                                "layout": "split",
                                "focusedPanel": 2,
                                "children": {
                                    "explicitList": [nexus_p2_id, "p2_d2_panel"]
                                }
                            }
                        }
                    },
                    nexus_component_p2,
                    {
                        "id": "p2_d2_panel",
                        "component": {
                            "gdm-diagram-view": {
                                "diagId": "system_diagram_mesh",
                                "svg": architecture_svg,
                                "version": 1,
                                "overlay": False,
                                "panel": 2
                            }
                        }
                    },
                    ticker_component,
                    chyron_p2
                ]
            },
            "root": "p2_split_grid"
        })

        await speak_narrator_caption(
            client, space, "p2_split_grid", 
            "Let's dive into how it works under the hood.", 
            delay_seconds=t_short
        )
        await speak_narrator_caption(
            client, space, "p2_split_grid", 
            "As you see on the right, the client connects to our FastAPI backend using high-frequency, bidirectional WebSockets.", 
            delay_seconds=t_base
        )
        await speak_narrator_caption(
            client, space, "p2_split_grid", 
            "A2UI translates declarative components into rich, GPU-accelerated HTML, CSS, and SVG components in less than 100 milliseconds!", 
            delay_seconds=t_base
        )

        # Laser sweep scan effect
        print(f"  {CLR_YELLOW}⚡ Triggering cyber laser-sweep scanning on diagram...{CLR_RESET}")
        laser_scan_component = {
            "id": "laser_sweep_diagram",
            "component": {
                "gdm-laser-sweep": {
                    "active": True,
                    "duration": 2.5,
                    "sweeps": 2,
                    "color": "#00ff88"
                }
            }
        }
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {"components": [laser_scan_component]},
            "root": "p2_split_grid"
        })
        await asyncio.sleep(3.0)

        # Deactivate Phase 2 chyron
        chyron_p2_off = {
            "id": "tech_chyron",
            "component": {"gdm-chyron": {"active": False, "title": "", "subtitle": ""}}
        }
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {"components": [chyron_p2_off]},
            "root": "p2_split_grid"
        })

        # ───────────────────────────────────────────────────────────
        # Phase 3: Immersive Glassmorphic Diagram Takeover (Overlay Mode)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 3] Full-Stage Immersive Glassmorphic Diagram Takeover (Overlay)...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})
        
        chyron_p3 = {
            "id": "takeover_chyron",
            "component": {
                "gdm-chyron": {
                    "title": "IMMERSIVE PRESENTATION MODE",
                    "subtitle": "Full-Stage Glassmorphic Diagram Overlay Active",
                    "active": True,
                    "accentColor": "#ff00d6",
                    "bottom": 56,
                    "left": 40
                }
            }
        }
        
        ticker_text_p3 = "IMMERSIVE TAKEOVER IN PROCESS (BACKDROP-FILTER: BLUR)... LIVE ARCHITECTURE OVERLAY LOADED... "
        ticker_component["component"]["gdm-ticker"]["text"] = ticker_text_p3
        ticker_component["component"]["gdm-ticker"]["badgeText"] = "OVERLAY ENGAGED"
        ticker_component["component"]["gdm-ticker"]["badgeColor"] = "#ff00d6"

        # Apply overlay. The A2UI Engine discovers components with overlay=True
        # and displays them floating beautifully over the active grid.
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {
                "components": [
                    # Retain background grid so it blurs elegantly underneath
                    {
                        "id": "p2_split_grid",
                        "component": {
                            "gdm-stage-grid": {
                                "layout": "split",
                                "children": {
                                    "explicitList": [nexus_p2_id, "p2_d2_panel"]
                                }
                            }
                        }
                    },
                    # Overlay Component Takeover
                    {
                        "id": "full_diagram_overlay",
                        "component": {
                            "gdm-diagram-view": {
                                "diagId": "system_diagram_mesh",
                                "svg": architecture_svg,
                                "version": 2,
                                "overlay": True
                            }
                        }
                    },
                    ticker_component,
                    chyron_p3
                ]
            },
            "root": "p2_split_grid"
        })

        await speak_narrator_caption(
            client, space, "p2_split_grid", 
            "Now, watch this. With a single layout update, we can project the architecture diagram as a full-screen, glassmorphic overlay!", 
            delay_seconds=t_base
        )
        await speak_narrator_caption(
            client, space, "p2_split_grid", 
            "The background elements are blurred elegantly behind, giving an extremely premium, cinematic presentation feel. This is perfect for slide deck talks!", 
            delay_seconds=t_base
        )

        # Trigger reaction burst
        await launch_emoji_burst(client, space, ["📐", "💎", "🚀"])
        await asyncio.sleep(2.0)

        # Turn off takeover chyron & clear overlay
        chyron_p3_off = {
            "id": "takeover_chyron",
            "component": {"gdm-chyron": {"active": False, "title": "", "subtitle": ""}}
        }
        clear_diagram_overlay = {
            "id": "full_diagram_overlay",
            "component": {
                "gdm-diagram-view": {
                    "overlay": False,
                    "active": False
                }
            }
        }
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {"components": [chyron_p3_off, clear_diagram_overlay]},
            "root": "p2_split_grid"
        })
        await asyncio.sleep(1.0)

        # ───────────────────────────────────────────────────────────
        # Phase 4: Interactive Audience Engagement (Real-Time Sliding Poll)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 4] Audience Engagement (Sliding Poll Overlay + Live Tally)...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})

        chyron_p4 = {
            "id": "poll_chyron",
            "component": {
                "gdm-chyron": {
                    "title": "COLLABORATOR ENGAGEMENT",
                    "subtitle": "Interactive Multi-Choice Real-time Poll Tally",
                    "active": True,
                    "accentColor": "#ffd60a",
                    "bottom": 56,
                    "left": 40
                }
            }
        }
        
        ticker_text_p4 = "AUDIENCE POLL LAUNCHED... ACCUMULATING VOTES IN REAL-TIME... DYNAMIC PROGRESS BARS RENDERING... "
        ticker_component["component"]["gdm-ticker"]["text"] = ticker_text_p4
        ticker_component["component"]["gdm-ticker"]["badgeText"] = "POLL LAUNCHED"
        ticker_component["component"]["gdm-ticker"]["badgeColor"] = "#ffd60a"

        # Tally vote animation loops
        votes_stages = [
            [4, 2, 6, 3],
            [12, 7, 18, 10],
            [28, 14, 38, 22],
            [54, 23, 72, 45]
        ]

        await speak_narrator_caption(
            client, space, "p2_split_grid", 
            "Interaction is key to retention. Let's fire a live audience poll directly on stage!", 
            delay_seconds=t_short
        )

        for step, current_votes in enumerate(votes_stages):
            print(f"  🗳️ Simulating Real-time Poll Votes (Step {step+1}/4): {current_votes}...")
            
            poll_overlay = {
                "id": "interactive_voting_poll",
                "component": {
                    "gdm-poll-overlay": {
                        "question": "Which A2UI element feels most premium? 🗳️",
                        "options": [
                            "1️⃣ Glassmorphic Overlays",
                            "2️⃣ Multi-split Video Grids",
                            "3️⃣ Real-time Scrolling Ticker",
                            "4️⃣ Clientcompiled Diagram Panels"
                        ],
                        "values": current_votes,
                        "layout": "rows",
                        "active": True
                    }
                }
            }

            await call_mcp_tool(client, "render_stage", {
                "space_id": space,
                "surfaceUpdate": {
                    "components": [
                        {
                            "id": "p2_split_grid",
                            "component": {
                                "gdm-stage-grid": {
                                    "layout": "split",
                                    "children": {
                                        "explicitList": [nexus_p2_id, "p2_d2_panel"]
                                    }
                                }
                            }
                        },
                        poll_overlay,
                        ticker_component,
                        chyron_p4
                    ]
                },
                "root": "p2_split_grid"
            })
            
            if step == 0:
                await speak_narrator_caption(
                    client, space, "p2_split_grid", 
                    "As meeting attendees tap their screens, the voting bars expand dynamically in real-time right on the stage!", 
                    delay_seconds=3.0
                )
            else:
                await asyncio.sleep(2.0)

        await speak_narrator_caption(
            client, space, "p2_split_grid", 
            "The top scroller ticker and chyrons rearrange spacing instantly to keep everything crisp and readable.", 
            delay_seconds=t_short
        )

        # Deactivate poll and chyron
        chyron_p4_off = {
            "id": "poll_chyron",
            "component": {"gdm-chyron": {"active": False, "title": "", "subtitle": ""}}
        }
        poll_overlay_off = {
            "id": "interactive_voting_poll",
            "component": {"gdm-poll-overlay": {"active": False}}
        }
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {"components": [chyron_p4_off, poll_overlay_off]},
            "root": "p2_split_grid"
        })
        await asyncio.sleep(1.0)

        # ───────────────────────────────────────────────────────────
        # Phase 5: Control Center & Telemetry HUD (Custom HTML Sandbox)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 5] Transitioning to Custom Neon HTML Iframe Dashboard HUD...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})
        
        chyron_p5 = {
            "id": "hud_chyron",
            "component": {
                "gdm-chyron": {
                    "title": "ISOLATED HTML SANDBOX",
                    "subtitle": "Futuristic Neon Server Operations Console HUD",
                    "active": True,
                    "accentColor": "#00f2ff",
                    "bottom": 56,
                    "left": 40
                }
            }
        }

        ticker_text_p5 = "MAPPING FLIGHT RADAR APPROACH DESCENT VECTOR... RENDERING GLASSMORPHIC KPI DATA TILES... "
        ticker_component["component"]["gdm-ticker"]["text"] = ticker_text_p5
        ticker_component["component"]["gdm-ticker"]["badgeText"] = "MESH CONTROL"
        ticker_component["component"]["gdm-ticker"]["badgeColor"] = "#00f2ff"

        html_hud_content = (
            '<style>'
            '  body { background: transparent; margin: 0; color: #fff; font-family: system-ui, -apple-system, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; overflow:hidden; }'
            '  .hud-container { width: 90%; max-width: 480px; background: rgba(8, 12, 28, 0.88); backdrop-filter: blur(14px); border: 2px solid #00f2ff; border-radius: 16px; padding: 20px; box-shadow: 0 0 30px rgba(0, 242, 255, 0.35); text-align: center; }'
            '  h1 { font-family: monospace; font-size: 20px; color: #00f2ff; margin: 0 0 4px 0; text-shadow: 0 0 10px rgba(0, 242, 255, 0.5); letter-spacing: 1px; }'
            '  p { font-size: 11px; color: rgba(255,255,255,0.65); margin: 0 0 16px 0; }'
            '  .kpi-row { display: flex; justify-content: space-around; gap: 12px; margin-bottom: 16px; }'
            '  .kpi-card { flex: 1; background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(0, 242, 255, 0.25); border-radius: 10px; padding: 10px 4px; text-align: center; box-shadow: inset 0 0 8px rgba(0, 242, 255, 0.05); }'
            '  .kpi-card h4 { font-size: 18px; margin: 0; font-family: monospace; color: #00ff88; text-shadow: 0 0 4px rgba(0,255,136,0.3); }'
            '  .kpi-card.cyan h4 { color: #00f2ff; text-shadow: 0 0 4px rgba(0,242,255,0.3); }'
            '  .kpi-card.orange h4 { color: #ffaa00; text-shadow: 0 0 4px rgba(255,170,0,0.3); }'
            '  .kpi-card span { font-size: 8px; color: rgba(255,255,255,0.5); text-transform: uppercase; font-weight: bold; letter-spacing: 0.5px; }'
            '  .sys-badge { background: rgba(0, 242, 255, 0.12); border: 1px solid rgba(0, 242, 255, 0.25); padding: 5px 10px; border-radius: 4px; font-family: monospace; font-size: 9px; color: #00f2ff; display: inline-block; letter-spacing: 0.5px; animation: pulse 1.5s infinite alternate; }'
            '  @keyframes pulse { from { opacity: 0.5; } to { opacity: 1; } }'
            '</style>'
            '<div class="hud-container">'
            '  <h1>🚀 NEXUS OPERATIONS HUD</h1>'
            '  <p>Isolated glassmorphic HTML frame rendered dynamically inside the A2UI sandbox component.</p>'
            '  <div class="kpi-row">'
            '    <div class="kpi-card">'
            '      <h4>99.98%</h4>'
            '      <span>SYSTEM HEALTH</span>'
            '    </div>'
            '    <div class="kpi-card cyan">'
            '      <h4>582 rps</h4>'
            '      <span>THROUGHPUT</span>'
            '    </div>'
            '    <div class="kpi-card orange">'
            '      <h4>1,420 ms</h4>'
            '      <span>VERTEX LATENCY</span>'
            '    </div>'
            '  </div>'
            '  <div class="sys-badge">ACTIVE SHIELD STATE: SECURED</div>'
            '</div>'
        )

        TABS_CONFIG = [{"id": "stk", "label": "📈 STOCKS"}, {"id": "flt", "label": "✈️ FLIGHT RADAR"}]
        stock_chart = [30, 32, 35, 41, 40, 43, 42, 45, 48, 47, 51, 50, 53, 52, 56]

        # Fetch active ticker prices
        nvda_p, nvda_c = await get_live_stock_price(client, "NVDA", 1054.50)
        goog_p, goog_c = await get_live_stock_price(client, "GOOG", 176.80)

        # Assemble split layout: left telemetry dashboard (live stocks), right secure HTML panel
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {
                "components": [
                    {
                        "id": "p5_split_grid",
                        "component": {
                            "gdm-stage-grid": {
                                "layout": "split",
                                "focusedPanel": 2,
                                "children": {
                                    "explicitList": ["p5_telemetry_dashboard", "p5_html_panel"]
                                }
                            }
                        }
                    },
                    {
                        "id": "p5_telemetry_dashboard",
                        "component": {
                            "gdm-telemetry-dashboard": {
                                "tabs": TABS_CONFIG,
                                "activeTabId": "stk",
                                "title": "⚡ Live Stock Telemetry Stream",
                                "metrics": [
                                    {"label": f"NVDA ({'+' if nvda_c >= 0 else ''}{nvda_c:.2f}%)", "value": f"${nvda_p:.2f} {'▲' if nvda_c >= 0 else '▼'}", "color": "#00ff88" if nvda_c >= 0 else "#ff3b30"},
                                    {"label": f"GOOG ({'+' if goog_c >= 0 else ''}{goog_c:.2f}%)", "value": f"${goog_p:.2f} {'▲' if goog_c >= 0 else '▼'}", "color": "#00f2ff" if goog_c >= 0 else "#ff3b30"},
                                ],
                                "chart": stock_chart,
                                "panel": 1
                            }
                        }
                    },
                    {
                        "id": "p5_html_panel",
                        "component": {
                            "gdm-html-panel": {
                                "html": html_hud_content,
                                "title": "⚡ Secure Cloud Run Sandbox Node",
                                "version": 1,
                                "overlay": False,
                                "panel": 2
                            }
                        }
                    },
                    ticker_component,
                    chyron_p5
                ]
            },
            "root": "p5_split_grid"
        })

        await speak_narrator_caption(
            client, space, "p5_split_grid", 
            "Finally, A2UI allows you to embed secure, isolated HTML sandboxes.", 
            delay_seconds=t_short
        )
        await speak_narrator_caption(
            client, space, "p5_split_grid", 
            "Our premium glassmorphic control center displays live server mesh metrics and active user nodes in real-time.", 
            delay_seconds=t_base
        )
        await speak_narrator_caption(
            client, space, "p5_split_grid", 
            "Everything is responsive, styled with custom neon glows and animated pulse indicators!", 
            delay_seconds=t_base
        )

        # Deactivate chyron
        chyron_p5_off = {
            "id": "hud_chyron",
            "component": {"gdm-chyron": {"active": False, "title": "", "subtitle": ""}}
        }
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {"components": [chyron_p5_off]},
            "root": "p5_split_grid"
        })

        # ───────────────────────────────────────────────────────────
        # Phase 6: Celebration Storm & Audience Feedback (Reset & Chats)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 6] Resetting Stage and Triggering Celebration Storm...{CLR_RESET}")
        
        # Clear overlays and grid to prepare for beautiful closing card
        await call_mcp_tool(client, "clear_stage", {"space_id": space})
        await asyncio.sleep(1.0)

        # Render clean, premium final card
        ticker_text_p6 = "DEMO CONCLUDED NOMINALLY • NEXUS STAGE SHUTTING DOWN... RETURNING CANVAS TO CORE ACTIVE LISTENERS... "
        ticker_component["component"]["gdm-ticker"]["text"] = ticker_text_p6
        ticker_component["component"]["gdm-ticker"]["badgeText"] = "STAGING NOMINAL"
        ticker_component["component"]["gdm-ticker"]["badgeColor"] = "#00f2ff"

        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {
                "components": [
                    {
                        "id": "final_closing_layout",
                        "component": {
                            "gdm-stage-grid": {
                                "layout": "single",
                                "children": {"explicitList": ["closing_card_panel"]}
                            }
                        }
                    },
                    {
                        "id": "closing_card_panel",
                        "component": {
                            "gdm-stage-card": {
                                "badge": "SHOWCASE COMPLETED",
                                "title": "Google Meet Studio Staging ✅",
                                "text": "The entire presentation was dynamically controlled using Python, WebSockets, and the Gemini A2UI declarative specification.",
                                "accent": "#00f2ff"
                            }
                        }
                    },
                    ticker_component
                ]
            },
            "root": "final_closing_layout"
        })

        await speak_narrator_caption(
            client, space, "final_closing_layout", 
            "That wraps up our live robot talk-through. Our Meet Live Concierge provides an incredible pairing of generative AI and collaboration.", 
            delay_seconds=t_base
        )
        await speak_narrator_caption(
            client, space, "final_closing_layout", 
            "Thank you for watching, and let's build the future of Workspace together! Nexus signing off.", 
            delay_seconds=t_short
        )

        # Clear active overlays
        await clear_captions_overlay(client, space, "final_closing_layout")
        await call_mcp_tool(client, "clear_stage", {"space_id": space})
        await asyncio.sleep(0.5)

        # Simulated user attendees reactions chat stream!
        chat_stream = [
            ("Librarian AI", "Outstanding visual fidelity! The live stock ticker coupled with subtitles is spectacular! 📈💎"),
            ("Sofia — Design", "That glassmorphic fullscreen D2 diagram takeover felt incredibly premium. Pure magic! 📐✨"),
            ("Antoine — Dev", "The responsive interactive poll and secure HTML operational HUD are absolute game-changers. 🗳️🌐"),
            ("Dana K. — Investor", "No rebuild required? Purely driven via python scripts? Stellar performance on A2UI! 🤩🔥")
        ]

        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})
        await asyncio.sleep(0.5)

        for idx, (username, comment) in enumerate(chat_stream):
            print(f"  💬 [Attendee Chat] {username}: {comment}")
            await broadcast_chat_comment(client, space, username, comment)
            if idx in (1, 3):
                await launch_emoji_burst(client, space, ["👏", "💯"])
            await asyncio.sleep(1.8)

        # Final massive celebration storm
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "applause"})
        await launch_emoji_burst(client, space, ["🎉", "💯", "🚀", "✨", "🔥", "🤩", "👏", "👑", "💎"])
        
    print(f"\n{CLR_GREEN}🎉 Cinematic AI Robot Host Staging executed successfully!{CLR_RESET}\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{CLR_MAGENTA}Showcase interrupted by user.{CLR_RESET}")
        sys.exit(0)
