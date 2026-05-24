#!/usr/bin/env python3
"""
Meet Live Concierge — Full Feature Showcase
============================================
Auto-detects the active session and runs through all features.

The diagram is generated from the transcript lines SPOKEN in the demo —
not a pre-written description. trigger_diagram fires mid-speech using
the accumulated transcript text, just like the real Architect mode does.

Usage:
    python3 demo_showcase.py
    python3 demo_showcase.py spaces/abc123
"""
import asyncio
import httpx
import os
import sys

API_URL = os.environ.get("CONCIERGE_API_URL", "CONCIERGE_API_URL_PLACEHOLDER").rstrip("/")
MCP_URL = f"{API_URL}/mcp"
KEY = os.environ.get("STAGE_API_KEY", "")

SPACE = ""
spoken_lines: list[str] = []   # accumulates what's been "said" so far


# ── Transport ──────────────────────────────────────────────────────────────────

async def call(name: str, args: dict) -> str:
    headers = {"Content-Type": "application/json"}
    if KEY:
        headers["Authorization"] = f"Bearer {KEY}"
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(MCP_URL, headers=headers, json={
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": name, "arguments": args}
        })
        text = resp.json().get("result", {}).get("content", [{}])[0].get("text", "")
        print(f"  ✓ {name}")
        return text


async def get_active_space() -> str:
    headers = {"Authorization": f"Bearer {KEY}"} if KEY else {}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{API_URL}/api/dev/sessions", headers=headers)
        data = resp.json()
        # Prefer a space with a stage listener even if no live WS session
        listeners = data.get("stage_listeners", {})
        sessions = data.get("active_sessions", [])
        return sessions[0] if sessions else (list(listeners.keys())[0] if listeners else "")


# ── Tool helpers ───────────────────────────────────────────────────────────────

async def tx(text: str, role: str = "user", pause_ms: int = 0):
    """Send a transcript line and track it in spoken_lines."""
    spoken_lines.append(f"[{role}] {text}")
    await call("send_transcript", {
        "text": text, "space_id": SPACE,
        "role": role, "pause_before_ms": pause_ms
    })

async def emoji(e: str, repeat: int = 1):
    await call("send_emoji", {"emoji": e, "space_id": SPACE, "repeat": repeat})

async def diagram_from_transcript(style: str = "cyber"):
    """Trigger diagram from whatever has been spoken so far — no pre-canned input."""
    transcript = "\n".join(spoken_lines)
    await call("trigger_diagram", {
        "transcript": transcript,
        "space_id": SPACE,
        "style": style
    })

async def image(prompt: str):
    await call("generate_image", {"prompt": prompt, "space_id": SPACE})

async def wait(ms: int):
    await asyncio.sleep(ms / 1000)


# ── Demo ───────────────────────────────────────────────────────────────────────

async def main():
    global SPACE
    SPACE = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SPACE", "")
    if not SPACE:
        print("Auto-detecting active session...")
        SPACE = await get_active_space()
    if not SPACE:
        print("No active session found. Open a Meet call and start the add-on first.")
        sys.exit(1)

    print(f"\n🎬  SHOWCASE DEMO  →  {SPACE}\n{'─' * 52}")

    # ═══════════════════════════════════════════════════════════
    # ACT I — The Hook
    # Build up transcript context; no diagram fired yet.
    # ═══════════════════════════════════════════════════════════
    print("\n▶  ACT I — THE HOOK\n")

    await tx(
        "Good morning everyone. What you're watching right now is a Google Meet call "
        "with a live AI co-pilot built directly into the session.",
        "user", 0
    )
    await wait(3800)

    await tx(
        "The system is powered by Gemini Live 2.5 Flash — streaming audio in real time "
        "from every participant in the call via the Meet Media API.",
        "agent", 0
    )
    await wait(4000)

    await tx(
        "The side panel captures your voice, sends it as PCM audio over a WebSocket "
        "to a FastAPI backend running on Google Cloud Run.",
        "user", 2000
    )
    await wait(4000)

    await tx(
        "Gemini Live returns audio responses and live transcriptions simultaneously. "
        "That's how these captions appear with no perceptible delay.",
        "agent", 2000
    )
    await wait(4000)

    # ═══════════════════════════════════════════════════════════
    # ACT II — Emoji Reactions (keyword-triggered)
    # ═══════════════════════════════════════════════════════════
    print("\n▶  ACT II — EMOJI REACTIONS\n")

    await tx(
        "The system is also brilliant at picking up emotional context from speech.",
        "user", 2000
    )
    # "brilliant" auto-triggers 💡
    await wait(3500)

    await tx(
        "Watch what happens when I say something incredible — the backend detects "
        "trigger words in the transcript and fires reactions automatically.",
        "user", 2000
    )
    # "incredible" auto-triggers 🔥
    await wait(3500)

    await tx(
        "I love that this works for any participant — not just the presenter.",
        "user", 2000
    )
    # "love" auto-triggers 🫶
    await wait(3500)

    await emoji("👏", 3)   # direct burst on top
    await wait(1800)

    await tx(
        "You can also fire reactions via MCP — congrats to the whole team on shipping this.",
        "agent", 1500
    )
    # "congrats" auto-triggers 🎉
    await wait(3500)

    # ═══════════════════════════════════════════════════════════
    # ACT II.B — Live Comments on Main Stage
    # ═══════════════════════════════════════════════════════════
    print("\n▶  ACT II.B — LIVE COMMENTS ON STAGE\n")

    await tx(
        "For interactive events, it is now possible to share comments on the main stage "
        "as modern glassmorphic overlays with smooth sliding animations.",
        "user", 2000
    )
    await wait(4000)

    print("  → Firing custom live chat comment...")
    await call("send_chat_comment", {
        "space_id": SPACE,
        "sender": "Audience Member",
        "text": "wow I had no idea Google Meet was so versatile!"
    })
    await wait(5000)

    # ═══════════════════════════════════════════════════════════
    # ACT III — Live Architecture Diagram
    # Fire trigger_diagram NOW using only what's been spoken above.
    # Gemini Flash reads the real transcript — no pre-written input.
    # ═══════════════════════════════════════════════════════════
    print("\n▶  ACT III — DIAGRAM FROM LIVE TRANSCRIPT\n")

    await tx(
        "Now let's push things further. We're going to generate an architecture diagram — "
        "not from a pre-written description, but from this conversation.",
        "user", 2000
    )
    await wait(3500)

    await tx(
        "Gemini Flash will read everything said so far — the Media API, FastAPI, "
        "Cloud Run, WebSocket — and map it into a live D2 diagram on the stage.",
        "agent", 2000
    )
    await wait(3500)

    # *** Diagram fires from the real accumulated transcript ***
    print("  → Firing diagram from live transcript...")
    await diagram_from_transcript(style="cyber")

    await tx(
        "The diagram is generating now. No slides, no Visio. "
        "Just the architecture as it was described in this room.",
        "user", 2000
    )
    await wait(4500)

    await tx(
        "Every node and data flow you see was inferred purely from the words spoken in this meeting.",
        "agent", 2000
    )
    await wait(4500)

    # ═══════════════════════════════════════════════════════════
    # ACT IV — AI Image Generation
    # ═══════════════════════════════════════════════════════════
    print("\n▶  ACT IV — IMAGEN 4 LIVE\n")

    await tx(
        "One more thing. We can ask Imagen 4 to generate a visual — "
        "describe anything and it appears full-screen on the stage.",
        "user", 2000
    )
    await wait(3500)

    # Fire image — the prompt here is intentional (you're directing a visual)
    await image(
        "A photorealistic wide-angle shot of a futuristic command centre: "
        "holographic Google Meet tiles, real-time neural network activity on floating screens, "
        "glowing blue and purple ambient light, a radiant AI presence as a sphere of light. "
        "Cinematic, dramatic, 16:9."
    )

    await tx(
        "Imagen 4 is running now. The image will appear on the main stage for all participants "
        "as soon as it's ready — usually under fifteen seconds.",
        "agent", 2000
    )
    await wait(4500)

    await emoji("🔥", 2)
    await wait(1500)

    await tx(
        "An AI-generated image. Live. In a meeting. Triggered by a sentence.",
        "user", 2000
    )
    await wait(5000)

    # ═══════════════════════════════════════════════════════════
    # ACT V — The Close
    # ═══════════════════════════════════════════════════════════
    print("\n▶  ACT V — THE CLOSE\n")

    await tx(
        "Live captions from real speech. Keyword emoji reactions. "
        "Architecture diagrams built from the conversation. "
        "AI images on demand. All inside a standard Google Meet call.",
        "user", 2000
    )
    await wait(5500)

    await tx(
        "This is what meetings look like when the AI is actually in the room. "
        "Not summarising afterwards. Present. Now. Amazing.",
        "agent", 2000
    )
    # "amazing" auto-triggers 🔥
    await wait(4000)

    print("\n🎆  FINALE\n")
    await emoji("🎉", 3)
    await wait(800)
    await emoji("🔥", 2)
    await wait(700)
    await emoji("🫶", 2)
    await wait(700)
    await emoji("💡", 2)

    print(f"\n✅  Done — {SPACE}\n")


if __name__ == "__main__":
    asyncio.run(main())
