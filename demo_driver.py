#!/usr/bin/env python3
"""
Meet Remote Control CLI — Developer Driver
==========================================
Control layouts, stream terminal sessions, trigger sound effects,
generate TTS, and rollback diagrams directly from the command line.

Usage:
    python3 demo_driver.py speak "Hello World"
    python3 demo_driver.py terminal "ls -la"
    python3 demo_driver.py sound applause
    python3 demo_driver.py layout terminal
    python3 demo_driver.py rollback 1
    python3 demo_driver.py status
"""
import asyncio
import sys
import os
import argparse
import httpx

API_URL = os.environ.get("CONCIERGE_API_URL", "http://localhost:8080")
KEY = os.environ.get("STAGE_API_KEY", "")

async def get_active_space() -> str:
    headers = {"Authorization": f"Bearer {KEY}"} if KEY else {}
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{API_URL}/api/dev/sessions", headers=headers)
            resp.raise_for_status()
            data = resp.json()
            listeners = data.get("stage_listeners", {})
            sessions = data.get("active_sessions", [])
            return sessions[0] if sessions else (list(listeners.keys())[0] if listeners else "")
        except Exception:
            return ""

async def post_api(endpoint: str, payload: dict) -> dict:
    headers = {"Content-Type": "application/json"}
    if KEY:
        headers["Authorization"] = f"Bearer {KEY}"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(f"{API_URL}{endpoint}", headers=headers, json=payload)
        if resp.status_code != 200:
            print(f"Error ({resp.status_code}): {resp.text}", file=sys.stderr)
            resp.raise_for_status()
        return resp.json()

async def run_and_stream_terminal(space_id: str, command: str):
    print(f"🚀 Running and streaming command: {command}")
    print(f"📺 Mirroring to Meet stage in session: {space_id}\n")
    
    # Send initial command display and clear terminal stage
    await post_api(f"/api/terminal-stream/{space_id}", {"data": f"$ {command}\n", "append": False})
    
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    async def read_stream(stream, is_stderr=False):
        while True:
            line = await stream.readline()
            if not line:
                break
            decoded = line.decode('utf-8', errors='replace')
            # Stream line-by-line to WebSocket
            await post_api(f"/api/terminal-stream/{space_id}", {"data": decoded, "append": True})
            # Local mirror echo
            sys.stdout.write(decoded)
            sys.stdout.flush()
            
    await asyncio.gather(
        read_stream(process.stdout),
        read_stream(process.stderr, is_stderr=True)
    )
    await process.wait()
    await post_api(f"/api/terminal-stream/{space_id}", {"data": f"\n[Process completed with exit code {process.returncode}]\n", "append": True})

async def main():
    global API_URL
    parser = argparse.ArgumentParser(description="Meet Concierge Remote Control Driver CLI")
    parser.add_argument("--space", help="Target Meet space (e.g. spaces/gMbhferA31YB). Auto-detected if not specified.")
    parser.add_argument("--api-url", default=API_URL, help=f"FastAPI backend URL. Default: {API_URL}")
    
    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommands")
    
    # speak
    p_speak = subparsers.add_parser("speak", help="Synthesize on-demand speech via Kore voice")
    p_speak.add_argument("text", help="Text to speak")
    p_speak.add_argument("--voice", help="Specific speaker voice preset")
    
    # terminal
    p_term = subparsers.add_parser("terminal", help="Run local command and stream stdout/stderr live to stage")
    p_term.add_argument("cmd", help="Local shell command to run and stream")
    
    # sound
    p_sound = subparsers.add_parser("sound", help="Trigger synthesized soundboard preset")
    p_sound.add_argument("name", choices=["applause", "drumroll", "buzzer", "chimes", "ding"], help="Preset sound effect")
    
    # layout
    p_layout = subparsers.add_parser("layout", help="Switch stage layouts/views")
    p_layout.add_argument("view", choices=["placeholder", "doc", "diagram", "browser", "image", "video", "terminal", "notepad"], help="View to display")
    
    # pointer
    p_pointer = subparsers.add_parser("pointer", help="Trigger laser pointer coordinates on the stage")
    p_pointer.add_argument("x", type=float, help="X coordinate percentage (0-100)")
    p_pointer.add_argument("y", type=float, help="Y coordinate percentage (0-100)")
    
    # draw
    p_draw = subparsers.add_parser("draw", help="Render drawings on the stage canvas overlay")
    p_draw.add_argument("action", choices=["line", "rect", "text", "clear"], help="Drawing action")
    p_draw.add_argument("--x1", type=float, help="Start X percentage")
    p_draw.add_argument("--y1", type=float, help="Start Y percentage")
    p_draw.add_argument("--x2", type=float, help="End X percentage")
    p_draw.add_argument("--y2", type=float, help="End Y percentage")
    p_draw.add_argument("--x", type=float, help="X percentage for rect/text")
    p_draw.add_argument("--y", type=float, help="Y percentage for rect/text")
    p_draw.add_argument("--w", type=float, help="Width percentage for rect")
    p_draw.add_argument("--h", type=float, help="Height percentage for rect")
    p_draw.add_argument("--text", help="Text contents")
    p_draw.add_argument("--color", default="#ff003c", help="Color code")
    
    # notepad
    p_note = subparsers.add_parser("notepad", help="Update the collaborative live notepad")
    p_note.add_argument("action", choices=["overwrite", "append"], help="Action on notepad")
    p_note.add_argument("text", help="Text contents (markdown supported)")
    
    # layout-config
    p_layout_conf = subparsers.add_parser("layout-config", help="Set split/grid layout style")
    p_layout_conf.add_argument("layout", choices=["single", "split", "grid"], help="Layout style name")
    
    # theme-config
    p_theme_conf = subparsers.add_parser("theme-config", help="Set stage color/style theme")
    p_theme_conf.add_argument("theme", choices=["cyberpunk", "glassmorphism", "darkflow", "light"], help="Theme schema name")

    # rollback
    p_rollback = subparsers.add_parser("rollback", help="Roll back diagram to previous version")
    p_rollback.add_argument("steps", nargs="?", type=int, default=1, help="Steps to roll back (default: 1)")
    p_rollback.add_argument("--version", type=int, help="Rollback directly to a specific absolute version ID")
    
    # status
    subparsers.add_parser("status", help="Display real-time Meet Main Stage status dashboard")
    
    args = parser.parse_args()
    
    API_URL = args.api_url
    
    space = args.space or os.environ.get("SPACE", "")
    if not space:
        space = await get_active_space()
        
    if not space:
        print("❌ Error: No active Meet space detected. Ensure the side panel and stage are connected, or pass --space explicitly.", file=sys.stderr)
        sys.exit(1)
        
    if args.command == "speak":
        payload = {"text": args.text}
        if args.voice:
            payload["voice"] = args.voice
        print(f"🗣️  Generating TTS: '{args.text}'")
        res = await post_api(f"/api/speak/{space}", payload)
        print("✓ Audio broadcasted and injected.")
        
    elif args.command == "terminal":
        await run_and_stream_terminal(space, args.cmd)
        
    elif args.command == "sound":
        print(f"🎵 Triggering soundboard effect: {args.name}")
        await post_api(f"/api/sound-event/{space}", {"sound": args.name})
        print("✓ Trigger sent.")
        
    elif args.command == "layout":
        print(f"🖥️  Switching layout view to: {args.view}")
        await post_api(f"/api/layout/{space}", {"view": args.view})
        print("✓ View swapped.")
        
    elif args.command == "pointer":
        print(f"🔴 Moving laser pointer to ({args.x}%, {args.y}%)")
        await post_api(f"/api/pointer/{space}", {"x": args.x, "y": args.y})
        print("✓ Pointer event sent.")
        
    elif args.command == "draw":
        print(f"🎨 Canvas drawing: action={args.action}")
        payload = {"action": args.action, "color": args.color}
        if args.x1 is not None: payload["x1"] = args.x1
        if args.y1 is not None: payload["y1"] = args.y1
        if args.x2 is not None: payload["x2"] = args.x2
        if args.y2 is not None: payload["y2"] = args.y2
        if args.x is not None: payload["x"] = args.x
        if args.y is not None: payload["y"] = args.y
        if args.w is not None: payload["w"] = args.w
        if args.h is not None: payload["h"] = args.h
        if args.text is not None: payload["text"] = args.text
        await post_api(f"/api/draw/{space}", payload)
        print("✓ Draw event sent.")
        
    elif args.command == "notepad":
        print(f"📝 Updating live notepad: action={args.action}")
        await post_api(f"/api/notepad/{space}", {"action": args.action, "text": args.text})
        print("✓ Notepad updated.")
        
    elif args.command == "layout-config":
        print(f"📐 Adjusting grid layout to: {args.layout}")
        await post_api(f"/api/layout-config/{space}", {"layout": args.layout})
        print("✓ Layout configuration sent.")
        
    elif args.command == "theme-config":
        print(f"✨ Changing color theme to: {args.theme}")
        await post_api(f"/api/theme-config/{space}", {"theme": args.theme})
        print("✓ Theme configuration sent.")
        
    elif args.command == "rollback":
        payload = {}
        if args.version is not None:
            payload["version"] = args.version
            print(f"⏳ Rolling back diagram in {space} to absolute version {args.version}...")
        else:
            payload["steps"] = args.steps
            print(f"⏳ Rolling back diagram in {space} by {args.steps} steps...")
            
        res = await post_api(f"/api/diagram/{space}/rollback", payload)
        print(f"✓ Diagram successfully rolled back to Version {res['rolled_to']} ('{res['title']}')")
        
    elif args.command == "status":
        headers = {"Authorization": f"Bearer {KEY}"} if KEY else {}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{API_URL}/api/stage-state/{space}", headers=headers)
            if resp.status_code == 200:
                s = resp.json()
                print(f"\n📊 MEET LIVE CONCIERGE — STAGE DASHBOARD")
                print(f"=================================================")
                print(f"📍 Active Space:    {s['space_id']}")
                print(f"👥 Listener Count: {s['listeners_count']} browser(s)")
                print(f"📺 Active View:     {s['active_view'].upper()}")
                print(f"🎙️  Gemini Session:  {'ACTIVE' if s['session_active'] else 'INACTIVE'}")
                print(f"🔇 Audio Output:    {'MUTED (Automated narration)' if s['audio_muted'] else 'UNMUTED (Interactive mode)'}")
                print(f"📐 Diagram Title:   {s['active_diagram_title'] or 'None'}")
                print(f"🔄 Diagram Version: V{s['active_diagram_version']}")
                print(f"🎬 Video Queue:     {s['video_queue_length']} video(s) in queue")
                print(f"=================================================\n")
            else:
                print(f"Failed to query status ({resp.status_code}): {resp.text}", file=sys.stderr)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 CLI session terminated.")
        sys.exit(0)
