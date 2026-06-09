#!/usr/bin/env python3
"""Headless capture of the composable market board — opens the stage in
Playwright (becomes its own stage listener), renders the board across ticks,
and screenshots consecutive frames so we can confirm the flicker is gone."""
import asyncio, os, sys, glob
_base = os.path.dirname(os.path.abspath(__file__))
for _vd in glob.glob(os.path.join(_base, "venv", "lib", "python3.*", "site-packages")):
    if _vd not in sys.path:
        sys.path.insert(0, _vd)
import httpx
from playwright.async_api import async_playwright
from demo_a2ui_composable_market import render_stage_api, generate_composed_market_board

API_URL = os.environ.get("CONCIERGE_API_URL") or exit("CONCIERGE_API_URL not set — see .env.production.sample")
KEY = os.environ.get("STAGE_API_KEY") or exit("STAGE_API_KEY required — export it before running this script")
SPACE = os.environ.get("CAPTURE_SPACE", "spaces/capshot-composable")
OUT = "/tmp/cap"

async def main():
    os.makedirs(OUT, exist_ok=True)
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{API_URL}/api/stage-ticket/{SPACE}", headers={"Authorization": f"Bearer {KEY}"})
        r.raise_for_status()
        stage_url = r.json()["stage_url"]
        print("stage_url:", stage_url)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = await (await browser.new_context(viewport={"width": 1920, "height": 1080}, ignore_https_errors=True)).new_page()
            errs = []
            page.on("console", lambda m: errs.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
            page.on("pageerror", lambda e: errs.append(f"pageerror: {e}"))
            await page.goto(stage_url, wait_until="networkidle")
            await page.wait_for_timeout(3000)  # let /ws/stage connect + engine init

            async def render(tick):
                await render_stage_api(client, SPACE, generate_composed_market_board(tick), root_id="stage_root_grid")

            await render(5); await page.wait_for_timeout(1500)
            await page.screenshot(path=f"{OUT}/01_settled.png")
            await render(6); await page.wait_for_timeout(120)   # immediately after a re-render
            await page.screenshot(path=f"{OUT}/02_postrender.png")
            await page.wait_for_timeout(1200)                    # settled again
            await page.screenshot(path=f"{OUT}/03_settled2.png")

            print("console errors/warnings:")
            for e in errs[:25]:
                print("  ", e)
            await browser.close()
    print("saved to", OUT)

asyncio.run(main())
