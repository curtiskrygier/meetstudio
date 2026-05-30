#!/usr/bin/env python3
"""Record Clip 1 — the side-panel widget at zoomed-in 1920x1080.

Pure visual record of the user-action moment: cursor enters → types
"A2UI 0.9 spec" → clicks "Draft & Fire Playbook" → status flips. No
backend involvement; the mock is faithful to the real widget styles.

Output: articles/sidepanel-widget.{webm,mp4}
"""
import asyncio, os, shutil, subprocess, sys
from pathlib import Path
from playwright.async_api import async_playwright

OUT_DIR    = Path(__file__).parent / "articles"
VIDEO_DIR  = OUT_DIR / "_video_raw"
MOCK_HTML  = OUT_DIR / "_sidepanel_mock.html"
FINAL_WEBM = OUT_DIR / "sidepanel-widget.webm"
FINAL_MP4  = OUT_DIR / "sidepanel-widget.mp4"

TYPED_TEXT = "Outline me the A2UI 0.9 spec"


async def main():
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    for f in VIDEO_DIR.glob("*.webm"):
        f.unlink()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox"],
        )
        ctx = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(VIDEO_DIR),
            record_video_size={"width": 1920, "height": 1080},
        )
        page = await ctx.new_page()
        await page.goto(MOCK_HTML.as_uri(), wait_until="domcontentloaded")
        # Wait for fonts to load so first frames don't show fallback Times.
        await page.wait_for_function("document.fonts && document.fonts.ready")
        await asyncio.sleep(0.5)

        # ── Scene timing ──────────────────────────────────────────────
        # 0.0 – 1.0   idle
        # 1.0 – 1.8   cursor moves from bottom-right to input field
        # 1.8 – 2.1   click input (focus)
        # 2.1 – 5.0   type "A2UI 0.9 spec" character-by-character
        # 5.0 – 5.8   pause, cursor moves to CTA button
        # 5.8 – 6.1   click CTA (depress + ripple)
        # 6.1 – 6.4   button label flips to "Drafting & Compiling…"
        # 6.4 – 6.6   status text fades in
        # 6.6 – 9.0   hold (gives post-prod a transition window)

        # Helper — interrogate the page for element rects.
        async def rect(sel):
            return await page.evaluate(f"""(() => {{
                const el = document.querySelector({sel!r});
                const r = el.getBoundingClientRect();
                return {{ x: r.x + r.width/2, y: r.y + r.height/2,
                          left: r.left, top: r.top, width: r.width, height: r.height }};
            }})()""")

        async def move_cursor(x, y):
            await page.evaluate(f"""
                const c = document.getElementById('cursor');
                c.style.left = '{x}px';
                c.style.top  = '{y}px';
            """)

        async def click_pulse(x, y):
            await page.evaluate(f"""
                const c = document.getElementById('cursor');
                c.classList.add('clicking');
                const r = document.createElement('div');
                r.className = 'ripple fire';
                r.style.left = '{x}px';
                r.style.top  = '{y}px';
                document.body.appendChild(r);
                setTimeout(() => {{ c.classList.remove('clicking'); r.remove(); }}, 600);
            """)

        # Frame 0 — idle hold.
        await asyncio.sleep(1.0)

        # Cursor → input
        input_rect = await rect("#input")
        await move_cursor(input_rect["x"], input_rect["y"])
        await asyncio.sleep(0.85)

        # Focus the input + show caret.
        await click_pulse(input_rect["x"], input_rect["y"])
        await page.evaluate("""
            const el = document.getElementById('input');
            el.classList.add('focused');
            // Inject a caret span we control (cleaner than relying on browser caret).
            const c = document.createElement('span');
            c.className = 'caret on';
            c.id = 'caret';
            el.parentElement.appendChild(c);
            // Position the caret right after the input's text (we'll move it as we type).
            const place = () => {
                const r = el.getBoundingClientRect();
                c.style.position = 'fixed';
                c.style.left = (r.left + 22 + (el.value.length * 13)) + 'px';
                c.style.top  = (r.top + 18) + 'px';
            };
            place();
            window._placeCaret = place;
        """)
        await asyncio.sleep(0.3)

        # Type the prompt char-by-char.
        per_char = 0.22  # ~4.5 chars/sec — readable on camera
        for ch in TYPED_TEXT:
            await page.evaluate(f"""
                const el = document.getElementById('input');
                el.value += {ch!r};
                if (window._placeCaret) window._placeCaret();
            """)
            await asyncio.sleep(per_char)

        # Pause for emphasis.
        await asyncio.sleep(0.65)

        # Cursor → CTA
        cta_rect = await rect("#cta")
        await move_cursor(cta_rect["x"], cta_rect["y"])
        await asyncio.sleep(0.55)

        # Click CTA — depress, ripple, then transform to drafting state.
        await click_pulse(cta_rect["x"], cta_rect["y"])
        await page.evaluate("""
            const b = document.getElementById('cta');
            b.classList.add('pressed');
        """)
        await asyncio.sleep(0.18)
        await page.evaluate("""
            const b = document.getElementById('cta');
            b.classList.remove('pressed');
            b.classList.add('drafting');
            b.textContent = 'Drafting & Compiling…';
            const s = document.getElementById('status');
            s.classList.add('show');
            // Hide caret once the button takes over.
            const c = document.getElementById('caret');
            if (c) c.classList.remove('on');
        """)
        await asyncio.sleep(0.35)

        # Hold end-state so post-prod has cushion for the cut to Clip 2.
        await asyncio.sleep(2.4)

        await ctx.close()
        await browser.close()

    # Rename Playwright's randomly-named WebM
    clips = sorted(VIDEO_DIR.glob("*.webm"), key=lambda p: p.stat().st_mtime)
    if not clips:
        print("  ✗ no video found"); sys.exit(1)
    src = clips[-1]
    if FINAL_WEBM.exists(): FINAL_WEBM.unlink()
    shutil.move(str(src), str(FINAL_WEBM))
    print(f"  ✓ webm: {FINAL_WEBM} ({FINAL_WEBM.stat().st_size//1024} KB)")

    # mp4 via ffmpeg
    if shutil.which("ffmpeg"):
        if FINAL_MP4.exists(): FINAL_MP4.unlink()
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(FINAL_WEBM),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", "-an",
            str(FINAL_MP4),
        ], check=True)
        print(f"  ✓ mp4:  {FINAL_MP4} ({FINAL_MP4.stat().st_size//1024} KB)")

    try: VIDEO_DIR.rmdir()
    except OSError: pass


if __name__ == "__main__":
    asyncio.run(main())
