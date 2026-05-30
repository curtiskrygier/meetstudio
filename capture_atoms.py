#!/usr/bin/env python3
"""Showcase + capture: a 'Market Pulse' board composed ENTIRELY from atoms
(gdm-grid, gdm-stat, gdm-text[flip], gdm-spacer, gdm-container, gdm-divider,
gdm-badge). Renders to spaces/local-preview (visible in the user's tab) and
screenshots headlessly across ticks so the flip animation is exercised."""
import asyncio, os, sys, glob, random, datetime
_base = os.path.dirname(os.path.abspath(__file__))
for _vd in glob.glob(os.path.join(_base, "venv", "lib", "python3.*", "site-packages")):
    if _vd not in sys.path: sys.path.insert(0, _vd)
import httpx
from playwright.async_api import async_playwright

API_URL = os.environ.get("CONCIERGE_API_URL", "http://127.0.0.1:8085")
KEY = os.environ.get("STAGE_API_KEY") or exit("STAGE_API_KEY required — export it before running this script")
SPACE = os.environ.get("CAPTURE_SPACE", "spaces/local-preview")
OUT = "/tmp/cap"

INSTRUMENTS = [
    ("S&P 500", 5310.45, 0.42, "#00f2ff"), ("NASDAQ", 18650.10, 0.88, "#00f2ff"),
    ("GOLD", 2342.60, -0.45, "#ffd60a"), ("WTI CRUDE", 78.20, 1.12, "#ffd60a"),
    ("BITCOIN", 68450.00, 2.65, "#ff9f0a"), ("ETHEREUM", 3820.10, 1.10, "#ff9f0a"),
    ("NVIDIA", 1090.20, 3.82, "#00ff88"), ("EUR / USD", 1.0854, 0.12, "#b388ff"),
]

def C(cid: str, el: str, props: dict) -> dict:
    """Build a v0.9 component dict. Strips structural keys from props to
    prevent accidental clobbering of `id` / `component` if a YAML author
    or LLM emits those as component-level attributes."""
    clean_props = {k: v for k, v in props.items() if k not in ('id', 'component')}
    return {"id": cid, "component": el, **clean_props}

def board(tick: int):
    random.seed(99 + tick)
    now = datetime.datetime.now().strftime("%H:%M:%S")
    comps = [
        C("root", "gdm-stage-grid", {"layout": "hero", "children": {"explicitList": ["main"]}}),
        C("main", "gdm-container", {"direction": "column", "padding": "28px", "gap": "18px",
                                    "width": "100%", "height": "100%", "glass": True,
                                    "children": {"explicitList": ["hdr", "div0", "grid"]}}),
        # header: title | spacer | flip clock
        C("hdr", "gdm-container", {"direction": "row", "align": "center", "width": "100%",
                                   "children": {"explicitList": ["titlecol", "sp", "clock"]}}),
        C("titlecol", "gdm-container", {"direction": "column", "gap": "4px",
                                        "children": {"explicitList": ["badge", "title", "sub"]}}),
        C("badge", "gdm-badge", {"text": "LIVE · COMPOSED FROM ATOMS", "type": "danger", "pulse": True}),
        C("title", "gdm-text", {"content": "▲ MARKET PULSE", "size": "h1", "color": "accent", "uppercase": True}),
        C("sub", "gdm-text", {"content": "gdm-grid · gdm-stat · gdm-text[flip] · gdm-spacer", "size": "caption", "color": "mute"}),
        C("sp", "gdm-spacer", {}),
        # Live clock = the gdm-clock MOLECULE (self-ticking timer + internal flip),
        # not the passive gdm-text[flip] atom which only flips on server re-render.
        C("clock", "gdm-clock", {"showClock": True, "showDate": True, "variant": "flip", "accentColor": "accent"}),
        C("div0", "gdm-divider", {"color": "rgba(0,242,255,0.18)"}),
        # 4-column real grid of stat tiles
        C("grid", "gdm-grid", {"columns": "4", "gap": "14px", "width": "100%",
                               "children": {"explicitList": [f"tile{i}" for i in range(len(INSTRUMENTS))]}}),
    ]
    for i, (name, base, chg, accent) in enumerate(INSTRUMENTS):
        drift = random.uniform(-0.5, 0.6)
        price = base * (1 + (chg + drift) / 100)
        delta = chg + drift
        up = delta >= 0
        dp = 4 if base < 10 else 2
        comps += [
            C(f"tile{i}", "gdm-container", {"direction": "column", "padding": "16px", "glass": True,
                                            "borderRadius": "14px",
                                            "children": {"explicitList": [f"stat{i}"]}}),
            C(f"stat{i}", "gdm-stat", {"label": name, "value": f"{price:,.{dp}f}",
                                       "delta": f"{'+' if up else ''}{delta:.2f}%", "isUp": up,
                                       "accent": accent, "size": "md"}),
        ]
    return comps

async def render(client, tick):
    await client.post(f"{API_URL}/api/render-stage/{SPACE}",
                      headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
                      json={"surfaceUpdate": {"components": board(tick)}, "root": "root"})

async def main():
    os.makedirs(OUT, exist_ok=True)
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{API_URL}/api/stage-ticket/{SPACE}", headers={"Authorization": f"Bearer {KEY}"})
        stage_url = r.json()["stage_url"]
        async with async_playwright() as p:
            br = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = await (await br.new_context(viewport={"width": 1920, "height": 1080})).new_page()
            errs = []
            page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            await page.goto(stage_url, wait_until="networkidle")
            await page.wait_for_timeout(2500)
            for t in range(6):                       # tick a few times so flip + deltas move
                await render(client, t)
                await page.wait_for_timeout(900)
            await page.screenshot(path=f"{OUT}/atoms_board.png")
            await br.close()
            print("CSP/style errors:", [e for e in errs if "Content-Security" in e][:3] or "none")
            print("other console errors:", [e for e in errs if "Content-Security" not in e][:5] or "none")
    print("saved", f"{OUT}/atoms_board.png")

if __name__ == "__main__":
    asyncio.run(main())
