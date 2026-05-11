import httpx
import re
import asyncio
import subprocess
from app.config import MAX_SVG_SIZE

async def fetch_url(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            text = resp.text
            # Strip HTML tags
            text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL)
            text = re.sub(r'<script[^>]*>.*?</script>', ' ', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'[ \t]+', ' ', text)
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = text.strip()
            print(f"[fetch_url] {url} — {len(text)} chars", flush=True)
            return text[:6000]  # cap at ~1.5k tokens
    except Exception as e:
        print(f"[fetch_url] error: {e}", flush=True)
        return f"Error fetching {url}: {e}"

def svg_to_png(svg_bytes: bytes, width: int = 2400) -> bytes | None:
    if len(svg_bytes) > MAX_SVG_SIZE:
        print(f"[drive] SVG too large for conversion: {len(svg_bytes)} bytes", flush=True)
        return None
    try:
        result = subprocess.run(
            ["rsvg-convert", "-w", str(width), "--format", "png"],
            input=svg_bytes, capture_output=True, timeout=15,
        )
        if result.returncode == 0:
            return result.stdout
        else:
            print(f"[drive] PNG conversion failed (code {result.returncode}): {result.stderr.decode()}", flush=True)
            return None
    except Exception as e:
        print(f"[drive] PNG conversion error: {e}", flush=True)
        return None
