#!/usr/bin/env python3
import asyncio
import os
import sys
from playwright.async_api import async_playwright
import httpx

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from demo_a2ui_toulouse_airspace import (
    get_fallback_flights,
    make_target_profile_html,
    render_stage_api,
    fetch_lfbo_metar,
    KEY,
    API_URL
)

async def capture():
    space_id = "spaces/OJrdOKDMKtUB"
    screenshot_path = os.environ.get("SCREENSHOT_PATH", "airspace_stage.png")
    
    print(f"🔗 Target Space ID: {space_id}")
    print(f"🔗 API URL: {API_URL}")
    
    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Issue a stage-ticket authenticated by STAGE_API_KEY
        headers = {"Authorization": f"Bearer {KEY}"}
        ticket_url = f"{API_URL}/api/stage-ticket/{space_id}"
        print(f"🎫 Requesting stage ticket from: {ticket_url}")
        
        resp = await client.get(ticket_url, headers=headers)
        resp.raise_for_status()
        ticket_data = resp.json()
        stage_url = ticket_data["stage_url"]
        print(f"✅ Received Stage URL: {stage_url}")
        
        # Fetch weather
        weather = await fetch_lfbo_metar(client)
        print(f"🌦️ Fetched weather: {weather['raw']}")

        # 2. Render a gorgeous high-fidelity active target lock 3D airspace layout
        print("🚀 Rendering active 3D Airspace target lock profile on the stage...")
        flights = get_fallback_flights(tick=3)
        lead_flight = flights[0] # AFR6129
        html_hud = make_target_profile_html(lead_flight, tick=3)
        
        ticker_comp = {
            "id": "airspace_ticker",
            "component": {
                "gdm-ticker": {
                    "text": f"📍 LFBO Terminal Information • RUNWAY 32L/R ACTIVE FOR ARRIVALS • SURFACE WIND: {weather['wind'].upper()} • TEMP: {weather['temp']} • QNH: {weather['pressure']} • SQUAWK 7700 ALERT: NONE • ACTIVE TRAFFIC SENSORS: ONLINE • RAW METAR: {weather['raw']} •",
                    "scrollSpeed": 50,
                    "active": True,
                    "accentColor": "#00ff88"
                }
            }
        }
        
        chyron_comp = {
            "id": "atc_chyron",
            "component": {
                "gdm-chyron": {
                    "title": "TARGET ACQUIRED: AFR6129",
                    "subtitle": "Tracking Descent Path and Instrument Glide Slope Runway 32L",
                    "active": True,
                    "accentColor": "#00f2ff"
                }
            }
        }
        
        deactivated_slate = {
            "id": "calibration_slate",
            "component": {
                "gdm-standby-slate": {
                    "active": False
                }
            }
        }
        
        await render_stage_api(client, space_id, [
            {
                "id": "grid_layout",
                "component": {
                    "gdm-stage-grid": {
                        "layout": "split",
                        "children": {"explicitList": ["radar_view", "html_panel"]}
                    }
                }
            },
            {
                "id": "radar_view",
                "component": {
                    "gdm-3d-airspace": {
                        "flights": flights,
                        "lockedCallsign": "AFR6129",
                        "zoom": 4.0,
                        "cameraPitch": 25.0,
                        "cameraYaw": 135.0,
                        "showGlideSlope": True,
                        "showTerrain": True,
                        "cinematicOrbit": True,
                        "autoTrack": True
                    }
                }
            },
            {
                "id": "html_panel",
                "component": {
                    "gdm-html-panel": {
                        "html": html_hud,
                        "title": "🎯 Active Target Profiler",
                        "version": 4
                    }
                }
            },
            deactivated_slate,
            ticker_comp,
            chyron_comp
        ], root_id="grid_layout")
        
        # 3. Spin up Playwright to navigate to stage_url and take a screenshot
        print("🦊 Initializing Playwright browser instance...")
        async with async_playwright() as p:
            # We bypass SSL verification issues if any on Cloud Run HTTPS
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                ignore_https_errors=True
            )
            page = await context.new_page()
            
            print(f"🌐 Navigating to stage_url...")
            await page.goto(stage_url)
            
            # Allow some time for WebSocket to connect, components to load,
            # and the 3D Canvas cinematic orbit loop to spin up
            print("⏳ Waiting 6 seconds for WebSockets and canvas rendering loop...")
            await asyncio.sleep(6.0)
            
            print(f"📸 Snapping viewport screenshot...")
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"🏆 Screenshot saved successfully to: {screenshot_path}")
            
            await browser.close()

if __name__ == "__main__":
    asyncio.run(capture())
