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
    CONCIERGE_API_URL: Target FastAPI backend URL (required — set in .env.production.sample)
    STAGE_API_KEY: Secure authorization token.
    MEET_SPACE_ID: Force target Google Meet space.
"""

import asyncio
import os
import sys
import glob
import random
import re
import httpx

# --- Virtualenv Auto-Resolution ---
_base_dir = os.path.dirname(os.path.abspath(__file__))
_venv_dirs = glob.glob(os.path.join(_base_dir, "venv", "lib", "python3.*", "site-packages"))
for _vd in _venv_dirs:
    if _vd not in sys.path:
        sys.path.insert(0, _vd)

# --- Configuration & Environment Setup ---
API_URL = os.environ.get("CONCIERGE_API_URL") or exit("CONCIERGE_API_URL not set — see .env.production.sample")
KEY = os.environ.get("STAGE_API_KEY") or exit("STAGE_API_KEY required — export it before running this script")
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

async def fetch_lfbo_metar(client: httpx.AsyncClient) -> dict:
    """Fetches real METAR for Toulouse Blagnac and parses it. Falls back dynamically if offline."""
    url = "https://tgftp.nws.noaa.gov/data/observations/metar/stations/LFBO.TXT"
    fallback = {
        "wind": "310° @ 12kt",
        "temp": "16°C",
        "pressure": "1015 hPa",
        "clouds": "Few clouds 3000ft",
        "raw": "LFBO 262100Z 31012KT 9999 FEW030 16/11 Q1015"
    }
    try:
        resp = await client.get(url, timeout=3.0)
        if resp.status_code == 200:
            lines = resp.text.strip().splitlines()
            if len(lines) >= 2:
                metar_raw = lines[1].strip()
                # Simple parsing of wind (e.g. 32015KT, VRB05KT, 32015G25KT)
                wind_match = re.search(r'\b(\d{3}|VRB)(\d{2})(G\d{2})?KT\b', metar_raw)
                wind_str = "310° @ 12kt"
                if wind_match:
                    dir_val = wind_match.group(1)
                    speed_val = wind_match.group(2)
                    gust_val = wind_match.group(3)
                    dir_deg = f"{dir_val}°" if dir_val != "VRB" else "Variable"
                    wind_str = f"{dir_deg} @ {speed_val}kt"
                    if gust_val:
                        wind_str += f" (Gusts {gust_val[1:]}kt)"
                
                # Parse temperature (e.g. 15/10, M02/M05)
                temp_match = re.search(r'\b(M?\d{2})\/(M?\d{2})\b', metar_raw)
                temp_str = "16°C"
                if temp_match:
                    t = temp_match.group(1)
                    t_val = int(t.replace('M', '-')) if t.startswith('M') else int(t)
                    temp_str = f"{t_val}°C"
                
                # Parse pressure (e.g. Q1015)
                qnh_match = re.search(r'\bQ(\d{4})\b', metar_raw)
                qnh_str = "1015 hPa"
                if qnh_match:
                    qnh_str = f"{qnh_match.group(1)} hPa"
                
                # Parse clouds (e.g. FEW030, SCT045, BKN035, OVC010)
                cloud_match = re.search(r'\b(FEW|SCT|BKN|OVC|CAVOK|NSC)(\d{3})?\b', metar_raw)
                cloud_str = "Clear skies"
                if cloud_match:
                    typ = cloud_match.group(1)
                    alt = cloud_match.group(2)
                    if typ == "CAVOK":
                        cloud_str = "Clear (CAVOK)"
                    elif typ == "NSC":
                        cloud_str = "No significant clouds"
                    else:
                        alt_ft = int(alt) * 100 if alt else 3000
                        names = {"FEW": "Few", "SCT": "Scattered", "BKN": "Broken", "OVC": "Overcast"}
                        cloud_str = f"{names.get(typ, typ)} clouds @ {alt_ft}ft"
                
                return {
                    "wind": wind_str,
                    "temp": temp_str,
                    "pressure": qnh_str,
                    "clouds": cloud_str,
                    "raw": metar_raw
                }
    except Exception:
        pass
    return fallback

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


def C(cid: str, el: str, props: dict) -> dict:
    """v0.9 flat component dict; strips id/component from props to prevent
    accidental clobbering of structural keys (mirrors the helper in the
    primitives demo and the central template library)."""
    clean = {k: v for k, v in props.items() if k not in ("id", "component")}
    return {"id": cid, "component": el, **clean}


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
            "company": "Air France",
            "aircraft": "Airbus A321",
            "altitude": max(150, 1150 - tick * 100),
            "speed": max(135, 260 - tick * 12),
            "vrate": -1100,
            "origin": "ORY",
            "destination": "TLS",
            "dep_time": "19:40",
            "squawk": "1242"
        },
        {
            "callsign": "BAW373",
            "company": "British Airways",
            "aircraft": "Airbus A320",
            "altitude": max(300, 2400 - tick * 150),
            "speed": max(145, 300 - tick * 15),
            "vrate": -1400,
            "origin": "LHR",
            "destination": "TLS",
            "dep_time": "18:15",
            "squawk": "2104"
        },
        {
            "callsign": "EZY4218",
            "company": "EasyJet",
            "aircraft": "Airbus A319",
            "altitude": max(600, 3800 - tick * 200),
            "speed": max(155, 340 - tick * 18),
            "vrate": -1700,
            "origin": "LGW",
            "destination": "TLS",
            "dep_time": "18:45",
            "squawk": "4215"
        },
        {
            "callsign": "RYR109B",
            "company": "Ryanair",
            "aircraft": "Boeing 737",
            "altitude": max(1200, 4900 - tick * 250),
            "speed": max(165, 380 - tick * 20),
            "vrate": -900,
            "origin": "STN",
            "destination": "TLS",
            "dep_time": "18:30",
            "squawk": "7302"
        },
        {
            "callsign": "DLH11A",
            "company": "Lufthansa",
            "aircraft": "Airbus A321",
            "altitude": max(2100, 5800 - tick * 300),
            "speed": max(180, 410 - tick * 22),
            "vrate": -1200,
            "origin": "FRA",
            "destination": "TLS",
            "dep_time": "19:25",
            "squawk": "1104"
        }
    ]

    # Calculate ETA based on remaining altitude and descent rate
    for f in flights:
        alt_m = f["altitude"]
        vrate_fpm = abs(f["vrate"])
        # convert altitude from meters to feet: 1m = 3.28084ft
        alt_ft = alt_m * 3.28084
        # minutes to touchdown = alt_ft / vrate_fpm
        if vrate_fpm > 0:
            minutes_to_touchdown = alt_ft / vrate_fpm
        else:
            minutes_to_touchdown = 5.0
            
        seconds_to_touchdown = int(minutes_to_touchdown * 60)
        
        # Calculate dynamic absolute ETA assuming current base time of 20:50:00
        base_seconds = 20 * 3600 + 50 * 60
        target_seconds = base_seconds + seconds_to_touchdown
        
        eta_hr = (target_seconds // 3600) % 24
        eta_min = (target_seconds // 60) % 60
        eta_sec = target_seconds % 60
        
        f["eta"] = f"{eta_hr:02d}:{eta_min:02d}:{eta_sec:02d}"
        f["eta_relative"] = f"{seconds_to_touchdown // 60}m {seconds_to_touchdown % 60:02d}s"

    flights.sort(key=lambda f: f["altitude"])
    return flights

# --- Custom HTML Console Markup Generator ---
def make_supervisor_console_html(flights: list[dict], weather: dict) -> str:
    """Generates the live ATC Sector Supervisor Console HTML panel content."""
    rows_markup = ""
    for f in flights:
        vrate = f["vrate"]
        vr_symbol = "▼" if vrate < -250 else ("▲" if vrate > 250 else "—")
        if vrate < -250:
            color_class = "text-up"
        elif vrate > 250:
            color_class = "text-warning"
        else:
            color_class = "text-cyan"
            
        fl = f"{int(f['altitude'] * 3.28084 / 100):03d}"
        
        # Determine airspace handover fix based on altitude
        if f["altitude"] < 500:
            status_pill = '<span class="status-pill landed">Landed</span>'
        elif f["altitude"] < 1000:
            status_pill = '<span class="status-pill approach">Final Approach</span>'
        elif f["altitude"] < 2500:
            status_pill = '<span class="status-pill approach">Approach Fix</span>'
        else:
            status_pill = '<span class="status-pill established">Established</span>'
            
        rows_markup += f"""
        <tr>
            <td class="font-bold">{f['company']}</td>
            <td class="{color_class} font-bold font-mono">{f['callsign']}</td>
            <td class="font-mono">{f['aircraft']}</td>
            <td class="font-mono font-bold">{f['origin']} ➔ {f['destination']}</td>
            <td class="font-mono text-mute">{f['dep_time']}</td>
            <td class="font-mono text-warning">{f['eta']}</td>
            <td class="font-mono text-warning font-bold">{f['eta_relative']}</td>
            <td class="font-mono">FL{fl} <span class="text-mute text-xs">({f['altitude']}m)</span></td>
            <td class="{color_class} font-mono">{vr_symbol} {abs(vrate)} fpm</td>
            <td>{status_pill}</td>
            <td class="font-mono text-mute">{f['squawk']}</td>
        </tr>
        """
        
    return f"""
    <link rel="stylesheet" href="{API_URL}/stage_components.css">
    <div class="hud-container">
        <div class="hud-header">
            <div class="hud-title">
                <div class="pulse-dot"></div>
                📡 TLS-SECTOR SUPERVISOR CONSOLE
            </div>
            <div class="hud-subtitle-badge">LFBO-APP</div>
        </div>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Active Runway Corridor</div>
                <div class="metric-value text-up">ILS Runway 32L/R</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Active Wind & METAR</div>
                <div class="metric-value font-mono">{weather['wind']} ({weather['temp']})</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Sector Capacity</div>
                <div class="metric-value text-cyan">5/12 ACFT</div>
            </div>
        </div>
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>Airline</th>
                        <th>Flight No</th>
                        <th>Aircraft</th>
                        <th>Route</th>
                        <th>Departure</th>
                        <th>ETA (UTC)</th>
                        <th>Countdown</th>
                        <th>Altitude</th>
                        <th>V-Rate</th>
                        <th>Sector Status</th>
                        <th>Squawk</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_markup}
                </tbody>
            </table>
        </div>
    </div>
    """

def make_target_profile_html(flight: dict, tick: int) -> str:
    """Generates the glowing Target Operations Profile HUD for a locked aircraft."""
    altitude_ft = int(flight["altitude"] * 3.28084)
    fl = f"{int(altitude_ft / 100):03d}"
    vrate = flight["vrate"]
    
    # Deceleration progress bar (Target landing speed ~135kt, max approach speed ~340kt)
    pct_speed = int(max(0, min(100, (flight["speed"] - 135) / (340 - 135) * 100)))
    
    # Glidepath deviation visualizer (simulate on glideslope centering diamond)
    glide_deviation = "ON COURSE" if flight["altitude"] > 100 else "DECELERATION ROLL"
    
    return f"""
    <link rel="stylesheet" href="{API_URL}/stage_components.css">
    <div class="hud-container green-theme">
        <div class="hud-header green-theme">
            <div class="hud-title green-theme">
                <div class="pulse-dot"></div>
                🎯 ACTIVE TARGET OPERATIONS PROFILE
            </div>
            <div class="hud-subtitle-badge green-theme">VECTORS LOCK ON</div>
        </div>
        
        <div class="flex-between align-start margin-bottom-md">
            <div>
                <div class="target-callsign">{flight['callsign']}</div>
                <div class="font-bold font-mono text-up text-uppercase text-xs">
                    {flight['company']} • {flight['origin']} ➔ {flight['destination']}
                </div>
            </div>
            <div class="text-right">
                <div class="font-bold text-uppercase text-mute text-xs">Squawk</div>
                <div class="font-bold font-mono text-cyan text-lg glow-cyan">{flight['squawk']}</div>
            </div>
        </div>
        
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Primary Altitude</div>
                <div class="metric-value">{flight['altitude']}m <span class="text-mute text-xs">/ FL{fl}</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Airspeed Reference</div>
                <div class="metric-value text-up">{flight['speed']} kt</div>
                <progress value="{pct_speed}" max="100"></progress>
            </div>
            <div class="metric-card">
                <div class="metric-label">Vertical Descent Speed</div>
                <div class="metric-value text-up">{vrate} fpm</div>
            </div>
        </div>
        
        <div class="metric-grid grid-2 margin-bottom-md">
            <div class="metric-card">
                <div class="metric-label">Aircraft Type</div>
                <div class="metric-value font-mono">{flight['aircraft']}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Touchdown ETA</div>
                <div class="metric-value text-warning">{flight['eta_relative']} <span class="text-mute text-xs">({flight['eta']})</span></div>
            </div>
        </div>
        
        <div class="glidepath-visual">
            <div class="font-bold text-uppercase text-mute text-xs text-letterspace margin-bottom-sm">3-Degree Instrument Landing Corridor</div>
            <div class="font-bold text-cyan text-letterspace margin-bottom-sm">{glide_deviation}</div>
            <div class="glideslope-line">
                <div class="glide-notch"></div>
                <div class="glide-notch"></div>
                <div class="glide-diamond"></div>
                <div class="glide-notch"></div>
                <div class="glide-notch"></div>
            </div>
            <div class="font-mono text-mute text-xs margin-top-sm">ILS GS-32L FREQ: 110.10 MHz • DME LOCK: 1.8 NM</div>
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
        print(f"  {CLR_SLATE}A2UI Specification:{CLR_RESET} {CLR_CYAN}v0.9 Dark Cyberpunk Theme{CLR_RESET}\n")

        # Fetch live METAR weather data
        weather = await fetch_lfbo_metar(client)
        print(f"  🌦️  Fetched Toulouse Live METAR: {weather['raw']}")
        local_airspace_svg = airspace_svg.replace("QNH 1015 HPA", f"QNH {weather['pressure'].upper()}")

        # ───────────────────────────────────────────────────────────
        # Phase 0: S-Band Transceiver Calibration (Countdown Slate)
        # ───────────────────────────────────────────────────────────
        print(f"{CLR_CYAN}🎬 [Phase 0] Calibrating Primary S-Band Radar Transceivers...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})
        await render_stage_api(client, space, [
            C("calibration_slate", "gdm-standby-slate", {
                "title": "📡 TLS Sector 32L/R Sweep Calibration",
                "description": "Booting transponder tracking matrix and aligning primary S-Band receivers...",
                "active": True,
                "seconds": 5,
                "fullscreen": True,
            })
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
        
        ticker_comp = C("airspace_ticker", "gdm-ticker", {
            "text": f"📍 LFBO Terminal Information • RUNWAY 32L/R ACTIVE FOR ARRIVALS • SURFACE WIND: {weather['wind'].upper()} • TEMP: {weather['temp']} • QNH: {weather['pressure']} • SQUAWK 7700 ALERT: NONE • ACTIVE TRAFFIC SENSORS: ONLINE • RAW METAR: {weather['raw']} •",
            "scrollSpeed": 50,
            "active": True,
            "accentColor": "#00ff88",
        })
        
        chyron_comp = C("atc_chyron", "gdm-chyron", {
            "title": "LFBO TMA APPROACH CONTROL",
            "subtitle": "Active Approach Vectors Runway 32L/R",
            "active": True,
            "accentColor": "#00ff88",
        })

        deactivated_slate = C("calibration_slate", "gdm-standby-slate", {
            "active": False,
        })

        for tick in range(loop_ticks):
            print(f"  📡 Sweeping Sector Space (Tick {tick+1}/{loop_ticks})...")
            flights = get_fallback_flights(tick=tick)
            html_console = make_supervisor_console_html(flights, weather)
            
            await render_stage_api(client, space, [
                C("grid_layout", "gdm-stage-grid", {
                    "layout": "split",
                    "children": ["radar_view", "html_panel"],
                }),
                C("radar_view", "gdm-3d-airspace", {
                    "flights": flights,
                    "lockedCallsign": "",
                    **({
                        "zoom": 5.5,
                        "cameraPitch": 35.0,
                        "cameraYaw": 45.0,
                    } if tick == 0 else {}),
                    "showGlideSlope": True,
                    "showTerrain": True,
                    "cinematicOrbit": True,
                    "autoTrack": False,
                }),
                C("html_panel", "gdm-html-panel", {
                    "html": html_console,
                    "title": "📡 Tactical Supervisor HUD",
                    "version": tick + 1,
                }),
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
        
        chyron_comp["title"] = "TARGET ACQUIRED: AFR6129"
        chyron_comp["subtitle"] = "Tracking Descent Path and Instrument Glide Slope Runway 32L"
        chyron_comp["accentColor"] = "#00f2ff"

        for tick in range(loop_ticks):
            print(f"  🎯 Profiling Target AFR6129 (Tick {tick+1}/{loop_ticks})...")
            flights = get_fallback_flights(tick=tick + loop_ticks)
            lead_flight = flights[0]  # AFR6129 is sorted to index 0 (lowest altitude)
            html_hud = make_target_profile_html(lead_flight, tick)
            
            await render_stage_api(client, space, [
                C("grid_layout", "gdm-stage-grid", {
                    "layout": "split",
                    "children": ["radar_view", "html_panel"],
                }),
                C("radar_view", "gdm-3d-airspace", {
                    "flights": flights,
                    "lockedCallsign": "AFR6129",
                    **({
                        "zoom": 4.0,
                        "cameraPitch": 25.0,
                        "cameraYaw": 135.0,
                    } if tick == 0 else {}),
                    "showGlideSlope": True,
                    "showTerrain": True,
                    "cinematicOrbit": True,
                    "autoTrack": True,
                }),
                C("html_panel", "gdm-html-panel", {
                    "html": html_hud,
                    "title": "🎯 Active Target Profiler",
                    "version": tick + loop_ticks + 1,
                }),
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
        
        chyron_comp["title"] = "LFBO TMA AIRWAY NETWORKS"
        chyron_comp["subtitle"] = "Standard Terminal Arrival Paths & Intercept Vectors Map"
        chyron_comp["accentColor"] = "#ffd60a"

        # Display the custom SVG as a fullscreen glassmorphic diagram takeover overlay
        await render_stage_api(client, space, [
            C("grid_layout", "gdm-stage-grid", {
                "layout": "split",
                "children": ["radar_view", "html_panel"],
            }),
            C("radar_view", "gdm-3d-airspace", {
                "flights": get_fallback_flights(2),
                "lockedCallsign": "AFR6129",
                "cameraPitch": 35.0,
                "cameraYaw": 45.0,
                "zoom": 5.5,
                "showGlideSlope": True,
                "showTerrain": True,
            }),
            C("html_panel", "gdm-html-panel", {
                "html": make_supervisor_console_html(get_fallback_flights(2), weather),
                "title": "📡 Supervisor Live Console",
            }),
            C("airspace_overlay", "gdm-diagram-view", {
                "svg": local_airspace_svg,
                "diagId": "airway_network",
                "overlay": True,
            }),
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
        
        chyron_comp["title"] = "TMA CONFLICT RESOLUTION"
        chyron_comp["subtitle"] = "Select separation maneuvers and runway vector allocation"
        chyron_comp["accentColor"] = "#00f2ff"

        await render_stage_api(client, space, [
            C("grid_layout", "gdm-stage-grid", {
                "layout": "split",
                "children": ["radar_view", "html_panel"],
            }),
            C("radar_view", "gdm-3d-airspace", {
                "flights": get_fallback_flights(3),
                "lockedCallsign": "",
                "cameraPitch": 35.0,
                "cameraYaw": 45.0,
                "zoom": 5.5,
                "showGlideSlope": True,
                "showTerrain": True,
                "cinematicOrbit": True,
                "autoTrack": False,
            }),
            C("html_panel", "gdm-html-panel", {
                "html": make_supervisor_console_html(get_fallback_flights(3), weather),
                "title": "📡 Supervisor Live Console",
            }),
            C("traffic_poll", "gdm-poll-overlay", {
                "question": "TMA Direction: Resolve separation conflict? 🗳️",
                "options": [
                    "Establish parallel simultaneous visual arrivals Runway 32L/R",
                    "Vector RYR109B to enter holding pattern at TOU VOR",
                    "Instruct EZY4218 to reduce speed to minimum 180kt"
                ],
                "values": [0, 0, 0],
                "active": True,
            }),
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
                C("grid_layout", "gdm-stage-grid", {
                    "layout": "split",
                    "children": ["radar_view", "html_panel"],
                }),
                C("radar_view", "gdm-3d-airspace", {
                    "flights": get_fallback_flights(3),
                    "lockedCallsign": "",
                    "showGlideSlope": True,
                    "showTerrain": True,
                    "cinematicOrbit": True,
                    "autoTrack": False,
                }),
                C("html_panel", "gdm-html-panel", {
                    "html": make_supervisor_console_html(get_fallback_flights(3), weather),
                    "title": "📡 Supervisor Live Console",
                }),
                C("traffic_poll", "gdm-poll-overlay", {
                    "question": "TMA Direction: Resolve separation conflict? 🗳️",
                    "options": [
                        "Establish parallel simultaneous visual arrivals Runway 32L/R",
                        "Vector RYR109B to enter holding pattern at TOU VOR",
                        "Instruct EZY4218 to reduce speed to minimum 180kt"
                    ],
                    "values": votes_db,
                    "active": True,
                }),
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
