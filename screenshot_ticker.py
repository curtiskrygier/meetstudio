#!/usr/bin/env python3
import asyncio
import os
import sys
import glob
from playwright.async_api import async_playwright
import httpx

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import helpers from the market ticker demo
from demo_a2ui_market_ticker import (
    get_active_space,
    render_stage_api,
    generate_macro_indices,
    generate_t212_holdings,
    make_trading_order_book_html,
    KEY,
    API_URL
)

async def capture():
    # Use fallback space_id if no active session is found
    space_id = "spaces/OJrdOKDMKtUB"
    screenshot_path = os.environ.get("SCREENSHOT_PATH", "ticker_stage.png")
    
    print(f"🔗 API URL: {API_URL}")
    
    async with httpx.AsyncClient(timeout=30) as client:
        # Determine the target space
        active_space = await get_active_space(client)
        if active_space:
            space_id = active_space
            print(f"📡 Found Active Meeting Space: {space_id}")
        else:
            print(f"📡 No active space detected, using fallback space: {space_id}")
            
        # 1. Issue a stage-ticket authenticated by STAGE_API_KEY
        headers = {"Authorization": f"Bearer {KEY}"}
        ticket_url = f"{API_URL}/api/stage-ticket/{space_id}"
        print(f"🎫 Requesting stage ticket from: {ticket_url}")
        
        try:
            resp = await client.get(ticket_url, headers=headers)
            resp.raise_for_status()
            ticket_data = resp.json()
            stage_url = ticket_data["stage_url"]
            print(f"✅ Received Stage URL: {stage_url}")
        except Exception as e:
            print(f"❌ Error getting stage ticket: {e}")
            sys.exit(1)

        # 2. Render a gorgeous high-fidelity persistent market ticker and trading console layout
        print("🚀 Rendering active Market Ticker and Trading Console on the stage...")
        
        tick = 3  # Stable midpoint dataset
        macros = generate_macro_indices(tick)
        holdings = generate_t212_holdings(tick)
        html_order_book = make_trading_order_book_html(holdings, tick)
        
        ticker_comp = {
            "id": "market_scroller",
            "component": {
                "gdm-market-ticker": {
                    "macroRow": macros,
                    "holdingsRow": holdings,
                    "active": True,
                    "badgeText": "T212 LINKED",
                    "badgeColor": "#ffd60a",
                    "height": 110
                }
            }
        }
        
        chyron_comp = {
            "id": "financial_chyron",
            "component": {
                "gdm-chyron": {
                    "title": "TRADING 212 GLOBAL PORTFOLIO",
                    "subtitle": "Macro Indices & Active Portfolio Holdings Deck",
                    "active": True,
                    "accentColor": "#ffd60a"
                }
            }
        }
        
        deactivated_slate = {
            "id": "financial_standby_slate",
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
                        "layout": "hero",
                        "children": {"explicitList": ["html_panel"]}
                    }
                }
            },
            {
                "id": "html_panel",
                "component": {
                    "gdm-html-panel": {
                        "html": html_order_book,
                        "title": "💼 Live Order Book Management Console",
                        "version": tick + 1
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
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                ignore_https_errors=True
            )
            page = await context.new_page()
            
            # Diagnostic event listeners
            page.on("console", lambda msg: print(f"🖥️ [Browser Console] {msg.type.upper()}: {msg.text}"))
            page.on("pageerror", lambda err: print(f"❌ [Browser Error] {err}"))
            page.on("requestfailed", lambda req: print(f"⚠️ [Net Request Failed] {req.method} {req.url} - {req.failure}"))
            
            print(f"🌐 Navigating to stage_url...")
            await page.goto(stage_url)
            
            # Allow some time for WebSocket to connect, components to load and render
            print("⏳ Waiting 6 seconds for WebSockets and component render loop...")
            await asyncio.sleep(6.0)
            
            # Let's evaluate and print stage DOM details
            diagnostics = await page.evaluate("""() => {
                const root = document.getElementById('a2ui-stage-root');
                if (!root) return '❌ No stage root element found';
                const children = Array.from(root.children).map(c => {
                    const tag = c.tagName.toLowerCase();
                    const id = c.id || c.getAttribute('data-a2ui-id') || 'no-id';
                    const activeAttr = c.hasAttribute('active') ? 'active=true' : 'no-active';
                    const disp = window.getComputedStyle(c).display;
                    const vis = window.getComputedStyle(c).visibility;
                    const op = window.getComputedStyle(c).opacity;
                    const bounds = c.getBoundingClientRect();
                    return `${tag}#${id} (${activeAttr}) display:${disp} visibility:${vis} opacity:${op} rect:[w:${bounds.width}, h:${bounds.height}, t:${bounds.top}, l:${bounds.left}]`;
                });
                return children.join('\\n');
            }""")
            print("🔍 STAGE ROOT DIAGNOSTICS:")
            print(diagnostics)
            
            print(f"📸 Snapping viewport screenshot...")
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"🏆 Screenshot saved successfully to: {screenshot_path}")
            
            await browser.close()

if __name__ == "__main__":
    asyncio.run(capture())
