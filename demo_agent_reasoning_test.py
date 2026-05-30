#!/usr/bin/env python3
"""
Meet Live Concierge — Live Agentic Reasoning Test (Vertex AI Mode)
===================================================================
This script bridges deterministic execution and live agentic reasoning.
Instead of pre-programming the sequence, it gives a broad natural-language
instruction to Gemini 2.5 Flash on Vertex AI, equips it with the actual layout/drawing
tools, and lets the LLM dynamically decide how, when, and with what parameters
to orchestrate your live Google Meet stage.
"""
import os
import sys
import time
import httpx
from google import genai
from google.genai import types

API_URL = os.environ.get("CONCIERGE_API_URL", "CONCIERGE_API_URL_PLACEHOLDER")
KEY = os.environ.get("STAGE_API_KEY") or exit("STAGE_API_KEY required — export it before running this script")
PROJECT = os.environ.get("GEMINI_PROJECT") or exit("GEMINI_PROJECT required — export it before running this script")
LOCATION = os.environ.get("REGION", "us-central1")

def get_active_space() -> str:
    headers = {"Authorization": f"Bearer {KEY}"} if KEY else {}
    try:
        resp = httpx.get(f"{API_URL}/api/dev/sessions", headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        sessions = data.get("active_sessions", [])
        return sessions[0] if sessions else ""
    except Exception as e:
        print(f"⚠️ Error detecting session: {e}")
        return ""

# ───────────────────────────────────────────────────────────
# Real Orchestration Tools exposed to Gemini (Synchronous for automatic calling)
# ───────────────────────────────────────────────────────────
def trigger_standby(seconds: int, title: str, description: str):
    """Activates the intermission/standby countdown slate with custom title/desc."""
    space = get_active_space()
    print(f"🛠️ [Tool Executed] trigger_standby({seconds}s, '{title}')")
    with httpx.Client() as client:
        client.post(f"{API_URL}/api/standby/{space}", headers={"Authorization": f"Bearer {KEY}"}, json={
            "active": True, "duration": 0, "seconds": seconds, "badge": "AI ORCHESTRATION",
            "title": title, "description": description
        })
    time.sleep(seconds) # Let the countdown finish
    with httpx.Client() as client:
        client.post(f"{API_URL}/api/standby/{space}", headers={"Authorization": f"Bearer {KEY}"}, json={"active": False})

def set_panel_content(panel: int, source: str, label: str, layout: str = "grid", autoplay: bool = False):
    """Sets the media source, image URL, or video stream for a specific quadrant/panel on the grid."""
    space = get_active_space()
    print(f"🛠️ [Tool Executed] set_panel_content(panel={panel}, source='{source}', autoplay={autoplay})")
    payload = {
        "space_id": space, "prompt": source, "panel": panel, "image_layout": layout, "label": label
    }
    if autoplay:
        payload["autoplay"] = True
    with httpx.Client() as client:
        client.post(f"{API_URL}/api/image", headers={"Authorization": f"Bearer {KEY}"}, json=payload)

def draw_on_canvas(action: str, x: int, y: int, extra: int, color: str):
    """Draws a vector shape ('rect' or 'circle') over the active stage canvas."""
    space = get_active_space()
    print(f"🛠️ [Tool Executed] draw_on_canvas({action} at x={x}, y={y})")
    payload = {"action": action, "x": x, "y": y, "color": color}
    if action == "rect":
        payload["w"] = extra
        payload["h"] = extra
    else:
        payload["r"] = extra
    with httpx.Client() as client:
        client.post(f"{API_URL}/api/draw/{space}", headers={"Authorization": f"Bearer {KEY}"}, json=payload)

def focus_panel(panel: int):
    """Directs the active speaker highlight and zoom to a specific panel (1-4)."""
    space = get_active_space()
    print(f"🛠️ [Tool Executed] focus_panel({panel})")
    with httpx.Client() as client:
        client.post(f"{API_URL}/api/focus-panel/{space}", headers={"Authorization": f"Bearer {KEY}"}, json={"panel": panel})

def send_emoji_burst(emojis: list):
    """Launches floating emoji reactions rising up from the bottom of the screen."""
    space = get_active_space()
    print(f"🛠️ [Tool Executed] send_emoji_burst({emojis})")
    with httpx.Client() as client:
        for emoji in emojis:
            client.post(f"{API_URL}/api/sound-event/{space}", headers={"Authorization": f"Bearer {KEY}"}, json={
                "emoji": emoji, "repeat": 2
            })

# ───────────────────────────────────────────────────────────
# LLM Orchestrator Driver Loop
# ───────────────────────────────────────────────────────────
def run_agent_test():
    space = get_active_space()
    if not space:
        print("❌ Error: No active Meet space detected. Launch the side-panel first.")
        sys.exit(1)

    print(f"\n🧠 Starting Live Gemini Agent Test (Vertex AI Mode) on Space: {space}")
    print(f"🏢 GCP Project: {PROJECT} | Region: {LOCATION}")
    print("=" * 70)

    # Initialize Google GenAI client configured for Vertex AI backend
    client = genai.Client(
        vertexai=True,
        project=PROJECT,
        location=LOCATION
    )
    
    # Define mapping of tool names to functions
    tools_map = {
        "trigger_standby": trigger_standby,
        "set_panel_content": set_panel_content,
        "draw_on_canvas": draw_on_canvas,
        "focus_panel": focus_panel,
        "send_emoji_burst": send_emoji_burst,
    }

    prompt = (
        "We are running our Live AI Concierge presentation on Google Meet. "
        "I want you to autonomously orchestrate the stage layout and elements to guide our audience. "
        "Here is the plan:\n"
        "1. Start by displaying a clean 5-second Standby Countdown slate titled 'Dynamic Agent Orchestra' "
        "to let the audience warm up.\n"
        "2. Once the countdown finishes, morph the screen into a Quad-Grid layout and set up the quadrants as follows:\n"
        "   - Panel 1: Set content to our premium sidebar mockup ('/panel1_a2ui.png') labeled 'A2UI Controls'\n"
        "   - Panel 2: Set content to our coordination blueprint ('/panel2_a2a.png') labeled 'A2A Blueprint'\n"
        "   - Panel 3: Set content to our telemetry cockpit dashboard ('/cockpit_dashboard.png') labeled 'Live Telemetry'\n"
        "   - Panel 4: Set content to the autoplay video stream 'https://youtu.be/LWGJA9i18Co' and ensure it starts playing automatically (autoplay=True)\n"
        "3. Once the layout is populated, direct the focus highlight to Panel 2 (the coordination blueprint) and draw "
        "a neon green circle around the 'Gemini Reasoning Core' node (which is centered on the diagram around coordinates x=50, y=50).\n"
        "4. Finish by releasing some celebratory sparkle and brain emojis across the screen."
    )

    print("📬 Sending broad goal to Gemini 2.5 Flash on Vertex AI...")
    print(f"💬 Goal Description: \"{prompt[:120]}...\"\n")

    # Call the model with tool execution capability
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=list(tools_map.values()),
            temperature=0.1
        )
    )

    # Walk through the model's decided tool calls and execute them
    if response.function_calls:
        print("🤔 [Gemini Thought Loop]: I decided to execute the following sequence of tools to fulfill the request:")
        for call in response.function_calls:
            func_name = call.name
            func_args = call.args
            
            if func_name in tools_map:
                print(f"  👉 Decided Tool: {func_name} with arguments: {func_args}")
                # Execute the live python tool
                tools_map[func_name](**func_args)
                time.sleep(1.5) # Small buffer between steps
            else:
                print(f"  ⚠️ Unknown Tool decided by model: {func_name}")
        
        print("\n🎉 Live Gemini Agentic Orchestration completed successfully!")
    else:
        print("⚠️ Model did not decide to invoke any tools. Response:")
        print(response.text)

if __name__ == "__main__":
    run_agent_test()
