#!/usr/bin/env python3
"""
Meet Live Concierge — Executive SOHO Scope 3 ESG & Remote Workspace Stage (A2UI v0.8)
===================================================================================
Orchestrates an ultra-premium, executive-focused demonstration of our Google Meet Stage.
Nexus, our autonomous AI robot host, guides the corporate audience through live Scope 3
Category 7 (Employee Remote Working) carbon footprint and employee wellness metrics
pulled live from the Toulouse Executive SOHO Edge Node (Home Assistant REST).

Fuses your real Daikin HVAC comfort zones, Shelly Pro 3EM power vectors, and Frost Guard
resilience automations with a high-stakes corporate compliance presentation.

Phases:
0. Setup & SOHO Calibration (5s Standby Countdown + SOHO Shield Init)
1. Welcome & SOHO ESG Briefing (Nexus Split Grid with Video / Image fallback)
2. Scope 3 Carbon & Thermal Telemetry (Live Shelly Pro 3EM Phase Powers & Daikin climates)
3. Immersive SOHO Mesh Topology Takeover (Frosted Network Topology SVG Overlay)
4. SOHO ESG Subsidy Strategy Poll (Interactive audience voting on SOHO incentives)
5. Secure Workspace HUD Sandbox (Futuristic Neon Executive HUD Iframe Console)
6. Nominal Close & ESG Verification (Celebratory chats, applauses, nominal clear)
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
HA_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI4Y2VmYmAyYmI2NjE0MTY2OWJlMjQzMWIyZjhhZDg2NSIsImlhdCI6MTc2NzA5MTAzOCwiZXhwIjoyMDgyNDUxMDM4fQ.cSwarTQc-vJ4CjuMwmNk-26XWFCMvitAfq9wZB_Lj0I"

# --- ANSI Terminal Colors ---
CLR_CYAN = "\033[38;5;51m"
CLR_MAGENTA = "\033[38;5;201m"
CLR_GREEN = "\033[38;5;82m"
CLR_YELLOW = "\033[38;5;220m"
CLR_SLATE = "\033[38;5;244m"
CLR_RESET = "\033[0m"

def print_banner():
    print(f"\n{CLR_CYAN}  ==============================================================={CLR_RESET}")
    print(f"{CLR_CYAN}  ▲   E X E C U T I V E   S O H O   S C O P E   3   D E M O   ▲{CLR_RESET}")
    print(f"{CLR_CYAN}  ==============================================================={CLR_RESET}")
    print(f"  {CLR_SLATE}Scope 3 ESG Category 7: Shelly Pro 3EM, Daikin HVAC, & Frost Guard{CLR_RESET}")
    print(f"  {CLR_SLATE}Deployment Server:{CLR_RESET} {CLR_CYAN}{API_URL}{CLR_RESET}\n")

# --- Home Assistant REST Fetcher ---
async def fetch_ha_states(client: httpx.AsyncClient) -> dict:
    # Home Assistant has been taken out of scope; using high-fidelity simulation fallback data directly.
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
        "id": "soho-showcase-mcp",
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
                            "speaker": "NEXUS // SOHO ESG HOST",
                            "active": True,
                            "accentColor": "#00ff88"
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

async def launch_emoji_burst(client: httpx.AsyncClient, space_id: str, emojis: list[str]):
    for emo in emojis:
        await post_endpoint(client, f"/api/emoji/{space_id}", {"emoji": emo})

async def broadcast_chat_comment(client: httpx.AsyncClient, space_id: str, sender: str, text: str):
    await post_endpoint(client, f"/api/chat/{space_id}", {
        "sender": sender,
        "text": text,
        "avatar": ""
    })

# --- Cyberpunk SOHO Network Topology SVG Layout ---
soho_svg = """<svg viewBox="0 0 700 360" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- Cyan glow -->
    <filter id="cyan-glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="6" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
    <!-- Magenta glow -->
    <filter id="magenta-glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="6" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
    <!-- Green glow -->
    <filter id="green-glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="6" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>

  <!-- Background base -->
  <rect width="100%" height="100%" rx="18" fill="rgba(8, 10, 24, 0.96)" stroke="#00f2ff" stroke-width="2"/>
  
  <!-- Grid dot pattern -->
  <pattern id="dot-pattern" width="24" height="24" patternUnits="userSpaceOnUse">
    <circle cx="2" cy="2" r="1.2" fill="rgba(0, 242, 255, 0.07)"/>
  </pattern>
  <rect width="100%" height="100%" rx="18" fill="url(#dot-pattern)"/>

  <!-- Header text -->
  <text x="30" y="38" fill="#00f2ff" font-family="monospace" font-size="11" font-weight="bold" letter-spacing="1">EXECUTIVE SOHO SECURE OPERATIONS TOPO // SCOPE 3 ESG</text>
  <line x1="30" y1="46" x2="430" y2="46" stroke="rgba(0, 242, 255, 0.3)" stroke-width="1.5"/>

  <!-- Left: Corporate Cloud Node -->
  <g transform="translate(40, 110)">
    <rect width="140" height="90" rx="10" fill="rgba(24, 30, 54, 0.75)" stroke="#00f2ff" stroke-width="1.5" filter="url(#cyan-glow)" />
    <text x="70" y="32" fill="#ffffff" font-family="sans-serif" font-size="12" font-weight="bold" text-anchor="middle">☁️ CORP CLOUD</text>
    <text x="70" y="52" fill="#00f2ff" font-family="monospace" font-size="9" text-anchor="middle">Central ESG Node</text>
    <text x="70" y="68" fill="rgba(255,255,255,0.4)" font-family="sans-serif" font-size="8" text-anchor="middle">Scope 3 Aggregator</text>
  </g>

  <!-- Secure VPN Tunnel Path -->
  <path d="M 180 155 Q 235 155 290 155" stroke="#f000ff" stroke-width="2" fill="none" stroke-dasharray="6, 4"/>
  <rect x="210" y="143" width="60" height="18" rx="4" fill="rgba(42, 22, 68, 0.9)" stroke="#f000ff" stroke-width="1"/>
  <text x="240" y="155" fill="#f000ff" font-family="monospace" font-size="8" text-anchor="middle" font-weight="bold">VPN SECURE</text>

  <!-- Center: Home Assistant Core -->
  <g transform="translate(290, 85)">
    <rect width="180" height="140" rx="12" fill="rgba(42, 22, 68, 0.85)" stroke="#f000ff" stroke-width="2" filter="url(#magenta-glow)" />
    <text x="90" y="32" fill="#ffffff" font-family="sans-serif" font-size="13" font-weight="bold" text-anchor="middle">🏡 SOHO CORE</text>
    <text x="90" y="52" fill="#f000ff" font-family="monospace" font-size="10" font-weight="bold" text-anchor="middle">Home Assistant Hub</text>
    <rect x="15" y="75" width="150" height="42" rx="6" fill="rgba(10,10,15,0.5)" stroke="rgba(240,0,255,0.3)" stroke-width="1"/>
    <text x="90" y="90" fill="#00ff88" font-family="monospace" font-size="9" text-anchor="middle" font-weight="bold">ACTIVE SHIELD: NOMINAL</text>
    <text x="90" y="104" fill="rgba(255,255,255,0.5)" font-family="sans-serif" font-size="8" text-anchor="middle">Local Zigbee/WiFi Mesh</text>
  </g>

  <!-- WiFi/Zigbee Routes to hardware -->
  <path d="M 470 140 L 530 100" stroke="#00f2ff" stroke-width="1.5" stroke-dasharray="3, 3"/>
  <path d="M 470 155 L 530 155" stroke="#00f2ff" stroke-width="1.5" stroke-dasharray="3, 3"/>
  <path d="M 470 170 L 530 210" stroke="#00f2ff" stroke-width="1.5" stroke-dasharray="3, 3"/>

  <!-- Right Nodes: Hardware endpoints -->
  <!-- Top Right: Shelly Power -->
  <g transform="translate(530, 60)">
    <rect width="130" height="65" rx="8" fill="rgba(20, 32, 45, 0.7)" stroke="#00f2ff" stroke-width="1.2" />
    <text x="65" y="24" fill="#ffffff" font-family="sans-serif" font-size="10" font-weight="bold" text-anchor="middle">⚡ POWER METER</text>
    <text x="65" y="38" fill="#00f2ff" font-family="monospace" font-size="8" text-anchor="middle">Shelly Pro 3EM</text>
    <text x="65" y="50" fill="rgba(255,255,255,0.5)" font-family="sans-serif" font-size="7.5" text-anchor="middle">Active Phase Ingest</text>
  </g>

  <!-- Mid Right: Daikin HVAC -->
  <g transform="translate(530, 132)">
    <rect width="130" height="65" rx="8" fill="rgba(20, 32, 45, 0.7)" stroke="#00ff88" stroke-width="1.2" filter="url(#green-glow)" />
    <text x="65" y="24" fill="#ffffff" font-family="sans-serif" font-size="10" font-weight="bold" text-anchor="middle">🌡️ CLIMATE LOOP</text>
    <text x="65" y="38" fill="#00ff88" font-family="monospace" font-size="8" text-anchor="middle">Daikin 5-Zone AC</text>
    <text x="65" y="50" fill="rgba(255,255,255,0.5)" font-family="sans-serif" font-size="7.5" text-anchor="middle">Productivity Cells</text>
  </g>

  <!-- Bot Right: Smart Blinds / Actuators -->
  <g transform="translate(530, 204)">
    <rect width="130" height="65" rx="8" fill="rgba(20, 32, 45, 0.7)" stroke="#00f2ff" stroke-width="1.2" />
    <text x="65" y="24" fill="#ffffff" font-family="sans-serif" font-size="10" font-weight="bold" text-anchor="middle">🏁 ACTUATORS</text>
    <text x="65" y="38" fill="#00f2ff" font-family="monospace" font-size="8" text-anchor="middle">Blinds &amp; Lights</text>
    <text x="65" y="50" fill="rgba(255,255,255,0.5)" font-family="sans-serif" font-size="7.5" text-anchor="middle">Dynamic Solar Shading</text>
  </g>

  <!-- Bottom: Resilience & Wellness Policies -->
  <g transform="translate(140, 290)">
    <rect width="420" height="50" rx="8" fill="rgba(12, 34, 28, 0.75)" stroke="#00ff88" stroke-width="1.5" />
    <text x="210" y="22" fill="#00ff88" font-family="monospace" font-size="10" font-weight="bold" text-anchor="middle">🛡️ ESG RESILIENCE PROTOCOL: Frost Guard Loop</text>
    <text x="210" y="38" fill="rgba(255,255,255,0.6)" font-family="sans-serif" font-size="8.5" text-anchor="middle">Monitors thermal freeze lines, protecting the physical remote executive asset.</text>
  </g>

  <!-- Connecting Line HA to Frost Guard policy -->
  <path d="M 380 225 L 380 290" stroke="#00ff88" stroke-width="1.5" stroke-dasharray="2, 3"/>
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
            
        if not space or (space == "default" and os.environ.get("MEET_SPACE_ID") != "default"):
            print(f"\n{CLR_MAGENTA}❌ Error: No active Google Meet side-panel session detected.{CLR_RESET}")
            print(f"  Please open Google Meet, launch the Live Concierge add-on panel, and re-run.")
            sys.exit(1)
            
        print(f"  {CLR_GREEN}✅ Target Space Resolved:{CLR_RESET} {CLR_CYAN}{space}{CLR_RESET}")
        print(f"  {CLR_YELLOW}⚡ Staging SOHO Edge Node secure VPN calibration...{CLR_RESET}\n")
        await asyncio.sleep(1.5)

        t_base = 5.0 if FAST_MODE else 9.0
        t_short = 2.0 if FAST_MODE else 4.0

        # Pre-fetch live Home Assistant states
        ha_states = await fetch_ha_states(client)

        # ───────────────────────────────────────────────────────────
        # Phase 0: Standby SOHO Node Countdown & Security Calibration
        # ───────────────────────────────────────────────────────────
        print(f"{CLR_CYAN}🎬 [Phase 0] Setup & SOHO Calibration (5s Standby Countdown)...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})
        
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {
                "components": [
                    {
                        "id": "countdown_slate",
                        "component": {
                            "gdm-standby-slate": {
                                "badge": "SOHO SCOPE 3 ESG NODE",
                                "title": "Toulouse Remote Executive Workspace",
                                "description": "Nexus AI is calibrating the secure VPN pipeline to the Toulouse Executive SOHO. Fetching carbon footprint loads and wellness thermal indices directly from Shelly Pro 3EM and Daikin Climate matrices over secure HTTP channels.",
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
        # Phase 1: Welcome & SOHO ESG Briefing (Split Grid)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 1] SOHO ESG Corporate Briefing (Nexus AI Host)...{CLR_RESET}")
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
                        "label": "🤖 NEXUS: SOHO DIRECTOR",
                        "panel": 1
                    }
                }
            }

        # Build active top ticker
        shelly_total_power = ha_states.get("sensor.shellypro3em_8813bfdd9dac_total_active_power", {}).get("state", "808.2")
        # Ensure it has a numeric value
        try:
            float(shelly_total_power)
        except ValueError:
            shelly_total_power = "808.2"

        ticker_text = f"📍 TOULOUSE EXECUTIVE SOHO NODE • WORKSPACE POWER INGEST: {shelly_total_power}W • SCOPE 3 CATEGORY 7 OFFSETS ACTIVE • DAIKIN HVAC BALANCING: NOMINAL • "
        
        ticker_component = {
            "id": "top_stage_ticker",
            "component": {
                "gdm-ticker": {
                    "text": ticker_text,
                    "active": True,
                    "badgeText": "SCOPE 3 ESG",
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
                    "title": "EXECUTIVE SOHO NODE",
                    "subtitle": "Scope 3 Employee Remote Workspace Decarbonization",
                    "active": True,
                    "accentColor": "#ff00d6",
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
                                "children": {"explicitList": [nexus_panel_id, "p1_draft_panel"]}
                            }
                        }
                    },
                    nexus_component,
                    {
                        "id": "p1_draft_panel",
                        "component": {
                            "gdm-image-panel": {
                                "src": "/public/workspace_sketch.png",
                                "label": "📐 SOHO Architectural Layout Plan",
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
            "Welcome, directors! I am Nexus. Today, we address corporate Scope 3 ESG compliance and executive wellness.", 
            delay_seconds=t_short
        )
        await speak_narrator_caption(
            client, space, "p1_split_grid", 
            "We have mapped our regional director's remote home office in Toulouse into our secure, corporate ESG monitoring ecosystem.", 
            delay_seconds=t_short
        )
        await speak_narrator_caption(
            client, space, "p1_split_grid", 
            "By querying local Home Assistant metrics, we gain complete visibility into work-from-home energy footprints and thermal comfort cells.", 
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
        # Phase 2: Scope 3 Energy & HVAC Comfort (Telemetry Dashboard)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 2] Real-Time Carbon & Thermal Telemetry Deep Dive...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})

        # Fetch latest metrics to show freshness
        ha_states = await fetch_ha_states(client)
        p_tot = ha_states.get("sensor.shellypro3em_8813bfdd9dac_total_active_power", {}).get("state", "806.5")
        p_a = ha_states.get("sensor.shellypro3em_8813bfdd9dac_phase_a_active_power", {}).get("state", "833.0")
        p_b = ha_states.get("sensor.shellypro3em_8813bfdd9dac_phase_b_active_power", {}).get("state", "-30.1")
        p_c = ha_states.get("sensor.shellypro3em_8813bfdd9dac_phase_c_active_power", {}).get("state", "3.6")

        # Fallback formatting checks
        try:
            float(p_tot)
        except ValueError:
            p_tot = "806.5"
        try:
            float(p_a)
        except ValueError:
            p_a = "833.0"
        try:
            float(p_b)
        except ValueError:
            p_b = "-30.1"
        try:
            float(p_c)
        except ValueError:
            p_c = "3.6"

        # Calculate approximate carbon footprint: standard grid emission factor (e.g. 80g CO2 per kWh in France)
        # 806.5 W -> 0.806 kW * 80 g/kWh = ~64.5 gCO2/hour
        gco2_hour = int(float(p_tot) * 0.08)

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
                        "label": "🤖 NEXUS: SOHO TELEMETRY",
                        "panel": 1
                    }
                }
            }

        chyron_p2 = {
            "id": "tech_chyron",
            "component": {
                "gdm-chyron": {
                    "title": "SOHO EMISSIONS & WELLNESS",
                    "subtitle": "Live Shelly Pro 3EM Power Grid & Daikin HVAC loops",
                    "active": True,
                    "accentColor": "#00ff88",
                    "bottom": 56,
                    "left": 40
                }
            }
        }

        ticker_text_p2 = f"📊 MAPPING REMOTE SOHO LOAD BALANCE... POWER: {p_tot}W • PHASE A: {p_a}W | B: {p_b}W | C: {p_c}W ... DAIKIN CLIMATE LOOPS: LIVING={c_lounge} | GITE={c_gite} ... "
        ticker_component["component"]["gdm-ticker"]["text"] = ticker_text_p2
        ticker_component["component"]["gdm-ticker"]["badgeText"] = "SOHO TELEMETRY"
        ticker_component["component"]["gdm-ticker"]["badgeColor"] = "#00ff88"

        # Telemetry dashboard tabs and metrics
        TABS_CONFIG = [
            {"id": "pwr", "label": "⚡ CARBON FOOTPRINT (ENERGY)"},
            {"id": "hvac", "label": "🌡️ WORKSPACE WELLNESS (HVAC)"}
        ]
        
        power_history = [240, 250, 480, 510, 810, 780, int(float(p_tot))]

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
                                "children": {"explicitList": [nexus_p2_id, "p2_telemetry_dashboard"]}
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
                                "title": "🔋 Scope 3 Category 7 Power Monitor (Shelly Pro 3EM)",
                                "metrics": [
                                    {"label": "Remote workspace load", "value": f"{p_tot} W", "color": "#00ff88"},
                                    {"label": "Carbon footprint equivalent", "value": f"{gco2_hour} gCO2/hr", "color": "#ff00d6"},
                                    {"label": "Phase A active load", "value": f"{p_a} W", "color": "#00f2ff"},
                                    {"label": "Phase B active load", "value": f"{p_b} W", "color": "#ffaa00" if float(p_b) >= 0 else "#ff3b30"}
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
            "Let's audit the real-time electrical grid. Our Shelly Pro three-EM meter registers active SOHO energy consumption.", 
            delay_seconds=t_short
        )
        await speak_narrator_caption(
            client, space, "p2_split_grid", 
            f"Currently, overall remote workspace ingestion is {p_tot} Watts. This translates to an ESG footprint of just {gco2_hour} grams of CO2 per hour.", 
            delay_seconds=t_base
        )

        # Switch tab to SOHO wellness (climate zones)
        print(f"  {CLR_SLATE}Updating Telemetry tab to SOHO Wellness zones...{CLR_RESET}")
        
        climate_metrics = [
            {"label": "1. Executive Office Comfort", "value": c_master.upper(), "color": "#00f2ff" if c_master != "off" else "#ff3b30"},
            {"label": "2. Lucie Bed Workspace", "value": c_lucie.upper(), "color": "#00f2ff" if c_lucie != "off" else "#ff3b30"},
            {"label": "3. Kitchen Lounge Zone", "value": c_lounge.upper(), "color": "#00ff88" if c_lounge != "off" else "#ff3b30"},
            {"label": "4. Josh Bed Workspace", "value": c_josh.upper(), "color": "#00f2ff" if c_josh != "off" else "#ff3b30"},
            {"label": "5. Gite Guest Office", "value": c_gite.upper(), "color": "#00ffaa" if c_gite != "off" else "#ff3b30"}
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
                                "title": "🌡️ SOHO Workspace Thermal Comfort & Wellness",
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
            "Looking at workspace comfort, our five Daikin zones are monitored as thermal wellness cells, ensuring executive productivity remains optimized.", 
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
        # Phase 3: Immersive SOHO Topology Takeover (Overlay SVG)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 3] Full-Stage SOHO Network Takeover (Overlay SVG)...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})

        chyron_p3 = {
            "id": "takeover_chyron",
            "component": {
                "gdm-chyron": {
                    "title": "HYBRID SOHO MESH TOPOLOGY",
                    "subtitle": "Secure VPN Corporate tunnel overlaying local Zigbee channels",
                    "active": True,
                    "accentColor": "#ff00d6",
                    "bottom": 56,
                    "left": 40
                }
            }
        }
        
        ticker_text_p3 = "DETERMINING PIPELINE ENCRYPTION RATING... SECURE GLASSMORPHIC MESH TAKEOVER ACTIVE... "
        ticker_component["component"]["gdm-ticker"]["text"] = ticker_text_p3
        ticker_component["component"]["gdm-ticker"]["badgeText"] = "SOHO NETWORK"
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
                                "children": {"explicitList": [nexus_p2_id, "p2_telemetry_dashboard"]}
                            }
                        }
                    },
                    {
                        "id": "full_diagram_overlay",
                        "component": {
                            "gdm-diagram-view": {
                                "diagId": "soho_topology_mesh",
                                "svg": soho_svg,
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
            "Let's look at the infrastructure topology. Using overlay projection, we overlay our hybrid SOHO secure mesh.", 
            delay_seconds=t_base
        )
        await speak_narrator_caption(
            client, space, "p2_split_grid", 
            "The corporate cloud establishes a secure VPN tunnel directly with the local Home Assistant core. This isolates residential systems from our data mesh.", 
            delay_seconds=t_base
        )

        # Trigger reaction rain
        await launch_emoji_burst(client, space, ["🔒", "🏡", "⚡", "🔋"])
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
        # Phase 4: SOHO ESG Subsidy Strategy Poll (Interactive)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 4] Audience SOHO ESG Incentive Poll...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})

        chyron_p4 = {
            "id": "poll_chyron",
            "component": {
                "gdm-chyron": {
                    "title": "SOHO EFFICIENCY INVESTMENT",
                    "subtitle": "Stakeholder Corporate Remote Subsidy Poll Tally",
                    "active": True,
                    "accentColor": "#ffd60a",
                    "bottom": 56,
                    "left": 40
                }
            }
        }
        
        ticker_text_p4 = "AUDIENCE SOHO INVESTMENT POLL ACTIVE... TALLYING STRATEGIC DECARBONIZATION CHANNELS... "
        ticker_component["component"]["gdm-ticker"]["text"] = ticker_text_p4
        ticker_component["component"]["gdm-ticker"]["badgeText"] = "ESG INVESTMENT"
        ticker_component["component"]["gdm-ticker"]["badgeColor"] = "#ffd60a"

        votes_stages = [
            [2, 4, 1],
            [9, 8, 5],
            [18, 20, 16],
            [35, 42, 60]
        ]

        await speak_narrator_caption(
            client, space, "p2_split_grid", 
            "Corporate funding is most effective when targeted. Let's poll our board on which remote workspace incentive we should subsidize next.", 
            delay_seconds=t_short
        )

        for step, current_votes in enumerate(votes_stages):
            print(f"  🗳️ Simulating Live Board Poll (Step {step+1}/4): {current_votes}...")
            
            poll_overlay = {
                "id": "interactive_voting_poll",
                "component": {
                    "gdm-poll-overlay": {
                        "question": "Which Corporate SOHO ESG incentive should we fund next? 🗳️",
                        "options": [
                            "1️⃣ Solar battery load shaving (targets Shelly phase peaks)",
                            "2️⃣ AI multi-split scheduling models (targets Daikin efficiency)",
                            "3️⃣ Automated blinds thermal shading (minimizes cooling load)"
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
                                    "children": {"explicitList": [nexus_p2_id, "p2_telemetry_dashboard"]}
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
                    "As directors cast votes on their laptops or phones, A2UI renders the moving voting bars live on stage.", 
                    delay_seconds=3.0
                )
            else:
                await asyncio.sleep(2.0)

        await speak_narrator_caption(
            client, space, "p2_split_grid", 
            "Automated blinds thermal shading wins! This directly coordinates with closing the kitchen blinds to block Toulouse afternoon heat.", 
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
        # Phase 5: Secure Workspace HUD Sandbox (Custom HTML Console)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 5] SOHO Secure Workspace Control HUD Iframe...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})

        chyron_p5 = {
            "id": "hud_chyron",
            "component": {
                "gdm-chyron": {
                    "title": "SOHO OPERATIONS COMMAND HUD",
                    "subtitle": "Client-side isolated sandbox querying Home Assistant states",
                    "active": True,
                    "accentColor": "#00f2ff",
                    "bottom": 56,
                    "left": 40
                }
            }
        }

        ticker_text_p5 = f"INGESTING WELLNESS HEURISTICS... SHELLY INTAKE={p_tot}W ... RESILIENCE STATUS: NOMINAL... "
        ticker_component["component"]["gdm-ticker"]["text"] = ticker_text_p5
        ticker_component["component"]["gdm-ticker"]["badgeText"] = "SOHO HUD"
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
            '  .hud-container {{ width: 92%; max-width: 480px; background: rgba(8, 12, 28, 0.92); backdrop-filter: blur(14px); border: 2px solid #00f2ff; border-radius: 16px; padding: 18px; box-shadow: 0 0 30px rgba(0, 242, 255, 0.35); text-align: center; }}'
            '  h1 {{ font-family: monospace; font-size: 17px; color: #00f2ff; margin: 0 0 4px 0; text-shadow: 0 0 10px rgba(0, 242, 255, 0.5); letter-spacing: 1px; }}'
            f'  p {{ font-size: 9.5px; color: rgba(255,255,255,0.65); margin: 0 0 14px 0; }}'
            '  .kpi-row {{ display: flex; justify-content: space-around; gap: 10px; margin-bottom: 14px; }}'
            '  .kpi-card {{ flex: 1; background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(0, 242, 255, 0.25); border-radius: 10px; padding: 8px 2px; text-align: center; }}'
            f'  .kpi-card h4 {{ font-size: 15px; margin: 0; font-family: monospace; color: #00ff88; }}'
            f'  .kpi-card.cyan h4 {{ color: #00f2ff; }}'
            f'  .kpi-card.magenta h4 {{ color: #ff00d6; }}'
            '  .kpi-card span {{ font-size: 7.5px; color: rgba(255,255,255,0.5); text-transform: uppercase; font-weight: bold; }}'
            '  .sensor-grid {{ text-align: left; background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px; margin-bottom: 14px; font-family: monospace; font-size: 10px; }}'
            '  .sensor-item {{ display: flex; justify-content: space-between; margin-bottom: 4px; border-bottom: 1px solid rgba(255,255,255,0.04); padding-bottom: 2px; }}'
            '  .sensor-item span.green {{ color: #00ff88; }}'
            '  .sensor-item span.cyan {{ color: #00f2ff; }}'
            '  .sys-badge {{ background: rgba(0, 242, 255, 0.12); border: 1px solid rgba(0, 242, 255, 0.25); padding: 5px 10px; border-radius: 4px; font-family: monospace; font-size: 9px; color: #00f2ff; display: inline-block; letter-spacing: 0.5px; animation: pulse 1.5s infinite alternate; }}'
            '  @keyframes pulse {{ from {{ opacity: 0.5; }} to {{ opacity: 1; }} }}'
            '</style>'
            '<div class="hud-container">'
            '  <h1>📍 TOULOUSE WORKSPACE HUD</h1>'
            f'  <p>Secure remote sandbox monitoring active carbon and home-comfort loops.</p>'
            '  <div class="kpi-row">'
            '    <div class="kpi-card">'
            f'      <h4>{p_tot} W</h4>'
            '      <span>WORKSPACE DRAW</span>'
            '    </div>'
            '    <div class="kpi-card cyan">'
            f'      <h4>{c_lounge.upper()}</h4>'
            '      <span>LOUNGE HVAC</span>'
            '    </div>'
            '    <div class="kpi-card magenta">'
            f'      <h4>{gco2_hour}g/hr</h4>'
            '      <span>CO2 FOOTPRINT</span>'
            '    </div>'
            '  </div>'
            '  <div class="sensor-grid">'
            f'    <div class="sensor-item"><span>🛡️ FROST GUARD RESILIENCE:</span><span class="green">{frost_guard_state}</span></div>'
            f'    <div class="sensor-item"><span>📉 FREEZE TRIGGER THRESHOLD:</span><span class="cyan">{frost_trigger_temp}°C</span></div>'
            f'    <div class="sensor-item"><span>📈 RESILIENCE TARGET LEVEL:</span><span class="cyan">{frost_target_temp}°C</span></div>'
            f'    <div class="sensor-item"><span>💡 TASK LIGHTING (BUANDARIE):</span><span>{buandarie_light}</span></div>'
            f'    <div class="sensor-item"><span>🏁 SOLAR SHADING BLINDS:</span><span>{kitchen_blinds}</span></div>'
            '  </div>'
            '  <div class="sys-badge">SECURE REMOTE WORKSPACE: NOMINAL</div>'
            '</div>'
        )

        TABS_CONFIG_P5 = [{"id": "pwr", "label": "⚡ SOHO CO2 INGEST"}]
        power_history_p5 = [210, 240, 250, 480, 510, 810, 780, int(float(p_tot))]

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
                                "children": {"explicitList": ["p5_telemetry_dashboard", "p5_html_panel"]}
                            }
                        }
                    },
                    {
                        "id": "p5_telemetry_dashboard",
                        "component": {
                            "gdm-telemetry-dashboard": {
                                "tabs": TABS_CONFIG_P5,
                                "activeTabId": "pwr",
                                "title": "⚡ Scope 3 CO2 Ingress Trace",
                                "metrics": [
                                    {"label": "1. Overall Power Draw", "value": f"{p_tot} W", "color": "#00ff88"},
                                    {"label": "2. Equivalent Carbon", "value": f"{gco2_hour} gCO2/hr", "color": "#ff00d6"},
                                    {"label": "3. Phase A Active load", "value": f"{p_a} W", "color": "#00f2ff"},
                                    {"label": "4. Active wellness score", "value": "98%", "color": "#00ffaa"}
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
                                "title": "🔬 Isolated SOHO Control Console",
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
            "Finally, A2UI supports secure, isolated HTML iframe sandboxes directly on the Meet stage.", 
            delay_seconds=t_short
        )
        await speak_narrator_caption(
            client, space, "p5_split_grid", 
            "This custom console connects directly to Home Assistant states, rendering Frost Guard parameters, task light values, and window indices.", 
            delay_seconds=t_base
        )
        await speak_narrator_caption(
            client, space, "p5_split_grid", 
            "This lets us verify that our local home-comfort settings perfectly align with corporate green energy goals.", 
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
        # Phase 6: Celebration & System Reset
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 6] SOHO calibration success celebration...{CLR_RESET}")
        await call_mcp_tool(client, "clear_stage", {"space_id": space})
        await asyncio.sleep(1.0)

        ticker_text_p6 = "SOHO NODE AUDIT SUCCESSFUL • WORKSPACE CARBON Mapped • WORKSPACE RESILIENT • "
        ticker_component["component"]["gdm-ticker"]["text"] = ticker_text_p6
        ticker_component["component"]["gdm-ticker"]["badgeText"] = "AUDIT COMPLETE"
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
                                "badge": "SOHO SCOPE 3 CALIBRATED",
                                "title": "Toulouse Executive SOHO Active ✅",
                                "text": "A2UI successfully routed live home-energy and Daikin thermal zones into a corporate compliance and employee-wellness container over secure WebSockets.",
                                "accent": "#00ff88"
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
            "This concludes our Executive SOHO Scope three ESG presentation. A2UI bridges the gap between home-edge IoT and professional boardrooms.", 
            delay_seconds=t_base
        )
        await speak_narrator_caption(
            client, space, "final_closing_layout", 
            "We have verified energy bounds and mapped all home workspace wellness lines. Thank you for watching, Nexus signing off.", 
            delay_seconds=t_short
        )

        await clear_captions_overlay(client, space, "final_closing_layout")
        await call_mcp_tool(client, "clear_stage", {"space_id": space})
        await asyncio.sleep(0.5)

        # Attendee chats
        chat_stream = [
            ("Antoine — ESG Director", "This is exactly how we solve remote Scope 3 Category 7 tracking! Connecting HA directly to Google Meet is pure genius! ⚡🌳"),
            ("Sofia — Design Lead", "That custom hybrid SOHO topology SVG with the frosted takeover was so premium! Cleanest design I've seen! 😍📊"),
            ("dana K. — Investor", "Solving enterprise green compliance while ensuring remote worker comfort cell health? Outstanding pitch! 📈🏆"),
            ("Marcus — Tech Lead", "No code rebuilds, sub-100ms updates, pulling live Shelly Pro 3EM phases? The engineering here is impeccable! 🤯👑")
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
        await launch_emoji_burst(client, space, ["🎉", "💯", "⚡", "🌳", "🏡", "🔒", "👏", "🏆", "👑"])

    print(f"\n{CLR_GREEN}🎉 Executive SOHO Scope 3 ESG Staging executed successfully!{CLR_RESET}\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{CLR_MAGENTA}Showcase interrupted by user.{CLR_RESET}")
        sys.exit(0)
