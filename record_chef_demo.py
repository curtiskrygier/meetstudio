#!/usr/bin/env python3
"""Record a demo script via Playwright.

Spawns a headless Chromium at 1920x1080, mints a stage ticket, opens the
listener, then runs the chosen demo script in a subprocess. The browser
records the whole sequence to WebM; ffmpeg converts to MP4 at the end.

Usage:
  record_chef_demo.py                                  # chef demo → chef-at-the-table.{webm,mp4}
  record_chef_demo.py demo_a2ui_market_ticker.py market-ticker
"""
import asyncio, os, subprocess, sys, shutil, glob
from pathlib import Path
import httpx
from playwright.async_api import async_playwright

API   = os.environ.get("CONCIERGE_API_URL", "http://127.0.0.1:8085")
KEY   = os.environ.get("STAGE_API_KEY") or exit("STAGE_API_KEY required — export it before running this script")
SPACE = os.environ.get("CAPTURE_SPACE", "default")

DEMO_SCRIPT = sys.argv[1] if len(sys.argv) > 1 else "demo_a2ui_primitives.py"
OUT_STEM    = sys.argv[2] if len(sys.argv) > 2 else "chef-at-the-table"

OUT_DIR = Path(__file__).parent / "articles"
VIDEO_DIR = OUT_DIR / "_video_raw"
FINAL_WEBM = OUT_DIR / f"{OUT_STEM}.webm"
FINAL_MP4  = OUT_DIR / f"{OUT_STEM}.mp4"

# Head-room each side for ws connect + final hold.
PRE_RUN_PAUSE  = 2.5
POST_RUN_PAUSE = 4.0


async def mint_stage_url() -> str:
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{API}/api/stage-ticket/{SPACE}",
                        headers={"Authorization": f"Bearer {KEY}"})
        r.raise_for_status()
        return r.json()["stage_url"]


async def main():
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    # Clean any previous raw clips so we know which file is fresh.
    for f in VIDEO_DIR.glob("*.webm"):
        f.unlink()

    stage_url = await mint_stage_url()
    print(f"  ▶ stage_url: {stage_url}")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        ctx = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(VIDEO_DIR),
            record_video_size={"width": 1920, "height": 1080},
        )
        page = await ctx.new_page()
        # Hide the production topbar so it doesn't flash between scenes when
        # gdm-stage-grid (position:fixed) un-covers it during deleteSurface.
        await page.add_init_script("""
            const css = `.topbar { display: none !important; }
                         #a2ui-stage-root { top: 0 !important; height: 100vh !important; }
                         html, body { background: #000 !important; }`;
            const style = document.createElement('style');
            style.textContent = css;
            (document.head || document.documentElement).appendChild(style);
        """)
        await page.goto(stage_url, wait_until="networkidle")
        # Wait for the WebSocket to negotiate + stage to render its empty frame.
        await asyncio.sleep(PRE_RUN_PAUSE)

        # Kick off the demo as a subprocess. Pin CONCIERGE_API_URL to local
        # and MEET_SPACE_ID to the same space so demos that look up active
        # sessions don't dial out to a stale Cloud Run host.
        env = os.environ.copy()
        env["CAPTURE_SPACE"]      = SPACE
        env["MEET_SPACE_ID"]      = SPACE
        env["CONCIERGE_API_URL"]  = API
        print(f"  ▶ launching {DEMO_SCRIPT}…")
        proc = subprocess.Popen(
            ["/usr/bin/python3", DEMO_SCRIPT],
            cwd=str(Path(__file__).parent),
            env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )

        # Stream demo output to our stdout in real time, AND keep the
        # Playwright event loop alive so the page keeps recording.
        loop = asyncio.get_event_loop()
        while True:
            line = await loop.run_in_executor(None, proc.stdout.readline)
            if not line:
                break
            print(line.rstrip())

        rc = proc.wait()
        print(f"  ▶ demo exited rc={rc}")

        # Hold a couple extra seconds so the final signoff card lands cleanly.
        await asyncio.sleep(POST_RUN_PAUSE)

        # Close the context to finalise the video file.
        await ctx.close()
        await browser.close()

    # Playwright writes to a random filename inside VIDEO_DIR. Find + rename.
    clips = sorted(VIDEO_DIR.glob("*.webm"), key=lambda p: p.stat().st_mtime)
    if not clips:
        print("  ✗ no video found")
        sys.exit(1)
    src = clips[-1]
    if FINAL_WEBM.exists():
        FINAL_WEBM.unlink()
    shutil.move(str(src), str(FINAL_WEBM))
    print(f"  ✓ webm: {FINAL_WEBM} ({FINAL_WEBM.stat().st_size//1024} KB)")

    # ffmpeg → mp4 (h264 + aac-less, faststart) for article embedding.
    if shutil.which("ffmpeg"):
        if FINAL_MP4.exists():
            FINAL_MP4.unlink()
        print("  ▶ ffmpeg: webm → mp4…")
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(FINAL_WEBM),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-an",
            str(FINAL_MP4),
        ], check=True)
        print(f"  ✓ mp4:  {FINAL_MP4} ({FINAL_MP4.stat().st_size//1024} KB)")

    # Sweep up the raw dir.
    try:
        VIDEO_DIR.rmdir()
    except OSError:
        pass


if __name__ == "__main__":
    asyncio.run(main())
