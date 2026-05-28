#!/usr/bin/env python3
"""
Meet Live Concierge — "Google Meet Kicks Ass" Flip-Slate Showcase
==============================================================
Drives the new `gdm-flip-slate` element: a luxury cyber-mechanical split-flap
letter board that animates characters sequentially to spell "GOOGLE MEET KICKS ASS".

Environment Variables:
    CONCIERGE_API_URL: Target FastAPI backend URL.
    STAGE_API_KEY: Secure authorization token.
    MEET_SPACE_ID: Force target Google Meet space.
"""

import asyncio
import os
import sys
import glob
import httpx

# --- Virtualenv Auto-Resolution ---
_base_dir = os.path.dirname(os.path.abspath(__file__))
_venv_dirs = glob.glob(os.path.join(_base_dir, "venv", "lib", "python3.*", "site-packages"))
for _vd in _venv_dirs:
    if _vd not in sys.path:
        sys.path.insert(0, _vd)

# --- Configuration & Environment Setup ---
API_URL = os.environ.get("CONCIERGE_API_URL", "http://127.0.0.1:8085")
KEY = os.environ.get("STAGE_API_KEY", "meet-live_STAGE_SECURE_v1_zG9fN8qL7vP2mX6tY9wK4jC5bS8xQ7hZ3uW0rA")

# --- ANSI Terminal Colors ---
CLR_CYAN = "\033[38;5;51m"
CLR_MAGENTA = "\033[38;5;201m"
CLR_GREEN = "\033[38;5;82m"
CLR_YELLOW = "\033[38;5;220m"
CLR_SLATE = "\033[38;5;244m"
CLR_RESET = "\033[0m"


async def get_active_space(client: httpx.AsyncClient) -> str:
    headers = {"Authorization": f"Bearer {KEY}"} if KEY else {}
    try:
        resp = await client.get(f"{API_URL}/api/dev/sessions", headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        listeners = data.get("stage_listeners", {})
        sessions = data.get("active_sessions", [])
        return sessions[0] if sessions else (list(listeners.keys())[0] if listeners else "")
    except Exception:
        return ""


async def post_endpoint(client: httpx.AsyncClient, endpoint: str, payload: dict):
    headers = {"Content-Type": "application/json"}
    if KEY:
        headers["Authorization"] = f"Bearer {KEY}"
    try:
        resp = await client.post(f"{API_URL}{endpoint}", headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  {CLR_MAGENTA}⚠️ Error calling {endpoint}: {e}{CLR_RESET}", file=sys.stderr)


async def render_stage_api(client: httpx.AsyncClient, space_id: str, components: list[dict], root_id: str = None):
    payload = {"surfaceUpdate": {"components": components}}
    if root_id:
        payload["root"] = root_id
    await post_endpoint(client, f"/api/render-stage/{space_id}", payload)


async def set_transcript(client: httpx.AsyncClient, space_id: str, text: str, label: str = "Presentation Desk"):
    await post_endpoint(client, f"/api/transcript/{space_id}", {
        "role": "agent", "label": label, "text": text, "is_final": True,
    })


async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        space = os.environ.get("MEET_SPACE_ID") or await get_active_space(client)
        if not space:
            print(f"\n{CLR_MAGENTA}❌ No active Meet space detected. Open a Meet call first.{CLR_RESET}\n")
            sys.exit(1)

        print(f"\n{CLR_CYAN}  ==============================================================={CLR_RESET}")
        print(f"{CLR_CYAN}  📟   S P L I T - F L A P   K I C K S   A S S   S H O W C A S E   ▲{CLR_RESET}")
        print(f"{CLR_CYAN}  ==============================================================={CLR_RESET}")
        print(f"  {CLR_SLATE}Active Meeting Space:{CLR_RESET} {CLR_CYAN}{space}{CLR_RESET}")
        print(f"  {CLR_SLATE}Component:{CLR_RESET} {CLR_CYAN}gdm-flip-slate (Mechanical presentation matrix){CLR_RESET}\n")

        # Phase 0 — triggering audio & slate
        print(f"{CLR_CYAN}🎬 [Phase 0] Initializing Mechanical Flipping Display...{CLR_RESET}")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "sonar"})
        
        # Prepare components
        slate_comp = {
            "id": "flip_slate_main",
            "component": {
                "gdm-flip-slate": {
                    "text": "GOOGLE MEET KICKS ASS",
                    "active": True,
                    "badgeText": "A2UI ULTIMATE SHOWCASE",
                    "subtitle": "INTELLIGENT FLIGHT-BOARD SIMULATION",
                    "accentColor": "#00f2ff",
                    "delayMs": 100
                }
            }
        }

        # Render stage
        print(f"{CLR_CYAN}🎬 [Phase 1] Flapping message onto stage: 'GOOGLE MEET KICKS ASS'...{CLR_RESET}")
        await set_transcript(
            client, space,
            "Activating the high-fidelity Split-Flap mechanical board. Spell sequence initialized.",
            label="Presentation Desk"
        )
        await render_stage_api(client, space, [slate_comp], root_id="flip_slate_main")

        # Leave it active so user can enjoy the 3D hover tracking
        print(f"  💖 Board is now LIVE on stage!")
        await asyncio.sleep(4.0)

        # Trigger applause and reaction emojis
        print(f"🎬 [Phase 2] Triggering interactive chat reactions...")
        await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "applause"})
        
        for sender, text in [
            ("Alex (Product)", "Incredible mechanical action! The character staggered delay feels so organic. 🤯"),
            ("Sophia (UX)", "The subtle 3D hover parallax tilt and specular glass glow on that split-flap board are breathtaking!"),
        ]:
            await post_endpoint(client, f"/api/chat/{space}", {"sender": sender, "text": text})
            await asyncio.sleep(1.5)

        for emo in ["🎉", "✨", "👏", "🔥", "🚀"]:
            await post_endpoint(client, f"/api/emoji/{space}", {"emoji": emo})
            await asyncio.sleep(0.1)

        print(f"\n{CLR_GREEN}🎉 Split-flap showcase executed successfully!{CLR_RESET}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{CLR_MAGENTA}Showcase interrupted.{CLR_RESET}")
        sys.exit(0)
