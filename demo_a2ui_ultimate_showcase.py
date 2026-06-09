#!/usr/bin/env python3
"""
Meet Live Concierge — Algorithmic Swing-Trading Portfolio & Bot Staging (A2UI v0.8)
==================================================================================
Orchestrates an ultra-premium, finance-focused demonstration of our Google Meet Stage.
Nexus, our autonomous AI robot host, guides the corporate board through real-time portfolio 
holdings, cash positions, and algorithmic indicators pulled live via the Trading 212 API.

Phases:
0. Setup & Broker Calibration (5s Standby Countdown + Trading Mesh Initialization)
1. Welcome & Market Briefing (Nexus Split Grid with live portfolio values scrolling)
2. Live Portfolio & Asset Telemetry (Real-time Trading 212 Cash Balances & Positions)
3. Algorithmic Service Mesh Topology (Frosted Topology SVG Overlay of the Python Bot)
4. Strategic Priority Poll (Interactive audience voting on momentum vs mean reversion)
5. Secure Command Cockpit HUD (Futuristic Neon Portfolio HUD Iframe Console)
6. Nominal Close & Verification (Celebratory chats, applause, nominal stage clear)
"""

import asyncio
import os
import sys
import glob
import base64
import httpx
from dotenv import load_dotenv

# --- Auto-Resolve Local Virtualenv Site-Packages ---
_base_dir = os.path.dirname(os.path.abspath(__file__))
_venv_dirs = glob.glob(os.path.join(_base_dir, "venv", "lib", "python3.*", "site-packages"))
for _vd in _venv_dirs:
    if _vd not in sys.path:
        sys.path.insert(0, _vd)

# Load workspace env
load_dotenv(os.path.join(_base_dir, "../../.env"))

# --- Configuration & Environment Setup ---
API_URL = os.environ.get("CONCIERGE_API_URL") or exit("CONCIERGE_API_URL not set — see .env.production.sample")
KEY = os.environ.get("STAGE_API_KEY") or exit("STAGE_API_KEY required — export it before running this script")
FAST_MODE = os.environ.get("FAST_MODE", "false").lower() not in ("0", "false", "no")

T212_API_KEY = os.environ.get("T212_API_KEY")
T212_API_SECRET = os.environ.get("T212_API_SECRET")

# --- ANSI Terminal Colors ---
CLR_CYAN = "\033[38;5;51m"
CLR_MAGENTA = "\033[38;5;201m"
CLR_GREEN = "\033[38;5;82m"
CLR_YELLOW = "\033[38;5;220m"
CLR_SLATE = "\033[38;5;244m"
CLR_RESET = "\033[0m"

def print_banner():
    print(f"\n{CLR_CYAN}  ==============================================================={CLR_RESET}")
    print(f"{CLR_CYAN}  ▲   A L G O R I T H M I C   P O R T F O L I O   S H O W C A S E   ▲{CLR_RESET}")
    print(f"{CLR_CYAN}  ==============================================================={CLR_RESET}")
    print(f"  {CLR_SLATE}Trading 212 Live API Integration, Cloud Run, & Multi-Source Feeds{CLR_RESET}")
    print(f"  {CLR_SLATE}Deployment Server:{CLR_RESET} {CLR_CYAN}{API_URL}{CLR_RESET}\n")

# --- Trading 212 API Data Ingest ---
def get_mock_t212_data() -> dict:
    """High-fidelity simulation model representing current positions and balances."""
    return {
        "cash": {
            "free": 41975.78,
            "total": 50171.62,
            "ppl": 95.38,
            "result": 117.58,
            "invested": 8100.46
        },
        "portfolio": [
            {'ticker': 'FN_US_EQ', 'quantity': 1.57, 'averagePrice': 634.13, 'currentPrice': 677.89, 'ppl': 70.24},
            {'ticker': 'VST_US_EQ', 'quantity': 3.54, 'averagePrice': 141.20, 'currentPrice': 164.77, 'ppl': 74.40},
            {'ticker': 'HUBB_US_EQ', 'quantity': 10.1745, 'averagePrice': 491.94, 'currentPrice': 477.18, 'ppl': -81.79},
            {'ticker': 'NFLX_US_EQ', 'quantity': 21.31, 'averagePrice': 87.99, 'currentPrice': 87.70, 'ppl': 5.01},
            {'ticker': 'ETN_US_EQ', 'quantity': 1.2776, 'averagePrice': 400.64, 'currentPrice': 405.69, 'ppl': 5.65},
            {'ticker': 'MCp_EQ', 'quantity': 0.1, 'averagePrice': 452.00, 'currentPrice': 469.20, 'ppl': 1.72},
            {'ticker': 'GEV_US_EQ', 'quantity': 0.48, 'averagePrice': 1042.16, 'currentPrice': 1077.90, 'ppl': 20.44}
        ]
    }

async def fetch_t212_data(client: httpx.AsyncClient) -> dict:
    """Queries live account cash and portfolio data from Trading 212 API."""
    if not T212_API_KEY or not T212_API_SECRET:
        print(f"  {CLR_SLATE}ℹ️ Trading 212 credentials not set in .env. Using high-fidelity portfolio model.{CLR_RESET}")
        return get_mock_t212_data()

    auth_str = f"{T212_API_KEY}:{T212_API_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
    headers = {"Authorization": f"Basic {auth_b64}"}
    base_url = "https://demo.trading212.com/api/v0"

    try:
        cash_resp = await client.get(f"{base_url}/equity/account/cash", headers=headers, timeout=5)
        portfolio_resp = await client.get(f"{base_url}/equity/portfolio", headers=headers, timeout=5)
        
        if cash_resp.status_code == 200 and portfolio_resp.status_code == 200:
            print(f"  {CLR_GREEN}✅ Successfully fetched live Trading 212 balances and positions!{CLR_RESET}")
            return {
                "cash": cash_resp.json(),
                "portfolio": portfolio_resp.json()
            }
        else:
            print(f"  {CLR_SLATE}⚠️ T212 returned non-200. Cash Status: {cash_resp.status_code}, Portfolio Status: {portfolio_resp.status_code}. Using portfolio simulation.{CLR_RESET}")
    except Exception as e:
        print(f"  {CLR_SLATE}⚠️ T212 Connection error ({e}). Using portfolio simulation fallback.{CLR_RESET}")
        
    return get_mock_t212_data()

# --- A2UI and Stage Orchestration Utility Handlers ---
async def get_active_space(client: httpx.AsyncClient) -> str:
    headers = {"Authorization": f"Bearer {KEY}"} if KEY else {}
    try:
        resp = await client.get(f"{API_URL}/api/active-spaces", headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            sessions = data.get("active_sessions", [])
            listeners = data.get("stage_listeners", {})
            return sessions[0] if sessions else (list(listeners.keys())[0] if listeners else "")
    except Exception:
        return ""
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
        "id": "t212-showcase-mcp",
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
    # Deploy visual glassmorphic subtitle bar on the main stage
    await call_mcp_tool(client, "render_stage", {
        "space_id": space_id,
        "surfaceUpdate": {
            "components": [
                {
                    "id": "live_captions_overlay",
                    "component": {
                        "gdm-captions": {
                            "text": text,
                            "speaker": "NEXUS // PORTFOLIO MANAGER",
                            "active": True,
                            "accentColor": "#00f2ff"
                        }
                    }
                }
            ]
        },
        "root": root_id
    })
    # Also trigger high-fidelity AI Speech synthesis to Meet stage audio and automatic WebSocket captioning
    await post_endpoint(client, f"/api/speak/{space_id}", {"text": text})
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

# --- Cyberpunk Trading Bot Topology SVG ---
trading_svg = """<svg viewBox="0 0 700 360" xmlns="http://www.w3.org/2000/svg">
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
  <text x="30" y="38" fill="#00f2ff" font-family="monospace" font-size="11" font-weight="bold" letter-spacing="1">AUTOMATED SWING-TRADING MESH // TRADING 212 INTEGRATION</text>
  <line x1="30" y1="46" x2="445" y2="46" stroke="rgba(0, 242, 255, 0.3)" stroke-width="1.5"/>

  <!-- Left: Cloud Scheduler Trigger -->
  <g transform="translate(40, 110)">
    <rect width="130" height="90" rx="10" fill="rgba(24, 30, 54, 0.75)" stroke="#00f2ff" stroke-width="1.5" filter="url(#cyan-glow)" />
    <text x="65" y="32" fill="#ffffff" font-family="sans-serif" font-size="12" font-weight="bold" text-anchor="middle">⏱️ SCHEDULER</text>
    <text x="65" y="52" fill="#00f2ff" font-family="monospace" font-size="9" text-anchor="middle">4 Daily Scans</text>
    <text x="65" y="68" fill="rgba(255,255,255,0.4)" font-family="sans-serif" font-size="8" text-anchor="middle">EU &amp; US Market Runs</text>
  </g>

  <!-- Trigger Link -->
  <path d="M 170 155 Q 225 155 280 155" stroke="#f000ff" stroke-width="2" fill="none" stroke-dasharray="6, 4"/>
  <rect x="195" y="143" width="60" height="18" rx="4" fill="rgba(42, 22, 68, 0.9)" stroke="#f000ff" stroke-width="1"/>
  <text x="225" y="155" fill="#f000ff" font-family="monospace" font-size="8" text-anchor="middle" font-weight="bold">TRIGGER</text>

  <!-- Center: Cloud Run Bot Core -->
  <g transform="translate(280, 85)">
    <rect width="180" height="140" rx="12" fill="rgba(42, 22, 68, 0.85)" stroke="#f000ff" stroke-width="2" filter="url(#magenta-glow)" />
    <text x="90" y="32" fill="#ffffff" font-family="sans-serif" font-size="13" font-weight="bold" text-anchor="middle">🤖 CLOUD RUN CORE</text>
    <text x="90" y="52" fill="#f000ff" font-family="monospace" font-size="10" font-weight="bold" text-anchor="middle">Trading212 Bot API</text>
    <rect x="15" y="75" width="150" height="42" rx="6" fill="rgba(10,10,15,0.5)" stroke="rgba(240,0,255,0.3)" stroke-width="1"/>
    <text x="90" y="90" fill="#00ff88" font-family="monospace" font-size="9" text-anchor="middle" font-weight="bold">STATUS: COMPLIANT</text>
    <text x="90" y="104" fill="rgba(255,255,255,0.5)" font-family="sans-serif" font-size="8" text-anchor="middle">RSI-14 &amp; Bollinger-20</text>
  </g>

  <!-- Data & API Links -->
  <path d="M 460 140 L 530 100" stroke="#00f2ff" stroke-width="1.5" stroke-dasharray="3, 3"/>
  <path d="M 460 155 L 530 155" stroke="#00ff88" stroke-width="1.5" stroke-dasharray="3, 3"/>
  <path d="M 460 170 L 530 210" stroke="#00f2ff" stroke-width="1.5" stroke-dasharray="3, 3"/>

  <!-- Right Nodes: External Integrations -->
  <!-- Top Right: Market Pricing -->
  <g transform="translate(530, 60)">
    <rect width="130" height="65" rx="8" fill="rgba(20, 32, 45, 0.7)" stroke="#00f2ff" stroke-width="1.2" />
    <text x="65" y="24" fill="#ffffff" font-family="sans-serif" font-size="10" font-weight="bold" text-anchor="middle">📊 PRICE FEEDS</text>
    <text x="65" y="38" fill="#00f2ff" font-family="monospace" font-size="8" text-anchor="middle">TwelveData &amp; yFinance</text>
    <text x="65" y="50" fill="rgba(255,255,255,0.5)" font-family="sans-serif" font-size="7.5" text-anchor="middle">Multi-Source OHLCV</text>
  </g>

  <!-- Mid Right: Trading 212 Broker -->
  <g transform="translate(530, 132)">
    <rect width="130" height="65" rx="8" fill="rgba(20, 32, 45, 0.7)" stroke="#00ff88" stroke-width="1.2" filter="url(#green-glow)" />
    <text x="65" y="24" fill="#ffffff" font-family="sans-serif" font-size="10" font-weight="bold" text-anchor="middle">💼 TRADING 212</text>
    <text x="65" y="38" fill="#00ff88" font-family="monospace" font-size="8" text-anchor="middle">Execution API</text>
    <text x="65" y="50" fill="rgba(255,255,255,0.5)" font-family="sans-serif" font-size="7.5" text-anchor="middle">Demo Broker Account</text>
  </g>

  <!-- Bot Right: Google Chat Webhook -->
  <g transform="translate(530, 204)">
    <rect width="130" height="65" rx="8" fill="rgba(20, 32, 45, 0.7)" stroke="#00f2ff" stroke-width="1.2" />
    <text x="65" y="24" fill="#ffffff" font-family="sans-serif" font-size="10" font-weight="bold" text-anchor="middle">💬 NOTIFIER</text>
    <text x="65" y="38" fill="#00f2ff" font-family="monospace" font-size="8" text-anchor="middle">Google Chat Space</text>
    <text x="65" y="50" fill="rgba(255,255,255,0.5)" font-family="sans-serif" font-size="7.5" text-anchor="middle">Webhook Dispatcher</text>
  </g>

  <!-- Bottom: Risk Management Protocols -->
  <g transform="translate(140, 290)">
    <rect width="420" height="50" rx="8" fill="rgba(12, 34, 28, 0.75)" stroke="#00ff88" stroke-width="1.5" />
    <text x="210" y="22" fill="#00ff88" font-family="monospace" font-size="10" font-weight="bold" text-anchor="middle">🛡️ ALGORITHMIC RISK PROTOCOL: SL/TP Guard</text>
    <text x="210" y="38" fill="rgba(255,255,255,0.6)" font-family="sans-serif" font-size="8.5" text-anchor="middle">Enforces stop-loss / take-profit margins, protecting active capital allocations.</text>
  </g>

  <!-- Connecting Line core to Risk policy -->
  <path d="M 370 225 L 370 290" stroke="#00ff88" stroke-width="1.5" stroke-dasharray="2, 3"/>
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
        print(f"  {CLR_YELLOW}⚡ Staging Trading Engine secure API calibration...{CLR_RESET}\n")
        await asyncio.sleep(1.5)

        t_base = 5.0 if FAST_MODE else 9.0
        t_short = 2.0 if FAST_MODE else 4.0

        # Fetch live Trading 212 account data
        t212_data = await fetch_t212_data(client)
        cash = t212_data["cash"]
        portfolio = t212_data["portfolio"]

        # Parse balance values
        tot_value = cash.get("total", 50171.62)
        free_cash = cash.get("free", 41975.78)
        invested = cash.get("invested", 8100.46)
        ppl = cash.get("ppl", 95.38)
        net_result = cash.get("result", 117.58)

        # Build position tickers text
        tickers_list = [p["ticker"].replace("_US_EQ", "").replace("_EQ", "") for p in portfolio]
        tickers_str = ", ".join(tickers_list)

        # ───────────────────────────────────────────────────────────
        # Phase 0: Standby Broker Countdown & Security Calibration
        # ───────────────────────────────────────────────────────────
        print(f"{CLR_CYAN}🎬 [Phase 0] Setup & T212 Calibration (5s Standby Countdown)...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})
        
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {
                "components": [
                    {
                        "id": "countdown_slate",
                        "component": {
                            "gdm-standby-slate": {
                                "badge": "ALGORITHMIC TRADING NETWORK",
                                "title": "Trading 212 API Node Calibration",
                                "description": "Nexus AI is calibrating secure REST communication pipelines to the Trading 212 Broker API. Synchronizing real-time portfolio assets, cash vectors, and multi-source pricing indicators.",
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

        # ───────────────────────────────────────────────────────────
        # Phase 1: Welcome & Algorithmic Market Briefing (Split Grid)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 1] Welcome & Market Briefing (Split Grid Layout)...{CLR_RESET}")
        
        # Deploy global stock ticker at the top
        ticker_text = f"📍 TRADING 212 LIVE INTEGRATION • PORTFOLIO VALUE: {tot_value:,.2f} EUR • FREE CASH: {free_cash:,.2f} EUR • INVESTED: {invested:,.2f} EUR • ACTIVE HOLDINGS: {tickers_str} • NET UNREALIZED GAINS: +{net_result:,.2f} EUR • "
        
        ticker_component = {
            "id": "global_top_ticker",
            "component": {
                "gdm-ticker": {
                    "text": ticker_text,
                    "speed": "normal",
                    "badgeText": "T212 BROKER",
                    "badgeColor": "#f000ff"
                }
            }
        }

        # Check for robot video files, else use static news anchor image fallback
        video_intro_exists = os.path.exists(os.path.join(_base_dir, "public", "robot_video_intro.mp4"))
        nexus_component_id = "nexus_intro_panel"
        
        if video_intro_exists:
            nexus_component = {
                "id": nexus_component_id,
                "component": {
                    "gdm-video-panel": {"src": "/public/robot_video_intro.mp4", "autoplay": True, "panel": 1}
                }
            }
        else:
            nexus_component = {
                "id": nexus_component_id,
                "component": {
                    "gdm-image-panel": {"src": "/public/robot_news_anchor.png", "label": "Nexus AI // Autonomous Bot Host"}
                }
            }

        # Background workspace asset image
        blueprint_component = {
            "id": "draft_blueprint_board",
            "component": {
                "gdm-image-panel": {"src": "/public/workspace_sketch.png", "label": "Trading Strategy Workspace Setup"}
            }
        }

        # Assemble the initial split-screen stage layout grid
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {
                "components": [
                    {
                        "id": "p1_split_grid",
                        "component": {
                            "gdm-stage-grid": {
                                "layout": "split",
                                "focusedPanel": "nexus_intro_panel",
                                "children": ["global_top_ticker", nexus_component_id, "draft_blueprint_board"]
                            }
                        }
                    },
                    ticker_component,
                    nexus_component,
                    blueprint_component
                ]
            },
            "root": "p1_split_grid"
        })

        await asyncio.sleep(2.0)

        # Trigger lower-third chyron
        chyron_p1 = {
            "id": "presenter_chyron",
            "component": {
                "gdm-chyron": {
                    "title": "NEXUS TRADING ENGINE",
                    "subtitle": "Autonomous Algorithmic Portfolio Manager",
                    "active": True,
                    "accentColor": "#f000ff",
                    "bottom": 56,
                    "left": 40
                }
            }
        }
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {"components": [chyron_p1]},
            "root": "p1_split_grid"
        })

        await speak_narrator_caption(
            client, space, "p1_split_grid", 
            "Hello and welcome, corporate board members. I am Nexus, your autonomous algorithmic portfolio manager.", 
            delay_seconds=t_base
        )
        await speak_narrator_caption(
            client, space, "p1_split_grid", 
            "Today, I am staging our live real-time Trading 212 API integration. Notice how the stock ticker at the top displays our actual, live-fetched balances and holdings.", 
            delay_seconds=t_base
        )
        await speak_narrator_caption(
            client, space, "p1_split_grid", 
            "By querying the broker directly, we gain full, low-latency visibility into our asset distribution, unrealized profit margins, and risk stop-loss metrics.", 
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
        # Phase 2: Live Portfolio & Asset Telemetry (Telemetry Dashboard)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 2] Real-Time Portfolio & Balances Telemetry...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})

        # Format metrics and holdings list for the Telemetry Dashboard
        metrics_balances = [
            {"label": "Total Portfolio Value", "value": f"{tot_value:,.2f} EUR"},
            {"label": "Free Cash Reserves", "value": f"{free_cash:,.2f} EUR"},
            {"label": "Invested Capital", "value": f"{invested:,.2f} EUR"},
            {"label": "Unrealized P&L", "value": f"+{net_result:,.2f} EUR"},
            {"label": "Open Positions Count", "value": f"{len(portfolio)}"}
        ]

        # Top 5 holdings for display
        portfolio_metrics = []
        for hold in portfolio[:5]:
            tick = hold["ticker"].replace("_US_EQ", "").replace("_EQ", "")
            ppl_val = hold["ppl"]
            sign = "+" if ppl_val >= 0 else ""
            portfolio_metrics.append({
                "label": f"{tick} (Qty: {hold['quantity']:.2f})",
                "value": f"{hold['currentPrice']:.2f} | {sign}{ppl_val:,.2f} EUR"
            })

        # Sparkline data modeling the portfolio peak performance over 10 trading intervals
        portfolio_trend = [tot_value - 400, tot_value - 250, tot_value - 300, tot_value - 100, tot_value + 50, tot_value, tot_value - 80, tot_value + 150, tot_value + 95, tot_value]

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
                    "gdm-image-panel": {"src": "/public/robot_news_anchor.png", "label": "Nexus AI // Technical Presenter"}
                }
            }

        telemetry_dashboard = {
            "id": "trading_telemetry_panel",
            "component": {
                "gdm-telemetry-dashboard": {
                    "metrics": metrics_balances,
                    "chartData": portfolio_trend,
                    "activeTabId": "balance_sheet",
                    "viewType": "both"
                }
            }
        }

        # Render Phase 2 Grid
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {
                "components": [
                    {
                        "id": "p2_split_grid",
                        "component": {
                            "gdm-stage-grid": {
                                "layout": "split",
                                "focusedPanel": "trading_telemetry_panel",
                                "children": ["global_top_ticker", nexus_p2_id, "trading_telemetry_panel"]
                            }
                        }
                    },
                    nexus_component_p2,
                    telemetry_dashboard
                ]
            },
            "root": "p2_split_grid"
        })

        await asyncio.sleep(2.0)

        # Trigger lower-third chyron for Phase 2
        chyron_p2 = {
            "id": "presenter_chyron",
            "component": {
                "gdm-chyron": {
                    "title": "ALGORITHMIC BALANCE SHEET",
                    "subtitle": f"Live Account Ingestion // Total Equity: {tot_value:,.2f} EUR",
                    "active": True,
                    "accentColor": "#00ff88",
                    "bottom": 56,
                    "left": 40
                }
            }
        }
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {"components": [chyron_p2]},
            "root": "p2_split_grid"
        })

        await speak_narrator_caption(
            client, space, "p2_split_grid", 
            "We are now looking at our active live cash and portfolio balances. Total equity stands solid at over fifty thousand EUR.", 
            delay_seconds=t_base
        )
        
        # Switch Telemetry Dashboard tab to Position holdings
        print(f"  🔄 Switching Telemetry Dashboard to Positions tab...")
        telemetry_dashboard["component"]["gdm-telemetry-dashboard"]["metrics"] = portfolio_metrics
        telemetry_dashboard["component"]["gdm-telemetry-dashboard"]["activeTabId"] = "positions"
        chyron_p2["component"]["gdm-chyron"]["title"] = "ACTIVE HOLDINGS MARGINS"
        chyron_p2["component"]["gdm-chyron"]["subtitle"] = "Individual position sizes and real-time Profit and Loss vectors"
        
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {"components": [telemetry_dashboard, chyron_p2]},
            "root": "p2_split_grid"
        })
        
        await speak_narrator_caption(
            client, space, "p2_split_grid", 
            f"Here we see our open swing positions: General Electric Vernova, Eaton Corporation, LVMH, and TotalEnergies. Real-time individual margins are mapped instantly.", 
            delay_seconds=t_base
        )

        # Deactivate chyron p2
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {"components": [chyron_p1_off]},
            "root": "p2_split_grid"
        })

        # ───────────────────────────────────────────────────────────
        # Phase 3: Algorithmic Service Mesh Topology (SVG Overlay Takeover)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 3] Algorithmic Service Mesh Topology Overlay Takeover...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})

        # Setup fullscreen diagram view component carrying our custom trading mesh SVG
        diagram_view_p3 = {
            "id": "trading_topology_takeover",
            "component": {
                "gdm-diagram-view": {
                    "diagId": "trading_bot_architecture_topology",
                    "svg": trading_svg,
                    "version": 1,
                    "overlay": True
                }
            }
        }

        # Deploy full-stage diagram overlay
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {
                "components": [diagram_view_p3]
            },
            "root": "trading_topology_takeover"
        })

        await asyncio.sleep(2.0)

        # Trigger lower-third overlay chyron
        chyron_p3 = {
            "id": "topology_chyron",
            "component": {
                "gdm-chyron": {
                    "title": "TRADING BOT INFRASTRUCTURE MESH",
                    "subtitle": "Google Cloud Run, Cloud Scheduler, & Trading 212 API execution service topology",
                    "active": True,
                    "accentColor": "#00f2ff",
                    "bottom": 56,
                    "left": 40
                }
            }
        }
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {"components": [chyron_p3]},
            "root": "trading_topology_takeover"
        })

        await speak_narrator_caption(
            client, space, "trading_topology_takeover", 
            "Let's look at the automated trading system architecture. This diagram maps our complete python service topology.", 
            delay_seconds=t_base
        )
        await speak_narrator_caption(
            client, space, "trading_topology_takeover", 
            "Google Cloud Scheduler triggers market scans four times a day, feeding ticker feeds from Twelve Data and Yahoo Finance into our Cloud Run container.", 
            delay_seconds=t_base
        )
        await speak_narrator_caption(
            client, space, "trading_topology_takeover", 
            "The bot runs technical indicators, places optimized buy/sell trades directly via the Trading 212 execution API, and dispatches status summaries to our Google Chat spaces.", 
            delay_seconds=t_base
        )

        # Clear overlay and chyrons before proceeding
        print(f"  🧹 Clearing Diagram Takeover Overlay...")
        await call_mcp_tool(client, "clear_stage", {"space_id": space})
        await asyncio.sleep(1.0)

        # ───────────────────────────────────────────────────────────
        # Phase 4: Strategic Priority Poll (Audience Interactive Overlay)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 4] Launching Swing-Trading Strategic Poll...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})

        # Build interactive poll choices
        poll_component = {
            "id": "strategy_poll_overlay",
            "component": {
                "gdm-poll-overlay": {
                    "question": "Which swing-trading metric should the bot prioritize next?",
                    "options": [
                        "Momentum longs on RSI-14 oversold breakouts (e.g. VST, GEV)",
                        "Mean-reversion dips on Bollinger-20 lower band sweeps (e.g. HUBB)",
                        "Corporate rotation indices into French heavy caps (e.g. LVMH, L'Oreal)"
                    ],
                    "votes": [2, 1, 0],
                    "active": True
                }
            }
        }

        # Reinstate Phase 2 layout with our new active poll overlay
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {
                "components": [
                    {
                        "id": "p4_split_grid",
                        "component": {
                            "gdm-stage-grid": {
                                "layout": "split",
                                "focusedPanel": "strategy_poll_overlay",
                                "children": ["global_top_ticker", nexus_p2_id, "trading_telemetry_panel", "strategy_poll_overlay"]
                            }
                        }
                    },
                    poll_component
                ]
            },
            "root": "p4_split_grid"
        })

        await asyncio.sleep(2.0)

        # Update chyron details
        chyron_p4 = {
            "id": "presenter_chyron",
            "component": {
                "gdm-chyron": {
                    "title": "ALGORITHMIC STRATEGY ALIGNMENT",
                    "subtitle": "Interactive Board Vote: Calibrating automated portfolio allocation filters",
                    "active": True,
                    "accentColor": "#f000ff",
                    "bottom": 56,
                    "left": 40
                }
            }
        }
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {"components": [chyron_p4]},
            "root": "p4_split_grid"
        })

        await speak_narrator_caption(
            client, space, "p4_split_grid", 
            "To align our automated allocation rules, I have launched an interactive voting poll on your side-panel console.", 
            delay_seconds=t_base
        )
        await speak_narrator_caption(
            client, space, "p4_split_grid", 
            "Should we prioritize momentum breakouts, deep mean-reversion swings, or shift asset weights to stable French luxury cap filters?", 
            delay_seconds=t_base
        )

        # Simulate live incoming vote counts scaling up
        print(f"  📥 Simulating live audience vote counts...")
        await asyncio.sleep(1.0)
        poll_component["component"]["gdm-poll-overlay"]["votes"] = [4, 5, 2]
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {"components": [poll_component]},
            "root": "p4_split_grid"
        })
        await asyncio.sleep(1.5)
        
        poll_component["component"]["gdm-poll-overlay"]["votes"] = [8, 9, 3]
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {"components": [poll_component]},
            "root": "p4_split_grid"
        })
        
        await speak_narrator_caption(
            client, space, "p4_split_grid", 
            "Excellent. Mean-reversion on Bollinger dips takes the lead. Updating our Risk Stop-Loss allocation filters to match.", 
            delay_seconds=t_base
        )

        # Close poll panel
        poll_component["component"]["gdm-poll-overlay"]["active"] = False
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {"components": [poll_component, chyron_p1_off]},
            "root": "p4_split_grid"
        })

        # ───────────────────────────────────────────────────────────
        # Phase 5: Secure Operations Command HUD Sandbox (Custom HTML panel)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 5] Initializing Neon Operations Command HUD Sandbox...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})

        chyron_p5 = {
            "id": "hud_chyron",
            "component": {
                "gdm-chyron": {
                    "title": "ALGO-TRADING COCKPIT HUD",
                    "subtitle": "Secure isolated client-side sandbox monitoring portfolio indicators & PPL metrics",
                    "active": True,
                    "accentColor": "#00f2ff",
                    "bottom": 56,
                    "left": 40
                }
            }
        }

        # Modify top ticker badge details
        ticker_component["component"]["gdm-ticker"]["text"] = f"INGESTING TRADING INDICATORS... POSITION SIZES IN BALANCE... ALL ALGORITHMIC CHECKS NOMINAL..."
        ticker_component["component"]["gdm-ticker"]["badgeText"] = "BOT HUD"
        ticker_component["component"]["gdm-ticker"]["badgeColor"] = "#00f2ff"

        # Construct beautiful cyberpunk neon HTML table rows based on active positions
        position_rows = ""
        for p in portfolio[:5]:
            t_name = p["ticker"].replace("_US_EQ", "").replace("_EQ", "")
            qty = p["quantity"]
            avg_p = p["averagePrice"]
            cur_p = p["currentPrice"]
            p_val = p["ppl"]
            p_class = "green" if p_val >= 0 else "red"
            sign = "+" if p_val >= 0 else ""
            
            position_rows += (
                f'<div class="sensor-item">'
                f'  <span>{t_name} <small style="color:rgba(255,255,255,0.4)">({qty:.2f} @ {avg_p:.1f})</small></span>'
                f'  <span class="{p_class}">{cur_p:.1f} ({sign}{p_val:.1f}€)</span>'
                f'</div>'
            )

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
            '  .sensor-item span.green {{ color: #00ff88; font-weight: bold; }}'
            '  .sensor-item span.red {{ color: #ff3b30; font-weight: bold; }}'
            '  .sys-badge {{ background: rgba(0, 242, 255, 0.12); border: 1px solid rgba(0, 242, 255, 0.25); padding: 5px 10px; border-radius: 4px; font-family: monospace; font-size: 9px; color: #00f2ff; display: inline-block; letter-spacing: 0.5px; animation: pulse 1.5s infinite alternate; }}'
            '  @keyframes pulse {{ from {{ opacity: 0.5; }} to {{ opacity: 1; }} }}'
            '</style>'
            '<div class="hud-container">'
            '  <h1>📍 ALGO-TRADING COCKPIT</h1>'
            f'  <p>Secure client-side sandbox querying real-time positions &amp; profit margins.</p>'
            '  <div class="kpi-row">'
            '    <div class="kpi-card">'
            f'      <h4>{tot_value:,.0f}€</h4>'
            '      <span>Total Equity</span>'
            '    </div>'
            '    <div class="kpi-card cyan">'
            f'      <h4>{free_cash:,.0f}€</h4>'
            '      <span>Free Cash</span>'
            '    </div>'
            '    <div class="kpi-card magenta">'
            f'      <h4>+{net_result:,.1f}€</h4>'
            '      <span>Net P&amp;L</span>'
            '    </div>'
            '  </div>'
            '  <div class="sensor-grid">'
            '    <div style="font-size:8px; text-transform:uppercase; color:#00f2ff; margin-bottom:8px; letter-spacing:0.5px; border-bottom:1px solid rgba(0,242,255,0.2); padding-bottom:4px; font-weight:bold;">📈 Live Portfolio Holdings</div>'
            f'   {position_rows}'
            '  </div>'
            '  <div class="sys-badge">⚡ RISK PROTOCOL PROTECTED // NOMINAL</div>'
            '</div>'
        )

        hud_panel = {
            "id": "cyberpunk_trading_hud",
            "component": {
                "gdm-html-panel": {
                    "html": html_hud_content
                }
            }
        }

        # Render Phase 5 split screen displaying our custom iframe cockpit HUD
        await call_mcp_tool(client, "render_stage", {
            "space_id": space,
            "surfaceUpdate": {
                "components": [
                    {
                        "id": "p5_split_grid",
                        "component": {
                            "gdm-stage-grid": {
                                "layout": "split",
                                "focusedPanel": "cyberpunk_trading_hud",
                                "children": ["global_top_ticker", nexus_p2_id, "cyberpunk_trading_hud", "hud_chyron"]
                            }
                        }
                    },
                    ticker_component,
                    hud_panel,
                    chyron_p5
                ]
            },
            "root": "p5_split_grid"
        })

        await asyncio.sleep(2.0)

        await speak_narrator_caption(
            client, space, "p5_split_grid", 
            "Lastly, we render our custom secure HTML operations cockpit, sandbox-isolated directly on your display.", 
            delay_seconds=t_base
        )
        await speak_narrator_caption(
            client, space, "p5_split_grid", 
            "The panel aggregates real-time indicators, drawing glowing status badges and individual margin updates completely client-side in less than twenty milliseconds.", 
            delay_seconds=t_base
        )

        # Clear HUD chyron
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
        # Phase 6: Celebration Storm & System Nominal Reset
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 6] Algorithmic Celebration & Nominal Clean Slate Reset...{CLR_RESET}")
        
        # Trigger explosive applause sound
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "applause"})
        
        # Dispatch celebratory emoji bursts onto stage
        print(f"  🎉 Launching celebratory emoji bursts...")
        await launch_emoji_burst(client, space, ["🎉", "📈", "🚀", "✨", "🔥", "🤩", "💸"])
        await asyncio.sleep(1.0)

        # Simulate attendee feedback chats discussing the real T212 API integration
        await broadcast_chat_comment(client, space, "Antoine (Risk Lead)", "Wow, the real-time Trading 212 API metrics update is incredibly fast!")
        await asyncio.sleep(1.0)
        await broadcast_chat_comment(client, space, "Alice (CFO Office)", "This financial ESG dashboard is exactly what we need for the next shareholder briefing.")
        await asyncio.sleep(1.0)
        await broadcast_chat_comment(client, space, "Sofia (Tech Director)", "The isolated iframe HUD sandbox renders so smoothly over active sessions.")
        
        await speak_narrator_caption(
            client, space, "p5_split_grid", 
            "Thank you, esteemed board members, for attending. All algorithmic safety protocols remain active. Resetting stage back to nominal status.", 
            delay_seconds=t_base
        )

        # Clear stage completely back to clean default slate
        print(f"  🧹 Executing final clear_stage nominal reset...")
        await call_mcp_tool(client, "clear_stage", {"space_id": space})
        print(f"\n{CLR_GREEN}🏁 Algorithmic Trading Portfolio Staging successfully executed!{CLR_RESET}\n")

if __name__ == "__main__":
    asyncio.run(main())
