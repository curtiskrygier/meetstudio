#!/usr/bin/env python3
import asyncio
import os
import sys
from playwright.async_api import async_playwright
import httpx

API_URL = "http://127.0.0.1:8085"
KEY = os.environ.get("STAGE_API_KEY") or exit("STAGE_API_KEY required — export it before running this script")
SPACE = "default"
SCREENSHOT_PATH = "/home/curtis/.gemini/antigravity-cli/brain/aaa90b5d-fd91-4aa1-af75-ac1416d53d97/airspace_stage_flowing_pulses.png"

async def main():
    async with httpx.AsyncClient(timeout=10) as client:
        # Get stage URL with ticket
        headers = {"Authorization": f"Bearer {KEY}"}
        ticket_url = f"{API_URL}/api/stage-ticket/{SPACE}"
        print(f"Requesting stage ticket from: {ticket_url}")
        resp = await client.get(ticket_url, headers=headers)
        resp.raise_for_status()
        stage_url = resp.json()["stage_url"]
        print(f"Resolved Stage URL: {stage_url}")

    async with async_playwright() as p:
        print("Launching Chromium to capture stage screenshot...")
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.goto(stage_url)
        print("Waiting for page content to load and stabilize...")
        await asyncio.sleep(8) # Wait for page rendering to settle
        print(f"Saving screenshot to {SCREENSHOT_PATH}...")
        await page.screenshot(path=SCREENSHOT_PATH)
        await browser.close()
    print("Screenshot successfully captured!")

if __name__ == "__main__":
    asyncio.run(main())
