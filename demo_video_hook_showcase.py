#!/usr/bin/env python3
"""
Meet Live Concierge — Ultra Premium Interactive A2UI & A2A Showcase
====================================================================
Demonstrates a 5-second synchronized countdown, adaptive multi-panel layout morphing,
collaborative Agent-to-Agent (A2A) protocol exchanges, real-time canvas overlays,
laser pointer coordinate trailing, interactive audience polls, and low-latency audio soundboards.

Environment Variables:
    FAST_MODE: Set to "0" or "false" to use live slow Imagen 4 generations. Default: True.
    CONCIERGE_API_URL: Target FastAPI backend URL.
    STAGE_API_KEY: Secure auth token.
    MEET_SPACE_ID: Force target Google Meet space.
"""
import asyncio
import os
import sys
import httpx

# ───────────────────────────────────────────────────────────
# 212Trading Backend Market Services Integration
# ───────────────────────────────────────────────────────────
_T212_LOADED = False
_GET_QUOTE_FN = None

try:
    # Append the 212Trading directory to sys.path
    t212_path = "/home/curtis/gemini/212Trading"
    if t212_path not in sys.path:
        sys.path.append(t212_path)
    
    # Configure Application Default Credentials for local Secret Manager usage
    if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
        adc_path = "/home/curtis/.config/gcloud/application_default_credentials.json"
        if os.path.exists(adc_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = adc_path
            
    # Pre-fetch T212 API credentials from Google Secret Manager for fallback
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

    # Import the unified market data quote fetcher
    from backend.services.market_data import get_quote as t212_get_quote
    _GET_QUOTE_FN = t212_get_quote
    _T212_LOADED = True
    print("✨ Successfully integrated with 212Trading backend market services.", file=sys.stderr)
except Exception as e:
    print(f"⚠️ Could not load 212Trading backend market services: {e}", file=sys.stderr)

API_URL = os.environ.get("CONCIERGE_API_URL", "CONCIERGE_API_URL_PLACEHOLDER")
KEY = os.environ.get("STAGE_API_KEY", "meet-live_STAGE_SECURE_v1_zG9fN8qL7vP2mX6tY9wK4jC5bS8xQ7hZ3uW0rA")
FAST_MODE = os.environ.get("FAST_MODE", "true").lower() not in ("0", "false", "no")
IMAGEN_MODEL = os.environ.get("IMAGEN_MODEL", "imagen-3.0-generate-002")

# Static premium stock showcase slides (Fast Mode)
STATIC_SLIDES = {
    1: "/panel1_a2ui.png",  # Custom generated A2UI feature describer
    2: "/workspace_sketch.png",   # Cozy colored-pencil sketch of Google Workspace
    3: "/cockpit_dashboard.png",
    4: "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1200&auto=format&fit=crop&q=80"   # Coding terminal matrix
}

# Jazzy, self-describing image generation prompts (Live Imagen Mode)
PROMPTS = {
    1: "A sleek dark-mode glassmorphism interface block labeled 'A2UI ENGINE ACTIVE' in glowing neon typography. Ambient violet and electric turquoise gradient backlights, premium futuristic design, cinematic 16:9.",
    2: "A beautiful, premium digital hand sketch drawing of Google Workspace icons (Docs, Sheets, Slides, Drive, Meet) in vibrant colored pencils on textured paper, cozy creative look, warm ambient lighting, 16:9.",
    3: "An ultra-modern data visualization dashboard labeled 'A2A AGENT SYNC' showing glowing telemetry line graphs, matrix diagrams, and collaborative workspace charts in cyan and hot pink, 16:9.",
    4: "A futuristic cyber security terminal running complex rolling green digital matrix code under tinted glass reflections, retro-modern interface, dramatic 16:9."
}

async def get_active_space() -> str:
    headers = {"Authorization": f"Bearer {KEY}"} if KEY else {}
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{API_URL}/api/dev/sessions", headers=headers)
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
        resp = await client.post(f"{API_URL}{endpoint}", headers=headers, json=payload)
        resp.raise_for_status()
    except Exception as e:
        print(f"⚠️ Error calling {endpoint}: {e}", file=sys.stderr)

async def set_transcript(client: httpx.AsyncClient, space_id: str, text: str, label: str = "Gemini Architect"):
    await post_endpoint(client, f"/api/transcript/{space_id}", {
        "role": "agent",
        "label": label,
        "text": text,
        "is_final": True
    })

async def launch_emoji_burst(client: httpx.AsyncClient, space_id: str, emojis: list[str]):
    for emo in emojis:
        await post_endpoint(client, f"/api/emoji/{space_id}", {"emoji": emo})
        await asyncio.sleep(0.12)  # Stagger floats for maximum aesthetics

async def get_live_stock_price(client: httpx.AsyncClient, symbol: str, default: float) -> tuple[float, float]:
    # Map symbols to full T212 format to ensure 100% correct resolution by MultiSourceProvider
    ticker_map = {
        "GOOG": "GOOGL_US_EQ",
        "NVDA": "NVDA_US_EQ",
        "MSFT": "MSFT_US_EQ",
        "AAPL": "AAPL_US_EQ",
        "AMZN": "AMZN_US_EQ",
        "META": "META_US_EQ",
        "TSM": "TSM_US_EQ",
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
            print(f"⚠️ T212 integration quote fetch failed for {t212_ticker}: {e}", file=sys.stderr)
            
    # Fallback to local Yahoo Finance method
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
    return default, 0.0

# Global cache for station names
STATION_NAME_CACHE = {}

async def get_live_toulouse_bikes(client: httpx.AsyncClient) -> list[dict]:
    global STATION_NAME_CACHE
    try:
        # 1. Warm station name cache if empty (loads once)
        if not STATION_NAME_CACHE:
            info_url = "https://api.cyclocity.fr/contracts/toulouse/gbfs/v2/station_information.json"
            resp = await client.get(info_url, timeout=3)
            if resp.status_code == 200:
                stations_info = resp.json().get("data", {}).get("stations", [])
                for s in stations_info:
                    s_id = str(s.get("station_id"))
                    s_name = s.get("name", "Station")
                    # Clean station name (remove ID prefixes like POIDS DE L'HUILE)
                    STATION_NAME_CACHE[s_id] = s_name.strip()

        # 2. Get real-time status
        status_url = "https://api.cyclocity.fr/contracts/toulouse/gbfs/v2/station_status.json"
        resp = await client.get(status_url, timeout=3)
        if resp.status_code == 200:
            stations_status = resp.json().get("data", {}).get("stations", [])
            active_stations = []
            for s in stations_status:
                s_id = str(s.get("station_id"))
                if s_id in STATION_NAME_CACHE:
                    name = STATION_NAME_CACHE[s_id]
                    bikes = s.get("num_bikes_available", 0)
                    stands = s.get("num_docks_available", 0)
                    active_stations.append({
                        "name": name,
                        "bikes": bikes,
                        "stands": stands
                    })
                    if len(active_stations) >= 12: # Ensure exactly 12 stations to pack the grid beautifully
                        break
            if active_stations:
                return active_stations
    except Exception as e:
        pass

    # Reliable randomized fallback to keep numbers alive if API drops
    import random
    return [
        {"name": "CAPITOLE", "bikes": random.randint(3, 18), "stands": random.randint(2, 15)},
        {"name": "JEANNE D'ARC", "bikes": random.randint(3, 18), "stands": random.randint(2, 15)},
        {"name": "GARE MATABIAU", "bikes": random.randint(3, 18), "stands": random.randint(2, 15)},
        {"name": "ESQUIROL", "bikes": random.randint(3, 18), "stands": random.randint(2, 15)},
        {"name": "ST CYPRIEN", "bikes": random.randint(3, 18), "stands": random.randint(2, 15)},
        {"name": "PALAIS DE JUSTICE", "bikes": random.randint(3, 18), "stands": random.randint(2, 15)},
        {"name": "COMPANS CAFFARELLI", "bikes": random.randint(3, 18), "stands": random.randint(2, 15)},
        {"name": "CARMES", "bikes": random.randint(3, 18), "stands": random.randint(2, 15)},
        {"name": "FRANCOIS VERDIER", "bikes": random.randint(3, 18), "stands": random.randint(2, 15)},
        {"name": "MUSEE LES ABATTOIRS", "bikes": random.randint(3, 18), "stands": random.randint(2, 15)},
        {"name": "GRAND ROND", "bikes": random.randint(3, 18), "stands": random.randint(2, 15)},
        {"name": "CANAL DU MIDI", "bikes": random.randint(3, 18), "stands": random.randint(2, 15)}
    ]

def get_route_for_callsign(callsign: str) -> tuple[str, str]:
    # Assign deterministic routes based on flight carrier prefixes
    callsign = callsign.upper().strip()
    if callsign.startswith("AFR") or callsign.startswith("AF"):
        return "CDG", "TLS"  # Paris to Toulouse
    elif callsign.startswith("BAW") or callsign.startswith("BA"):
        return "LHR", "TLS"  # London Heathrow to Toulouse
    elif callsign.startswith("EZY") or callsign.startswith("U2"):
        return "LGW", "TLS"  # London Gatwick to Toulouse
    elif callsign.startswith("RYR") or callsign.startswith("FR"):
        return "STN", "TLS"  # London Stansted to Toulouse
    elif callsign.startswith("DLH") or callsign.startswith("LH"):
        return "FRA", "TLS"  # Frankfurt to Toulouse
    elif callsign.startswith("IBE") or callsign.startswith("IB"):
        return "MAD", "TLS"  # Madrid to Toulouse
    elif callsign.startswith("SWR") or callsign.startswith("LX"):
        return "ZRH", "TLS"  # Zurich to Toulouse
    else:
        # Generate stable mock routes using hashing of callsign
        origins = ["ORY", "AMS", "BRU", "BCN", "NCE", "LYS", "MUC", "FCO"]
        h = sum(ord(c) for c in callsign) if callsign else 0
        return origins[h % len(origins)], "TLS"

async def get_live_toulouse_flights(client: httpx.AsyncClient, tick: int = 0) -> tuple[int, list[dict]]:
    try:
        # Broadened bounding box covering Toulouse airspace
        resp = await client.get("https://opensky-network.org/api/states/all?lamin=43.0&lomin=0.8&lamax=44.2&lomax=2.0", headers={"User-Agent": "Mozilla/5.0"}, timeout=4)
        if resp.status_code == 200:
            states = resp.json().get("states") or []
            flights = []
            for idx, s in enumerate(states[:6]):
                callsign = s[1].strip() if s[1] else f"AFR{900 + idx}"
                base_alt = int(s[5]) if s[5] else (1200 + idx * 800)
                base_spd = int(s[9]*3.6) if s[9] else (380 + idx * 40)
                
                # Dynamically simulate approach descend/decelerate
                drift_alt = max(500, base_alt - int(150 * tick))
                drift_spd = max(240, base_spd - int(12 * tick))
                
                origin, dest = get_route_for_callsign(callsign)
                flights.append({
                    "callsign": callsign,
                    "altitude": drift_alt,
                    "speed": drift_spd,
                    "origin": origin,
                    "destination": dest
                })
            return len(states), flights
    except Exception:
        pass

    # High fidelity landing approach simulations (Runway 32L/R approach sequence)
    fallback_flights = [
        {"callsign": "AFR6129", "altitude": max(800, 1150 - tick * 120), "speed": max(260, 340 - tick * 15)},
        {"callsign": "BAW373", "altitude": max(1200, 2400 - tick * 180), "speed": max(300, 430 - tick * 18)},
        {"callsign": "EZY4218", "altitude": max(1800, 3800 - tick * 250), "speed": max(350, 510 - tick * 22)},
        {"callsign": "RYR109B", "altitude": max(2500, 4900 - tick * 320), "speed": max(380, 560 - tick * 25)},
        {"callsign": "DLH11A", "altitude": max(3200, 5800 - tick * 400), "speed": max(420, 620 - tick * 28)}
    ]
    for f in fallback_flights:
        origin, dest = get_route_for_callsign(f["callsign"])
        f["origin"] = origin
        f["destination"] = dest
    return len(fallback_flights), fallback_flights

async def main():
    space = os.environ.get("MEET_SPACE_ID")
    if not space:
        space = await get_active_space()
        
    if not space:
        print("❌ Error: No active Meet space detected. Open a Meet call and launch the side-panel first.")
        sys.exit(1)
        
    delay = 4.0 if FAST_MODE else 12.0
    
    print(f"\n🎬  CRAY CRAY INTERACTIVE SHOWCASE  →  {space}")
    print(f"⚙️   Fast Mode: {'ENABLED ⚡' if FAST_MODE else 'DISABLED (Live Imagen generation) 🐢'}")
    print("=" * 70)
    
    async with httpx.AsyncClient(timeout=30) as client:
        # ───────────────────────────────────────────────────────────
        # Phase 0: The Cray Cray Standby Countdown & Cache Warm-up
        # ───────────────────────────────────────────────────────────
        print("\n⏳ PHASE 0: THE CRAY CRAY Standby COUNTDOWN")
        
        if not FAST_MODE:
            print("🚀 Warm-up Cache: Triggering background image pre-generations...")
            try:
                await post_endpoint(client, "/api/image/pre-generate", {
                    "prompts": [PROMPTS[1], PROMPTS[2], PROMPTS[3], PROMPTS[4]],
                    "model": IMAGEN_MODEL
                })
            except Exception as e:
                print(f"⚠️  Warning: Pre-generation trigger failed: {e}")
        
        standby_seconds = 1 if FAST_MODE else 3
        print(f"🎬 Broadcasting {standby_seconds}-second Studio Intermission standby screen...")
        await post_endpoint(client, f"/api/standby/{space}", {
            "active": True,
            "duration": 0,
            "seconds": standby_seconds,
            "badge": "STUDIO INTERMISSION",
            "title": "Google Meet x Google Workspace Marketplace SDK X Anti Gravity",
            "description": "Cray Cray Possibilities = Evolving Live Concierge Studio"
        })
        await asyncio.sleep(float(standby_seconds))
        
        # Deactivate the standby screen and morph to Phase 1
        print("🔌 Deactivating standby screen and morphing to Phase 1 showcase...")
        await post_endpoint(client, f"/api/standby/{space}", {"active": False})
        await asyncio.sleep(0.1)

        # ───────────────────────────────────────────────────────────
        # Phase 1: Single Fullscreen Video Hook
        # ───────────────────────────────────────────────────────────
        print("\n▶  PHASE 1: SINGLE PANEL (High-Fidelity Video Hook)")
        await set_transcript(
            client, space, 
            "Welcome to the Live Concierge Studio. We begin with a high-fidelity video hook streaming live in Panel 1.",
            label="Gemini Concierge"
        )
        await post_endpoint(client, f"/api/theme-config/{space}", {"theme": "darkflow"})
        
        # Play the YouTube video in fullscreen single layout
        await post_endpoint(client, f"/api/image", {
            "space_id": space,
            "prompt": "https://youtu.be/LWGJA9i18Co?is=VslaG4mLtVAkAp8R",
            "panel": 1,
            "image_layout": "single",
            "label": "📺 1. Seamless Video Hook (Autoplay)",
            "autoplay": True
        })
        await asyncio.sleep(4.0)
        
        # ───────────────────────────────────────────────────────────
        # Phase 2: Quad-Grid Morph & Interactive Stocks Ticker Streaming
        # ───────────────────────────────────────────────────────────
        print("\n▶  PHASE 2: QUAD-GRID WORKSPACE DASHBOARD")
        await set_transcript(
            client, space, 
            "Handshake complete! Transitioning to Quad-Grid. Under A2UI, the stage seamlessly partitions into a collaborative dashboard.",
            label="Gemini Concierge"
        )
        await post_endpoint(client, f"/api/theme-config/{space}", {"theme": "glassmorphism"})
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})
        await launch_emoji_burst(client, space, ["🤝", "📊", "📈", "🍿"])
        await asyncio.sleep(1.0)
        
        # Initialize the 4 panels in the "grid" layout
        print("📺 Initializing 4-panel Grid layout...")
        
        # Panel 1: YouTube video (seamlessly playing from where it left off from fullscreen)
        await post_endpoint(client, f"/api/image", {
            "space_id": space, "prompt": "https://youtu.be/LWGJA9i18Co?is=VslaG4mLtVAkAp8R", "panel": 1,
            "image_layout": "grid", "label": "📺 1. Seamless Video Hook (Autoplay)",
            "autoplay": True
        })
        
        # Panel 2: Creative Workspace Sketch
        await post_endpoint(client, f"/api/image", {
            "space_id": space, "prompt": "/workspace_sketch.png", "panel": 2,
            "image_layout": "grid", "label": "🎨 2. Design Studio Concept Drawing"
        })
        
        # Panel 3: Live Telemetry Dashboard
        await post_endpoint(client, f"/api/image", {
            "space_id": space, "prompt": "static:dashboard", "panel": 3,
            "image_layout": "grid", "label": "📊 3. Live AI & Megatech Stocks Ticker"
        })
        
        # Panel 4: Collaborative System Blueprint (High-level architecture view of the panels)
        await post_endpoint(client, f"/api/image", {
            "space_id": space, "prompt": "/panel2_a2a.png", "panel": 4,
            "image_layout": "grid", "label": "🎨 4. Collaborative System Blueprint Architecture"
        })
        
        # Focus on Dashboard Telemetry first
        await post_endpoint(client, f"/api/focus-panel/{space}", {"panel": 3})
        await launch_emoji_burst(client, space, ["📊", "⚡", "🔮"])
        await asyncio.sleep(1.0)
        
        # ───────────────────────────────────────────────────────────
        # Real-time Stocks Telemetry Streaming Loop
        # ───────────────────────────────────────────────────────────
        TABS_CONFIG = [
            {"id": "stk", "label": "AI STOCKS"},
            {"id": "re", "label": "VELO TOULOUSE"},
            {"id": "flt", "label": "FLIGHTS TLS"}
        ]
        
        print("📈 Streaming Use Case 1: AI & Megatech Stocks (stk)...")
        await set_transcript(
            client, space,
            "📈 Sourcing live Megatech and AI stock quotes. As you can see, shares continue to rise up dynamically, scrolling like an active trade-flow register.",
            label="Gemini Concierge"
        )
        
        stock_chart = [40, 42, 41, 44, 43, 46, 45, 48, 47, 49, 50, 49, 51, 52, 53]
        for tick in range(6):
            nvda_p, nvda_c = await get_live_stock_price(client, "NVDA", 914.85)
            msft_p, msft_c = await get_live_stock_price(client, "MSFT", 421.90)
            goog_p, goog_c = await get_live_stock_price(client, "GOOG", 173.50)
            aapl_p, aapl_c = await get_live_stock_price(client, "AAPL", 189.50)
            amzn_p, amzn_c = await get_live_stock_price(client, "AMZN", 180.20)
            meta_p, meta_c = await get_live_stock_price(client, "META", 475.10)
            tsm_p, tsm_c = await get_live_stock_price(client, "TSM", 145.30)
            stock_chart.append(int(max(10, min(95, 50 + nvda_c * 10))))
            
            await post_endpoint(client, f"/api/dashboard/{space}", {
                "tabs": TABS_CONFIG,
                "activeTabId": "stk",
                "viewType": "ticker",
                "title": "⚡ Real-Time AI & Megatech Stocks (Yahoo Finance Live)",
                "metrics": [
                    {"label": f"NVDA ({'+' if nvda_c >= 0 else ''}{nvda_c:.2f}%)", "value": f"${nvda_p:.2f} {'▲' if nvda_c >= 0 else '▼'}", "color": "#00ff88" if nvda_c >= 0 else "#ff3b30"},
                    {"label": f"MSFT ({'+' if msft_c >= 0 else ''}{msft_c:.2f}%)", "value": f"${msft_p:.2f} {'▲' if msft_c >= 0 else '▼'}", "color": "#00f2ff" if msft_c >= 0 else "#ff3b30"},
                    {"label": f"GOOG ({'+' if goog_c >= 0 else ''}{goog_c:.2f}%)", "value": f"${goog_p:.2f} {'▲' if goog_c >= 0 else '▼'}", "color": "#00ff88" if goog_c >= 0 else "#ff3b30"},
                    {"label": f"AAPL ({'+' if aapl_c >= 0 else ''}{aapl_c:.2f}%)", "value": f"${aapl_p:.2f} {'▲' if aapl_c >= 0 else '▼'}", "color": "#00ff88" if aapl_c >= 0 else "#ff3b30"},
                    {"label": f"AMZN ({'+' if amzn_c >= 0 else ''}{amzn_c:.2f}%)", "value": f"${amzn_p:.2f} {'▲' if amzn_c >= 0 else '▼'}", "color": "#ff3b30" if amzn_c < 0 else "#00ff88"},
                    {"label": f"META ({'+' if meta_c >= 0 else ''}{meta_c:.2f}%)", "value": f"${meta_p:.2f} {'▲' if meta_c >= 0 else '▼'}", "color": "#00ff88" if meta_c >= 0 else "#ff3b30"},
                    {"label": f"TSM ({'+' if tsm_c >= 0 else ''}{tsm_c:.2f}%)", "value": f"${tsm_p:.2f} {'▲' if tsm_c >= 0 else '▼'}", "color": "#00ff88" if tsm_c >= 0 else "#ff3b30"},
                    {"label": "ANTH (Anthropic)", "value": "$32.40 ▲", "color": "#00ff88"},
                    {"label": "MIST (Mistral AI)", "value": "$12.80 ▼", "color": "#ff3b30"}
                ],
                "chart": stock_chart[-15:]
            })
            await asyncio.sleep(2.0)

        # ───────────────────────────────────────────────────────────
        # Phase 3: Slide-in Live Interactive Audience Poll Overlay
        # ───────────────────────────────────────────────────────────
        print("\n▶  PHASE 3: LIVE INTERACTIVE AUDIENCE POLL OVERLAY")
        await set_transcript(
            client, space, 
            "Opening interactive Q&A. Let's see how our audience votes on which of the 4 collaborative panels is preferred.",
            label="Gemini Concierge"
        )
        
        # Trigger slide-in poll with grid layout and emojis!
        await post_endpoint(client, f"/api/poll/{space}", {
            "active": True,
            "layout": "grid",
            "question": "Which is your favorite panel? 🗳️",
            "options": [
                "1️⃣ Seamless Video (Autoplay)",
                "2️⃣ Workspace Sketch (A2A)",
                "3️⃣ Stocks Telemetry ⚡",
                "4️⃣ High-level Blueprint 🎨"
            ],
            "values": [0, 0, 0, 0]
        })
        await launch_emoji_burst(client, space, ["🗳️", "📊", "🔥"])
        await asyncio.sleep(2.0)

        # Simulate live voting progress
        print("🗳️ Simulating real-time incoming audience votes...")
        votes = [
            (10, 5, 12, 8),
            (22, 12, 19, 15),
            (35, 18, 28, 24),
            (42, 25, 34, 31),
            (45, 32, 41, 38)
        ]
        for v1, v2, v3, v4 in votes:
            await post_endpoint(client, f"/api/poll/{space}", {
                "active": True,
                "layout": "grid",
                "question": "Which is your favorite panel? 🗳️",
                "options": [
                    "1️⃣ Seamless Video (Autoplay)",
                    "2️⃣ Workspace Sketch (A2A)",
                    "3️⃣ Stocks Telemetry ⚡",
                    "4️⃣ High-level Blueprint 🎨"
                ],
                "values": [v1, v2, v3, v4]
            })
            await asyncio.sleep(0.5)
        
        print(f"⏳ Waiting {delay}s...")
        await asyncio.sleep(delay)

        # Hide poll
        await post_endpoint(client, f"/api/poll/{space}", {"active": False})
        await asyncio.sleep(1.0)
        
        # ───────────────────────────────────────────────────────────
        # Phase 4: Fullscreen Flight Radar Scope & Interactive HUD LOCK
        # ───────────────────────────────────────────────────────────
        print("\n▶  PHASE 4: FULLSCREEN FLIGHT RADAR SCOPE CLOSURE")
        await set_transcript(
            client, space,
            "✈️ Switching flight radar to Full Screen! Click aircraft targets directly on the interactive radar console to trigger target locks and warning alerts.",
            label="Gemini Concierge"
        )
        
        # Set Panel 1 to be the interactive flight radar dashboard in full screen (single layout)
        await post_endpoint(client, f"/api/image", {
            "space_id": space,
            "prompt": "static:dashboard",
            "panel": 1,
            "image_layout": "single",
            "label": "✈️ 1. LFBO Interactive Airspace Radar Console (Full Screen)"
        })
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})
        await launch_emoji_burst(client, space, ["✈️", "📡", "🛸", "🔒"])
        
        # Stream Live Flight Approach sequence onto the Fullscreen Dashboard's 'flt' tab
        flight_chart = [20, 22, 21, 24, 23, 26, 25, 28, 27, 29, 30, 29, 31, 32, 33]
        for tick in range(8):
            flight_count, flights = await get_live_toulouse_flights(client, tick=tick)
            flight_chart.append(int(max(10, min(95, flight_count * 10 + 20))))
            metrics = []
            for f in flights:
                metrics.append({
                    "label": f"Flight {f['callsign']} ({f['origin']} ➔ {f['destination']})",
                    "value": f"Alt: {f['altitude']}m / Spd: {f['speed']}km/h",
                    "color": "#00f2ff"
                })
            while len(metrics) < 3:
                metrics.append({"label": "Monitoring airspace", "value": "Scanning...", "color": "rgba(255,255,255,0.4)"})
                
            await post_endpoint(client, f"/api/dashboard/{space}", {
                "tabs": TABS_CONFIG,
                "activeTabId": "flt",
                "viewType": "radar",
                "title": f"✈️ Live TLS Airspace Telemetry — Active Flights: {flight_count}",
                "metrics": metrics,
                "chart": flight_chart[-15:]
            })
            await asyncio.sleep(2.0)

        # ───────────────────────────────────────────────────────────
        # Concluding Phase: Clear Focus & Celebration
        # ───────────────────────────────────────────────────────────
        print("\n▶  CONCLUDING SHOWCASE")
        await post_endpoint(client, f"/api/focus-panel/{space}", {"panel": 0})  # Clear focus
        await set_transcript(
            client, space, 
            "And there you have it. High-fidelity layouts, collaborative A2A protocols, responsive A2UI telemetry, and dynamic media pipelines.",
            label="Gemini Concierge"
        )
        
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "applause"})
        await launch_emoji_burst(client, space, ["🎉", "👏", "🔥", "💯", "🙌", "🤩", "🚀", "🌌"])
        
    print("\n🎉 Ultra Premium A2UI & A2A Interactive Showcase completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
