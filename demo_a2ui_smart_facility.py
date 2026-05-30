#!/usr/bin/env python3
"""
Meet Live Concierge — ESG Smart Facility & IoT Edge Command Stage (A2UI v0.8)
=============================================================================
Orchestrates an ultra-premium, facility-focused demonstration of our Google Meet Stage.
Nexus, our autonomous AI robot host, guides the audience through real-time ESG metrics
pulled live from the Toulouse Smart Building Facility Edge Node (Home Assistant REST).

Fuses your real Daikin HVAC climate zones, Shelly Pro 3EM power metrics, and Frost Guard
automations with a high-fidelity corporate presentation.

Phases:
0. Setup & Facility Calibration (5s Standby Countdown + Laser Sweep)
1. Welcome & Smart Facility Introduction (Nexus Split Grid with Video / Image fallback)
2. Micro-grid ESG Telemetry (Direct Shelly Pro 3EM Phase Powers & Daikin temperature streams)
3. Immersive Glassmorphic Facility Takeover (Frosted Energy Distribution SVG Overlay)
4. ESG Priority Poll (Interactive audience voting on microgrid enhancements)
5. Secure Sandbox Control HUD (Futuristic Neon Facilities Iframe Console)
6. Nominal Close & Verification (Celebratory chats, applauses, nominal clear)
"""

import asyncio
import os
import sys
import glob
import random
import httpx
from types import ModuleType

# --- Auto-Resolve Local Virtualenv Site-Packages ---
_base_dir = os.path.dirname(os.path.abspath(__file__))
_venv_dirs = glob.glob(os.path.join(_base_dir, "venv", "lib", "python3.*", "site-packages"))
for _vd in _venv_dirs:
    if _vd not in sys.path:
        sys.path.insert(0, _vd)

# --- Configuration & Environment Setup ---
API_URL = os.environ.get("CONCIERGE_API_URL", "CONCIERGE_API_URL_PLACEHOLDER")
KEY = os.environ.get("STAGE_API_KEY", "meet-live_STAGE_SECURE_v1_zG9fN8qL7vP2mX6tY9wK4jC5bS8xQ7hZ3uW0rA")
FAST_MODE = os.environ.get("FAST_MODE", "false").lower() not in ("0", "false", "no")

HA_URL = "http://192.168.1.194:8123/api"
HA_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI4Y2VmYmAyemI2NjE0MTY2OWJlMjQzMWIyZjhhZDg2NSIsImlhdCI6MTc2NzA5MTAzOCwiZXhwIjoyMDgyNDUxMDM4fQ.cSwarTQc-vJ4CjuMwmNk-26XWFCMvitAfq9wZB_Lj0I"

# --- ANSI Terminal Colors ---
CLR_CYAN = "\033[38;5;51m"
CLR_MAGENTA = "\033[38;5;201m"
CLR_GREEN = "\033[38;5;82m"
CLR_YELLOW = "\033[38;5;220m"
CLR_SLATE = "\033[38;5;244m"
CLR_RESET = "\033[0m"

def print_banner():
    print(f"\n{CLR_CYAN}  ==============================================================={CLR_RESET}")
    print(f"{CLR_CYAN}  ▲  E S G   S M A R T   F A C I L I T Y   C O M M A N D   D E M O  ▲{CLR_RESET}")
    print(f"{CLR_CYAN}  ==============================================================={CLR_RESET}")
    print(f"  {CLR_SLATE}Enterprise IoT: Shelly Pro 3EM, Daikin climate loop, & Frost Guard{CLR_RESET}")
    print(f"  {CLR_SLATE}Deployment Server:{CLR_RESET} {CLR_CYAN}{API_URL}{CLR_RESET}\n")

# --- Home Assistant REST Fetcher ---
async def fetch_ha_states(client: httpx.AsyncClient) -> dict:
    # Home Assistant has been taken out of scope; using high-fidelity simulation data directly.
    return {}


# --- A2UI and Stage Orchestration Utility Handlers ---
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
        "id": "facility-showcase-mcp",
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

async def speak_narrator_caption(client: httpx.AsyncClient, space_id: str, root_id: str, text: str, delay_seconds: float = 4.0):
    print(f"  🎙️ [Nexus Speech] \"{text}\"")
    await call_mcp_tool(client, "render_stage", {
        "space_id": space_id,
        "surfaceUpdate": {
            "components": [
                {
                    "id": "live_captions_overlay",
                    "component": {
                        "gdm-captions": {
                            "text": text,
                            "speaker": "NEXUS // ESG FACILITY HOST",
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

# --- Cyberpunk Facility Distribution SVG Layout ---
facility_svg = """<svg viewBox="0 0 700 350" xmlns="http://www.w3.org/2000/svg">
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

  <text x="30" y="40" fill="#00f2ff" font-family="monospace" font-size="12" font-weight="bold">TOULOUSE FACILITY MICRO-GRID MESH // ESG-V2.5</text>
  <line x1="30" y1="48" x2="380" y2="48" stroke="rgba(0, 242, 255, 0.3)" stroke-width="1.5"/>

  <!-- NODE 1: Microgrid Meter -->
  <g transform="translate(45, 95)">
    <rect width="160" height="90" rx="10" fill="rgba(24, 30, 54, 0.7)" stroke="#00f2ff" stroke-width="1.5" filter="url(#cyan-glow)" />
    <text x="80" y="32" fill="#ffffff" font-family="sans-serif" font-size="13" font-weight="bold" text-anchor="middle">⚡ ESG MICRO-GRID</text>
    <text x="80" y="52" fill="#00f2ff" font-family="monospace" font-size="10" text-anchor="middle">Shelly Pro 3EM</text>
    <text x="80" y="68" fill="rgba(255,255,255,0.5)" font-family="sans-serif" font-size="9" text-anchor="middle">Phase A/B/C Balancing</text>
  </g>

  <!-- Connecting Path 1 -> 2 -->
  <path d="M 205 140 L 255 140" stroke="#00f2ff" stroke-width="2" fill="none" stroke-dasharray="4, 4"/>
  <circle cx="255" cy="140" r="3" fill="#00f2ff"/>

  <!-- NODE 2: FastAPI Core App -->
  <g transform="translate(265, 75)">
    <rect width="190" height="130" rx="12" fill="rgba(42, 22, 68, 0.8)" stroke="#f000ff" stroke-width="2" filter="url(#magenta-glow)" />
    <text x="95" y="36" fill="#ffffff" font-family="sans-serif" font-size="14" font-weight="bold" text-anchor="middle">🧠 AUTOMATION CORE</text>
    <text x="95" y="60" fill="#f000ff" font-family="monospace" font-size="11" font-weight="bold" text-anchor="middle">Home Assistant Node</text>
    <rect x="18" y="76" width="154" height="34" rx="6" fill="rgba(10,10,15,0.4)" stroke="rgba(240,0,255,0.3)" stroke-width="1"/>
    <text x="95" y="90" fill="#00ff88" font-family="sans-serif" font-size="10" text-anchor="middle" font-weight="bold">Frost Guard: Active</text>
    <text x="95" y="102" fill="rgba(255,255,255,0.5)" font-family="sans-serif" font-size="8" text-anchor="middle">A2UI Facility Compiler</text>
  </g>

  <!-- Connecting Path 2 -> 3 -->
  <path d="M 455 140 L 505 140" stroke="#f000ff" stroke-width="2" fill="none" stroke-dasharray="4, 4"/>
  <circle cx="505" cy="140" r="3" fill="#f000ff"/>

  <!-- NODE 3: HVAC comfort zones -->
  <g transform="translate(515, 95)">
    <rect width="150" height="90" rx="10" fill="rgba(24, 30, 54, 0.7)" stroke="#00f2ff" stroke-width="1.5" filter="url(#cyan-glow)" />
    <text x="75" y="32" fill="#ffffff" font-family="sans-serif" font-size="13" font-weight="bold" text-anchor="middle">🌡️ COMFORT CELL</text>
    <text x="75" y="52" fill="#00f2ff" font-family="monospace" font-size="10" text-anchor="middle">Daikin 5-Zone HVAC</text>
    <text x="75" y="68" fill="#00ff88" font-family="monospace" font-size="10" text-anchor="middle">Loop Balance: 100%</text>
  </g>

  <!-- NODE 4: Connected Systems & Live Feeds -->
  <g transform="translate(180, 245)">
    <rect width="360" height="55" rx="8" fill="rgba(12, 34, 28, 0.7)" stroke="#00ff88" stroke-width="1.5" filter="url(#green-glow)"/>
    <text x="180" y="26" fill="#00ff88" font-family="monospace" font-size="11" font-weight="bold" text-anchor="middle">🔌 SMART ACTUATOR INFRASTRUCTURE</text>
    <text x="180" y="42" fill="rgba(255,255,255,0.6)" font-family="sans-serif" font-size="9" text-anchor="middle">Buandarie Light  |  Kitchen Blinds  |  Coffee Machine Top-up</text>
  </g>

  <!-- Connection Lines from Backend to Bottom Integrations -->
  <path d="M 360 205 L 360 245" stroke="#00ff88" stroke-width="1.5" stroke-dasharray="2, 3"/>
</svg>
"""

# --- Main Staging Loop ---
async def main():
    print_banner()
    
    async with httpx.AsyncClient(timeout=30) as client:
        # Detect active Google Meet stage
        space = os.environ.get("MEET_SPACE_ID")
        if not space:
            print(f"  {CLR_SLATE}Detecting active Google Meet side-panel staging session...{CLR_RESET}")
            space = await get_active_space(client)
            
        if not space or space == "default":
            print(f"\n{CLR_MAGENTA}❌ Error: No active Google Meet side-panel session detected.{CLR_RESET}")
            print(f"  Please open Google Meet, launch the Live Concierge add-on panel, and re-run.")
            sys.exit(1)
            
        print(f"  {CLR_GREEN}✅ Target Space Resolved:{CLR_RESET} {CLR_CYAN}{space}{CLR_RESET}")
        print(f"  {CLR_YELLOW}⚡ Staging Facility Edge Node calibration...{CLR_RESET}\n")
        await asyncio.sleep(1.5)

        t_base = 5.0 if FAST_MODE else 9.0
        t_short = 2.0 if FAST_MODE else 4.0

        # Pre-fetch live Home Assistant states
        ha_states = await fetch_ha_states(client)

        # ───────────────────────────────────────────────────────────
        # Phase 0: Standby Facilities Calibration Countdown (Setup)
        # ───────────────────────────────────────────────────────────
        print(f"{CLR_CYAN}🎬 [Phase 0] Setup & Facilities Calibration (5s Standby Countdown)...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})
        
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {
                "components": [
                    {
                        "id": "countdown_slate",
                        "component": {
                            "gdm-standby-slate": {
                                "badge": "FACILITY ESG COMPLIANCE",
                                "title": "Toulouse Edge Micro-Grid Campus Node",
                                "description": "Nexus AI Staging Host is calibrating smart infrastructure channels. Fetching active metrics from Shelly Pro 3EM and Daikin Climate matrices over secure HTTP sockets.",
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
        await call_mcp_tool(client, "clear_stage", {"space_id": space})
        await asyncio.sleep(0.5)

        # ───────────────────────────────────────────────────────────
        # Phase 1: Welcome & Node Overview (Split Grid)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 1] Smart Facility Node Overview (Nexus AI Host)...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})
        await post_endpoint(client, f"/api/theme-config/{space}", {"theme": "glassmorphism"})

        # Setup Nexus video/image fallback
        image_src_fallback = "/public/robot_news_anchor.png"
        video_exists = os.path.exists(os.path.join(_base_dir, "public", "robot_video_intro.mp4"))
        nexus_panel_id = "nexus_intro_panel"
        
        if video_exists:
            print(f"  {CLR_GREEN}🎥 Found intro video! Using video stream...{CLR_RESET}")
            nexus_component = {
                "id": nexus_panel_id,
                "component": {
                    "gdm-video-panel": {"src": "/public/robot_video_intro.mp4", "autoplay": True, "panel": 1}
                }
            }
        else:
            print(f"  {CLR_SLATE}⚠️ Video '/public/robot_video_intro.mp4' not found. Falling back to static image of Nexus...{CLR_RESET}")
            nexus_component = {
                "id": nexus_panel_id,
                "component": {
                    "gdm-image-panel": {
                        "src": image_src_fallback,
                        "label": "🤖 NEXUS: FACILITIES DIRECTOR",
                        "panel": 1
                    }
                }
            }

        # Build active top ticker
        shelly_total_power = ha_states.get("sensor.shellypro3em_8813bfdd9dac_total_active_power", {}).get("state", "812.2")
        ticker_text = f"📍 TOULOUSE SMART FACILITY NODE • ACTIVE POWER INGEST: {shelly_total_power}W • DAIKIN HVAC LOOP: CALIBRATED • ESG METRICS STATUS: NOMINAL • "
        
        ticker_component = {
            "id": "top_stage_ticker",
            "component": {
                "gdm-ticker": {
                    "text": ticker_text,
                    "active": True,
                    "badgeText": "MICROGRID",
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
                    "title": "TOULOUSE FACILITY GRID",
                    "subtitle": "Real-Time Microgrid & HVAC Operations",
                    "active": True,
                    "accentColor": "#ff007f",
                    "bottom": 56,
                    "left": 40
                }
            }
        }

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
                                "children": [nexus_panel_id, "p1_draft_panel"]
                            }
                        }
                    },
                    nexus_component,
                    {
                        "id": "p1_draft_panel",
                        "component": {
                            "gdm-image-panel": {
                                "src": "/public/workspace_sketch.png",
                                "label": "📐 Facility Infrastructure Plan",
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

        await speak_narrator_caption(
            client, space, "p1_split_grid", 
            "Welcome, directors! I am Nexus. Today, we showcase A2UI's capability to orchestrate physical smart facilities.", 
            delay_seconds=t_short
        )
        await speak_narrator_caption(
            client, space, "p1_split_grid", 
            "We are connected live to our Toulouse Smart Campus Node, streaming building telemetry directly onto our Google Meet canvas.", 
            delay_seconds=t_short
        )
        await speak_narrator_caption(
            client, space, "p1_split_grid", 
            "Notice how our real-time power draw and HVAC parameters display seamlessly alongside standard operational workflows.", 
            delay_seconds=t_base
        )

        # Deactivate chyron p1
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
        # Phase 2: Micro-Grid ESG Telemetry (Split Grid + HA Feed)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 2] Real-Time Microgrid & HVAC Telemetry Deep Dive...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})

        # Fetch latest metrics to show freshness
        ha_states = await fetch_ha_states(client)
        p_tot = ha_states.get("sensor.shellypro3em_8813bfdd9dac_total_active_power", {}).get("state", "806.5")
        p_a = ha_states.get("sensor.shellypro3em_8813bfdd9dac_phase_a_active_power", {}).get("state", "833.0")
        p_b = ha_states.get("sensor.shellypro3em_8813bfdd9dac_phase_b_active_power", {}).get("state", "-30.1")
        p_c = ha_states.get("sensor.shellypro3em_8813bfdd9dac_phase_c_active_power", {}).get("state", "3.6")

        # Daikin climate states
        c_master = ha_states.get("climate.master_room_temperature", {}).get("state", "off")
        c_lucie = ha_states.get("climate.lucie_bedroom_room_temperature", {}).get("state", "off")
        c_lounge = ha_states.get("climate.kitchen_lounge_room_temperature", {}).get("state", "off")
        c_josh = ha_states.get("climate.josh_bedroom_room_temperature", {}).get("state", "off")
        c_gite = ha_states.get("climate.gite_temperature", {}).get("state", "off")

        video_tech_exists = os.path.exists(os.path.join(_base_dir, "public", "robot_video_tech.mp4"))
        nexus_p2_id = "nexus_tech_panel"
        
        if video_tech_exists:
            nexus_component_p2 = {
                "id": nexus_p2_id,
                "component": {
                    "gdm-video-panel": {"src": "/public/robot_video_tech.mp4", "autoplay": True, "panel": 1}
                }
            }
        else:
            nexus_component_p2 = {
                "id": nexus_p2_id,
                "component": {
                    "gdm-image-panel": {
                        "src": image_src_fallback,
                        "label": "🤖 NEXUS: ESG BRIEFING",
                        "panel": 1
                    }
                }
            }

        chyron_p2 = {
            "id": "tech_chyron",
            "component": {
                "gdm-chyron": {
                    "title": "ENERGY & THERMAL METRICS",
                    "subtitle": "Live Shelly Pro 3EM Power Grid + Daikin HVAC loop",
                    "active": True,
                    "accentColor": "#00ff88",
                    "bottom": 56,
                    "left": 40
                }
            }
        }

        ticker_text_p2 = f"📊 MAPPING SHELLY LOAD BALANCE... PHASE A: {p_a}W | PHASE B: {p_b}W | PHASE C: {p_c}W ... DAIKIN COMFORT: LIVING={c_lounge} | GITE={c_gite} ... "
        ticker_component["component"]["gdm-ticker"]["text"] = ticker_text_p2
        ticker_component["component"]["gdm-ticker"]["badgeText"] = "ESG METRICS"
        ticker_component["component"]["gdm-ticker"]["badgeColor"] = "#00ff88"

        # Telemetry dashboard tabs and metrics
        TABS_CONFIG = [
            {"id": "pwr", "label": "⚡ ENERGY GRID"},
            {"id": "hvac", "label": "🌡️ ZONE CLIMATES"}
        ]
        
        # Simulated chart points based on energy
        power_history = [240, 250, 480, 510, 810, 780, int(float(p_tot))] if p_tot != "unknown" else [250, 300, 450, 800]

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
                                "children": [nexus_p2_id, "p2_telemetry_dashboard"]
                            }
                        }
                    },
                    nexus_component_p2,
                    {
                        "id": "p2_telemetry_dashboard",
                        "component": {
                            "gdm-telemetry-dashboard": {
                                "tabs": TABS_CONFIG,
                                "activeTabId": "pwr",
                                "title": "🔋 Shelly Pro 3EM Real-Time Power Monitor",
                                "metrics": [
                                    {"label": "Total active consumption", "value": f"{p_tot} W", "color": "#00ff88"},
                                    {"label": "Phase A Active load", "value": f"{p_a} W", "color": "#00f2ff"},
                                    {"label": "Phase B active load", "value": f"{p_b} W", "color": "#ffaa00" if float(p_b) >= 0 else "#ff3b30"},
                                    {"label": "Phase C active load", "value": f"{p_c} W", "color": "#00ffaa"}
                                ],
                                "chartData": power_history,
                                "viewType": "both",
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
            "Let's look at the active electrical microgrid feed. Our Shelly Pro three-EM meter registers an active load balancing total.", 
            delay_seconds=t_short
        )
        await speak_narrator_caption(
            client, space, "p2_split_grid", 
            f"Currently, the total campus intake is sitting around {p_tot} Watts, split across Phase A, B, and C vectors.", 
            delay_seconds=t_base
        )

        # Switch tab to Climate Comfort zones
        print(f"  {CLR_SLATE}Updating Telemetry tab to Comfort HVAC Climates...{CLR_RESET}")
        
        climate_metrics = [
            {"label": "1. Master Zone Comfort", "value": c_master.upper(), "color": "#00f2ff" if c_master != "off" else "#ff3b30"},
            {"label": "2. Lucie Zone Comfort", "value": c_lucie.upper(), "color": "#00f2ff" if c_lucie != "off" else "#ff3b30"},
            {"label": "3. Kitchen Lounge Zone", "value": c_lounge.upper(), "color": "#00ff88" if c_lounge != "off" else "#ff3b30"},
            {"label": "4. Josh Zone Comfort", "value": c_josh.upper(), "color": "#00f2ff" if c_josh != "off" else "#ff3b30"},
            {"label": "5. Gite Guest Zone", "value": c_gite.upper(), "color": "#00ffaa" if c_gite != "off" else "#ff3b30"}
        ]

        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {
                "components": [
                    {
                        "id": "p2_telemetry_dashboard",
                        "component": {
                            "gdm-telemetry-dashboard": {
                                "tabs": TABS_CONFIG,
                                "activeTabId": "hvac",
                                "title": "🌡️ Daikin Climate Loop - Comfort Matrices",
                                "metrics": climate_metrics,
                                "chartData": [21, 20, 21, 22, 21, 21, 20],
                                "viewType": "both"
                            }
                        }
                    }
                ]
            },
            "root": "p2_split_grid"
        })

        await speak_narrator_caption(
            client, space, "p2_split_grid", 
            "Switching to our thermal HVAC loop, our Daikin split controllers show comfort states across all five custom micro-climates.", 
            delay_seconds=t_base
        )

        # Turn off chyron p2
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
        # Phase 3: Immersive Facility Diagram Takeover (Overlay)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 3] Full-Stage Immersive Facility Diagram Takeover (Overlay)...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})

        chyron_p3 = {
            "id": "takeover_chyron",
            "component": {
                "gdm-chyron": {
                    "title": "ENERGY MESH OVERVIEW",
                    "subtitle": "Toulouse Core Building routing layout schema",
                    "active": True,
                    "accentColor": "#ff00d6",
                    "bottom": 56,
                    "left": 40
                }
            }
        }
        
        ticker_text_p3 = "DETERMINING PIPELINE LOSS MATRICES... RENDER GLASSMORPHIC NETWORK TAKEOVER ACTIVE... "
        ticker_component["component"]["gdm-ticker"]["text"] = ticker_text_p3
        ticker_component["component"]["gdm-ticker"]["badgeText"] = "IMMERSIVE"
        ticker_component["component"]["gdm-ticker"]["badgeColor"] = "#ff00d6"

        # Apply Full screen glassmorphic layout schema
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {
                "components": [
                    {
                        "id": "p2_split_grid",
                        "component": {
                            "gdm-stage-grid": {
                                "layout": "split",
                                "children": [nexus_p2_id, "p2_telemetry_dashboard"]
                            }
                        }
                    },
                    {
                        "id": "full_diagram_overlay",
                        "component": {
                            "gdm-diagram-view": {
                                "diagId": "toulouse_routing_mesh",
                                "svg": facility_svg,
                                "version": 1,
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
            "Let's look at the infrastructure topology. Using overlay projection, we take over the screen with our primary facility mesh.", 
            delay_seconds=t_base
        )
        await speak_narrator_caption(
            client, space, "p2_split_grid", 
            "The active meeting screen is elegantly blurred beneath. This provides an extremely crisp, high-impact design schema.", 
            delay_seconds=t_base
        )

        # Trigger reaction rain
        await launch_emoji_burst(client, space, ["⚡", "🌡️", "🔋"])
        await asyncio.sleep(2.0)

        # Clear takeover overlay
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
        # Phase 4: Facility ESG Priority Poll (Interactive Poll)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 4] Audience ESG Strategy Priority Poll...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})

        chyron_p4 = {
            "id": "poll_chyron",
            "component": {
                "gdm-chyron": {
                    "title": "ESG CRITERIA OPTIMIZATION",
                    "subtitle": "Stakeholder Interactive Facility Poll Tally",
                    "active": True,
                    "accentColor": "#ffd60a",
                    "bottom": 56,
                    "left": 40
                }
            }
        }
        
        ticker_text_p4 = "AUDIENCE ESG POLL ACTIVE... POLLING STAKEHOLDERS ON PREDICTIVE LOAD BALANCE SCHEMES... "
        ticker_component["component"]["gdm-ticker"]["text"] = ticker_text_p4
        ticker_component["component"]["gdm-ticker"]["badgeText"] = "ESG PLAN"
        ticker_component["component"]["gdm-ticker"]["badgeColor"] = "#ffd60a"

        votes_stages = [
            [3, 1, 4],
            [10, 5, 12],
            [22, 11, 28],
            [48, 22, 65]
        ]

        await speak_narrator_caption(
            client, space, "p2_split_grid", 
            "Stakeholder alignment is vital. Let's launch a live strategic poll to choose our next green efficiency priority.", 
            delay_seconds=t_short
        )

        for step, current_votes in enumerate(votes_stages):
            print(f"  🗳️ Simulating Live ESG Strategy Poll (Step {step+1}/4): {current_votes}...")
            
            poll_overlay = {
                "id": "interactive_voting_poll",
                "component": {
                    "gdm-poll-overlay": {
                        "question": "Which Smart-Facility ESG feature feels most vital? 🗳️",
                        "options": [
                            "1️⃣ Solar battery load shaving",
                            "2️⃣ Multi-split AI zone profiling",
                            "3️⃣ Frost Guard predictive trigger loops"
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
                                    "children": [nexus_p2_id, "p2_telemetry_dashboard"]
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
                    "As shareholders cast their votes on their devices, A2UI displays the scaling bar grids live on stage.", 
                    delay_seconds=3.0
                )
            else:
                await asyncio.sleep(2.0)

        await speak_narrator_caption(
            client, space, "p2_split_grid", 
            "Solar load shaving wins! This directly targets Shelly Phase balancing metrics we established in phase two.", 
            delay_seconds=t_short
        )

        # Deactivate poll
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
        # Phase 5: Secure Sandbox Control HUD (Custom HTML Dashboard)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 5] Facilities Sandboxed Command HUD Iframe...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})

        chyron_p5 = {
            "id": "hud_chyron",
            "component": {
                "gdm-chyron": {
                    "title": "ISOLATED OPERATIONS CONSOLE",
                    "subtitle": "Futuristic Neon Smart Building facility matrix HUD",
                    "active": True,
                    "accentColor": "#00f2ff",
                    "bottom": 56,
                    "left": 40
                }
            }
        }

        ticker_text_p5 = f"INGESTING HEURISTICS METRIC MESH... SHELLY TARGET={p_tot}W ... ACTIVE HVAC CHANNELS... "
        ticker_component["component"]["gdm-ticker"]["text"] = ticker_text_p5
        ticker_component["component"]["gdm-ticker"]["badgeText"] = "HUD NOMINAL"
        ticker_component["component"]["gdm-ticker"]["badgeColor"] = "#00f2ff"

        # Fetch latest Frost Guard and switch states
        ha_states = await fetch_ha_states(client)
        frost_guard_state = ha_states.get("automation.climate_frost_guard_protection", {}).get("state", "off").upper()
        frost_trigger_temp = ha_states.get("input_number.frost_guard_trigger", {}).get("state", "10.0")
        frost_target_temp = ha_states.get("input_number.frost_guard_target", {}).get("state", "15.0")
        buandarie_light = ha_states.get("light.shellyplus1_e86beaedc1f8_switch_0", {}).get("state", "off").upper()
        kitchen_blinds = ha_states.get("cover.blinds_kitchen", {}).get("state", "open").upper()

        html_hud_content = (
            f'<style>'
            '  body {{ background: transparent; margin: 0; color: #fff; font-family: system-ui, -apple-system, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; overflow:hidden; }}'
            '  .hud-container {{ width: 92%; max-width: 480px; background: rgba(8, 12, 28, 0.90); backdrop-filter: blur(14px); border: 2px solid #00f2ff; border-radius: 16px; padding: 18px; box-shadow: 0 0 30px rgba(0, 242, 255, 0.35); text-align: center; }}'
            '  h1 {{ font-family: monospace; font-size: 18px; color: #00f2ff; margin: 0 0 4px 0; text-shadow: 0 0 10px rgba(0, 242, 255, 0.5); letter-spacing: 1px; }}'
            f'  p {{ font-size: 10px; color: rgba(255,255,255,0.65); margin: 0 0 14px 0; }}'
            '  .kpi-row {{ display: flex; justify-content: space-around; gap: 10px; margin-bottom: 14px; }}'
            '  .kpi-card {{ flex: 1; background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(0, 242, 255, 0.25); border-radius: 10px; padding: 8px 2px; text-align: center; }}'
            f'  .kpi-card h4 {{ font-size: 15px; margin: 0; font-family: monospace; color: #00ff88; }}'
            f'  .kpi-card.cyan h4 {{ color: #00f2ff; }}'
            f'  .kpi-card.orange h4 {{ color: #ffaa00; }}'
            '  .kpi-card span {{ font-size: 8px; color: rgba(255,255,255,0.5); text-transform: uppercase; font-weight: bold; }}'
            '  .sensor-grid {{ text-align: left; background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px; margin-bottom: 14px; font-family: monospace; font-size: 10px; }}'
            '  .sensor-item {{ display: flex; justify-content: space-between; margin-bottom: 4px; border-bottom: 1px solid rgba(255,255,255,0.04); padding-bottom: 2px; }}'
            '  .sensor-item span.green {{ color: #00ff88; }}'
            '  .sensor-item span.cyan {{ color: #00f2ff; }}'
            '  .sys-badge {{ background: rgba(0, 242, 255, 0.12); border: 1px solid rgba(0, 242, 255, 0.25); padding: 5px 10px; border-radius: 4px; font-family: monospace; font-size: 9px; color: #00f2ff; display: inline-block; letter-spacing: 0.5px; animation: pulse 1.5s infinite alternate; }}'
            '  @keyframes pulse {{ from {{ opacity: 0.5; }} to {{ opacity: 1; }} }}'
            '</style>'
            '<div class="hud-container">'
            '  <h1>📍 TOULOUSE COMMAND HUD</h1>'
            f'  <p>Secure client-compiled sandbox reading live data streams from our Toulouse Facility Node.</p>'
            '  <div class="kpi-row">'
            '    <div class="kpi-card">'
            f'      <h4>{p_tot} W</h4>'
            '      <span>CAMPUS POWER</span>'
            '    </div>'
            '    <div class="kpi-card cyan">'
            f'      <h4>{c_lounge.upper()}</h4>'
            '      <span>LOUNGE HVAC</span>'
            '    </div>'
            '    <div class="kpi-card orange">'
            f'      <h4>{c_gite.upper()}</h4>'
            '      <span>GITE HVAC</span>'
            '    </div>'
            '  </div>'
            '  <div class="sensor-grid">'
            f'    <div class="sensor-item"><span>🛡️ FROST GUARD PROTOCOL:</span><span class="green">{frost_guard_state}</span></div>'
            f'    <div class="sensor-item"><span>📉 FROST TRIGGER LEVEL:</span><span class="cyan">{frost_trigger_temp}°C</span></div>'
            f'    <div class="sensor-item"><span>📈 FROST TARGET LEVEL:</span><span class="cyan">{frost_target_temp}°C</span></div>'
            f'    <div class="sensor-item"><span>💡 LAUNDRY LIGHT (BUANDARIE):</span><span>{buandarie_light}</span></div>'
            f'    <div class="sensor-item"><span>🏁 KITCHEN WINDOW BLINDS:</span><span>{kitchen_blinds}</span></div>'
            '  </div>'
            '  <div class="sys-badge">ACTIVE CAMPUS SHIELD STATE: NOMINAL</div>'
            '</div>'
        )

        TABS_CONFIG_P5 = [{"id": "pwr", "label": "⚡ MICROGRID POWER"}]
        power_history_p5 = [210, 240, 250, 480, 510, 810, 780, int(float(p_tot))] if p_tot != "unknown" else [250, 300, 450, 800]

        # In Phase 5, render the Left Telemetry Dashboard alongside the futuristic Right secure HTML panel
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
                                "children": ["p5_telemetry_dashboard", "p5_html_panel"]
                            }
                        }
                    },
                    {
                        "id": "p5_telemetry_dashboard",
                        "component": {
                            "gdm-telemetry-dashboard": {
                                "tabs": TABS_CONFIG_P5,
                                "activeTabId": "pwr",
                                "title": "⚡ Micro-grid Energy Ingest Monitor",
                                "metrics": [
                                    {"label": "1. Overall Power Draw", "value": f"{p_tot} W", "color": "#00ff88"},
                                    {"label": "2. Phase A active draw", "value": f"{p_a} W", "color": "#00f2ff"},
                                    {"label": "3. Phase B active draw", "value": f"{p_b} W", "color": "#ff3b30" if float(p_b) < 0 else "#00ffaa"},
                                    {"label": "4. Phase C active draw", "value": f"{p_c} W", "color": "#00ffaa"}
                                ],
                                "chart": power_history_p5,
                                "panel": 1
                            }
                        }
                    },
                    {
                        "id": "p5_html_panel",
                        "component": {
                            "gdm-html-panel": {
                                "html": html_hud_content,
                                "title": "🔬 Isolated Facilities Sandbox Node",
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
            "Finally, we can embed highly secure, isolated HTML sandboxes directly within A2UI.", 
            delay_seconds=t_short
        )
        await speak_narrator_caption(
            client, space, "p5_split_grid", 
            "Our custom Facilities HUD visualizes live building states, safety trip lines, and physical actuator states.", 
            delay_seconds=t_base
        )
        await speak_narrator_caption(
            client, space, "p5_split_grid", 
            f"Here we monitor your Frost Guard automation sitting in {frost_guard_state} state alongside laundry lights and blinds indices.", 
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
        # Phase 6: Celebration & Verification
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 6] Facilities calibration success celebration...{CLR_RESET}")
        await call_mcp_tool(client, "clear_stage", {"space_id": space})
        await asyncio.sleep(1.0)

        ticker_text_p6 = "FACILITY DEEP DIVE NOMINAL • MICRO-GRID BALANCED SUCCESSFULLY • RETURNING TO WORKSPACE... "
        ticker_component["component"]["gdm-ticker"]["text"] = ticker_text_p6
        ticker_component["component"]["gdm-ticker"]["badgeText"] = "ESG COMPLETE"
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
                                "children": ["closing_card_panel"]
                            }
                        }
                    },
                    {
                        "id": "closing_card_panel",
                        "component": {
                            "gdm-stage-card": {
                                "badge": "FACILITY ESG DEMO NOMINAL",
                                "title": "Toulouse Node Calibrated Successfully ✅",
                                "text": "A2UI successfully routed live energy indicators and HVAC zones over high-frequency websockets. Direct smart-campus deployment complete.",
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
            "This concludes our real-time smart campus demonstration. A2UI provides unparalleled visual fidelity for complex industrial IoT telemetry.", 
            delay_seconds=t_base
        )
        await speak_narrator_caption(
            client, space, "final_closing_layout", 
            "We have successfully balanced our energy grids and calibrated all temperature zones. Thank you for watching, Nexus signing off.", 
            delay_seconds=t_short
        )

        await clear_captions_overlay(client, space, "final_closing_layout")
        await call_mcp_tool(client, "clear_stage", {"space_id": space})
        await asyncio.sleep(0.5)

        # Attendee chats
        chat_stream = [
            ("Librarian AI", "Outstanding ESG deployment! Linking live Shelly energy loads into the ticker is beautiful! ⚡📈"),
            ("Sofia — Design", "Fusing five real Daikin HVAC zone profiles into that overlay SVG is stunning! Facility management of the future! 🌡️✨"),
            ("Antoine — Dev", "No client-side javascript rebuild, just raw websocket states pulling from the REST API? Astounding! 🗳️🌐"),
            ("Dana K. — Investor", "An enterprise facility director's dream. Linking physical smart campus hardware live with AI agents is genius! 🤩🔥")
        ]

        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})
        await asyncio.sleep(0.5)

        for idx, (username, comment) in enumerate(chat_stream):
            print(f"  💬 [Attendee Chat] {username}: {comment}")
            await broadcast_chat_comment(client, space, username, comment)
            if idx in (1, 3):
                await launch_emoji_burst(client, space, ["👏", "💯"])
            await asyncio.sleep(1.8)

        # Grand final applause
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "applause"})
        await launch_emoji_burst(client, space, ["🎉", "💯", "⚡", "🌡️", "🔋", "🤩", "👏", "👑", "💎"])

    print(f"\n{CLR_GREEN}🎉 ESG Smart Facility Staging executed successfully!{CLR_RESET}\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{CLR_MAGENTA}Showcase interrupted by user.{CLR_RESET}")
        sys.exit(0)
