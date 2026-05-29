#!/usr/bin/env python3
"""Dense, full-screen 'Global Market Board' composed from atoms + polished
molecules: a real gdm-grid of 6 columns, each a list of gdm-trend-value rows,
a self-ticking gdm-clock, and a gdm-scroller 'ones to watch' strip. Renders a
live loop to spaces/local-preview so it fills the stage and updates."""
import asyncio, os, sys, glob
_base = os.path.dirname(os.path.abspath(__file__))
for _vd in glob.glob(os.path.join(_base, "venv", "lib", "python3.*", "site-packages")):
    if _vd not in sys.path: sys.path.insert(0, _vd)
import httpx
from demo_a2ui_composable_market import MARKET_UNIVERSE, fluctuate_prices

API_URL = os.environ.get("CONCIERGE_API_URL", "http://127.0.0.1:8085")
KEY = os.environ.get("STAGE_API_KEY", "meet-live_STAGE_SECURE_v1_zG9fN8qL7vP2mX6tY9wK4jC5bS8xQ7hZ3uW0rA")
SPACE = os.environ.get("CAPTURE_SPACE", "spaces/local-preview")

def C(cid: str, el: str, props: dict) -> dict:
    """Build a v0.9 component dict. Strips structural keys from props to
    prevent accidental clobbering of `id` / `component` if a YAML author
    or LLM emits those as component-level attributes."""
    clean_props = {k: v for k, v in props.items() if k not in ('id', 'component')}
    return {"id": cid, "component": el, **clean_props}

def dense_board(tick: int):
    sections = fluctuate_prices(tick)
    total = sum(len(s["items"]) for s in sections)
    col_ids = [f"col{i}" for i in range(len(sections))]
    comps = [
        C("root", "gdm-stage-grid", {"layout": "hero", "children": {"explicitList": ["main"]}}),
        C("main", "gdm-container", {"direction": "column", "padding": "18px", "gap": "12px",
                                    "width": "100%", "height": "100%", "glass": True,
                                    "children": {"explicitList": ["hdr", "hdrdiv", "bodywrap", "botdiv", "scroller"]}}),
        C("hdr", "gdm-container", {"direction": "row", "align": "center", "width": "100%",
                                   "children": {"explicitList": ["titlecol", "sp", "clock"]}}),
        C("titlecol", "gdm-container", {"direction": "column", "gap": "3px",
                                        "children": {"explicitList": ["badge", "title", "sub"]}}),
        C("badge", "gdm-badge", {"text": "LIVE · GLOBAL CROSS-ASSET SCAN", "type": "danger", "pulse": True}),
        C("title", "gdm-text", {"content": "▲ GLOBAL MARKET BOARD", "size": "h1", "color": "accent", "uppercase": True}),
        C("sub", "gdm-text", {"content": f"Composed from atoms · sweeping {total} instruments live", "size": "caption", "color": "mute"}),
        C("sp", "gdm-spacer", {}),
        C("clock", "gdm-clock", {"showClock": True, "showDate": True, "variant": "flip", "accentColor": "accent"}),
        C("hdrdiv", "gdm-divider", {"color": "rgba(0,242,255,0.18)"}),
        # body: a wrapper that grows to fill, holding the real 6-column grid
        C("bodywrap", "gdm-container", {"direction": "column", "grow": 1, "width": "100%",
                                        "children": {"explicitList": ["body"]}}),
        C("body", "gdm-grid", {"columns": str(len(sections)), "gap": "10px",
                               "width": "100%", "height": "100%", "align": "start",
                               "children": {"explicitList": col_ids}}),
    ]
    for sec, col_id in zip(sections, col_ids):
        kids = [f"{col_id}_h", f"{col_id}_d"] + [f"{col_id}_{it['symbol']}" for it in sec["items"]]
        comps.append(C(col_id, "gdm-container", {"direction": "column", "gap": "6px",
                                                 "children": {"explicitList": kids}}))
        comps.append(C(f"{col_id}_h", "gdm-text", {"content": sec["label"], "size": "h3", "color": sec["color"], "uppercase": True}))
        comps.append(C(f"{col_id}_d", "gdm-divider", {"color": f"{sec['color']}30"}))
        for it in sec["items"]:
            comps.append(C(f"{col_id}_{it['symbol']}", "gdm-trend-value", {
                "symbol": it["symbol"], "label": it["name"], "price": it["price"],
                "change": it["change"], "isUp": it["is_up"], "precision": it["precision"]}))
    # ones-to-watch scroller
    movers = sorted([i for s in sections for i in s["items"]], key=lambda x: abs(x["change"]), reverse=True)[:8]
    comps.append(C("botdiv", "gdm-divider", {"color": "rgba(255,214,10,0.18)"}))
    comps.append(C("scroller", "gdm-scroller", {"speed": "24s", "active": True, "children": {"explicitList": ["scrollrow"]}}))
    comps.append(C("scrollrow", "gdm-container", {"direction": "row", "gap": "26px", "align": "center",
                                                  "children": {"explicitList": ["movbadge"] + [f"mov{i}" for i in range(len(movers))]}}))
    comps.append(C("movbadge", "gdm-badge", {"text": "⭐ ONES TO WATCH", "type": "warning", "pulse": True, "outline": True}))
    for i, m in enumerate(movers):
        up = m["is_up"]
        comps.append(C(f"mov{i}", "gdm-text", {
            "content": f"{m['symbol']} {m['price']} ({'▲' if up else '▼'} {'+' if up else ''}{m['change']:.2f}%)",
            "color": "success" if up else "danger", "font": "mono", "weight": "bold"}))
    return comps

async def main():
    ticks = int(os.environ.get("LOOP_TICKS", "60"))
    async with httpx.AsyncClient(timeout=15) as c:
        for t in range(ticks):
            await c.post(f"{API_URL}/api/render-stage/{SPACE}",
                         headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
                         json={"surfaceUpdate": {"components": dense_board(t)}, "root": "root"})
            await asyncio.sleep(1.5)
    print("dense render loop done")

if __name__ == "__main__":
    asyncio.run(main())
