#!/usr/bin/env python3
import asyncio, os, sys, glob
_base = os.path.dirname(os.path.abspath(__file__))
for _vd in glob.glob(os.path.join(_base, "venv", "lib", "python3.*", "site-packages")):
    if _vd not in sys.path: sys.path.insert(0, _vd)
import httpx
from playwright.async_api import async_playwright

API_URL = "http://127.0.0.1:8085"
KEY = os.environ.get("STAGE_API_KEY") or exit("STAGE_API_KEY required — export it before running this script")
SPACE = "default"

async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        # Request a fresh stage ticket
        r = await client.get(f"{API_URL}/api/stage-ticket/{SPACE}", headers={"Authorization": f"Bearer {KEY}"})
        data = r.json()
        stage_url = data["stage_url"]
        print(f"Stage URL: {stage_url}")
        
        async with async_playwright() as p:
            br = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = await (await br.new_context(viewport={"width": 1280, "height": 720})).new_page()
            
            print("Navigating to stage...")
            await page.goto(stage_url, wait_until="networkidle")
            
            print("Waiting for captions (sleeping 5s)...")
            await page.wait_for_timeout(5000)
            
            # Fetch layout and styles of #lower_third_captions
            info = await page.evaluate("""() => {
                const el = document.getElementById('lower_third_captions');
                if (!el) return 'No element found';
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                const pillActive = el.shadowRoot ? el.shadowRoot.querySelector('.pill.active') : null;
                const pillRect = pillActive ? pillActive.getBoundingClientRect() : null;
                const pillStyle = pillActive ? window.getComputedStyle(pillActive) : null;
                
                return {
                    tagName: el.tagName,
                    attributes: Array.from(el.attributes).map(a => `${a.name}="${a.value}"`),
                    host: {
                        rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
                        opacity: style.opacity,
                        display: style.display,
                        visibility: style.visibility,
                        zIndex: style.zIndex,
                        position: style.position,
                        bottom: style.bottom,
                        left: style.left,
                        right: style.right
                    },
                    pill: pillActive ? {
                        rect: { x: pillRect.x, y: pillRect.y, width: pillRect.width, height: pillRect.height },
                        opacity: pillStyle.opacity,
                        display: pillStyle.display,
                        visibility: pillStyle.visibility,
                        color: pillStyle.color,
                        background: pillStyle.background,
                        fontSize: pillStyle.fontSize
                    } : 'No active pill'
                };
            }""")
            
            screenshot_path = "/home/curtis/.gemini/antigravity-cli/brain/aaa90b5d-fd91-4aa1-af75-ac1416d53d97/captions_stage_debug.png"
            print(f"Saving screenshot to {screenshot_path}...")
            await page.screenshot(path=screenshot_path)
            print("Screenshot saved.")
            
            import json
            print("\n--- Element Metrics & Styles ---")
            print(json.dumps(info, indent=2))
            print("---------------------------------\n")
            
            await br.close()

if __name__ == "__main__":
    asyncio.run(main())
