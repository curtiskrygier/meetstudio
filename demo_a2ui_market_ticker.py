#!/usr/bin/env python3
"""
Meet Live Concierge — Global Market Scan Board Showcase
=======================================================
Drives the redesigned `gdm-market-ticker` element: a realtime market-SCANNING
board with a flip-clock time/date, a broad spread of instruments across six
market sections, and an auto-highlighted "Ones to Watch" movers strip.

The point of this demo is to showcase the *live capability* — breadth + realtime
updates — not a personal portfolio.

Environment Variables:
    FAST_MODE: Set to "0" or "false" to slow down transitions. Default: True.
    CONCIERGE_API_URL: Target FastAPI backend URL.
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
    payload = {"surfaceUpdate": {"components": components}}
    if root_id:
        payload["root"] = root_id
    await post_endpoint(client, f"/api/render-stage/{space_id}", payload)


async def clear_stage_api(client: httpx.AsyncClient, space_id: str):
    await post_endpoint(client, f"/api/render-stage-clear/{space_id}", {})


async def set_transcript(client: httpx.AsyncClient, space_id: str, text: str, label: str = "Market Desk"):
    await post_endpoint(client, f"/api/transcript/{space_id}", {
        "role": "agent", "label": label, "text": text, "is_final": True,
    })


# --- Market universe: a broad spread, NOT a personal portfolio --------------
# (section_label, accent, [(symbol, name, base_price, base_change_pct), ...])
MARKET_UNIVERSE = [
    ("INDICES", "#00f2ff", [
        ("SPX", "S&P 500", 5310.45, 0.42), ("NDX", "Nasdaq 100", 18650.10, 0.88),
        ("DJI", "Dow Jones", 39850.35, -0.15), ("DAX", "Germany 40", 18450.20, 0.31),
        ("FTSE", "UK 100", 8250.60, 0.12), ("N225", "Nikkei 225", 38600.00, -0.44),
        ("CAC", "France 40", 8100.45, 0.08), ("HSI", "Hang Seng", 18900.10, 1.22),
    ]),
    ("FX", "#b388ff", [
        ("EURUSD", "Euro", 1.0854, 0.12), ("USDJPY", "Yen", 156.82, -0.21),
        ("GBPUSD", "Sterling", 1.2720, 0.05), ("USDCHF", "Franc", 0.9130, -0.09),
        ("AUDUSD", "Aussie", 0.6640, 0.18), ("USDCAD", "Loonie", 1.3660, -0.03),
    ]),
    ("COMMODITIES", "#ffd60a", [
        ("XAU", "Gold", 2342.60, -0.45), ("XAG", "Silver", 30.55, 1.05),
        ("WTI", "Crude Oil", 78.20, 1.12), ("BRENT", "Brent", 82.40, 0.96),
        ("NATGAS", "Nat Gas", 2.6500, 2.31), ("HG", "Copper", 4.6500, 0.74),
        ("ZW", "Wheat", 6.4500, -1.18),
    ]),
    ("CRYPTO", "#ff9f0a", [
        ("BTC", "Bitcoin", 68450.00, 2.65), ("ETH", "Ethereum", 3820.10, 1.10),
        ("SOL", "Solana", 168.40, 4.82), ("XRP", "Ripple", 0.5200, -0.32),
        ("ADA", "Cardano", 0.4500, 0.65), ("DOGE", "Dogecoin", 0.1600, 3.15),
        ("AVAX", "Avalanche", 36.20, -1.85),
    ]),
    ("MEGACAP", "#00ff88", [
        ("AAPL", "Apple", 189.95, 0.65), ("MSFT", "Microsoft", 421.35, 0.22),
        ("NVDA", "Nvidia", 1090.20, 3.82), ("GOOGL", "Alphabet", 178.10, 0.41),
        ("AMZN", "Amazon", 185.40, -0.28), ("META", "Meta", 478.30, 1.34),
        ("TSLA", "Tesla", 176.40, -1.85),
    ]),
    ("RATES & VOL", "#5ac8fa", [
        ("US10Y", "10Y Yield", 4.4600, 0.51), ("VIX", "Volatility", 12.80, -2.40),
        ("SPY", "S&P ETF", 530.10, 0.40), ("QQQ", "Nasdaq ETF", 455.20, 0.85),
        ("DXY", "Dollar Idx", 104.50, -0.12),
    ]),
]


def generate_market_sections(tick: int) -> list[dict]:
    """Fluctuate the whole universe per tick into the gdm-market-ticker `sections` shape."""
    random.seed(2024 + tick * 7)
    sections = []
    for label, accent, instruments in MARKET_UNIVERSE:
        items = []
        for symbol, name, base_price, base_change in instruments:
            drift = random.uniform(-0.6, 0.7)
            price = base_price * (1 + (base_change + drift * tick * 0.15) / 100)
            change = round(base_change + drift, 2)
            items.append({
                "symbol": symbol,
                "label": name,
                "price": round(price, 4 if base_price < 10 else 2),
                "changePercent": change,
                "isUp": change >= 0,
            })
        sections.append({"label": label, "accent": accent, "items": items})
    return sections


async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        space = os.environ.get("MEET_SPACE_ID") or await get_active_space(client)
        if not space:
            print(f"\n{CLR_MAGENTA}❌ No active Meet space detected. Open a Meet call first.{CLR_RESET}\n")
            sys.exit(1)

        delay = 2.5 if FAST_MODE else 9.0
        loop_ticks = 6
        total = sum(len(i) for _, _, i in MARKET_UNIVERSE)

        print(f"\n{CLR_CYAN}  ==============================================================={CLR_RESET}")
        print(f"{CLR_CYAN}  📡   G L O B A L   M A R K E T   S C A N   B O A R D   ▲{CLR_RESET}")
        print(f"{CLR_CYAN}  ==============================================================={CLR_RESET}")
        print(f"  {CLR_SLATE}Active Meeting Space:{CLR_RESET} {CLR_CYAN}{space}{CLR_RESET}")
        print(f"  {CLR_SLATE}Component:{CLR_RESET} {CLR_CYAN}gdm-market-ticker (scan board, {total} instruments){CLR_RESET}\n")

        # Phase 0 — connecting
        print(f"{CLR_CYAN}🎬 [Phase 0] Connecting to global market data feeds...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})
        await render_stage_api(client, space, [{
            "id": "scan_standby",
            "component": {"gdm-standby-slate": {
                "title": "📡 Synchronizing Global Market Feeds",
                "description": f"Connecting to {total} instruments across indices, FX, commodities, crypto and megacap equities...",
                "active": True, "seconds": 4,
            }},
        }], root_id="scan_standby")
        await asyncio.sleep(4.0)

        # Phase 1 — live scan
        print(f"\n{CLR_CYAN}🎬 [Phase 1] Live market scan — flip-clock + realtime movers...{CLR_RESET}")
        await set_transcript(
            client, space,
            "We are now scanning the global markets in realtime — indices, currencies, commodities, "
            "crypto and megacap equities. The board auto-surfaces the biggest movers as 'ones to watch'.",
            label="Market Desk",
        )
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "sonar"})

        chyron = {"id": "scan_chyron", "component": {"gdm-chyron": {
            "title": "GLOBAL MARKETS — LIVE",
            "subtitle": "Realtime cross-asset market scan",
            "active": True, "accentColor": "#00f2ff",
        }}}
        slate_off = {"id": "scan_standby", "component": {"gdm-standby-slate": {"active": False}}}

        for tick in range(loop_ticks):
            print(f"  📊 Sweeping market feed (Tick {tick + 1}/{loop_ticks})...")
            sections = generate_market_sections(tick)
            scan_board = {"id": "market_scan", "component": {"gdm-market-ticker": {
                "sections": sections,
                "active": True,
                "badgeText": "GLOBAL MARKET SCAN",
                "accentColor": "#00f2ff",
                "watchCount": 6,
                "showClock": True,
                "showDate": True,
            }}}
            await render_stage_api(client, space, [scan_board, chyron, slate_off], root_id="market_scan")
            await asyncio.sleep(delay)

        # Phase 2 — reset & reactions
        print(f"\n{CLR_CYAN}🎬 [Phase 2] Scan complete. Restoring workspace...{CLR_RESET}")
        await set_transcript(
            client, space,
            "Market scan session complete. Returning the stage to standby.",
            label="Market Desk",
        )
        await clear_stage_api(client, space)
        await asyncio.sleep(0.5)

        for user, msg in [
            ("Priya — Analyst", "The flip-clock and realtime mover detection look incredibly slick. 📈"),
            ("Marcus — Trader", "Love the breadth — scanning 40+ instruments across every asset class at once. ⚡"),
            ("Dana K.", "The 'ones to watch' strip auto-surfacing the biggest movers is genuinely useful. 🔥"),
        ]:
            print(f"  💬 Chat from: {user}")
            await post_endpoint(client, f"/api/chat/{space}", {"sender": user, "text": msg})
            await asyncio.sleep(1.0 if FAST_MODE else 1.8)

        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "applause"})
        for emo in ["🎉", "📈", "🚀", "✨", "🔥", "👏"]:
            await post_endpoint(client, f"/api/emoji/{space}", {"emoji": emo})
            await asyncio.sleep(0.08)

        print(f"\n{CLR_GREEN}🎉 Global Market Scan Board showcase executed successfully!{CLR_RESET}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{CLR_MAGENTA}Showcase interrupted.{CLR_RESET}")
        sys.exit(0)
