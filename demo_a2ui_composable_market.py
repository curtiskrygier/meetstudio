#!/usr/bin/env python3
"""
Meet Live Concierge — Composable Server-Driven UI Showcase
==========================================================
Drives a fully-composited Global Market Scan Board constructed entirely from
nested atomic elements (12 composable primitives) without client-side rebuilds.

This is a premium, high-density multicolor layout with a live tick update loop,
loop-driven countdown welcome card, real page-flipping clock, and dynamic movers scroller.

Environment Variables:
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
API_URL = os.environ.get("CONCIERGE_API_URL", "http://127.0.0.1:8085")
KEY = os.environ.get("STAGE_API_KEY", "meet-live_STAGE_SECURE_v1_zG9fN8qL7vP2mX6tY9wK4jC5bS8xQ7hZ3uW0rA")

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


def make_component(comp_id: str, element_name: str, props: dict) -> dict:
    """Helper to structure A2UI components."""
    return {
        "id": comp_id,
        "component": {
            element_name: props
        }
    }


# --- High density market cross-asset universe ---
MARKET_UNIVERSE = [
    ("INDICES", "#00f2ff", [
        ("SPX", "S&P 500", 5310.45, 0.42), ("NDX", "Nasdaq 100", 18650.10, 0.88),
        ("DJI", "Dow Jones", 39850.35, -0.15), ("DAX", "Germany 40", 18450.20, 0.31),
        ("FTSE", "UK 100", 8250.60, 0.12), ("N225", "Nikkei 225", 38600.00, -0.44),
    ]),
    ("FX", "#b388ff", [
        ("EURUSD", "Euro / USD", 1.0854, 0.12), ("USDJPY", "USD / Yen", 156.82, -0.21),
        ("GBPUSD", "Pound / USD", 1.2720, 0.05), ("USDCHF", "USD / Franc", 0.9130, -0.09),
        ("AUDUSD", "Aussie / USD", 0.6640, 0.18), ("USDCAD", "USD / Loonie", 1.3660, -0.03),
    ]),
    ("COMMODITIES", "#ffd60a", [
        ("XAU", "Gold Spot", 2342.60, -0.45), ("XAG", "Silver Spot", 30.55, 1.05),
        ("WTI", "Crude Oil", 78.20, 1.12), ("BRENT", "Brent Oil", 82.40, 0.96),
        ("NATGAS", "Nat Gas", 2.6500, 2.31), ("HG", "Copper Spot", 4.6500, 0.74),
    ]),
    ("CRYPTO", "#ff9f0a", [
        ("BTC", "Bitcoin", 68450.00, 2.65), ("ETH", "Ethereum", 3820.10, 1.10),
        ("SOL", "Solana", 168.40, 4.82), ("XRP", "Ripple", 0.5200, -0.32),
        ("ADA", "Cardano", 0.4500, 0.65), ("DOGE", "Dogecoin", 0.1600, 3.15),
    ]),
    ("MEGACAP", "#00ff88", [
        ("AAPL", "Apple Inc.", 189.95, 0.65), ("MSFT", "Microsoft", 421.35, 0.22),
        ("NVDA", "Nvidia Corp.", 1090.20, 3.82), ("GOOGL", "Alphabet Inc.", 178.10, 0.41),
        ("AMZN", "Amazon.com", 185.40, -0.28), ("TSLA", "Tesla Inc.", 176.40, -1.85),
    ]),
    ("ENERGY & RATES", "#5ac8fa", [
        ("US10Y", "10Y Treasury", 4.4600, 0.51), ("VIX", "CBOE Volatility", 12.80, -2.40),
        ("SPY", "S&P 500 ETF", 530.10, 0.40), ("QQQ", "Nasdaq ETF", 455.20, 0.85),
        ("DXY", "Dollar Index", 104.50, -0.12), ("US30Y", "30Y Treasury", 4.5800, 0.38),
    ]),
]


def fluctuate_prices(tick: int) -> list[dict]:
    """Fluctuate the whole universe per tick into the structured sections."""
    random.seed(2026 + tick * 11)
    sections = []
    for label, color, instruments in MARKET_UNIVERSE:
        items = []
        for symbol, name, base_price, base_change in instruments:
            drift = random.uniform(-0.8, 0.9)
            price = base_price * (1 + (base_change + drift * tick * 0.12) / 100)
            change = base_change + drift
            precision = 4 if base_price < 10 else 2
            items.append({
                "symbol": symbol,
                "name": name,
                "price": round(price, precision),
                "change": round(change, 2),
                "is_up": change >= 0,
                "precision": precision
            })
        sections.append({
            "label": label,
            "color": color,
            "items": items
        })
    return sections


def generate_welcome_stage(seconds_remaining: int) -> list[dict]:
    """Generates the countdown cold-start screen built entirely out of reusable primitives."""
    progress_val = int((6 - seconds_remaining) * 20.0)
    return [
        # 1. Root Grid
        make_component("stage_root_grid", "gdm-stage-grid", {
            "layout": "hero",
            "children": {
                "explicitList": ["welcome_outer_container"]
            }
        }),
        # 2. Outer Full-Stage Container (centers the card)
        make_component("welcome_outer_container", "gdm-container", {
            "direction": "column",
            "justify": "center",
            "align": "center",
            "width": "100%",
            "height": "100%",
            "background": "rgba(10, 15, 30, 0.35)",
            "children": {
                "explicitList": ["welcome_card"]
            }
        }),
        # 3. Glassmorphic Welcome Card
        make_component("welcome_card", "gdm-container", {
            "direction": "column",
            "justify": "center",
            "align": "center",
            "padding": "40px",
            "gap": "22px",
            "width": "550px",
            "glass": True,
            "borderRadius": "24px",
            "children": {
                "explicitList": [
                    "welcome_header_row",
                    "welcome_divider1",
                    "welcome_title",
                    "welcome_description",
                    "welcome_progress",
                    "welcome_status_row"
                ]
            }
        }),
        # 4. Header Row (Icon + Badge)
        make_component("welcome_header_row", "gdm-container", {
            "direction": "row",
            "justify": "space-between",
            "align": "center",
            "width": "100%",
            "children": {
                "explicitList": ["welcome_icon", "welcome_badge"]
            }
        }),
        make_component("welcome_icon", "gdm-icon", {
            "name": "radar",
            "color": "cyan",
            "size": "36px"
        }),
        make_component("welcome_badge", "gdm-badge", {
            "text": f"LAUNCHING IN {seconds_remaining}S",
            "type": "danger",
            "pulse": True
        }),
        # 5. Divider
        make_component("welcome_divider1", "gdm-divider", {
            "vertical": False,
            "color": "rgba(255, 255, 255, 0.12)"
        }),
        # 6. Title
        make_component("welcome_title", "gdm-text", {
            "content": "COMPOSABLE DECK COLD-START",
            "size": "h2",
            "color": "accent",
            "pulse": True,
            "uppercase": True,
            "font": "sans",
            "align": "center"
        }),
        # 7. Description
        make_component("welcome_description", "gdm-text", {
            "content": "Assembling 36 live asset trackers, flip-clock registers, scrolling tracks, and button websocket hooks entirely via atomic primitives...",
            "size": "body",
            "color": "white",
            "align": "center"
        }),
        # 8. Progress
        make_component("welcome_progress", "gdm-progress", {
            "value": float(progress_val),
            "color": "cyan",
            "height": "10px",
            "animated": True,
            "glow": True
        }),
        # 9. Status Row
        make_component("welcome_status_row", "gdm-container", {
            "direction": "row",
            "justify": "space-between",
            "align": "center",
            "width": "100%",
            "children": {
                "explicitList": ["welcome_status_lbl", "welcome_clock"]
            }
        }),
        make_component("welcome_status_lbl", "gdm-text", {
            "content": f"📡 Handshaking feed servers... (T-minus {seconds_remaining}s)",
            "size": "caption",
            "color": "mute"
        }),
        make_component("welcome_clock", "gdm-clock", {
            "showClock": True,
            "showDate": False,
            "format": "24h",
            "accentColor": "cyan",
            "variant": "flip"
        })
    ]


def generate_composed_market_board(tick: int) -> list[dict]:
    """Generates the massive screen-filling high-fidelity market board out of primitives."""
    sections = fluctuate_prices(tick)
    
    # Gather top movers for scroller dynamically
    all_items = []
    for sec in sections:
        all_items.extend(sec["items"])
    top_movers = sorted(all_items, key=lambda x: abs(x["change"]), reverse=True)[:6]
    
    components = []
    
    # 1. Root Grid
    components.append(make_component("stage_root_grid", "gdm-stage-grid", {
        "layout": "hero",
        "children": {
            "explicitList": ["main_board_container"]
        }
    }))
    
    # 2. Main Board Wrapper (Fully screen-filling)
    components.append(make_component("main_board_container", "gdm-container", {
        "direction": "column",
        "padding": "20px",
        "gap": "14px",
        "width": "100%",
        "height": "100%",
        "glass": True,
        "children": {
            "explicitList": [
                "header_container",
                "top_divider",
                "deck_row_container",
                "bottom_divider",
                "scroller_track",
                "footer_button_container"
            ]
        }
    }))
    
    # 3. Header Container
    components.append(make_component("header_container", "gdm-container", {
        "direction": "row",
        "justify": "space-between",
        "align": "center",
        "width": "100%",
        "children": {
            "explicitList": ["header_text_container", "header_clock"]
        }
    }))
    
    components.append(make_component("header_text_container", "gdm-container", {
        "direction": "column",
        "gap": "4px",
        "children": {
            "explicitList": ["header_badge_row", "header_title", "header_sub"]
        }
    }))
    
    components.append(make_component("header_badge_row", "gdm-container", {
        "direction": "row",
        "align": "center",
        "gap": "8px",
        "children": {
            "explicitList": ["header_badge"]
        }
    }))
    
    components.append(make_component("header_badge", "gdm-badge", {
        "text": "GLOBAL CROSS-ASSET MARKET BOARD · COMPOSABLE SERVER-DRIVEN STREAM",
        "type": "danger",
        "pulse": True
    }))
    
    components.append(make_component("header_title", "gdm-text", {
        "content": "▲ Global Market Composed Scan",
        "size": "h1",
        "color": "accent",
        "uppercase": True,
        "font": "sans"
    }))
    
    components.append(make_component("header_sub", "gdm-text", {
        "content": f"Server-driven high-density visualization using 12 catalog primitives · Sweeping {len(all_items)} instruments",
        "size": "caption",
        "color": "mute"
    }))
    
    components.append(make_component("header_clock", "gdm-clock", {
        "showClock": True,
        "showDate": True,
        "format": "24h",
        "accentColor": "accent",
        "variant": "flip"
    }))
    
    components.append(make_component("top_divider", "gdm-divider", {
        "vertical": False,
        "color": "rgba(0, 242, 255, 0.15)"
    }))
    
    # 4. Deck Row Container (holds 6 columns)
    column_ids = [f"col_{sec['label'].lower().replace(' ', '_').replace('&', 'and')}" for sec in sections]
    components.append(make_component("deck_row_container", "gdm-container", {
        "direction": "row",
        "gap": "12px",
        "width": "100%",
        "align": "stretch",
        "grow": 1,
        "children": {
            "explicitList": column_ids
        }
    }))
    
    # Build each of the 6 columns
    for sec, col_id in zip(sections, column_ids):
        col_children = [f"title_{col_id}", f"div_{col_id}"]
        for item in sec["items"]:
            col_children.append(f"item_{item['symbol'].lower()}")
            
        components.append(make_component(col_id, "gdm-container", {
            "direction": "column",
            "gap": "6px",
            "width": "16%",
            "grow": 1,
            "children": {
                "explicitList": col_children
            }
        }))
        
        components.append(make_component(f"title_{col_id}", "gdm-text", {
            "content": sec["label"],
            "size": "h3",
            "color": sec["color"],
            "uppercase": True
        }))
        
        components.append(make_component(f"div_{col_id}", "gdm-divider", {
            "vertical": False,
            "color": f"{sec['color']}20"
        }))
        
        # Build individual trend value widgets
        for item in sec["items"]:
            components.append(make_component(f"item_{item['symbol'].lower()}", "gdm-trend-value", {
                "symbol": item["symbol"],
                "label": item["name"],
                "price": item["price"],
                "change": item["change"],
                "isUp": item["is_up"],
                "precision": item["precision"]
            }))
            
    components.append(make_component("bottom_divider", "gdm-divider", {
        "vertical": False,
        "color": "rgba(0, 242, 255, 0.15)"
    }))
    
    # 5. Scrolling Ones to Watch Tracker
    scroller_children = ["ones_to_watch_badge"]
    for idx, mover in enumerate(top_movers):
        scroller_children.append(f"scroll_val_{mover['symbol'].lower()}")
        if idx < len(top_movers) - 1:
            scroller_children.append(f"scroll_div_{idx}")
            
    components.append(make_component("scroller_track", "gdm-scroller", {
        "speed": "16s",
        "direction": "left",
        "active": True,
        "children": {
            "explicitList": ["scroller_track_container"]
        }
    }))
    
    components.append(make_component("scroller_track_container", "gdm-container", {
        "direction": "row",
        "gap": "20px",
        "align": "center",
        "children": {
            "explicitList": scroller_children
        }
    }))
    
    components.append(make_component("ones_to_watch_badge", "gdm-badge", {
        "text": "⭐ ONES TO WATCH · TOP MOVERS",
        "type": "warning",
        "pulse": True,
        "outline": True
    }))
    
    for idx, mover in enumerate(top_movers):
        up = mover["is_up"]
        caret = "▲" if up else "▼"
        color = "success" if up else "danger"
        sign = "+" if up else ""
        content = f"{mover['symbol']} {mover['price']} ({caret} {sign}{mover['change']:.2f}%)"
        
        components.append(make_component(f"scroll_val_{mover['symbol'].lower()}", "gdm-text", {
            "content": content,
            "color": color,
            "font": "mono",
            "weight": "bold"
        }))
        
        if idx < len(top_movers) - 1:
            components.append(make_component(f"scroll_div_{idx}", "gdm-divider", {
                "vertical": True,
                "margin": "4px",
                "thickness": "1px",
                "color": "rgba(255, 255, 255, 0.12)"
            }))
            
    # 6. Action Button Controls Footer
    components.append(make_component("footer_button_container", "gdm-container", {
        "direction": "row",
        "gap": "14px",
        "justify": "center",
        "width": "100%",
        "children": {
            "explicitList": ["btn_refresh", "btn_sound", "btn_halt"]
        }
    }))
    
    components.append(make_component("btn_refresh", "gdm-button", {
        "text": "Sync Feeds",
        "action": {
            "event": {
                "name": "sync_feeds",
                "context": {"forced": True}
            }
        },
        "icon": "activity",
        "type": "primary"
    }))
    
    components.append(make_component("btn_sound", "gdm-button", {
        "text": "Ping Radar",
        "action": {
            "event": {
                "name": "radar_ping",
                "context": {"frequency": "high"}
            }
        },
        "icon": "sonar",
        "type": "secondary"
    }))
    
    components.append(make_component("btn_halt", "gdm-button", {
        "text": "Halt Board",
        "action": {
            "event": {
                "name": "emergency_halt",
                "context": {"reason": "manual_trigger"}
            }
        },
        "icon": "alert",
        "type": "danger"
    }))
    
    return components


async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        space = os.environ.get("MEET_SPACE_ID") or await get_active_space(client)
        if not space:
            print(f"\n{CLR_MAGENTA}❌ No active Meet space detected. Open a Meet call first or start local server.{CLR_RESET}\n")
            sys.exit(1)

        print(f"\n{CLR_CYAN}  ==============================================================={CLR_RESET}")
        print(f"{CLR_CYAN}  ⚛️   C O M P O S A B L E   M A R K E T   S C A N   B O A R D   ⚛️{CLR_RESET}")
        print(f"{CLR_CYAN}  ==============================================================={CLR_RESET}")
        print(f"  {CLR_SLATE}Active Meeting Space:{CLR_RESET} {CLR_CYAN}{space}{CLR_RESET}")
        print(f"  {CLR_SLATE}A2UI Atomic Catalogue Showcase (12 Primitives){CLR_RESET}\n")

        # Phase 0 — Composable Countdown Welcome Card (Loop-driven countdown)
        print(f"{CLR_CYAN}🎬 [Phase 0] Launching dynamic countdown cold-start card...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})
        
        for countdown in range(5, 0, -1):
            print(f"  ⏳ T-minus {countdown} seconds...")
            welcome_deck = generate_welcome_stage(countdown)
            await render_stage_api(client, space, welcome_deck, root_id="stage_root_grid")
            await asyncio.sleep(1.0)

        # Phase 1 — Assemble Live Composed Tree with Tick Update Loop
        print(f"\n{CLR_CYAN}🎬 [Phase 1] Launching fully composited visual dashboard tree...{CLR_RESET}")
        await set_transcript(
            client, space,
            "We have constructed a live cross-asset tracking screen entirely from reusable "
            "layout, text, clock, indicator, and scroller primitives, ticking in real time.",
            label="Live Desk",
        )
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "sonar"})

        # Continuous tick update loop to fluctuate prices in real-time
        tick = 0
        loop_ticks = int(os.environ.get("LOOP_TICKS", "1000"))
        print(f"  {CLR_GREEN}✨ Starting real-time tick updates (press Ctrl+C to stop)...{CLR_RESET}")
        
        try:
            for tick in range(loop_ticks):
                print(f"  📊 Sweeping market feed (Tick {tick + 1}/{loop_ticks})...")
                payload = generate_composed_market_board(tick)
                await render_stage_api(client, space, payload, root_id="stage_root_grid")
                await asyncio.sleep(2.5) # updates every 2.5 seconds for dynamic response!
                
        except KeyboardInterrupt:
            pass

        print(f"\n{CLR_CYAN}🧹 Cleaning up stage content...{CLR_RESET}")
        await clear_stage_api(client, space)
        print(f"{CLR_GREEN}🎉 Clean exit successful.{CLR_RESET}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
