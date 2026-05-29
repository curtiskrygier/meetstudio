#!/usr/bin/env python3
"""
A2UI On-The-Fly Primitive Cross-Formation Stock Showcase
=========================================================
Lays out the top 50 performing stocks in a majestic, high-fidelity neon cross (+) formation.
Demonstrates the power of composing nested containers, badges, texts, and trend-values
completely on-the-fly without client-side rebuilds.

The layout consists of:
- A prominent, glowing center stock (NVIDIA / NVDA) serving as the intersection core.
- A vertical axis of stacked, compact horizontal stock tickers stretching up and down.
- A horizontal axis of side-by-side, tall vertical stock card modules stretching left and right.
- Fluctuating live stock ticks updating every 1.5 seconds.
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

# --- Config & Setup ---
API_URL = os.environ.get("CONCIERGE_API_URL", "http://127.0.0.1:8085")
KEY = os.environ.get("STAGE_API_KEY", "meet-live_STAGE_SECURE_v1_zG9fN8qL7vP2mX6tY9wK4jC5bS8xQ7hZ3uW0rA")
SPACE = os.environ.get("CAPTURE_SPACE", "default")

# --- ANSI Terminal Styling ---
CLR_CYAN = "\033[38;5;51m"
CLR_MAGENTA = "\033[38;5;201m"
CLR_GREEN = "\033[38;5;82m"
CLR_YELLOW = "\033[38;5;220m"
CLR_SLATE = "\033[38;5;244m"
CLR_RESET = "\033[0m"

# Define top 50 high-performing stocks
STOCK_TICKERS = [
    # Center (1 stock)
    ("NVDA", "Nvidia Corp.", 1148.20, 8.45),
    # Top Branch (12 stocks)
    ("AAPL", "Apple Inc.", 191.20, 2.45),
    ("MSFT", "Microsoft Corp.", 423.50, 3.12),
    ("GOOGL", "Alphabet Inc.", 179.30, 4.05),
    ("AMZN", "Amazon.com Inc.", 187.15, 2.88),
    ("META", "Meta Platforms", 478.40, 5.21),
    ("TSLA", "Tesla Inc.", 182.90, 6.10),
    ("AVGO", "Broadcom Inc.", 1412.00, 4.89),
    ("ASML", "ASML Holding", 985.40, 3.75),
    ("AMD", "Adv. Micro Devices", 168.10, 5.34),
    ("NFLX", "Netflix Inc.", 642.80, 4.12),
    ("ADBE", "Adobe Inc.", 485.30, 2.95),
    ("CRM", "Salesforce Inc.", 272.10, 3.01),
    # Bottom Branch (12 stocks)
    ("QCOM", "Qualcomm Inc.", 205.40, 4.60),
    ("ORCL", "Oracle Corp.", 124.90, 3.25),
    ("NOW", "ServiceNow Inc.", 748.20, 3.90),
    ("INTU", "Intuit Inc.", 612.30, 2.80),
    ("PANW", "Palo Alto Networks", 312.40, 4.45),
    ("CRWD", "CrowdStrike", 328.90, 7.15),
    ("SNOW", "Snowflake Inc.", 142.50, 5.12),
    ("PLTR", "Palantir Tech", 24.85, 9.40),
    ("COIN", "Coinbase Global", 228.40, 11.20),
    ("MSTR", "MicroStrategy", 1650.00, 14.85),
    ("LLY", "Eli Lilly & Co.", 812.50, 3.65),
    ("NVO", "Novo Nordisk", 132.40, 4.10),
    # Left Branch (12 stocks)
    ("JPM", "JPMorgan Chase", 198.40, 2.10),
    ("V", "Visa Inc.", 276.50, 1.85),
    ("MA", "Mastercard Inc.", 452.90, 1.95),
    ("BAC", "Bank of America", 39.40, 2.30),
    ("GS", "Goldman Sachs", 462.10, 3.40),
    ("MS", "Morgan Stanley", 98.60, 2.85),
    ("WMT", "Walmart Inc.", 65.40, 1.70),
    ("COST", "Costco Wholesale", 808.20, 3.15),
    ("TGT", "Target Corp.", 146.30, 2.40),
    ("HD", "Home Depot Inc.", 342.10, 1.50),
    ("LOW", "Lowe's Companies", 222.80, 1.90),
    ("XOM", "Exxon Mobil Corp.", 114.30, 2.05),
    # Right Branch (13 stocks)
    ("CVX", "Chevron Corp.", 156.40, 2.20),
    ("COP", "ConocoPhillips", 118.20, 2.60),
    ("KO", "Coca-Cola Co.", 62.80, 1.45),
    ("PEP", "PepsiCo Inc.", 178.40, 1.55),
    ("PG", "Procter & Gamble", 164.90, 1.60),
    ("JNJ", "Johnson & Johnson", 152.10, 1.25),
    ("MRK", "Merck & Co. Inc.", 128.50, 2.45),
    ("PFE", "Pfizer Inc.", 28.90, 1.80),
    ("ABBV", "AbbVie Inc.", 161.40, 2.15),
    ("UNH", "UnitedHealth Group", 518.30, 1.90),
    ("GE", "General Electric", 162.70, 3.80),
    ("CAT", "Caterpillar Inc.", 348.90, 2.70),
    ("DE", "Deere & Co.", 382.40, 2.10),
]


def C(cid: str, el: str, props: dict) -> dict:
    """Build a v0.9 component dict. Strips structural keys from props to
    prevent accidental clobbering of `id` / `component` if a YAML author
    or LLM emits those as component-level attributes."""
    clean_props = {k: v for k, v in props.items() if k not in ('id', 'component')}
    return {"id": cid, "component": el, **clean_props}


def get_fluctuated_stocks(tick: int) -> list[dict]:
    """Generates stock prices and percentages with organic drift per tick."""
    random.seed(42 + tick * 7)
    fluctuated = []
    for symbol, name, base_price, base_change in STOCK_TICKERS:
        drift = random.uniform(-0.4, 0.45)
        price_change_pct = (base_change + drift * tick * 0.08)
        price = base_price * (1 + price_change_pct / 100.0)
        fluctuated.append({
            "symbol": symbol,
            "name": name,
            "price": round(price, 2 if price >= 10 else 4),
            "change": round(price_change_pct, 2),
            "is_up": price_change_pct >= 0
        })
    return fluctuated


def generate_cross_layout(tick: int) -> list[dict]:
    stocks = get_fluctuated_stocks(tick)

    # Distribute the 50 stocks into the cross layout segments
    center_s = stocks[0]       # 1 Center stock
    top_s = stocks[1:13]       # 12 stocks
    bottom_s = stocks[13:25]   # 12 stocks
    left_s = stocks[25:37]     # 12 stocks
    right_s = stocks[37:50]    # 13 stocks

    comps = []

    # 1. Root stage layout - Single hero slot
    comps.append(C("root", "gdm-stage-grid", {
        "layout": "hero",
        "children": {"explicitList": ["main_viewport"]}
    }))

    # 2. Main Full-Screen Backdrop and Layout Wrapper
    comps.append(C("main_viewport", "gdm-container", {
        "direction": "column",
        "align": "center",
        "justify": "center",
        "width": "100%",
        "height": "100%",
        "padding": "16px",
        "background": "radial-gradient(circle at center, #070913 0%, #020307 100%)",
        "children": {
            "explicitList": [
                "top_hud_header",
                "cross_master_container",
                "bottom_hud_footer"
            ]
        }
    }))

    # 3. HUD Header (Title & Stat Summary)
    comps.append(C("top_hud_header", "gdm-container", {
        "direction": "row",
        "align": "center",
        "justify": "space-between",
        "width": "100%",
        "padding": "0 10px 10px 10px",
        "border": "none",
        "children": {
            "explicitList": ["header_label_group", "header_clock_wrapper"]
        }
    }))

    comps.append(C("header_label_group", "gdm-container", {
        "direction": "column",
        "gap": "2px",
        "children": {"explicitList": ["hud_badge", "hud_title"]}
    }))

    comps.append(C("hud_badge", "gdm-badge", {
        "text": "A2UI ON-THE-FLY ENGINE PROTOTYPE",
        "type": "success",
        "pulse": True
    }))

    comps.append(C("hud_title", "gdm-text", {
        "content": "▲ TOP 50 STOCK PERFORMANCE CROSS-FORMATION",
        "size": "h2",
        "color": "accent",
        "uppercase": True,
        "font": "sans"
    }))

    comps.append(C("header_clock_wrapper", "gdm-clock", {
        "showClock": True,
        "showDate": True,
        "variant": "flip",
        "accentColor": "accent"
    }))

    # 4. Master Cross Assembly Grid/Flex Container
    # Contains: Vertical Top, Middle Row (Left + Center + Right), Vertical Bottom
    comps.append(C("cross_master_container", "gdm-container", {
        "direction": "column",
        "align": "center",
        "justify": "center",
        "grow": 1,
        "width": "100%",
        "children": {
            "explicitList": [
                "vertical_axis_top",
                "horizontal_axis_middle_row",
                "vertical_axis_bottom"
            ]
        }
    }))

    # --- TOP AXIS (Vertical Stack) ---
    top_kids = [f"top_stock_{s['symbol']}" for s in top_s]
    comps.append(C("vertical_axis_top", "gdm-container", {
        "direction": "column",
        "align": "center",
        "justify": "flex-end",
        "gap": "5px",
        "width": "260px",
        "children": {"explicitList": top_kids}
    }))

    for s in top_s:
        comps.append(C(f"top_stock_{s['symbol']}", "gdm-trend-value", {
            "symbol": s["symbol"],
            "label": s["name"],
            "price": s["price"],
            "change": s["change"],
            "isUp": s["is_up"]
        }))

    # --- MIDDLE ROW (Left Horizontal Axis + Center Spec Core + Right Horizontal Axis) ---
    comps.append(C("horizontal_axis_middle_row", "gdm-container", {
        "direction": "row",
        "align": "center",
        "justify": "center",
        "gap": "14px",
        "width": "100%",
        "margin": "10px 0",
        "children": {
            "explicitList": [
                "horizontal_axis_left",
                "center_glowing_core_wrapper",
                "horizontal_axis_right"
            ]
        }
    }))

    # LEFT AXIS (Horizontal Side-by-Side Cards)
    left_kids = [f"left_stock_{s['symbol']}" for s in left_s]
    comps.append(C("horizontal_axis_left", "gdm-container", {
        "direction": "row",
        "align": "center",
        "justify": "flex-end",
        "gap": "6px",
        "children": {"explicitList": left_kids}
    }))

    for s in left_s:
        # Build custom vertical stock cards using nested containers
        comps.append(C(f"left_stock_{s['symbol']}", "gdm-container", {
            "direction": "column",
            "align": "center",
            "justify": "center",
            "padding": "6px 8px",
            "gap": "2px",
            "width": "85px",
            "height": "75px",
            "borderRadius": "8px",
            "background": "linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%)",
            "border": "1px solid rgba(255, 255, 255, 0.08)",
            "children": {
                "explicitList": [
                    f"lbl_left_{s['symbol']}",
                    f"prc_left_{s['symbol']}",
                    f"bdg_left_{s['symbol']}"
                ]
            }
        }))
        comps.append(C(f"lbl_left_{s['symbol']}", "gdm-text", {
            "content": s["symbol"],
            "size": "caption",
            "weight": "bold",
            "color": "white",
            "font": "mono"
        }))
        comps.append(C(f"prc_left_{s['symbol']}", "gdm-text", {
            "content": f"${s['price']}",
            "size": "caption",
            "color": "accent",
            "font": "mono"
        }))
        comps.append(C(f"bdg_left_{s['symbol']}", "gdm-badge", {
            "text": f"+{s['change']}%" if s["is_up"] else f"{s['change']}%",
            "type": "success" if s["is_up"] else "danger"
        }))

    # CENTER GLOWING CORE (Highly styled intersection element)
    comps.append(C("center_glowing_core_wrapper", "gdm-container", {
        "direction": "column",
        "align": "center",
        "justify": "center",
        "padding": "12px 18px",
        "width": "180px",
        "height": "110px",
        "borderRadius": "14px",
        "border": "2px solid #00f2ff",
        "background": "linear-gradient(45deg, rgba(0, 242, 255, 0.15) 0%, rgba(179, 136, 255, 0.15) 100%)",
        "glass": True,
        "children": {
            "explicitList": [
                "core_title_badge",
                "core_symbol_text",
                "core_price_stat"
            ]
        }
    }))

    comps.append(C("core_title_badge", "gdm-badge", {
        "text": "🔥 CROSS INTERSECTION CORE",
        "type": "warning",
        "pulse": True
    }))

    comps.append(C("core_symbol_text", "gdm-text", {
        "content": f"{center_s['symbol']} · {center_s['name']}",
        "size": "caption",
        "weight": "bold",
        "color": "white"
    }))

    comps.append(C("core_price_stat", "gdm-stat", {
        "value": str(center_s["price"]),
        "delta": f"+{center_s['change']}%" if center_s["is_up"] else f"{center_s['change']}%",
        "isUp": center_s["is_up"],
        "size": "sm",
        "align": "center"
    }))

    # RIGHT AXIS (Horizontal Side-by-Side Cards)
    right_kids = [f"right_stock_{s['symbol']}" for s in right_s]
    comps.append(C("horizontal_axis_right", "gdm-container", {
        "direction": "row",
        "align": "center",
        "justify": "flex-start",
        "gap": "6px",
        "children": {"explicitList": right_kids}
    }))

    for s in right_s:
        # Build custom vertical stock cards
        comps.append(C(f"right_stock_{s['symbol']}", "gdm-container", {
            "direction": "column",
            "align": "center",
            "justify": "center",
            "padding": "6px 8px",
            "gap": "2px",
            "width": "85px",
            "height": "75px",
            "borderRadius": "8px",
            "background": "linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%)",
            "border": "1px solid rgba(255, 255, 255, 0.08)",
            "children": {
                "explicitList": [
                    f"lbl_right_{s['symbol']}",
                    f"prc_right_{s['symbol']}",
                    f"bdg_right_{s['symbol']}"
                ]
            }
        }))
        comps.append(C(f"lbl_right_{s['symbol']}", "gdm-text", {
            "content": s["symbol"],
            "size": "caption",
            "weight": "bold",
            "color": "white",
            "font": "mono"
        }))
        comps.append(C(f"prc_right_{s['symbol']}", "gdm-text", {
            "content": f"${s['price']}",
            "size": "caption",
            "color": "accent",
            "font": "mono"
        }))
        comps.append(C(f"bdg_right_{s['symbol']}", "gdm-badge", {
            "text": f"+{s['change']}%" if s["is_up"] else f"{s['change']}%",
            "type": "success" if s["is_up"] else "danger"
        }))

    # --- BOTTOM AXIS (Vertical Stack) ---
    bottom_kids = [f"bottom_stock_{s['symbol']}" for s in bottom_s]
    comps.append(C("vertical_axis_bottom", "gdm-container", {
        "direction": "column",
        "align": "center",
        "justify": "flex-start",
        "gap": "5px",
        "width": "260px",
        "children": {"explicitList": bottom_kids}
    }))

    for s in bottom_s:
        comps.append(C(f"bottom_stock_{s['symbol']}", "gdm-trend-value", {
            "symbol": s["symbol"],
            "label": s["name"],
            "price": s["price"],
            "change": s["change"],
            "isUp": s["is_up"]
        }))

    # 5. HUD Footer (Chyron + Actions info)
    comps.append(C("bottom_hud_footer", "gdm-container", {
        "direction": "row",
        "align": "center",
        "justify": "space-between",
        "width": "100%",
        "padding": "10px 0 0 0",
        "children": {
            "explicitList": ["footer_text", "footer_stats_badge"]
        }
    }))

    comps.append(C("footer_text", "gdm-text", {
        "content": "📡 Live A2UI Feed: active, streaming 50 symbols. Rendered dynamically via single root composition.",
        "size": "caption",
        "color": "mute",
        "font": "sans"
    }))

    comps.append(C("footer_stats_badge", "gdm-badge", {
        "text": f"TICK UPDATES ACTIVE · {len(stocks)} INSTRUMENTS",
        "type": "primary"
    }))

    return comps


async def main():
    ticks = int(os.environ.get("LOOP_TICKS", "1000"))
    print(f"\n{CLR_CYAN}==================================================================={CLR_RESET}")
    print(f"{CLR_CYAN}🛸   A 2 U I   F L Y - O N - T H E - G O   C R O S S   D E M O   🛸{CLR_RESET}")
    print(f"{CLR_CYAN}==================================================================={CLR_RESET}")
    print(f"  {CLR_SLATE}FastAPI Host:{CLR_RESET} {CLR_CYAN}{API_URL}{CLR_RESET}")
    print(f"  {CLR_SLATE}Stage Space: {CLR_RESET} {CLR_CYAN}{SPACE}{CLR_RESET}")
    print(f"  {CLR_SLATE}Tick updates:{CLR_RESET} {CLR_CYAN}{ticks} steps{CLR_RESET}\n")

    async with httpx.AsyncClient(timeout=15) as client:
        print(f"📡 Sending cross formation payload to {API_URL}/api/render-stage/{SPACE} ...")
        
        try:
            for t in range(ticks):
                print(f"  ⚡ Ticking Stock Cross Feed [Tick {t + 1}/{ticks}]...")
                payload = generate_cross_layout(t)
                
                resp = await client.post(
                    f"{API_URL}/api/render-stage/{SPACE}",
                    headers={
                        "Authorization": f"Bearer {KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "surfaceUpdate": {"components": payload},
                        "root": "root"
                    }
                )
                resp.raise_for_status()
                await asyncio.sleep(1.5)
                
        except KeyboardInterrupt:
            print(f"\n{CLR_YELLOW}⏹️ Execution halted by user. Leaving stage active...{CLR_RESET}")
        except Exception as e:
            print(f"\n{CLR_MAGENTA}❌ Execution encountered an error: {e}{CLR_RESET}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
