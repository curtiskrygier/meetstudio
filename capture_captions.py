#!/usr/bin/env python3
"""Verify gdm-captions flip: render one line, then change the text and capture a
frame right after (the old bug = only the first line flipped). Also confirms the
caption reads as flowing text (not a wall of fixed tiles) and clears the Meet bar."""
import asyncio, os, sys, glob
_base = os.path.dirname(os.path.abspath(__file__))
for _vd in glob.glob(os.path.join(_base, "venv", "lib", "python3.*", "site-packages")):
    if _vd not in sys.path: sys.path.insert(0, _vd)
import httpx
from playwright.async_api import async_playwright

API = os.environ.get("CONCIERGE_API_URL", "http://127.0.0.1:8085")
KEY = os.environ.get("STAGE_API_KEY", "meet-live_STAGE_SECURE_v1_zG9fN8qL7vP2mX6tY9wK4jC5bS8xQ7hZ3uW0rA")
SPACE = "spaces/cap-flip-test"
OUT = "/tmp/cap"

def caption(text):
    return {"surfaceUpdate": {"components": [
        {"id": "cap", "component": {"gdm-captions": {
            "text": text, "speaker": "Curtis Krygier", "active": True, "flip": True, "fontSize": 22}}}
    ]}, "root": "cap"}

async def main():
    os.makedirs(OUT, exist_ok=True)
    async with httpx.AsyncClient(timeout=20) as c:
        url = (await c.get(f"{API}/api/stage-ticket/{SPACE}", headers={"Authorization": f"Bearer {KEY}"})).json()["stage_url"]
        async with async_playwright() as p:
            br = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = await (await br.new_context(viewport={"width": 1600, "height": 900})).new_page()
            errs = []; page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            await page.goto(url, wait_until="networkidle"); await page.wait_for_timeout(2500)
            H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
            await c.post(f"{API}/api/render-stage/{SPACE}", headers=H, json=caption("Welcome everyone to the design review."))
            await page.wait_for_timeout(900)
            await page.screenshot(path=f"{OUT}/cap1_settled.png")
            # change the line — the fix means THIS one must flip too
            await c.post(f"{API}/api/render-stage/{SPACE}", headers=H, json=caption("Let us start with the architecture diagram."))
            await page.wait_for_timeout(160)
            await page.screenshot(path=f"{OUT}/cap2_midflip.png")
            await page.wait_for_timeout(800)
            await page.screenshot(path=f"{OUT}/cap3_settled.png")
            await br.close()
            print("console errors:", [e for e in errs if "Content-Security" in e][:3] or "none CSP")
asyncio.run(main())
