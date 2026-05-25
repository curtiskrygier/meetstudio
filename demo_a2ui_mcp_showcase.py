#!/usr/bin/env python3
"""
Meet Live Concierge — Ultra Premium Interactive A2UI MCP Showcase
====================================================================
Demonstrates driving the Google Meet main stage using the true Model Context Protocol (MCP)
and Google A2UI v0.8 specification.

Phases:
0. Standby Countdown: Renders gdm-standby-slate count down.
1. Single Panel Stage: Composites a fullscreen gdm-image-panel and lower-third gdm-chyron.
2. Split Screen Stage: Renders a split gdm-stage-grid with gdm-image-panel and gdm-notepad.
3. Telemetry Streaming: Renders gdm-telemetry-dashboard streaming live stock price metrics + radar view + bottom ticker.
4. Live Poll Overlay: Slides in a live audience voting poll gdm-poll-overlay with interactive votes.
5. Live Audience Reactions: Clears the finance grid, then cascades gdm-chat-card feedback on its own clean stage (single-panel backdrop + chyron) so chat never blocks the dashboard.
6. Clean Close: Clears the stage, shows a closing gdm-stage-card briefly, then resets to default via clear_stage.

Environment Variables:
    CONCIERGE_API_URL: Target FastAPI backend URL.
    STAGE_API_KEY: Secure auth token.
    MEET_SPACE_ID: Force target Google Meet space.
"""

import asyncio
import os
import sys
import httpx
import random

# --- Environment Configurations ---
API_URL = os.environ.get("CONCIERGE_API_URL", "CONCIERGE_API_URL_PLACEHOLDER")
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
    print(f"{CLR_PRIMARY}  ▲  A N T I G R A V I T Y   M C P   S H O W C A S E  ▲{CLR_RESET}")
    print(f"{CLR_PRIMARY}  ======================================================={CLR_RESET}")
    print(f"  {CLR_MUTED}Standard: Model Context Protocol (A2UI v0.8 Spec){CLR_RESET}")
    print(f"  {CLR_MUTED}Active Server:{CLR_RESET} {CLR_PRIMARY}{API_URL}/mcp{CLR_RESET}\n")

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
        "id": "antigravity-mcp-call",
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

async def say_caption(client: httpx.AsyncClient, space_id: str, text: str, root: str, speaker: str = "Gemini Architect"):
    """Display one caption point via the first-class A2UI `gdm-captions` overlay.

    Captions are composed through render_stage like every other component — the
    overlay persists in the engine buffer and re-renders over whatever scene
    `root` points at. NOTE: `root`'s component tree must already be on stage
    (in the engine buffer), otherwise the bare overlay render would wipe it.
    """
    await call_mcp_tool(client, "render_stage", {
        "space_id": space_id,
        "surfaceUpdate": {
            "components": [
                {
                    "id": "live_captions",
                    "component": {
                        "gdm-captions": {"text": text, "speaker": speaker, "active": True}
                    }
                }
            ]
        },
        "root": root,
    })

async def get_live_stock_price(client: httpx.AsyncClient, symbol: str) -> tuple[float, float]:
    """Retrieve mock live stock pricing if APIs are slow/blocked."""
    base_prices = {
        "NVDA": (914.85, 2.5), 
        "MSFT": (421.90, -0.8), 
        "GOOG": (173.50, 1.2),
        "CAP.PA": (212.40, 1.5)
    }
    bp, change = base_prices.get(symbol, (100.0, 0.0))
    drift = random.uniform(-1.5, 1.5)
    new_price = bp + drift
    new_change = change + (drift / bp * 100)
    return new_price, new_change

def make_grid_components(nvda_p, nvda_c, msft_p, msft_c, goog_p, goog_c, cap_p, cap_c, stock_chart, TABS_CONFIG, focused_panel=0):
    flights_data = [
        {"callsign": "AFR012", "altitude": 34000, "speed": 450, "vrate": 150, "origin": "CDG", "destination": "JFK"},
        {"callsign": "BAW207", "altitude": 38000, "speed": 470, "vrate": 0, "origin": "LHR", "destination": "MIA"},
        {"callsign": "DLH430", "altitude": 36000, "speed": 460, "vrate": -250, "origin": "FRA", "destination": "ORD"},
        {"callsign": "SWR18", "altitude": 39000, "speed": 485, "vrate": 0, "origin": "ZRH", "destination": "LAX"}
    ]
    
    return [
        {
            "id": "grid_layout",
            "component": {
                "gdm-stage-grid": {
                    "layout": "grid",
                    "focusedPanel": focused_panel,
                    "children": {
                        "explicitList": [
                            "radar_view",
                            "notepad_notes",
                            "telemetry_dashboard",
                            "youtube_feed"
                        ]
                    }
                }
            }
        },
        {
            "id": "radar_view",
            "component": {
                "gdm-radar-view": {
                    "flights": flights_data,
                    "lockedCallsign": "AFR012",
                    "zoom": 12.0
                }
            }
        },
        {
            "id": "notepad_notes",
            "component": {
                "gdm-notepad": {
                    "content": "### Collaborative Agent Notes\n\n1. **Dynamic Overlays:** Standard-compliant A2UI composite rendering active.\n2. **Live Telemetry:** Real-time system performance and metric feeds active.\n3. **Canvas State:** Multi-agent workspace synchronization verified."
                }
            }
        },
        {
            "id": "telemetry_dashboard",
            "component": {
                "gdm-telemetry-dashboard": {
                    "tabs": TABS_CONFIG,
                    "activeTabId": "stk",
                    "title": "⚡ Real-Time Systems & Megatech Dashboard",
                    "metrics": [
                        {"label": f"NVDA ({'+' if nvda_c >= 0 else ''}{nvda_c:.2f}%)", "value": f"${nvda_p:.2f} {'▲' if nvda_c >= 0 else '▼'}", "color": "#00ff88" if nvda_c >= 0 else "#ff3b30"},
                        {"label": f"MSFT ({'+' if msft_c >= 0 else ''}{msft_c:.2f}%)", "value": f"${msft_p:.2f} {'▲' if msft_c >= 0 else '▼'}", "color": "#00f2ff" if msft_c >= 0 else "#ff3b30"},
                        {"label": f"GOOG ({'+' if goog_c >= 0 else ''}{goog_c:.2f}%)", "value": f"${goog_p:.2f} {'▲' if goog_c >= 0 else '▼'}", "color": "#ff2af2" if goog_c >= 0 else "#ff3b30"},
                        {"label": f"CAP.PA ({'+' if cap_c >= 0 else ''}{cap_c:.2f}%)", "value": f"€{cap_p:.2f} {'▲' if cap_c >= 0 else '▼'}", "color": "#00f2ff" if cap_c >= 0 else "#ff3b30"},
                        {"label": "AMZN (+1.10%)", "value": "$180.20 ▲", "color": "#00ffaa"},
                        {"label": "TSLA (-1.85%)", "value": "$175.40 ▼", "color": "#ff3b30"}
                    ],
                    "chartData": stock_chart[-15:],
                    "viewType": "both"
                }
            }
        },
        {
            "id": "youtube_feed",
            "component": {
                "gdm-video-panel": {
                    "src": "https://youtu.be/LWGJA9i18Co",
                    "autoplay": True,
                    "panel": 4
                }
            }
        }
    ]

async def main():
    print_banner()
    
    async with httpx.AsyncClient(timeout=30) as client:
        space_id = os.environ.get("MEET_SPACE_ID")
        if not space_id:
            space_id = await get_active_space(client)
            
        print(f"  {CLR_MUTED}Active Meet Space:{CLR_RESET} {CLR_SUCCESS}{space_id}{CLR_RESET}")
        print(f"  {CLR_MUTED}Broadcasting sequences in 1s...{CLR_RESET}\n")
        await asyncio.sleep(1)

        # ───────────────────────────────────────────────────────────
        # Phase 0: Standby Countdown Slate
        # ───────────────────────────────────────────────────────────
        print(f"{CLR_ACCENT}[PHASE 0] RENDER INTERMISSION STANDBY COUNTDOWN SLATE{CLR_RESET}")
        
        await call_mcp_tool(client, "render_stage", {
            "space_id": space_id,
            "surfaceUpdate": {
                "components": [
                    {
                        "id": "countdown_slate",
                        "component": {
                            "gdm-standby-slate": {
                                "badge": "STUDIO INTERMISSION",
                                "title": "Model Context Protocol x Google A2UI v0.8",
                                "description": "True agent-driven layout composition and canvas orchestration",
                                "seconds": 5,
                                "active": True
                            }
                        }
                    }
                ]
            },
            "root": "countdown_slate"
        })
        print(f"  {CLR_MUTED}Waiting 5s for countdown to finish...{CLR_RESET}")
        await asyncio.sleep(5)

        # ───────────────────────────────────────────────────────────
        # Phase 1: Single Panel with Lower-Third Chyron
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_ACCENT}[PHASE 1] SINGLE PANEL MODE WITH LOWER-THIRD CHYRON OVERLAY{CLR_RESET}")
        
        await call_mcp_tool(client, "render_stage", {
            "space_id": space_id,
            "surfaceUpdate": {
                "components": [
                    {
                        "id": "single_layout",
                        "component": {
                            "gdm-stage-grid": {
                                "layout": "single",
                                "children": {
                                    "explicitList": ["feature_card", "presenter_chyron"]
                                }
                            }
                        }
                    },
                    {
                        "id": "feature_card",
                        "component": {
                            "gdm-image-panel": {
                                "src": "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1200&auto=format&fit=crop&q=80",
                                "label": "🎨 1. Seamless Grid Layout Orchestration"
                            }
                        }
                    },
                    {
                        "id": "presenter_chyron",
                        "component": {
                            "gdm-chyron": {
                                "title": "Gemini AI Concierge",
                                "subtitle": "Streaming stage modifications live via MCP",
                                "active": True
                            }
                        }
                    }
                ]
            },
            "root": "single_layout"
        })
        await say_caption(client, space_id, "Meet the Gemini Agent Architect — a live Google Meet add-on that drives the meeting main stage.", root="single_layout")
        await asyncio.sleep(4)

        # ───────────────────────────────────────────────────────────
        # Phase 2: Split Screen Layout (Image + Notepad)
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_ACCENT}[PHASE 2] SPLIT SCREEN LAYOUT (IMAGE & NOTEPAD PANEL){CLR_RESET}")
        
        await call_mcp_tool(client, "render_stage", {
            "space_id": space_id,
            "surfaceUpdate": {
                "components": [
                    {
                        "id": "split_layout",
                        "component": {
                            "gdm-stage-grid": {
                                "layout": "split",
                                "children": {
                                    "explicitList": ["vector_artwork", "notepad_notes"]
                                }
                            }
                        }
                    },
                    {
                        "id": "vector_artwork",
                        "component": {
                            "gdm-image-panel": {
                                "src": "/workspace_sketch.png",
                                "label": "✍️ Cozy Pencil Sketches"
                            }
                        }
                    },
                    {
                        "id": "notepad_notes",
                        "component": {
                            "gdm-notepad": {
                                "content": "### Collaborative Agent Notes\n\n1. **Unified Schema:** Circular dependencies resolved cleanly.\n2. **Protocol Parity:** Live MCP client synchronizing seamlessly.\n3. **Client Autonomy:** Dynamic state-bindings active."
                            }
                        }
                    }
                ]
            },
            "root": "split_layout"
        })
        await say_caption(client, space_id, "Under A2UI, the stage seamlessly partitions — here a split view pairing visuals with a shared collaborative notepad.", root="split_layout")
        await asyncio.sleep(4)

        # ───────────────────────────────────────────────────────────
        # Phase 3: Telemetry Dashboard with Stock Price Ticker, YouTube, and Flight Radar Grid
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_ACCENT}[PHASE 3] REAL-TIME TELEMETRY STREAMING & FLIGHT RADAR GRID{CLR_RESET}")
        
        TABS_CONFIG = [
            {"id": "stk", "label": "📈 STOCKS"},
            {"id": "pwr", "label": "🚲 TOULOUSE BIKES"},
            {"id": "ac",  "label": "🚄 METRO / TRAFFIC"}
        ]
        
        stock_chart = [40, 42, 41, 44, 43, 46, 45, 48, 47, 49, 50, 49, 51, 52, 53]
        
        # Top ticker = a genuine short scrolling market/live feed (NOT captions).
        # Captions are composed separately via the first-class gdm-captions overlay (see say_caption).
        ticker_comp = {
            "id": "top_ticker",
            "component": {
                "gdm-ticker": {
                    "text": "🚀 AEROSPACE LIVE: Airbus A350-1000 flight test over Toulouse nominal • SatLink 5G constellation deployment 85% complete • 📈 STOCKS: NVDA ▲ $914.85 • MSFT ▼ $421.90 • GOOG ▲ $173.50 • CAP.PA ▲ €212.40 • 🚲 Vélô Toulouse: 1,420 bikes available • Metro Line B: 2min wait • ⚡ A2UI Stage Orchestration Active",
                    "badgeText": "GLOBAL FEED",
                    "active": True
                }
            }
        }
        
        print(f"  {CLR_MUTED}Streaming live price ticks to telemetry component (5 ticks)...{CLR_RESET}")
        for tick in range(5):
            nvda_p, nvda_c = await get_live_stock_price(client, "NVDA")
            msft_p, msft_c = await get_live_stock_price(client, "MSFT")
            goog_p, goog_c = await get_live_stock_price(client, "GOOG")
            cap_p, cap_c = await get_live_stock_price(client, "CAP.PA")
            stock_chart.append(int(max(10, min(95, 50 + nvda_c * 10))))
 
            grid_comps = make_grid_components(
                nvda_p, nvda_c,
                msft_p, msft_c,
                goog_p, goog_c,
                cap_p, cap_c,
                stock_chart, TABS_CONFIG, focused_panel=4 if tick >= 2 else 0
            )

            await call_mcp_tool(client, "render_stage", {
                "space_id": space_id,
                "surfaceUpdate": {
                    "components": grid_comps + [ticker_comp]
                },
                "root": "grid_layout"
            })
            # Caption points fire only after the grid is on stage (root must
            # exist in the engine buffer before the caption-only overlay render).
            if tick == 0:
                await say_caption(client, space_id, "Use Case 1: AI & Megatech Stocks — streaming live price feeds for Nvidia, Microsoft and Google.", root="grid_layout")
            elif tick == 2:
                await say_caption(client, space_id, "Tap the dashboard tabs to swap use cases — Toulouse bike-share or live metro and traffic.", root="grid_layout")
            await asyncio.sleep(2.0)

        # ───────────────────────────────────────────────────────────
        # Phase 4: Slide-in Live Interactive Audience Poll
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_ACCENT}[PHASE 4] LIVE INTERACTIVE AUDIENCE POLL OVERLAY{CLR_RESET}")
        
        votes = [
            [5, 2, 4, 3],
            [12, 6, 11, 8],
            [25, 14, 21, 18],
            [41, 23, 35, 30]
        ]
        
        print(f"  {CLR_MUTED}Broadcasting slide-in interactive poll and accumulating votes...{CLR_RESET}")
        await say_caption(client, space_id, "Now a live audience poll — votes tally on stage in real time.", root="grid_layout")
        await asyncio.sleep(1.5)
        for current_votes in votes:
            grid_comps = make_grid_components(
                nvda_p, nvda_c,
                msft_p, msft_c,
                goog_p, goog_c,
                cap_p, cap_c,
                stock_chart, TABS_CONFIG, focused_panel=4
            )
            poll_comp = {
                "id": "poll_overlay",
                "component": {
                    "gdm-poll-overlay": {
                        "question": "Which A2UI feature is your favorite? 🗳️",
                        "options": [
                            "1️⃣ Dynamic layouts",
                            "2️⃣ Interactive overlays",
                            "3️⃣ Real-time telemetry",
                            "4️⃣ Agent-to-Agent syncing"
                        ],
                        "active": True,
                        "values": current_votes
                    }
                }
            }
            await call_mcp_tool(client, "render_stage", {
                "space_id": space_id,
                "surfaceUpdate": {
                    "components": grid_comps + [poll_comp, ticker_comp]
                },
                "root": "grid_layout"
            })
            await asyncio.sleep(1.0)
            
        await asyncio.sleep(2)
 
        # ───────────────────────────────────────────────────────────
        # Phase 5: Live Audience Reactions — its own clean scene
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_ACCENT}[PHASE 5] LIVE AUDIENCE REACTIONS (DEDICATED SCENE){CLR_RESET}")

        # Clear the finance grid first. The A2UI engine auto-renders overlay
        # components (ticker, poll, chat cards) that linger in its buffer until a
        # deleteSurface, so without this the chat cards cascade ON TOP of the grid
        # and block the dashboard. A clean clear gives chat its own stage.
        print(f"  {CLR_MUTED}Clearing finance grid before the reactions scene...{CLR_RESET}")
        await call_mcp_tool(client, "clear_stage", {"space_id": space_id})
        await asyncio.sleep(1.2)

        chats = [
            ("Alice", "The Flight Radar ✈️ component adds so much visual depth!"),
            ("Bob", "Real-time stock ticker updates and bottom captions look amazing!"),
            ("Charlie", "Google Meet main stage completely driven by AI agents with a beautiful layout.")
        ]

        # Calm single-panel backdrop so the cascading chat cards read as a
        # deliberate "reactions" scene rather than floating over a busy grid.
        backdrop = [
            {
                "id": "reactions_layout",
                "component": {
                    "gdm-stage-grid": {
                        "layout": "single",
                        "children": {"explicitList": ["reactions_bg", "reactions_chyron"]}
                    }
                }
            },
            {
                "id": "reactions_bg",
                "component": {
                    "gdm-image-panel": {
                        "src": "https://images.unsplash.com/photo-1521737604893-d14cc237f11d?w=1200&auto=format&fit=crop&q=80",
                        "label": "💬 Live Audience Reactions"
                    }
                }
            },
            {
                "id": "reactions_chyron",
                "component": {
                    "gdm-chyron": {
                        "title": "Live Audience Reactions",
                        "subtitle": "Real-time chat cascading onto the main stage",
                        "active": True
                    }
                }
            }
        ]

        active_chats = []
        for idx, (sender, text) in enumerate(chats, 1):
            print(f"  {CLR_MUTED}Cascading chat card {idx} onto the clean stage...{CLR_RESET}")
            chat_comp = {
                "id": f"chat_{idx}",
                "component": {"gdm-chat-card": {"sender": sender, "text": text}}
            }
            active_chats.append(chat_comp)
            await call_mcp_tool(client, "render_stage", {
                "space_id": space_id,
                "surfaceUpdate": {"components": backdrop + active_chats},
                "root": "reactions_layout"
            })
            if idx == 1:
                await say_caption(client, space_id, "And live reactions cascade in from the audience.", root="reactions_layout")
            await asyncio.sleep(2.0)

        await asyncio.sleep(2)

        # ───────────────────────────────────────────────────────────
        # Phase 6: Clean close
        # ───────────────────────────────────────────────────────────
        print(f"\n{CLR_ACCENT}[PHASE 6] CLEAN CLOSE{CLR_RESET}")
        print(f"  {CLR_MUTED}Clearing reactions scene...{CLR_RESET}")
        await call_mcp_tool(client, "clear_stage", {"space_id": space_id})
        await asyncio.sleep(1.0)

        print(f"  {CLR_MUTED}Showing closing card...{CLR_RESET}")
        await call_mcp_tool(client, "render_stage", {
            "space_id": space_id,
            "surfaceUpdate": {
                "components": [
                    {
                        "id": "closing_card",
                        "component": {
                            "gdm-stage-card": {
                                "title": "🎉 Gemini Agent Architect",
                                "text": "Live, agent-driven main-stage composition via Model Context Protocol & Google A2UI v0.8.",
                                "accent": "primary"
                            }
                        }
                    }
                ]
            },
            "root": "closing_card"
        })
        print(f"  {CLR_MUTED}Holding closing card for 10s (Ctrl+C to exit early)...{CLR_RESET}")
        await asyncio.sleep(10)

        print(f"\n{CLR_ACCENT}[RESET] CLEAR STAGE BACK TO DEFAULT{CLR_RESET}")
        await call_mcp_tool(client, "clear_stage", {"space_id": space_id})

    print(f"\n{CLR_SUCCESS}🎉 Ultra Premium A2UI MCP Interactive Showcase completed successfully!{CLR_RESET}\n")

if __name__ == "__main__":
    asyncio.run(main())
