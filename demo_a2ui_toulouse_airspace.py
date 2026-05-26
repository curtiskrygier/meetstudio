#!/usr/bin/env python3
"""
Meet Live Concierge — Toulouse Airspace Tactical Command Deck Showcase
======================================================================
Orchestrates an ultra-premium, multi-phase demonstration of the
Toulouse-Blagnac Terminal Maneuvering Area (TMA) Airspace Command Deck.

Features:
1. Native Lit Stretched Widescreen Radar View (gdm-radar-view)
2. Custom Cyber-Neon Sandboxed HTML ATC HUD Panels (gdm-html-panel)
3. Fullscreen Glassmorphic SVG Airspace Airway Topology Overlay (gdm-diagram-view)
4. Interactive Runway Approach Sequencing Board Poll (gdm-poll-overlay)
5. Synchronized Speech Subtitles, Sound Effects, and Audience Reactions

Environment Variables:
    FAST_MODE: Set to "0" or "false" to slow down transitions for recording. Default: True.
    CONCIERGE_API_URL: Target FastAPI backend URL. Default: CONCIERGE_API_URL_PLACEHOLDER
    STAGE_API_KEY: Secure authorization token.
    MEET_SPACE_ID: Force target Google Meet space.
"""

import asyncio
import os
import sys
import glob
import random
import httpx

# --- Virtualenv Auto-Resolution ---
_base_dir = os.path.dirname(os.path.abspath(__file__))
_venv_dirs = glob.glob(os.path.join(_base_dir, "venv", "lib", "python3.*", "site-packages"))
for _vd in _venv_dirs:
    if _vd not in sys.path:
        sys.path.insert(0, _vd)

# --- Configuration & Environment Setup ---
API_URL = os.environ.get("CONCIERGE_API_URL", "CONCIERGE_API_URL_PLACEHOLDER")
KEY = os.environ.get("STAGE_API_KEY", "meet-live_STAGE_SECURE_v1_zG9fN8qL7vP2mX6tY9wK4jC5bS8xQ7hZ3uW0rA")
FAST_MODE = os.environ.get("FAST_MODE", "true").lower() not in ("0", "false", "no")

# --- ANSI Terminal Colors ---
CLR_CYAN = "\033[38;5;51m"
CLR_MAGENTA = "\033[38;5;201m"
CLR_GREEN = "\033[38;5;82m"
CLR_YELLOW = "\033[38;5;220m"
CLR_SLATE = "\033[38;5;244m"
CLR_RESET = "\033[0m"

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

async def render_stage_api(client: httpx.AsyncClient, space_id: str, components: list[dict], root_id: str = None):
    payload = {
        "surfaceUpdate": {
            "components": components
        }
    }
    if root_id:
        payload["root"] = root_id
    await post_endpoint(client, f"/api/render-stage/{space_id}", payload)

async def clear_stage_api(client: httpx.AsyncClient, space_id: str):
    await post_endpoint(client, f"/api/render-stage-clear/{space_id}", {})

async def set_transcript(client: httpx.AsyncClient, space_id: str, text: str, label: str = "Gemini Concierge"):
    await post_endpoint(client, f"/api/transcript/{space_id}", {
        "role": "agent",
        "label": label,
        "text": text,
        "is_final": True
    })

TABS_CONFIG = [
    {"id": "stk", "label": "📡 RADAR CHANNELS"},
    {"id": "flt", "label": "✈️ TMA TRAFFIC"},
    {"id": "pwr", "label": "📊 METAR WEATHER"}
]

# --- High Fidelity Approach Simulation Telemetry ---
MS_TO_FPM = 196.85  # m/s -> ft/min

def get_fallback_flights(tick: int) -> list[dict]:
    """Generates progress-stepped approach sequences targeting LFBO Runway 32L/R."""
    # Approach flights sequence descending and decelerating towards runway centerpoint (0m altitude, 0kt speed)
    flights = [
        {
            "callsign": "AFR6129",
            "altitude": max(150, 1150 - tick * 100),
            "speed": max(135, 260 - tick * 12),
            "vrate": -1100,
            "origin": "ORY",
            "destination": "TLS"
        },
        {
            "callsign": "BAW373",
            "altitude": max(300, 2400 - tick * 150),
            "speed": max(145, 300 - tick * 15),
            "vrate": -1400,
            "origin": "LHR",
            "destination": "TLS"
        },
        {
            "callsign": "EZY4218",
            "altitude": max(600, 3800 - tick * 200),
            "speed": max(155, 340 - tick * 18),
            "vrate": -1700,
            "origin": "LGW",
            "destination": "TLS"
        },
        {
            "callsign": "RYR109B",
            "altitude": max(1200, 4900 - tick * 250),
            "speed": max(165, 380 - tick * 20),
            "vrate": -900,
            "origin": "STN",
            "destination": "TLS"
        },
        {
            "callsign": "DLH11A",
            "altitude": max(2100, 5800 - tick * 300),
            "speed": max(180, 410 - tick * 22),
            "vrate": -1200,
            "origin": "FRA",
            "destination": "TLS"
        }
    ]
    flights.sort(key=lambda f: f["altitude"])
    return flights

# --- Custom HTML Console Markup Generator ---
def make_supervisor_console_html(flights: list[dict]) -> str:
    """Generates the live ATC Sector Supervisor Console HTML panel content."""
    rows_markup = ""
    for f in flights:
        vrate = f["vrate"]
        vr_symbol = "▼" if vrate < -250 else ("▲" if vrate > 250 else "—")
        color = "#00ff88" if vrate < -250 else ("#ffd60a" if vrate > 250 else "#00f2ff")
        fl = f"{int(f['altitude'] * 3.28084 / 100):03d}"
        
        # Determine airspace handover fix based on altitude
        if f["altitude"] < 500:
            status = "LANDED"
        elif f["altitude"] < 1000:
            status = "FINAL APPROACH"
        elif f["altitude"] < 2500:
            status = "APPROACH FIX"
        else:
            status = "ESTABLISHED"
            
        rows_markup += f"""
        <tr>
            <td style="color:{color}; font-weight:bold; font-family:monospace;">{f['callsign']}</td>
            <td>FL{fl}</td>
            <td>{f['speed']}kt</td>
            <td style="color:{color}; font-family:monospace;">{vr_symbol} {abs(vrate)}</td>
            <td style="font-size:10px; opacity:0.8; letter-spacing:0.5px;">{status}</td>
        </tr>
        """
        
    return f"""
    <style>
        body {{
            background: #080a14 !important;
            color: #ffffff;
            font-family: 'Google Sans', 'Inter', system-ui, sans-serif;
            margin: 0;
            padding: 16px;
            box-sizing: border-box;
            color-scheme: dark !important;
        }}
        .console-container {{
            border: 1px solid rgba(0, 242, 255, 0.2);
            background: rgba(12, 16, 32, 0.65);
            border-radius: 12px;
            padding: 16px;
            box-shadow: inset 0 0 20px rgba(0, 242, 255, 0.05);
        }}
        .header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid rgba(0, 242, 255, 0.15);
            padding-bottom: 12px;
            margin-bottom: 14px;
        }}
        .title {{
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
            color: #00f2ff;
            text-shadow: 0 0 8px rgba(0, 242, 255, 0.3);
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .pulse-light {{
            width: 8px;
            height: 8px;
            background: #00ff88;
            border-radius: 50%;
            box-shadow: 0 0 8px #00ff88;
            animation: pulse-anim 1.5s infinite alternate;
        }}
        @keyframes pulse-anim {{
            from {{ opacity: 0.4; }}
            to {{ opacity: 1; }}
        }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 16px;
        }}
        .metric-card {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 10px 12px;
        }}
        .metric-label {{
            font-size: 9px;
            color: rgba(255, 255, 255, 0.5);
            text-transform: uppercase;
            font-weight: bold;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }}
        .metric-value {{
            font-size: 14px;
            font-weight: 700;
            font-family: monospace;
            color: #ffffff;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
            text-align: left;
        }}
        th {{
            color: rgba(0, 242, 255, 0.6);
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-size: 9px;
            padding: 8px 6px;
            border-bottom: 1px solid rgba(0, 242, 255, 0.1);
        }}
        td {{
            padding: 8px 6px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.03);
        }}
        .system-footer {{
            margin-top: 14px;
            padding-top: 10px;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 9px;
            color: rgba(255, 255, 255, 0.4);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
    </style>
    <div class="console-container">
        <div class="header">
            <div class="title">
                <div class="pulse-light"></div>
                📡 TLS-SECTOR SUPERVISOR CONSOLE
            </div>
            <div style="font-size:10px; font-family:monospace; color:rgba(255,255,255,0.4)">LFBO-APP</div>
        </div>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Active Runway Corridor</div>
                <div class="metric-value" style="color:#00ff88">ILS Runway 32L/R</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Active Wind & METAR</div>
                <div class="metric-value">320° / 15kt</div>
            </div>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Callsign</th>
                    <th>Altitude</th>
                    <th>Speed</th>
                    <th>V-Rate</th>
                    <th>Sector Status</th>
                </tr>
            </thead>
            <tbody>
                {rows_markup}
            </tbody>
        </table>
        <div class="system-footer">
            <span>S-BAND RADAR: ONLINE</span>
            <span>ADS-B COHERENCY: 99.8% NOMINAL</span>
        </div>
    </div>
    """

def make_target_profile_html(flight: dict, tick: int) -> str:
    """Generates the glowing Target Operations Profile HUD for a locked aircraft."""
    altitude_ft = int(flight["altitude"] * 3.28084)
    fl = f"{int(altitude_ft / 100):03d}"
    vrate = flight["vrate"]
    
    # Calculate ETA countdown based on altitude
    eta_sec = max(5, int(flight["altitude"] / 6))
    eta_min = eta_sec // 60
    eta_rem = eta_sec % 60
    eta_str = f"{eta_min:02d}m {eta_rem:02d}s"
    
    # Deceleration progress bar (Target landing speed ~135kt, max approach speed ~340kt)
    pct_speed = int(max(0, min(100, (flight["speed"] - 135) / (340 - 135) * 100)))
    
    # Glidepath deviation visualizer (simulate on glideslope centering diamond)
    glide_deviation = "ON COURSE" if flight["altitude"] > 100 else "DECELERATION ROLL"
    
    return f"""
    <style>
        body {{
            background: #080a14 !important;
            color: #ffffff;
            font-family: 'Google Sans', 'Inter', system-ui, sans-serif;
            margin: 0;
            padding: 16px;
            box-sizing: border-box;
            color-scheme: dark !important;
        }}
        .hud-container {{
            border: 1px solid rgba(0, 255, 136, 0.3);
            background: rgba(12, 32, 20, 0.45);
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 0 20px rgba(0, 255, 136, 0.1), inset 0 0 20px rgba(0, 255, 136, 0.05);
        }}
        .header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid rgba(0, 255, 136, 0.2);
            padding-bottom: 12px;
            margin-bottom: 14px;
        }}
        .title {{
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
            color: #00ff88;
            text-shadow: 0 0 8px rgba(0, 255, 136, 0.3);
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .pulse-light {{
            width: 8px;
            height: 8px;
            background: #00f2ff;
            border-radius: 50%;
            box-shadow: 0 0 8px #00f2ff;
            animation: pulse-anim 1s infinite alternate;
        }}
        @keyframes pulse-anim {{
            from {{ opacity: 0.4; }}
            to {{ opacity: 1; }}
        }}
        .target-callsign {{
            font-size: 32px;
            font-weight: 800;
            font-family: monospace;
            color: #00ff88;
            letter-spacing: 1.5px;
            margin-bottom: 12px;
            text-shadow: 0 0 12px rgba(0, 255, 136, 0.4);
        }}
        .data-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 16px;
        }}
        .data-card {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 8px 10px;
        }}
        .card-label {{
            font-size: 8px;
            color: rgba(255, 255, 255, 0.5);
            text-transform: uppercase;
            font-weight: bold;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }}
        .card-value {{
            font-size: 13px;
            font-weight: 700;
            font-family: monospace;
        }}
        .bar-container {{
            background: rgba(255, 255, 255, 0.05);
            height: 6px;
            border-radius: 3px;
            overflow: hidden;
            margin-top: 4px;
        }}
        .bar-fill {{
            background: #00ff88;
            height: 100%;
            width: {pct_speed}%;
            border-radius: 3px;
            box-shadow: 0 0 6px #00ff88;
        }}
        .glidepath-visual {{
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 10px;
            background: rgba(0, 0, 0, 0.2);
            text-align: center;
            font-size: 11px;
            margin-bottom: 12px;
        }}
        .glideslope-line {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin: 8px 0;
            position: relative;
        }}
        .glideslope-line::before {{
            content: '';
            position: absolute;
            left: 10%;
            right: 10%;
            height: 1px;
            background: rgba(255,255,255,0.15);
            top: 50%;
            z-index: 1;
        }}
        .glide-notch {{
            width: 4px;
            height: 4px;
            border-radius: 50%;
            background: rgba(255,255,255,0.3);
            z-index: 2;
        }}
        .glide-diamond {{
            width: 8px;
            height: 8px;
            background: #00f2ff;
            transform: rotate(45deg);
            box-shadow: 0 0 6px #00f2ff;
            z-index: 3;
            margin: 0 auto;
        }}
    </style>
    <div class="hud-container">
        <div class="header">
            <div class="title">
                <div class="pulse-light"></div>
                🎯 ACTIVE TARGET OPERATIONS PROFILE
            </div>
            <div style="font-size:9px; font-family:monospace; color:rgba(0,255,136,0.7)">VECTORS LOCK ON</div>
        </div>
        
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
                <div class="target-callsign">{flight['callsign']}</div>
                <div style="font-size:10px; opacity:0.7; margin-top:-6px; text-transform:uppercase; font-weight:bold; letter-spacing:0.5px;">Air France • ORY ➔ TLS</div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:9px; color:rgba(255,255,255,0.4); text-transform:uppercase; font-weight:bold;">Squawk</div>
                <div style="font-size:16px; font-family:monospace; font-weight:bold; color:#00f2ff; text-shadow: 0 0 6px rgba(0, 242, 255, 0.4)">1242</div>
            </div>
        </div>
        
        <div class="data-grid" style="margin-top:14px;">
            <div class="data-card">
                <div class="card-label">Primary Altitude</div>
                <div class="card-value">{flight['altitude']}m <span style="font-size:10px; color:rgba(255,255,255,0.5)">/ FL{fl}</span></div>
            </div>
            <div class="data-card">
                <div class="card-label">Airspeed Reference</div>
                <div class="card-value" style="color:#00ff88">{flight['speed']} kt</div>
                <div class="bar-container"><div class="bar-fill"></div></div>
            </div>
            <div class="data-card">
                <div class="card-label">Vertical Descent Speed</div>
                <div class="card-value" style="color:#00ff88">{vrate} fpm</div>
            </div>
            <div class="data-card">
                <div class="card-label">Touchdown ETA</div>
                <div class="card-value" style="color:#ffd60a">{eta_str}</div>
            </div>
        </div>
        
        <div class="glidepath-visual">
            <div style="font-size:8px; font-weight:bold; text-transform:uppercase; color:rgba(255,255,255,0.5); letter-spacing:0.5px; margin-bottom:4px;">3-Degree Instrument Landing Corridor</div>
            <div style="font-weight:bold; color:#00f2ff; letter-spacing:0.5px;">{glide_deviation}</div>
            <div class="glideslope-line">
                <div class="glide-notch"></div>
                <div class="glide-notch"></div>
                <div class="glide-diamond"></div>
                <div class="glide-notch"></div>
                <div class="glide-notch"></div>
            </div>
            <div style="font-size:8px; color:rgba(255,255,255,0.4)">ILS GS-32L FREQ: 110.10 MHz • DME LOCK: 1.8 NM</div>
        </div>
    </div>
    """

# --- Custom Airway Corridor SVG System Takeover Diagram ---
airspace_svg = """<svg viewBox="0 0 700 350" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- Cyberpunk Glowing drop shadows -->
    <filter id="cyan-glow" x="-15%" y="-15%" width="130%" height="130%">
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
    <filter id="gold-glow" x="-15%" y="-15%" width="130%" height="130%">
      <feGaussianBlur stdDeviation="5" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>

  <!-- Deep Command Space Background -->
  <rect width="100%" height="100%" fill="#040812" rx="16" />
  
  <!-- Sleek Tactical Background Coordinate Grid -->
  <g stroke="rgba(0, 242, 255, 0.04)" stroke-width="0.5">
    <line x1="50" y1="0" x2="50" y2="350" />
    <line x1="100" y1="0" x2="100" y2="350" />
    <line x1="150" y1="0" x2="150" y2="350" />
    <line x1="200" y1="0" x2="200" y2="350" />
    <line x1="250" y1="0" x2="250" y2="350" />
    <line x1="300" y1="0" x2="300" y2="350" />
    <line x1="350" y1="0" x2="350" y2="350" />
    <line x1="400" y1="0" x2="400" y2="350" />
    <line x1="450" y1="0" x2="450" y2="350" />
    <line x1="500" y1="0" x2="500" y2="350" />
    <line x1="550" y1="0" x2="550" y2="350" />
    <line x1="600" y1="0" x2="600" y2="350" />
    <line x1="650" y1="0" x2="650" y2="350" />
    
    <line x1="0" y1="50" x2="700" y2="50" />
    <line x1="0" y1="100" x2="700" y2="100" />
    <line x1="0" y1="150" x2="700" y2="150" />
    <line x1="0" y1="200" x2="700" y2="200" />
    <line x1="0" y1="250" x2="700" y2="250" />
    <line x1="0" y1="300" x2="700" y2="300" />
  </g>

  <!-- Outer Bounding Circle representing 40NM TMA Boundary -->
  <circle cx="350" cy="175" r="160" fill="none" stroke="rgba(0, 242, 255, 0.08)" stroke-width="1" />
  <circle cx="350" cy="175" r="110" fill="none" stroke="rgba(0, 242, 255, 0.05)" stroke-dasharray="4 4" stroke-width="0.5" />
  <circle cx="350" cy="175" r="60" fill="none" stroke="rgba(0, 242, 255, 0.05)" stroke-width="0.5" />

  <!-- Airway Corridor Connectors (Glowing Lines) -->
  <g fill="none" stroke-width="1.5" opacity="0.8">
    <!-- Agen STAR arrival path -->
    <path d="M 200 70 L 350 175" stroke="#00f2ff" filter="url(#cyan-glow)" />
    <!-- Laura STAR arrival path -->
    <path d="M 500 70 L 350 175" stroke="#ffd60a" filter="url(#gold-glow)" />
    <!-- Toulouse Approach ILS runway intercept cone -->
    <path d="M 350 175 L 350 260" stroke="#00ff88" stroke-dasharray="2 2" stroke-width="2" filter="url(#green-glow)" />
  </g>

  <!-- Runway 32L/R approach sequence graphical dashes -->
  <rect x="345" y="260" width="4" height="20" fill="#ffffff" rx="1" />
  <rect x="351" y="260" width="4" height="20" fill="#ffffff" rx="1" />
  <text x="350" y="295" fill="rgba(255,255,255,0.4)" font-size="7" font-family="monospace" text-anchor="middle">RUNWAY 32L/R</text>

  <!-- Airway Fix Holding Point Nodes -->
  <!-- AGN Node -->
  <g class="node">
    <circle cx="200" cy="70" r="14" fill="#0c1d2e" stroke="#00f2ff" stroke-width="2" />
    <circle cx="200" cy="70" r="4" fill="#00f2ff" />
    <text x="200" y="100" fill="#00f2ff" font-size="11" font-weight="700" font-family="monospace" text-anchor="middle">AGN</text>
    <text x="200" y="110" fill="rgba(255,255,255,0.5)" font-size="7" font-family="monospace" text-anchor="middle">AGEN HOLDING FIX</text>
  </g>

  <!-- TOU VOR Node -->
  <g class="node">
    <polygon points="350,161 364,175 350,189 336,175" fill="#0a2a1a" stroke="#00ff88" stroke-width="2" />
    <circle cx="350" cy="175" r="4" fill="#00ff88" />
    <text x="350" y="150" fill="#00ff88" font-size="11" font-weight="700" font-family="monospace" text-anchor="middle">TOU</text>
    <text x="350" y="140" fill="rgba(255,255,255,0.5)" font-size="7" font-family="monospace" text-anchor="middle">TOULOUSE VOR</text>
  </g>

  <!-- LAU Node -->
  <g class="node">
    <circle cx="500" cy="70" r="14" fill="#2d220a" stroke="#ffd60a" stroke-width="2" />
    <circle cx="500" cy="70" r="4" fill="#ffd60a" />
    <text x="500" y="100" fill="#ffd60a" font-size="11" font-weight="700" font-family="monospace" text-anchor="middle">LAU</text>
    <text x="500" y="110" fill="rgba(255,255,255,0.5)" font-size="7" font-family="monospace" text-anchor="middle">LAURA HOLDING FIX</text>
  </g>

  <!-- Title Indicator Block -->
  <text x="30" y="40" fill="#00f2ff" font-size="14" font-weight="800" font-family="monospace" letter-spacing="1">LFBO AIRSPACE TERMINAL MAP</text>
  <text x="30" y="55" fill="rgba(255,255,255,0.5)" font-size="8" font-family="monospace">TOULOUSE TERMINAL MANEUVERING AREA (TMA) OVERVIEW</text>

  <!-- Status Info Cards -->
  <g stroke="rgba(0, 242, 255, 0.2)" fill="rgba(12, 16, 32, 0.65)" stroke-width="1">
    <rect x="30" y="260" width="130" height="60" rx="6" />
    <rect x="540" y="260" width="130" height="60" rx="6" />
  </g>
  
  <g font-family="monospace">
    <text x="40" y="278" fill="rgba(255,255,255,0.4)" font-size="7" font-weight="bold">ACTIVE RUNWAYS</text>
    <text x="40" y="292" fill="#ffffff" font-size="11" font-weight="bold">32L / 32R</text>
    <text x="40" y="306" fill="#00ff88" font-size="8">ILS CAT III APPROACH</text>

    <text x="550" y="278" fill="rgba(255,255,255,0.4)" font-size="7" font-weight="bold">BARO PRESSURE</text>
    <text x="550" y="292" fill="#ffffff" font-size="11" font-weight="bold">QNH 1015 HPA</text>
    <text x="550" y="306" fill="#ffd60a" font-size="8">ALT ALIGN: COMPLIANT</text>
  </g>
</svg>
"""

# --- Main Presenter Orchestrator Loops ---
async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        # Detect active Space ID
        space = os.environ.get("MEET_SPACE_ID")
        if not space:
            space = await get_active_space(client)
            
        if not space:
            print(f"\n{CLR_MAGENTA}❌ Error: No active Meet space detected.{CLR_RESET}")
            print(f"Please open a Meet call first to register the live websocket.\n")
            sys.exit(1)
            
        delay = 1.8 if FAST_MODE else 10.0
        loop_ticks = 4
        
        print(f"\n{CLR_CYAN}  ==============================================================={CLR_RESET}")
        print(f"{CLR_CYAN}  ✈️   T O U L O U S E   A I R S P A C E   C O M M A N D   D E C K   ▲{CLR_RESET}")
        print(f"{CLR_CYAN}  ==============================================================={CLR_RESET}")
        print(f"  {CLR_SLATE}Active Meeting Space:{CLR_RESET} {CLR_CYAN}{space}{CLR_RESET}")
        print(f"  {CLR_SLATE}A2UI Specification:{CLR_RESET} {CLR_CYAN}v0.8 Dark Cyberpunk Theme{CLR_RESET}\n")

        # ───────────────────────────────────────────────────────────
        # Phase 0: S-Band Transceiver Calibration (Countdown Slate)
        # ───────────────────────────────────────────────────────────
        print(f"{CLR_CYAN}🎬 [Phase 0] Calibrating Primary S-Band Radar Transceivers...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})
        await render_stage_api(client, space, [
            {
                "id": "calibration_slate",
                "component": {
                    "gdm-standby-slate": {
                        "title": "📡 TLS Sector 32L/R Sweep Calibration",
                        "description": "Booting transponder tracking matrix and aligning primary S-Band receivers...",
                        "active": True,
                        "seconds": 5
                    }
                }
            }
        ], root_id="calibration_slate")
        await asyncio.sleep(5.0)

        # ───────────────────────────────────────────────────────────
        # Phase 1: Grid Initialization (Stretched Radar & Tactical HUD)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 1] Establishing Dual-Sweep Airspace Control Deck Grid...{CLR_RESET}")
        await set_transcript(
            client, space,
            "Welcome, sector controllers. We are initializing the Toulouse-Blagnac TMA approach sectors. The widescreen layout utilizes dual-sweep radar tracking side-by-side.",
            label="Sector Chief"
        )
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "sonar" if not FAST_MODE else "chimes"})
        
        ticker_comp = {
            "id": "airspace_ticker",
            "component": {
                "gdm-ticker": {
                    "text": "📍 LFBO Terminal Information • RUNWAY 32L/R ACTIVE FOR ARRIVALS • SURFACE WIND: 320° AT 15KT • QNH: 1015 HPA • SQUAWK 7700 ALERT: NONE • ACTIVE TRAFFIC SENSORS: ONLINE •",
                    "scrollSpeed": 50,
                    "active": True,
                    "accentColor": "#00ff88"
                }
            }
        }
        
        chyron_comp = {
            "id": "atc_chyron",
            "component": {
                "gdm-chyron": {
                    "title": "LFBO TMA APPROACH CONTROL",
                    "subtitle": "Active Approach Vectors Runway 32L/R",
                    "active": True,
                    "accentColor": "#00ff88"
                }
            }
        }

        deactivated_slate = {
            "id": "calibration_slate",
            "component": {
                "gdm-standby-slate": {
                    "active": False
                }
            }
        }

        for tick in range(loop_ticks):
            print(f"  📡 Sweeping Sector Space (Tick {tick+1}/{loop_ticks})...")
            flights = get_fallback_flights(tick=tick)
            html_console = make_supervisor_console_html(flights)
            
            await render_stage_api(client, space, [
                {
                    "id": "grid_layout",
                    "component": {
                        "gdm-stage-grid": {
                            "layout": "split",
                            "children": {"explicitList": ["radar_view", "html_panel"]}
                        }
                    }
                },
                {
                    "id": "radar_view",
                    "component": {
                        "gdm-3d-airspace": {
                            "flights": flights,
                            "lockedCallsign": "",
                            "zoom": 10.0,
                            "cameraPitch": 35.0,
                            "cameraYaw": 45.0,
                            "showGlideSlope": True,
                            "showTerrain": True
                        }
                    }
                },
                {
                    "id": "html_panel",
                    "component": {
                        "gdm-html-panel": {
                            "html": html_console,
                            "title": "📡 Tactical Supervisor HUD",
                            "version": tick + 1
                        }
                    }
                },
                deactivated_slate,
                ticker_comp,
                chyron_comp
            ], root_id="grid_layout")
            await asyncio.sleep(2.5 if FAST_MODE else 5.0)

        # ───────────────────────────────────────────────────────────
        # Phase 2: Transponder Lock & Approach Profiling (AFR6129 HUD)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 2] Locking Transponder Array on Lead Flight AFR6129...{CLR_RESET}")
        await set_transcript(
            client, space,
            "Target locked on flight AFR6129 descending on the three-degree instrument glide path. Notice the descent profile card updating live on the supervisor console.",
            label="Radar Analyst"
        )
        
        chyron_comp["component"]["gdm-chyron"]["title"] = "TARGET ACQUIRED: AFR6129"
        chyron_comp["component"]["gdm-chyron"]["subtitle"] = "Tracking Descent Path and Instrument Glide Slope Runway 32L"
        chyron_comp["component"]["gdm-chyron"]["accentColor"] = "#00f2ff"

        for tick in range(loop_ticks):
            print(f"  🎯 Profiling Target AFR6129 (Tick {tick+1}/{loop_ticks})...")
            flights = get_fallback_flights(tick=tick + loop_ticks)
            lead_flight = flights[0]  # AFR6129 is sorted to index 0 (lowest altitude)
            html_hud = make_target_profile_html(lead_flight, tick)
            
            await render_stage_api(client, space, [
                {
                    "id": "grid_layout",
                    "component": {
                        "gdm-stage-grid": {
                            "layout": "split",
                            "children": {"explicitList": ["radar_view", "html_panel"]}
                        }
                    }
                },
                {
                    "id": "radar_view",
                    "component": {
                        "gdm-3d-airspace": {
                            "flights": flights,
                            "lockedCallsign": "AFR6129",
                            "zoom": 6.0,
                            "cameraPitch": 25.0,
                            "cameraYaw": 135.0,
                            "showGlideSlope": True,
                            "showTerrain": True
                        }
                    }
                },
                {
                    "id": "html_panel",
                    "component": {
                        "gdm-html-panel": {
                            "html": html_hud,
                            "title": "🎯 Active Target Profiler",
                            "version": tick + loop_ticks + 1
                        }
                    }
                },
                ticker_comp,
                chyron_comp
            ], root_id="grid_layout")
            await asyncio.sleep(2.5 if FAST_MODE else 5.0)

        # ───────────────────────────────────────────────────────────
        # Phase 3: TMA Holding Fix Network Topology Overlay
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 3] Overlaying Glassmorphic Airway Corridor Map...{CLR_RESET}")
        await set_transcript(
            client, space,
            "Projecting terminal holding fix coordinates. Standard arrival paths are mapped from Agen and Laura, merging at the Toulouse TOU VOR for parallel runway sequencing.",
            label="Sector Chief"
        )
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})
        
        chyron_comp["component"]["gdm-chyron"]["title"] = "LFBO TMA AIRWAY NETWORKS"
        chyron_comp["component"]["gdm-chyron"]["subtitle"] = "Standard Terminal Arrival Paths & Intercept Vectors Map"
        chyron_comp["component"]["gdm-chyron"]["accentColor"] = "#ffd60a"

        # Display the custom SVG as a fullscreen glassmorphic diagram takeover overlay
        await render_stage_api(client, space, [
            {
                "id": "grid_layout",
                "component": {
                    "gdm-stage-grid": {
                        "layout": "split",
                        "children": {"explicitList": ["radar_view", "html_panel"]}
                    }
                }
            },
            {
                "id": "radar_view",
                "component": {
                    "gdm-3d-airspace": {
                        "flights": get_fallback_flights(2),
                        "lockedCallsign": "AFR6129",
                        "cameraPitch": 35.0,
                        "cameraYaw": 45.0,
                        "zoom": 10.0,
                        "showGlideSlope": True,
                        "showTerrain": True
                    }
                }
            },
            {
                "id": "html_panel",
                "component": {
                    "gdm-html-panel": {
                        "html": make_supervisor_console_html(get_fallback_flights(2)),
                        "title": "📡 Supervisor Live Console"
                    }
                }
            },
            {
                "id": "airspace_overlay",
                "component": {
                    "gdm-diagram-view": {
                        "svg": airspace_svg,
                        "diagId": "airway_network",
                        "overlay": True
                    }
                }
            },
            ticker_comp,
            chyron_comp
        ], root_id="airspace_overlay")
        await asyncio.sleep(delay)

        # ───────────────────────────────────────────────────────────
        # Phase 4: Sector Traffic Control Poll (Interactive Board Decision)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 4] Initiating Runway Separation Poll...{CLR_RESET}")
        await set_transcript(
            client, space,
            "Launching audience poll. Please select the sequencing vector to resolve landing spacing between EZY4218 and RYR109B.",
            label="Sector Chief"
        )
        
        chyron_comp["component"]["gdm-chyron"]["title"] = "TMA CONFLICT RESOLUTION"
        chyron_comp["component"]["gdm-chyron"]["subtitle"] = "Select separation maneuvers and runway vector allocation"
        chyron_comp["component"]["gdm-chyron"]["accentColor"] = "#00f2ff"

        await render_stage_api(client, space, [
            {
                "id": "grid_layout",
                "component": {
                    "gdm-stage-grid": {
                        "layout": "split",
                        "children": {"explicitList": ["radar_view", "html_panel"]}
                    }
                }
            },
            {
                "id": "radar_view",
                "component": {
                    "gdm-3d-airspace": {
                        "flights": get_fallback_flights(3),
                        "lockedCallsign": "",
                        "cameraPitch": 35.0,
                        "cameraYaw": 45.0,
                        "zoom": 10.0,
                        "showGlideSlope": True,
                        "showTerrain": True
                    }
                }
            },
            {
                "id": "html_panel",
                "component": {
                    "gdm-html-panel": {
                        "html": make_supervisor_console_html(get_fallback_flights(3)),
                        "title": "📡 Supervisor Live Console"
                    }
                }
            },
            {
                "id": "traffic_poll",
                "component": {
                    "gdm-poll-overlay": {
                        "question": "TMA Direction: Resolve separation conflict? 🗳️",
                        "options": [
                            "Establish parallel simultaneous visual arrivals Runway 32L/R",
                            "Vector RYR109B to enter holding pattern at TOU VOR",
                            "Instruct EZY4218 to reduce speed to minimum 180kt"
                        ],
                        "values": [0, 0, 0],
                        "active": True
                    }
                }
            },
            ticker_comp,
            chyron_comp
        ], root_id="grid_layout")
        await asyncio.sleep(2.0)

        # Simulate progressive voting bars
        votes_db = [0, 0, 0]
        for vote_tick in range(4):
            v_add = [random.randint(1, 3), random.randint(0, 2), random.randint(0, 1)]
            votes_db = [votes_db[i] + v_add[i] for i in range(3)]
            print(f"  🗳️ Accumulating board votes... {votes_db}")
            
            await render_stage_api(client, space, [
                {
                    "id": "grid_layout",
                    "component": {
                        "gdm-stage-grid": {
                            "layout": "split",
                            "children": {"explicitList": ["radar_view", "html_panel"]}
                        }
                    }
                },
                {
                    "id": "radar_view",
                    "component": {
                        "gdm-3d-airspace": {
                            "flights": get_fallback_flights(3),
                            "lockedCallsign": "",
                            "cameraPitch": 35.0,
                            "cameraYaw": 45.0,
                            "zoom": 10.0,
                            "showGlideSlope": True,
                            "showTerrain": True
                        }
                    }
                },
                {
                    "id": "html_panel",
                    "component": {
                        "gdm-html-panel": {
                            "html": make_supervisor_console_html(get_fallback_flights(3)),
                            "title": "📡 Supervisor Live Console"
                        }
                    }
                },
                {
                    "id": "traffic_poll",
                    "component": {
                        "gdm-poll-overlay": {
                            "question": "TMA Direction: Resolve separation conflict? 🗳️",
                            "options": [
                                "Establish parallel simultaneous visual arrivals Runway 32L/R",
                                "Vector RYR109B to enter holding pattern at TOU VOR",
                                "Instruct EZY4218 to reduce speed to minimum 180kt"
                            ],
                            "values": votes_db,
                            "active": True
                        }
                    }
                },
                ticker_comp,
                chyron_comp
            ], root_id="grid_layout")
            await asyncio.sleep(0.8)
            
        await asyncio.sleep(delay)

        # ───────────────────────────────────────────────────────────
        # Phase 5: Space Clear & Reaction Storm
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_CYAN}🎬 [Phase 5] Landing Sequence Complete. Initiating Reset Storm...{CLR_RESET}")
        await set_transcript(
            client, space,
            "Approach sequence complete. All flights safely vector-aligned and merged on active runway centerpoints. Restoring TMA sectors back to standby surveillance mode.",
            label="Sector Chief"
        )
        
        # Reset the stage back to standby
        await clear_stage_api(client, space)
        await asyncio.sleep(0.5)

        # Broadcast simulated pilot/controller chats praising the presentation
        chat_logs = [
            ("Librarian AI", "The wide widescreen radar layout with split approach details is absolute genius! 🛰️"),
            ("Antoine — Pilot", "Glideslope alignment profile inside the custom supervisor HTML HUD is extremely professional! ✈️"),
            ("Priya — ATC", "Toulouse TMA airway SVG holding corridors overlay looks incredibly premium. 🗺️"),
            ("Dana K.", "/mainstage Dual-sweep radar sweep tracking live coordinates over LFBO Blagnac is flawless! 🤩")
        ]
        
        for idx, (user, msg) in enumerate(chat_logs):
            print(f"  💬 Broadcasting chat from: {user}")
            await post_endpoint(client, f"/api/chat/{space}", {"sender": user, "text": msg})
            if idx in (0, 2):
                await post_endpoint(client, f"/api/emoji/{space}", {"emoji": "👏"})
                await post_endpoint(client, f"/api/emoji/{space}", {"emoji": "💯"})
            await asyncio.sleep(1.0 if FAST_MODE else 1.8)

        # Final massive congratulations celebration
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "applause"})
        for emo in ["🎉", "✈️", "💯", "🚀", "✨", "🔥", "🤩", "👏", "👑", "🗺️"]:
            await post_endpoint(client, f"/api/emoji/{space}", {"emoji": emo})
            await asyncio.sleep(0.08)

        print(f"\n{CLR_GREEN}🎉 Toulouse Airspace Command Deck Showcase executed successfully!{CLR_RESET}\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{CLR_MAGENTA}Showcase interrupted by user.{CLR_RESET}")
        sys.exit(0)
