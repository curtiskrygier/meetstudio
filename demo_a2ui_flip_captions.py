#!/usr/bin/env python3
"""
Meet Live Concierge — Configurable Flip Captions Showcase
======================================================
Drives the upgraded `gdm-captions` lower-third overlay, showing both the standard 
minimalist glassmorphic styling and the premium micro mechanical split-flap style on the fly.

Usage:
    python3 demo_a2ui_flip_captions.py

Environment Variables:
    FLIP_STYLE: Set to "true" or "false" to force a specific mode. Otherwise,
                the demo automatically alternates styles to showcase configuration.
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
FORCE_FLIP = os.environ.get("FLIP_STYLE", "").lower()

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


async def render_stage_api(client: httpx.AsyncClient, space_id: str, components: list[dict]):
    payload = {"surfaceUpdate": {"components": components}}
    await post_endpoint(client, f"/api/render-stage/{space_id}", payload)


async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        space = os.environ.get("MEET_SPACE_ID") or await get_active_space(client)
        if not space:
            print(f"\n{CLR_MAGENTA}❌ No active Meet space detected. Open a Meet call first.{CLR_RESET}\n")
            sys.exit(1)

        print(f"\n{CLR_CYAN}  ==============================================================={CLR_RESET}")
        print(f"{CLR_CYAN}  💬   C O N F I G U R A B L E   L I V E   C A P T I O N S   ▲{CLR_RESET}")
        print(f"{CLR_CYAN}  ==============================================================={CLR_RESET}")
        print(f"  {CLR_SLATE}Active Meeting Space:{CLR_RESET} {CLR_CYAN}{space}{CLR_RESET}")
        print(f"  {CLR_SLATE}Component:{CLR_RESET} {CLR_CYAN}gdm-captions (with optional micro split-flap mode){CLR_RESET}\n")

        # Define speech sequence
        sequence = [
            ("Curtis Krygier", "Hello and welcome to Google Meet A2UI live stage session.", False),
            ("Curtis Krygier", "Today we are demonstrating live lower-third conversational captions.", False),
            ("System", "DYNAMIC STYLES SWITCH ENABLING MICRO MECHANICAL SPLIT-FLAPS...", False),
            ("Curtis Krygier", "A2UI COMPOSABLE STAGE — REALTIME, MULTI-DOMAIN", True),
            ("Curtis Krygier", "Notice how each micro card flips rapidly to reveal the spoken sentence", True),
            ("Curtis Krygier", "This creates a luxury mechanical action that remains clean and legible", True),
            ("Curtis Krygier", "We can toggle this toggleable feature on and off dynamically per speaker", True),
        ]

        # Let the user force a specific configuration via env variables if they want
        if FORCE_FLIP in ("true", "1", "yes", "on"):
            print(f"🔧 {CLR_YELLOW}Override Active: Forcing all captions into Split-Flap style{CLR_RESET}")
            sequence = [(sp, txt, True) for sp, txt, _ in sequence]
        elif FORCE_FLIP in ("false", "0", "no", "off"):
            print(f"🔧 {CLR_YELLOW}Override Active: Forcing all captions into Classic text style{CLR_RESET}")
            sequence = [(sp, txt, False) for sp, txt, _ in sequence]

        for i, (speaker, text, use_flip) in enumerate(sequence):
            style_name = "Split-Flap 📟" if use_flip else "Classic Glass 💬"
            print(f"  🗣️  [{style_name}] {speaker}: \"{text}\"")

            caption_comp = {
                "id": "lower_third_captions",
                "component": {
                    "gdm-captions": {
                        "speaker": speaker,
                        "text": text,
                        "active": True,
                        "accentColor": "#ff9f0a" if speaker == "System" else "#00f2ff",
                        "flip": use_flip
                    }
                }
            }

            await render_stage_api(client, space, [caption_comp])
            
            # Sound effects for specific events
            if speaker == "System":
                await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "sonar"})
            elif use_flip and i == 3:
                await post_endpoint(client, f"/api/sound-event/{space}", {"sound": "chimes"})

            # Adaptive delay based on sentence length
            await asyncio.sleep(max(3.0, len(text) * 0.08))

        print(f"\n{CLR_GREEN}🎉 Configurable Captions showcase executed successfully!{CLR_RESET}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{CLR_MAGENTA}Showcase interrupted.{CLR_RESET}")
        sys.exit(0)
