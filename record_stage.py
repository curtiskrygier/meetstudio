#!/usr/bin/env python3
"""
Record the Meet Live Concierge main stage as an MP4.

Opens the stage in a headless Chromium, subscribes to the WebSocket,
and records everything rendered — captions, diagrams, images, emoji.

Prerequisites:
    pip install playwright
    playwright install chromium

Usage:
    python3 record_stage.py                          # auto-detect space
    python3 record_stage.py spaces/abc123            # force space
    python3 record_stage.py spaces/abc123 demo.mp4   # custom output path

Run the demo script in a second terminal once this says "Recording...":
    python3 demo_showcase.py

Press Ctrl+C to stop and save.

To add the voice-cloned audio track afterwards:
    ffmpeg -i demo_recording.mp4 -i narration.wav -c:v copy -c:a aac -shortest demo_final.mp4
"""
import asyncio
import httpx
import os
import signal
import sys
from pathlib import Path
from playwright.async_api import async_playwright

API_URL = "https://meet-live-concierge-649226456677.us-central1.run.app"
KEY = os.environ.get("STAGE_API_KEY", "50WNPPSa7n5VhzN05aoyfXepxrlQCF5W3GQrl1Q3ex0")
OUTPUT_PATH = sys.argv[3] if len(sys.argv) > 3 else sys.argv[2] if (len(sys.argv) > 2 and sys.argv[2].endswith(".mp4")) else "demo_recording.mp4"
SPACE_ARG = next((a for a in sys.argv[1:] if a.startswith("spaces/")), "")


async def get_active_space() -> str:
    headers = {"Authorization": f"Bearer {KEY}"} if KEY else {}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{API_URL}/api/dev/sessions", headers=headers)
        data = resp.json()
        listeners = data.get("stage_listeners", {})
        sessions = data.get("active_sessions", [])
        return sessions[0] if sessions else (list(listeners.keys())[0] if listeners else "")


async def get_stage_url(space_id: str) -> str:
    headers = {}
    if KEY:
        headers["Authorization"] = f"Bearer {KEY}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{API_URL}/api/stage-ticket/{space_id}", headers=headers)
        if resp.status_code == 401:
            print("✗ Unauthorized — set STAGE_API_KEY env var")
            sys.exit(1)
        resp.raise_for_status()
        return resp.json()["stage_url"]


async def main():
    space_id = SPACE_ARG
    if not space_id:
        print("Auto-detecting active session...")
        space_id = await get_active_space()
    if not space_id:
        print("No active session found. Open a Meet call and start the add-on.")
        sys.exit(1)

    print(f"Space: {space_id}")
    print("Fetching stage URL...")
    stage_url = await get_stage_url(space_id)
    print(f"Stage URL obtained.")

    output = Path(OUTPUT_PATH).with_suffix(".mp4")
    # Playwright saves as webm internally — we'll convert at the end
    videos_dir = Path("/tmp/stage_recording")
    videos_dir.mkdir(exist_ok=True)

    stop_event = asyncio.Event()

    def _handle_sigint(*_):
        print("\nStopping recording...")
        stop_event.set()

    signal.signal(signal.SIGINT, _handle_sigint)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(videos_dir),
            record_video_size={"width": 1920, "height": 1080},
        )

        page = await context.new_page()

        # Suppress console noise from the page
        page.on("console", lambda msg: None)

        print(f"Opening stage...")
        await page.goto(stage_url, wait_until="networkidle")

        # Unlock Web Audio API — required by browser autoplay policy
        unlock = page.locator("#audio-unlock")
        if await unlock.is_visible(timeout=3000):
            await unlock.click()
            print("  ✓ Audio unlocked")

        print(f"\n✓ Recording — press Ctrl+C when the demo is done\n")

        # Keep page alive until stopped
        await stop_event.wait()

        # Close context to flush the video file
        video = page.video
        await context.close()
        await browser.close()

        # Find the recorded webm and convert to mp4
        webm_path = await video.path()
        print(f"Converting {webm_path} → {output} ...")
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", str(webm_path),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            str(output),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()

        if output.exists():
            size_mb = output.stat().st_size / 1_000_000
            print(f"✓ Saved: {output}  ({size_mb:.1f} MB)")
            print(f"\nTo add narration audio:")
            print(f"  ffmpeg -i {output} -i narration.wav -c:v copy -c:a aac -shortest demo_final.mp4")
        else:
            print(f"✗ Conversion failed — raw webm at {webm_path}")


if __name__ == "__main__":
    asyncio.run(main())
