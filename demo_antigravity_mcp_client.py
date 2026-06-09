#!/usr/bin/env python3
"""
Antigravity MCP Interactive Client — Live Google Meet Controller

This interactive CLI client connects to your live Cloud Run Model Context Protocol
server to showcase real-time video-conference control using the MCP standard.
"""

import sys
import os
import httpx
import asyncio

# --- Environment Configurations ---
API_URL = os.environ.get("CONCIERGE_API_URL") or exit("CONCIERGE_API_URL not set — see .env.production.sample")
MCP_URL = f"{API_URL}/mcp"
KEY = os.environ.get("STAGE_API_KEY") or exit("STAGE_API_KEY required — export it before running this script")

# --- ANSI Terminal Colors ---
CLR_PRIMARY = "\033[38;5;51m"   # Neon Cyan
CLR_ACCENT = "\033[38;5;201m"   # Neon Magenta
CLR_SUCCESS = "\033[38;5;82m"   # Neon Green
CLR_WARNING = "\033[38;5;220m"  # Gold Yellow
CLR_MUTED = "\033[38;5;244m"    # Cool Slate
CLR_RESET = "\033[0m"

def print_banner():
    print(f"\n{CLR_PRIMARY}  ======================================================={CLR_RESET}")
    print(f"{CLR_PRIMARY}  ▲  A N T I G R A V I T Y   M C P   C L I   C L I E N T  ▲{CLR_RESET}")
    print(f"{CLR_PRIMARY}  ======================================================={CLR_RESET}")
    print(f"  {CLR_MUTED}Standard: Model Context Protocol (v2024-11-05){CLR_RESET}")
    print(f"  {CLR_MUTED}Active Server:{CLR_RESET} {CLR_PRIMARY}{MCP_URL}{CLR_RESET}")
    print(f"  {CLR_MUTED}Auth Security:{CLR_RESET} {CLR_SUCCESS}Enabled (Bearer Token Active){CLR_RESET}\n")

async def get_active_space() -> str:
    """Retrieves the active Google Meet session ID from the dev status endpoint."""
    headers = {"Authorization": f"Bearer {KEY}"} if KEY else {}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
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

async def call_mcp_tool(name: str, arguments: dict):
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
    
    print(f"\n  {CLR_MUTED}Sending JSON-RPC call to MCP endpoint...{CLR_RESET}")
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(MCP_URL, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                if "error" in data:
                    print(f"  {CLR_ACCENT}❌ Server Error [{data['error'].get('code')}]: {data['error'].get('message')}{CLR_RESET}")
                else:
                    result = data.get("result", {})
                    is_error = result.get("isError", False)
                    content = result.get("content", [{}])[0].get("text", "")
                    
                    if is_error:
                        print(f"  {CLR_ACCENT}❌ Tool Execution Error:{CLR_RESET} {content}")
                    else:
                        print(f"  {CLR_SUCCESS}✅ Success:{CLR_RESET} {content}")
            else:
                print(f"  {CLR_ACCENT}❌ HTTP Error {resp.status_code}: {resp.text}{CLR_RESET}")
    except Exception as e:
        print(f"  {CLR_ACCENT}❌ Connection Failed: {e}{CLR_RESET}")

async def main():
    print_banner()
    
    space_id = await get_active_space()
    print(f"  {CLR_MUTED}Active Meet Space:{CLR_RESET} {CLR_SUCCESS}{space_id}{CLR_RESET}\n")

    menu_options = [
        ("send_chat_comment", "💬 Post a glassmorphic chat card to main stage"),
        ("send_emoji", "🚀 Launch a dynamic emoji burst reaction"),
        ("trigger_diagram", "📊 Generate and draw a live D2 architecture diagram"),
        ("generate_image", "🎨 Render an AI image using Imagen 4"),
        ("send_transcript", "🎙️ Broadcast live AI captions/subtitles"),
    ]

    while True:
        print(f"  {CLR_PRIMARY}Choose an MCP Tool to invoke:{CLR_RESET}")
        for idx, (_, desc) in enumerate(menu_options, 1):
            print(f"    {CLR_PRIMARY}{idx}.{CLR_RESET} {desc}")
        print(f"    {CLR_PRIMARY}6.{CLR_RESET} Exit Client\n")

        try:
            choice = input(f"  {CLR_MUTED}Enter selection [1-6]: {CLR_RESET}").strip()
            if choice == "6":
                print(f"\n  {CLR_MUTED}Exiting Antigravity MCP Client. Good luck with the showcase!{CLR_RESET}\n")
                break

            if not choice.isdigit() or not (1 <= int(choice) <= 5):
                print(f"\n  {CLR_ACCENT}⚠️ Invalid selection. Please choose between 1 and 6.{CLR_RESET}\n")
                continue

            tool_name = menu_options[int(choice) - 1][0]
            arguments = {"space_id": space_id}

            if tool_name == "send_chat_comment":
                sender = input(f"  {CLR_MUTED}Sender Name [Default: Curtis]: {CLR_RESET}").strip() or "Curtis"
                text = input(f"  {CLR_MUTED}Message text to display: {CLR_RESET}").strip()
                if not text:
                    print(f"  {CLR_ACCENT}⚠️ Message text cannot be empty!{CLR_RESET}\n")
                    continue
                arguments.update({"sender": sender, "text": text})

            elif tool_name == "send_emoji":
                emoji = input(f"  {CLR_MUTED}Emoji characters (e.g. 👏, 🔥, 🚀): {CLR_RESET}").strip() or "🚀"
                try:
                    repeat = int(input(f"  {CLR_MUTED}Burst repeat factor [1-5]: {CLR_RESET}").strip() or "1")
                except ValueError:
                    repeat = 1
                arguments.update({"emoji": emoji, "repeat": min(5, max(1, repeat))})

            elif tool_name == "trigger_diagram":
                print(f"  {CLR_MUTED}Enter architecture description (D2 syntax or raw text describing blocks):{CLR_RESET}")
                desc_lines = []
                while True:
                    line = input()
                    if not line:
                        break
                    desc_lines.append(line)
                transcript_text = "\n".join(desc_lines)
                if not transcript_text:
                    print(f"  {CLR_ACCENT}⚠️ Description cannot be empty!{CLR_RESET}\n")
                    continue
                style = input(f"  {CLR_MUTED}Theme [cyber / blueprint / sketch / google]: {CLR_RESET}").strip() or "cyber"
                arguments.update({"transcript": transcript_text, "style": style})

            elif tool_name == "generate_image":
                prompt = input(f"  {CLR_MUTED}Enter AI image prompt: {CLR_RESET}").strip()
                if not prompt:
                    print(f"  {CLR_ACCENT}⚠️ Prompt cannot be empty!{CLR_RESET}\n")
                    continue
                arguments.update({"prompt": prompt})

            elif tool_name == "send_transcript":
                text = input(f"  {CLR_MUTED}Subtitle caption text: {CLR_RESET}").strip()
                if not text:
                    print(f"  {CLR_ACCENT}⚠️ Caption text cannot be empty!{CLR_RESET}\n")
                    continue
                role = input(f"  {CLR_MUTED}Speaker Role [user / agent]: {CLR_RESET}").strip() or "user"
                arguments.update({"text": text, "role": role})

            # Call the MCP server tool
            await call_mcp_tool(tool_name, arguments)
            print(f"\n  {CLR_MUTED}-------------------------------------------------------{CLR_RESET}\n")

        except (KeyboardInterrupt, EOFError):
            print(f"\n\n  {CLR_MUTED}Exiting Antigravity MCP Client. Good luck!{CLR_RESET}\n")
            break

if __name__ == "__main__":
    asyncio.run(main())
