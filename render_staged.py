#!/usr/bin/env python3
"""Staged entrance demo: a dashboard that "sets the stage" — the frame scales in,
the header frames up, then stat tiles cascade in via gdm-container reveal +
staggered revealDelay. Loops clear->render so the entrance choreography replays."""
import asyncio, os, sys, glob, random
_base = os.path.dirname(os.path.abspath(__file__))
for _vd in glob.glob(os.path.join(_base, "venv", "lib", "python3.*", "site-packages")):
    if _vd not in sys.path: sys.path.insert(0, _vd)
import httpx

API = os.environ.get("CONCIERGE_API_URL", "http://127.0.0.1:8085")
KEY = os.environ.get("STAGE_API_KEY", "meet-live_STAGE_SECURE_v1_zG9fN8qL7vP2mX6tY9wK4jC5bS8xQ7hZ3uW0rA")
SPACE = os.environ.get("CAPTURE_SPACE", "default")

def C(cid, el, props): return {"id": cid, "component": {el: props}}

TILES = [
    ("ACTIVE USERS", "12,480", "+4.2%", True, "#00f2ff"),
    ("REVENUE", "$1.24M", "+1.8%", True, "#00ff88"),
    ("LATENCY", "142ms", "-6.0%", True, "#ffd60a"),
    ("ERROR RATE", "0.04%", "-12%", True, "#b388ff"),
    ("THROUGHPUT", "8.2k/s", "+3.1%", True, "#00f2ff"),
    ("QUEUE", "37", "+9", False, "#ff9f0a"),
    ("UPTIME", "99.98%", "+0.01%", True, "#00ff88"),
    ("COST/HR", "$48.10", "-2.4%", True, "#5ac8fa"),
]

def staged_board(tick: int):
    random.seed(tick)
    comps = [
        C("root", "gdm-stage-grid", {"layout": "hero", "children": {"explicitList": ["main"]}}),
        # outer frame scales in first
        C("main", "gdm-container", {"direction": "column", "padding": "26px", "gap": "16px",
                                    "width": "100%", "height": "100%", "glass": True,
                                    "reveal": "scale-in", "revealDelay": 0,
                                    "children": {"explicitList": ["hdr", "div0", "grid"]}}),
        # header frames up next
        C("hdr", "gdm-container", {"direction": "row", "align": "center", "width": "100%",
                                   "reveal": "fade-up", "revealDelay": 0.18,
                                   "children": {"explicitList": ["titlecol", "sp", "clock"]}}),
        C("titlecol", "gdm-container", {"direction": "column", "gap": "4px",
                                        "children": {"explicitList": ["badge", "title", "sub"]}}),
        C("badge", "gdm-badge", {"text": "LIVE · STAGED ENTRANCE", "type": "danger", "pulse": True}),
        C("title", "gdm-text", {"content": "▲ OPERATIONS DECK", "size": "h1", "color": "accent", "uppercase": True}),
        C("sub", "gdm-text", {"content": "panels frame in with gdm-container reveal + staggered revealDelay", "size": "caption", "color": "mute"}),
        C("sp", "gdm-spacer", {}),
        C("clock", "gdm-clock", {"showClock": True, "showDate": True, "variant": "flip", "accentColor": "accent"}),
        C("div0", "gdm-divider", {"color": "rgba(0,242,255,0.18)", "reveal": "fade-up"}),
        C("grid", "gdm-grid", {"columns": "4", "gap": "16px", "width": "100%",
                               "children": {"explicitList": [f"tile{i}" for i in range(len(TILES))]}}),
    ]
    for i, (label, value, delta, up, accent) in enumerate(TILES):
        # each tile cascades in, staggered left-to-right / top-to-bottom
        delay = round(0.4 + i * 0.09, 2)
        comps.append(C(f"tile{i}", "gdm-container", {
            "direction": "column", "padding": "18px", "glass": True, "borderRadius": "14px",
            "reveal": "fade-up", "revealDelay": delay,
            "children": {"explicitList": [f"stat{i}"]}}))
        comps.append(C(f"stat{i}", "gdm-stat", {"label": label, "value": value, "delta": delta,
                                                "isUp": up, "accent": accent, "size": "md",
                                                "countUp": True, "countDelay": delay, "countDuration": 0.9}))
    return comps

async def main():
    cycles = int(os.environ.get("CYCLES", "8"))
    async with httpx.AsyncClient(timeout=15) as c:
        H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
        for t in range(cycles):
            # clear first so the next render mounts fresh elements -> entrance replays
            await c.post(f"{API}/api/render-stage-clear/{SPACE}", headers=H, json={})
            await asyncio.sleep(0.25)
            await c.post(f"{API}/api/render-stage/{SPACE}", headers=H,
                         json={"surfaceUpdate": {"components": staged_board(t)}, "root": "root"})
            await asyncio.sleep(4.5)
    print("staged demo done")

if __name__ == "__main__":
    asyncio.run(main())
