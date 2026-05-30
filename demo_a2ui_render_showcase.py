#!/usr/bin/env python3
"""
Meet Live Concierge — A2UI Render Showcase (Mermaid, HTML Panel & Diagram Overlay)
================================================================================
Demonstrates the client-side compiled Mermaid panel, flexible isolated HTML panels,
and immersive glassmorphic fullscreen overlays.

Phases:
1. Split Screen - Telemetry & Mermaid: Renders a split stage with Stock/Flight telemetry
   on the left, and a client-side compiled transaction flowchart on the right.
2. Full-Stage D2 Overlay: Centers a premium system architecture diagram in a glassmorphic
   hud overlay floating above the dimmed, blurred telemetry panels.
3. Split Screen - Telemetry & HTML Table: Clears the overlay and replaces the right-hand slot
   with a fully custom HTML table displaying real-time connection latencies.
4. Full-Stage HTML Dashboard Overlay: Projects the HTML frame to a full-stage overlay,
   displaying custom metrics as a floating HUD.
5. Clean Reset: Clears the stage.

Environment Variables:
    CONCIERGE_API_URL: Target FastAPI backend URL. Default: http://localhost:8000
    STAGE_API_KEY: Secure auth token.
    MEET_SPACE_ID: Force target Google Meet space.
"""

import asyncio
import os
import sys
import httpx
import random

# --- Environment Configurations ---
API_URL = os.environ.get("CONCIERGE_API_URL", "http://localhost:8000")
KEY = os.environ.get("STAGE_API_KEY", "meet-live_STAGE_SECURE_v1_zG9fN8qL7vP2mX6tY9wK4jC5bS8xQ7hZ3uW0rA")

# --- ANSI Terminal Colors ---
CLR_PRIMARY = "\033[38;5;51m"   # Neon Cyan
CLR_ACCENT = "\033[38;5;201m"   # Neon Magenta
CLR_SUCCESS = "\033[38;5;82m"   # Neon Green
CLR_WARNING = "\033[38;5;220m"  # Gold Yellow
CLR_MUTED = "\033[38;5;244m"    # Cool Slate
CLR_RESET = "\033[0m"

def print_banner():
    print(f"\n{CLR_PRIMARY}  ======================================================={CLR_RESET}")
    print(f"{CLR_PRIMARY}  ▲  A 2 U I   V I S U A L   S H O W C A S E   D E M O   ▲{CLR_RESET}")
    print(f"{CLR_PRIMARY}  ======================================================={CLR_RESET}")
    print(f"  {CLR_MUTED}Interactive Elements: Mermaid.js, HTML Iframe, D2 Overlay{CLR_RESET}")
    print(f"  {CLR_MUTED}Target Server:{CLR_RESET} {CLR_PRIMARY}{API_URL}{CLR_RESET}\n")

async def get_active_space(client: httpx.AsyncClient) -> str:
    """Retrieves the active Google Meet session ID from the dev status endpoint."""
    headers = {"Authorization": f"Bearer {KEY}"} if KEY else {}
    try:
        resp = await client.get(f"{API_URL}/api/dev/sessions", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            sessions = data.get("active_sessions", [])
            listeners = data.get("stage_listeners", {})
            if sessions:
                return sessions[0]
            elif listeners:
                return list(listeners.keys())[0]
        return "default"
    except Exception:
        return "default"

async def call_mcp_tool(client: httpx.AsyncClient, name: str, arguments: dict):
    """Executes a JSON-RPC 2.0 tools/call request to the MCP server."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {KEY}"
    }
    payload = {
        "jsonrpc": "2.0",
        "id": "antigravity-visual-mcp",
        "method": "tools/call",
        "params": {
            "name": name,
            "arguments": arguments
        }
    }

    try:
        resp = await client.post(f"{API_URL}/mcp", headers=headers, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            if "error" in data:
                print(f"  {CLR_ACCENT}❌ MCP Server Error: {data['error'].get('message')}{CLR_RESET}")
            else:
                result = data.get("result", {})
                is_error = result.get("isError", False)
                content = result.get("content", [{}])[0].get("text", "")
                if is_error:
                    print(f"  {CLR_ACCENT}❌ Tool Execution Error:{CLR_RESET} {content}")
                else:
                    print(f"  {CLR_SUCCESS}✅ Tool Executed:{CLR_RESET} {content}")
        else:
            print(f"  {CLR_ACCENT}❌ HTTP Error {resp.status_code}: {resp.text}{CLR_RESET}")
    except Exception as e:
        print(f"  {CLR_ACCENT}❌ Request Failed: {e}{CLR_RESET}")

async def run_showcase():
    print_banner()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Resolve space ID
        space_id = os.environ.get("MEET_SPACE_ID")
        if not space_id:
            print(f"  {CLR_MUTED}Detecting active Meet session...{CLR_RESET}")
            space_id = await get_active_space(client)
        
        print(f"  {CLR_WARNING}▶ Space Target ID:{CLR_RESET} {CLR_PRIMARY}{space_id}{CLR_RESET}\n")

        # Mock mockups
        mermaid_syntax = (
            "sequenceDiagram\n"
            "  participant Client as 🖥️ Main Stage\n"
            "  participant Agent as 🤖 Gemini Agent\n"
            "  participant DB as 💾 Memory Bank\n"
            "  Client->>Agent: Speaks voice command\n"
            "  Agent->>DB: Query context memory\n"
            "  DB-->>Agent: Returns memory records\n"
            "  Agent->>Client: Renders Mermaid Sequence (<100ms)\n"
        )

        # Fallback static SVG representation
        d2_svg = (
            '<svg viewBox="0 0 400 200" xmlns="http://www.w3.org/2000/svg">'
            '  <defs>'
            '    <linearGradient id="neonGlow" x1="0%" y1="0%" x2="100%" y2="100%">'
            '      <stop offset="0%" stop-color="#00f2ff" stop-opacity="0.8"/>'
            '      <stop offset="100%" stop-color="#f000ff" stop-opacity="0.8"/>'
            '    </linearGradient>'
            '  </defs>'
            '  <rect width="100%" height="100%" rx="12" fill="#080a14" stroke="#00f2ff" stroke-width="1.5"/>'
            '  <circle cx="100" cy="100" r="40" fill="url(#neonGlow)"/>'
            '  <text x="100" y="105" fill="#ffffff" font-family="sans-serif" font-size="12" text-anchor="middle" font-weight="bold">Client A2UI (Fallback)</text>'
            '  <line x1="140" y1="100" x2="260" y2="100" stroke="#00f2ff" stroke-width="2" stroke-dasharray="5,5"/>'
            '  <rect x="260" y="60" width="80" height="80" rx="8" fill="#121620" stroke="#f000ff" stroke-width="1.5"/>'
            '  <text x="300" y="105" fill="#ffffff" font-family="sans-serif" font-size="12" text-anchor="middle" font-weight="bold">Backend</text>'
            '</svg>'
        )

        d2_code = (
            '"👤 User".class: user\n'
            '"🧠 Backend Engine".class: app\n'
            '"🤖 Gemini 2.5".class: cloud\n'
            '"💾 Session Store".class: storage\n'
            '"🖥️ Main Stage".class: infra\n\n'
            '"👤 User" -> "🧠 Backend Engine": "Voice command"\n'
            '"🧠 Backend Engine" -> "🤖 Gemini 2.5": "Analyze context"\n'
            '"🧠 Backend Engine" -> "💾 Session Store": "Save state"\n'
            '"🧠 Backend Engine" -> "🖥️ Main Stage": "Render A2UI layout"\n'
        )

        print(f"  {CLR_MUTED}Compiling dynamic D2 diagram via backend...{CLR_RESET}")
        try:
            resp = await client.post(
                f"{API_URL}/api/render",
                headers={"Authorization": f"Bearer {KEY}"} if KEY else {},
                json={"d2": d2_code, "style": "cyber"}
            )
            if resp.status_code == 200:
                d2_svg = resp.text
                print(f"  {CLR_SUCCESS}✓ Successfully compiled live D2 diagram ({len(d2_svg)} bytes)!{CLR_RESET}")
            else:
                print(f"  {CLR_WARNING}⚠️ Server D2 compilation failed (status {resp.status_code}): {resp.text}. Using pre-baked fallback SVG.{CLR_RESET}")
        except Exception as e:
            print(f"  {CLR_WARNING}⚠️ Connection to D2 compiler endpoint failed: {e}. Using pre-baked fallback SVG.{CLR_RESET}")


        html_table = (
            '<h3 style="color:#00f2ff; margin-bottom:12px; font-family:sans-serif;">🌐 Connection Latency Dashboard</h3>'
            '<table style="width:100%; border-collapse:collapse; font-family:sans-serif; font-size:12px; color:rgba(255,255,255,0.85);">'
            '  <tr style="border-bottom:1px solid rgba(0,242,255,0.3); background:rgba(0,242,255,0.05); text-align:left;">'
            '    <th style="padding:10px;">Route Endpoint</th>'
            '    <th style="padding:10px;">Latency</th>'
            '    <th style="padding:10px;">Jitter</th>'
            '    <th style="padding:10px;">Status</th>'
            '  </tr>'
            '  <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">'
            '    <td style="padding:10px;">/ws/stage?meeting_id=123</td>'
            '    <td style="padding:10px; color:#00ff88; font-weight:bold;">12ms</td>'
            '    <td style="padding:10px;">1.2ms</td>'
            '    <td style="padding:10px; color:#00ff88;">ONLINE</td>'
            '  </tr>'
            '  <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">'
            '    <td style="padding:10px;">/api/render-stage</td>'
            '    <td style="padding:10px; color:#00ff88; font-weight:bold;">45ms</td>'
            '    <td style="padding:10px;">2.8ms</td>'
            '    <td style="padding:10px; color:#00ff88;">ONLINE</td>'
            '  </tr>'
            '  <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">'
            '    <td style="padding:10px;">Vertex AI API /gemini-2.5</td>'
            '    <td style="padding:10px; color:#ffaa00; font-weight:bold;">180ms</td>'
            '    <td style="padding:10px;">14.5ms</td>'
            '    <td style="padding:10px; color:#ffaa00;">STABLE</td>'
            '  </tr>'
            '</table>'
        )

        html_overlay = (
            '<div style="text-align:center; padding:40px; font-family:sans-serif;">'
            '  <h1 style="color:#00f2ff; margin-bottom:8px; font-size:32px; text-shadow:0 0 10px rgba(0,242,255,0.5);">🚀 CRITICAL ALERT: DISPATCH ENGINE</h1>'
            '  <p style="color:rgba(255,255,255,0.7); font-size:16px; margin-bottom:30px;">Immersive fullscreen glassmorphic takeover widget rendering live HTML5 markup.</p>'
            '  <div style="display:flex; justify-content:center; gap:20px;">'
            '    <div style="background:rgba(18,26,48,0.6); border:1px solid rgba(0,242,255,0.3); border-radius:12px; padding:20px; width:150px;">'
            '      <h4 style="color:#00ff88; margin:0 0 8px 0; font-size:24px;">99.98%</h4>'
            '      <span style="font-size:11px; color:rgba(255,255,255,0.5);">ENGINE HEALTH</span>'
            '    </div>'
            '    <div style="background:rgba(18,26,48,0.6); border:1px solid rgba(0,242,255,0.3); border-radius:12px; padding:20px; width:150px;">'
            '      <h4 style="color:#00f2ff; margin:0 0 8px 0; font-size:24px;">450 Mbps</h4>'
            '      <span style="font-size:11px; color:rgba(255,255,255,0.5);">THROUGHPUT</span>'
            '    </div>'
            '  </div>'
            '</div>'
        )

        # ───────────────────────────────────────────────────────────
        # Phase 1: Split Screen - Telemetry & Mermaid Diagram
        # ───────────────────────────────────────────────────────────
        print(f"{CLR_PRIMARY}[Phase 1]{CLR_RESET} Rendering split screen grid with Telemetry Dashboard and client-side Mermaid flowchart...")
        await call_mcp_tool(client, "render_stage", {
            "space_id": space_id,
            "surfaceUpdate": {
                "components": [
                    {
                        "id": "grid_layout",
                        "component": {
                            "gdm-stage-grid": {
                                "layout": "split",
                                "focusedPanel": 0,
                                "children": ["telemetry_dashboard", "mermaid_panel"]
                            }
                        }
                    },
                    {
                        "id": "telemetry_dashboard",
                        "component": {
                            "gdm-telemetry-dashboard": {
                                "title": "🔴 Systems Telemetry Feed",
                                "activeTabId": "sys",
                                "tabs": [{"id": "sys", "label": "CPU & Network", "active": True}]
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
        
        await asyncio.sleep(6.0)

        # ───────────────────────────────────────────────────────────
        # Phase 2: Full-Stage D2 Overlay
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_PRIMARY}[Phase 2]{CLR_RESET} Launching fullscreen glassmorphic D2 diagram overlay above live telemetry...")
        await call_mcp_tool(client, "render_stage", {
            "space_id": space_id,
            "surfaceUpdate": {
                "components": [
                    # Retain the grid underneath so it is visible but blurred
                    {
                        "id": "grid_layout",
                        "component": {
                            "gdm-stage-grid": {
                                "layout": "split",
                                "children": ["telemetry_dashboard", "mermaid_panel"]
                            }
                        }
                    },
                    {
                        "id": "telemetry_dashboard",
                        "component": {
                            "gdm-telemetry-dashboard": {
                                "title": "🔴 Systems Telemetry Feed",
                                "activeTabId": "sys",
                                "tabs": [{"id": "sys", "label": "CPU & Network", "active": True}]
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
                    },
                    # Add overlay component on top
                    {
                        "id": "diagram_overlay",
                        "component": {
                            "gdm-diagram-view": {
                                "diagId": "system_arch",
                                "svg": d2_svg,
                                "version": 1,
                                "overlay": True
                            }
                        }
                    }
                ]
            },
            "root": "grid_layout"
        })
        
        await asyncio.sleep(6.0)

        # ───────────────────────────────────────────────────────────
        # Phase 3: Split Screen - Telemetry & HTML Table
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_PRIMARY}[Phase 3]{CLR_RESET} Dismounting overlay and replacing panel with custom HTML connection table...")
        await call_mcp_tool(client, "render_stage", {
            "space_id": space_id,
            "surfaceUpdate": {
                "components": [
                    {
                        "id": "grid_layout",
                        "component": {
                            "gdm-stage-grid": {
                                "layout": "split",
                                "focusedPanel": 0,
                                "children": ["telemetry_dashboard", "html_panel"]
                            }
                        }
                    },
                    {
                        "id": "telemetry_dashboard",
                        "component": {
                            "gdm-telemetry-dashboard": {
                                "title": "🔴 Systems Telemetry Feed",
                                "activeTabId": "sys",
                                "tabs": [{"id": "sys", "label": "CPU & Network", "active": True}]
                            }
                        }
                    },
                    {
                        "id": "html_panel",
                        "component": {
                            "gdm-html-panel": {
                                "html": html_table,
                                "title": "🌐 Network RTT Statistics",
                                "version": 1,
                                "overlay": False
                            }
                        }
                    }
                ]
            },
            "root": "grid_layout"
        })
        
        await asyncio.sleep(6.0)

        # ───────────────────────────────────────────────────────────
        # Phase 4: Full-Stage HTML Overlay Takeover
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_PRIMARY}[Phase 4]{CLR_RESET} Expanding HTML frame into full-stage HUD dashboard overlay...")
        await call_mcp_tool(client, "render_stage", {
            "space_id": space_id,
            "surfaceUpdate": {
                "components": [
                    {
                        "id": "grid_layout",
                        "component": {
                            "gdm-stage-grid": {
                                "layout": "split",
                                "children": ["telemetry_dashboard", "html_panel"]
                            }
                        }
                    },
                    {
                        "id": "telemetry_dashboard",
                        "component": {
                            "gdm-telemetry-dashboard": {
                                "title": "🔴 Systems Telemetry Feed"
                            }
                        }
                    },
                    {
                        "id": "html_panel",
                        "component": {
                            "gdm-html-panel": {
                                "html": html_overlay,
                                "title": "🚀 Dispatch Control Hub",
                                "version": 2,
                                "overlay": True
                            }
                        }
                    }
                ]
            },
            "root": "grid_layout"
        })
        
        await asyncio.sleep(6.0)

        # ───────────────────────────────────────────────────────────
        # Phase 5: Clear and Reset
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_PRIMARY}[Phase 5]{CLR_RESET} Clearing stage layout back to default standby...")
        await call_mcp_tool(client, "clear_stage", {
            "space_id": space_id
        })
        
        print(f"\n{CLR_SUCCESS}🎉 Showcase completed successfully!{CLR_RESET}\n")

if __name__ == "__main__":
    try:
        asyncio.run(run_showcase())
    except KeyboardInterrupt:
        print(f"\n{CLR_ACCENT}Showcase interrupted by user.{CLR_RESET}")
        sys.exit(0)
