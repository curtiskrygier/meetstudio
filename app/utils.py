import httpx
import re
import asyncio
import subprocess
import logging
from app.config import MAX_SVG_SIZE

logger = logging.getLogger("concierge")

async def fetch_url(url: str) -> str:
    # SSRF Protection: Block metadata server and private IP ranges
    if re.search(r'169\.254\.|127\.0\.0\.1|localhost|^10\.|^172\.(1[6-9]|2[0-9]|3[0-1])\.|^192\.168\.', url):
        logger.warning(f"[fetch_url] SSRF Attempt Blocked: {url}")
        return "Error: Access to internal or restricted addresses is forbidden."
    
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
            logger.info(f"[fetch_url] {url} — {len(text)} chars")
            return text[:6000]  # cap at ~1.5k tokens
    except Exception as e:
        logger.error(f"[fetch_url] error: {e}")
        return f"Error fetching {url}: {e}"

def svg_to_png(svg_bytes: bytes, width: int = 2400) -> bytes | None:
    if len(svg_bytes) > MAX_SVG_SIZE:
        logger.warning(f"[drive] SVG too large for conversion: {len(svg_bytes)} bytes")
        return None
    try:
        result = subprocess.run(
            ["rsvg-convert", "-w", str(width), "--format", "png"],
            input=svg_bytes, capture_output=True, timeout=15,
        )
        if result.returncode == 0:
            return result.stdout
        else:
            logger.error(f"[drive] PNG conversion failed (code {result.returncode}): {result.stderr.decode()}")
            return None
    except Exception as e:
        logger.error(f"[drive] PNG conversion error: {e}")
        return None
