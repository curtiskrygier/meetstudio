#!/usr/bin/env python3
"""
Capture High-Resolution Viewport Screenshots of Meet Live Concierge Stage
========================================================================
Launches a headless Playwright Chromium instance, connects to the active 
Google Meet Main Stage, programmatically renders each of the new visual A2UI 
components in sequence, waits for animations to settle, and captures screenshots.

Outputs:
  - screenshot_p1_mermaid.png
  - screenshot_p2_diag_overlay.png
  - screenshot_p3_html_panel.png
  - screenshot_p4_html_overlay.png
"""

import asyncio
import os
import sys
import httpx
from playwright.async_api import async_playwright

API_URL = os.environ.get("CONCIERGE_API_URL", "http://localhost:8080")
KEY = os.environ.get("STAGE_API_KEY") or exit("STAGE_API_KEY required — export it before running this script")

# --- ANSI Formatting ---
CLR_CYAN = "\033[38;5;51m"
CLR_GREEN = "\033[38;5;82m"
CLR_MAGENTA = "\033[38;5;201m"
CLR_RESET = "\033[0m"

async def get_active_space() -> str:
    headers = {"Authorization": f"Bearer {KEY}"} if KEY else {}
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{API_URL}/api/dev/sessions", headers=headers)
            resp.raise_for_status()
            data = resp.json()
            listeners = data.get("stage_listeners", {})
            sessions = data.get("active_sessions", [])
            space = sessions[0] if sessions else (list(listeners.keys())[0] if listeners else "")
            return space if space else "spaces/mock-space"
        except Exception:
            return "spaces/mock-space"

async def get_stage_url(space_id: str) -> str:
    headers = {"Authorization": f"Bearer {KEY}"} if KEY else {}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{API_URL}/api/stage-ticket/{space_id}", headers=headers)
        resp.raise_for_status()
        return resp.json()["stage_url"]

async def call_mcp_tool(client: httpx.AsyncClient, tool_name: str, arguments: dict):
    headers = {"Content-Type": "application/json"}
    if KEY:
        headers["Authorization"] = f"Bearer {KEY}"
    payload = {
        "jsonrpc": "2.0",
        "id": "screenshot-capturer-mcp",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    resp = await client.post(f"{API_URL}/mcp", headers=headers, json=payload, timeout=15)
    resp.raise_for_status()

async def main():
    print(f"{CLR_CYAN}📸 [Visual Audit] Initializing headless Playwright capturer...{CLR_RESET}")
    
    # 1. Resolve space
    try:
        space_id = await get_active_space()
    except Exception as e:
        print(f"{CLR_MAGENTA}❌ Failed to fetch active sessions: {e}{CLR_RESET}")
        sys.exit(1)
        
    if not space_id:
        print(f"{CLR_MAGENTA}❌ No active Google Meet sessions detected.{CLR_RESET}")
        sys.exit(1)
        
    print(f"  ✓ Target Space: {space_id}")
    
    # 2. Get Stage ticket URL
    stage_url = await get_stage_url(space_id)
    print(f"  ✓ Stage URL resolved.")

    # Mock Data Mockups
    mermaid_syntax = (
        "sequenceDiagram\n"
        "  autonumber\n"
        "  actor User as 👤 Voice Command\n"
        "  participant Concierge as 🤖 Concierge\n"
        "  participant T212 as 📈 212Trading\n"
        "  participant Stage as 🖥️ Main Stage\n"
        "  User->>Concierge: Speaks Order Intent\n"
        "  activate Concierge\n"
        "  Concierge->>T212: Verify NVDA Stock Price\n"
        "  T212-->>Concierge: Return Quote Price ($1,042.50)\n"
        "  Concierge->>Stage: Compile Neon Mermaid Flowchart\n"
        "  activate Stage\n"
        "  Note over Stage: Client-side CSS neon overrides injected\n"
        "  Stage-->>User: Renders Liquid Stage HUD (<100ms)\n"
        "  deactivate Stage\n"
        "  deactivate Concierge\n"
    )

    architecture_svg = """<svg viewBox="0 0 700 350" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <filter id="cyan-glow" x="-15%" y="-15%" width="130%" height="130%">
          <feGaussianBlur stdDeviation="5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="magenta-glow" x="-15%" y="-15%" width="130%" height="130%">
          <feGaussianBlur stdDeviation="5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <rect width="100%" height="100%" rx="18" fill="rgba(10, 12, 28, 0.95)" stroke="#00f2ff" stroke-width="2"/>
      <text x="30" y="40" fill="#00f2ff" font-family="monospace" font-size="12" font-weight="bold">CONCIERGE MASTER ROUTING ENGINE // V2.0</text>
      <line x1="30" y1="48" x2="350" y2="48" stroke="rgba(0, 242, 255, 0.3)" stroke-width="1.5"/>
      <g transform="translate(45, 110)">
        <rect width="160" height="90" rx="10" fill="rgba(24, 30, 54, 0.7)" stroke="#00f2ff" stroke-width="1.5" filter="url(#cyan-glow)" />
        <text x="80" y="45" fill="#ffffff" font-family="sans-serif" font-size="13" font-weight="bold" text-anchor="middle">🎙️ CLIENT STAGE</text>
      </g>
      <path d="M 205 155 L 255 155" stroke="#00f2ff" stroke-width="2" fill="none" stroke-dasharray="4, 4"/>
      <g transform="translate(265, 90)">
        <rect width="190" height="130" rx="12" fill="rgba(42, 22, 68, 0.8)" stroke="#f000ff" stroke-width="2" filter="url(#magenta-glow)" />
        <text x="95" y="60" fill="#ffffff" font-family="sans-serif" font-size="14" font-weight="bold" text-anchor="middle">🧠 FastAPI BACKEND</text>
      </g>
    </svg>"""

    html_latency_table = (
        '<style>'
        '  body { background: transparent; margin: 0; color: #fff; font-family: system-ui, sans-serif; }'
        '  .title { color: #00f2ff; font-family: monospace; border-bottom: 1px solid rgba(0, 242, 255, 0.25); padding-bottom: 6px; font-size: 13px; }'
        '  table { width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 10px; }'
        '  th { text-align: left; padding: 6px; background: rgba(0, 242, 255, 0.05); color: #00f2ff; }'
        '  td { padding: 6px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); }'
        '</style>'
        '<div class="title">🌐 NETWORK HEALTH METRIC NODES</div>'
        '<table>'
        '  <tr><th>Service Endpoint</th><th>RTT Ping</th><th>Packet Status</th></tr>'
        '  <tr><td>/ws/stage?meeting_id=meet_v2</td><td style="color:#00ff88;">14ms</td><td style="color:#00ff88;">NOMINAL</td></tr>'
        '  <tr><td>FastAPI Stage Gateway</td><td style="color:#00ff88;">38ms</td><td style="color:#00ff88;">NOMINAL</td></tr>'
        '  <tr><td>Vertex LLM Connector (Gemini)</td><td style="color:#ffaa00;">165ms</td><td style="color:#ffaa00;">THROTTLED</td></tr>'
        '</table>'
    )

    html_hud_overlay = (
        '<style>'
        '  body { background: transparent; margin: 0; color: #fff; font-family: system-ui, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; }'
        '  .hud-container { width: 500px; background: rgba(8, 12, 28, 0.85); backdrop-filter: blur(12px); border: 2px solid #f000ff; border-radius: 16px; padding: 24px; box-shadow: 0 0 25px rgba(240, 0, 255, 0.4); text-align: center; }'
        '  h1 { font-family: monospace; font-size: 24px; color: #f000ff; margin: 0 0 10px 0; text-shadow: 0 0 10px rgba(240, 0, 255, 0.5); }'
        '  .kpi-row { display: flex; justify-content: space-around; gap: 16px; margin: 20px 0; }'
        '  .kpi-card { flex: 1; background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(0, 242, 255, 0.25); border-radius: 12px; padding: 14px 8px; }'
        '  .kpi-card h4 { font-size: 22px; margin: 0; font-family: monospace; color: #00ff88; }'
        '  .kpi-card span { font-size: 9px; color: rgba(255,255,255,0.5); font-weight: bold; letter-spacing: 0.5px; }'
        '</style>'
        '<div class="hud-container">'
        '  <h1>🚀 EXECUTIVE MISSION CONTROL HUD</h1>'
        '  <div class="kpi-row">'
        '    <div class="kpi-card"><h4>99.98%</h4><span>SYSTEM HEALTH</span></div>'
        '    <div class="kpi-card"><h4>582 rps</h4><span>API INTENSITY</span></div>'
        '  </div>'
        '</div>'
    )

    # 3. Launch browser
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        print(f"  ✓ Opening Meet Main Stage browser viewport...")
        await page.goto(stage_url, wait_until="networkidle")
        await asyncio.sleep(2.0)

        async with httpx.AsyncClient(timeout=30) as http_client:
            # Theme config reset
            await http_client.post(f"{API_URL}/api/theme-config/{space_id}", json={"theme": "glassmorphism"})

            # Clear stage initially to ensure a clean state
            print(f"↩ Pre-clearing stage...")
            await call_mcp_tool(http_client, "clear_stage", {"space_id": space_id})
            await asyncio.sleep(1.0)

            # ---- PHASE 1 SCREENSHOT ----
            print(f"🎬 [Layout 1] Rendering Stock Telemetry + Mermaid.js Flowchart...")
            await call_mcp_tool(http_client, "render_stage", {
                "space_id": space_id,
                "surfaceUpdate": {
                    "components": [
                        {
                            "id": "grid_layout",
                            "component": {
                                "gdm-stage-grid": {
                                    "layout": "split",
                                    "children": {
                                        "explicitList": ["telemetry_dashboard", "mermaid_panel"]
                                    }
                                }
                            }
                        },
                        {
                            "id": "telemetry_dashboard",
                            "component": {
                                "gdm-telemetry-dashboard": {
                                    "tabs": [{"id": "stk", "label": "MARKET INDICES"}],
                                    "activeTabId": "stk",
                                    "title": "⚡ Live Market Feeds",
                                    "metrics": [
                                        {"label": "NVDA (+1.45%)", "value": "$1,042.50 ▲", "color": "#00ff88"},
                                        {"label": "GOOG (+0.80%)", "value": "$175.20 ▲", "color": "#00ff88"}
                                    ],
                                    "chart": [45, 47, 46, 49, 48, 51, 50, 53]
                                }
                            }
                        },
                        {
                            "id": "mermaid_panel",
                            "component": {
                                "gdm-mermaid-panel": {
                                    "syntax": mermaid_syntax,
                                    "title": "🧜‍♀️ Live Transaction Processing Pipeline",
                                    "version": 1
                                }
                            }
                        }
                    ]
                },
                "root": "grid_layout"
            })
            
            # Wait for transitions and Mermaid rendering (crucial as mermaid loads async)
            await asyncio.sleep(3.5)
            await page.screenshot(path="screenshot_p1_mermaid.png")
            print(f"  {CLR_GREEN}✓ Captured: screenshot_p1_mermaid.png{CLR_RESET}")

            # ---- PHASE 2 SCREENSHOT ----
            print(f"🎬 [Layout 2] Launching SVG System Architecture Overlay...")
            await call_mcp_tool(http_client, "render_stage", {
                "space_id": space_id,
                "surfaceUpdate": {
                    "components": [
                        {
                            "id": "grid_layout",
                            "component": {
                                "gdm-stage-grid": {
                                    "layout": "split",
                                    "children": {"explicitList": ["telemetry_dashboard", "mermaid_panel"]}
                                }
                            }
                        },
                        {
                            "id": "telemetry_dashboard",
                            "component": {"gdm-telemetry-dashboard": {"activeTabId": "stk"}}
                        },
                        {
                            "id": "mermaid_panel",
                            "component": {"gdm-mermaid-panel": {"syntax": mermaid_syntax}}
                        },
                        {
                            "id": "architecture_overlay",
                            "component": {
                                "gdm-diagram-view": {
                                    "diagId": "concierge_arch",
                                    "svg": architecture_svg,
                                    "version": 1,
                                    "overlay": True
                                }
                            }
                        }
                    ]
                },
                "root": "grid_layout"
            })
            await asyncio.sleep(3.0)
            await page.screenshot(path="screenshot_p2_diag_overlay.png")
            print(f"  {CLR_GREEN}✓ Captured: screenshot_p2_diag_overlay.png{CLR_RESET}")

            # Clear stage before transitioning to Layout 3 to clear Phase 2's architecture_overlay
            print(f"↩ Clearing stage before Phase 3 to clear previous overlay...")
            await call_mcp_tool(http_client, "clear_stage", {"space_id": space_id})
            await asyncio.sleep(1.0)

            # ---- PHASE 3 SCREENSHOT ----
            print(f"🎬 [Layout 3] Transitioning to Flights Telemetry + Sandboxed HTML Latency...")
            await call_mcp_tool(http_client, "render_stage", {
                "space_id": space_id,
                "surfaceUpdate": {
                    "components": [
                        {
                            "id": "grid_layout",
                            "component": {
                                "gdm-stage-grid": {
                                    "layout": "split",
                                    "children": {
                                        "explicitList": ["telemetry_dashboard", "html_panel"]
                                    }
                                }
                            }
                        },
                        {
                            "id": "telemetry_dashboard",
                            "component": {
                                "gdm-telemetry-dashboard": {
                                    "tabs": [{"id": "flt", "label": "AIRSPACE"}],
                                    "activeTabId": "flt",
                                    "title": "✈️ Live Radar Sectors",
                                    "metrics": [
                                        {"label": "Flight AFR6129", "value": "Alt: 1500m / Spd: 310km/h", "color": "#00ff88"}
                                    ],
                                    "chart": [22, 25, 24, 27, 26, 29]
                                }
                            }
                        },
                        {
                            "id": "html_panel",
                            "component": {
                                "gdm-html-panel": {
                                    "html": html_latency_table,
                                    "title": "🌐 Network Latency Node Map",
                                    "version": 1,
                                    "overlay": False
                                }
                            }
                        }
                    ]
                },
                "root": "grid_layout"
            })
            await asyncio.sleep(3.0)
            panel_html = await page.evaluate("""() => {
                const el = document.getElementById('html_panel');
                if (!el || !el.shadowRoot) return 'no element or shadow root';
                return el.shadowRoot.innerHTML;
            }""")
            print("DEBUG SHADOW HTML:")
            print(panel_html)
            await page.screenshot(path="screenshot_p3_html_panel.png")
            print(f"  {CLR_GREEN}✓ Captured: screenshot_p3_html_panel.png{CLR_RESET}")

            # ---- PHASE 4 SCREENSHOT ----
            print(f"🎬 [Layout 4] Launching Fullscreen HTML Overlay...")
            await call_mcp_tool(http_client, "render_stage", {
                "space_id": space_id,
                "surfaceUpdate": {
                    "components": [
                        {
                            "id": "grid_layout",
                            "component": {
                                "gdm-stage-grid": {
                                    "layout": "split",
                                    "children": {
                                        "explicitList": ["telemetry_dashboard", "html_panel"]
                                    }
                                }
                            }
                        },
                        {
                            "id": "telemetry_dashboard",
                            "component": {"gdm-telemetry-dashboard": {"activeTabId": "flt"}}
                        },
                        {
                            "id": "html_panel",
                            "component": {
                                "gdm-html-panel": {
                                    "html": html_hud_overlay,
                                    "title": "🚀 Mission Control Console",
                                    "version": 2,
                                    "overlay": True
                                }
                            }
                        }
                    ]
                },
                "root": "grid_layout"
            })
            await asyncio.sleep(3.0)
            await page.screenshot(path="screenshot_p4_html_overlay.png")
            print(f"  {CLR_GREEN}✓ Captured: screenshot_p4_html_overlay.png{CLR_RESET}")

            # Reset Stage
            print(f"↩ Clear stage back to standby...")
            await call_mcp_tool(http_client, "clear_stage", {"space_id": space_id})

        await context.close()
        await browser.close()
        
    print(f"\n{CLR_GREEN}🎉 All screenshots captured successfully in headless mode!{CLR_RESET}\n")

if __name__ == "__main__":
    asyncio.run(main())
