#!/usr/bin/env python3
"""
Stream an audio file into a live Meet session and watch Gemini transcribe it in real time.

Prerequisites:
    ffmpeg must be installed (brew install ffmpeg / apt install ffmpeg)
    export STAGE_API_KEY=...   (same key used for MCP tools)

Usage:
    python3 stream_audio.py path/to/audio.mp3
    python3 stream_audio.py path/to/audio.wav spaces/abc123   # force space
    python3 stream_audio.py path/to/audio.mp3 --fast          # 2x speed
"""
import asyncio
import httpx
import os
import subprocess
import sys
import tempfile

API_URL = os.environ.get("CONCIERGE_API_URL") or exit("CONCIERGE_API_URL not set — see .env.production.sample")
KEY = os.environ.get("STAGE_API_KEY", "")

SAMPLE_RATE = 16000
CHANNELS = 1
BYTES_PER_SAMPLE = 2           # 16-bit
CHUNK_MS = 100                 # send 100ms of audio per chunk
CHUNK_SIZE = SAMPLE_RATE * CHANNELS * BYTES_PER_SAMPLE * CHUNK_MS // 1000  # 3200 bytes


async def get_active_space() -> str:
    headers = {"Authorization": f"Bearer {KEY}"} if KEY else {}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{API_URL}/api/dev/sessions", headers=headers)
        data = resp.json()
        sessions = data.get("active_sessions", [])
        return sessions[0] if sessions else ""


def convert_to_pcm(input_path: str) -> bytes:
    """Use ffmpeg to decode any audio format to 16kHz 16-bit mono raw PCM."""
    print(f"  Converting {input_path} → 16kHz mono PCM...")
    with tempfile.NamedTemporaryFile(suffix=".pcm", delete=False) as tmp:
        tmp_path = tmp.name

    result = subprocess.run([
        "ffmpeg", "-y", "-i", input_path,
        "-ar", str(SAMPLE_RATE),
        "-ac", str(CHANNELS),
        "-f", "s16le",
        tmp_path
    ], capture_output=True)

    if result.returncode != 0:
        print("ffmpeg error:", result.stderr.decode())
        sys.exit(1)

    with open(tmp_path, "rb") as f:
        pcm = f.read()
    os.unlink(tmp_path)

    duration_s = len(pcm) / (SAMPLE_RATE * CHANNELS * BYTES_PER_SAMPLE)
    print(f"  PCM ready: {len(pcm):,} bytes  ({duration_s:.1f}s)")
    return pcm


async def stream(space_id: str, pcm: bytes, speed: float = 1.0):
    headers = {"Content-Type": "audio/pcm"}
    mute_headers = {}
    if KEY:
        headers["Authorization"] = f"Bearer {KEY}"
        mute_headers["Authorization"] = f"Bearer {KEY}"

    mute_url = f"{API_URL}/api/gemini-mute/{space_id}"
    url = f"{API_URL}/api/audio-inject/{space_id}"
    total = len(pcm)
    sent = 0
    delay = (CHUNK_MS / 1000) / speed

    print(f"\n▶  Muting Gemini responses for clean transcription...")
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            resp = await client.post(mute_url, json={"muted": True}, headers=mute_headers)
            if resp.status_code == 200:
                print("  ✓ Gemini muted (Transcription-Only mode active)")
            else:
                print(f"  ⚠ Failed to mute Gemini (Status {resp.status_code})")
        except Exception as e:
            print(f"  ⚠ Could not contact muting endpoint: {e}")

    print(f"\n▶  Streaming to {space_id} ({speed}x speed)...\n")

    async with httpx.AsyncClient(timeout=10) as client:
        while sent < total:
            chunk = pcm[sent:sent + CHUNK_SIZE]
            try:
                resp = await client.post(url, content=chunk, headers=headers)
                if resp.status_code == 404:
                    print("  ✗ No active Gemini session for this space — start the add-on first")
                    return
                if resp.status_code == 401:
                    print("  ✗ Unauthorized — set STAGE_API_KEY env var")
                    return
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                print(f"  ✗ HTTP {e.response.status_code}: {e.response.text}")
                return

            sent += len(chunk)
            pct = sent / total * 100
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            print(f"\r  [{bar}] {pct:5.1f}%  {sent//1000}kB / {total//1000}kB", end="", flush=True)
            await asyncio.sleep(delay)

    print(f"\n\n✅  Stream complete — {total:,} bytes sent")

    print(f"\n▶  Restoring Gemini responses...")
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            resp = await client.post(mute_url, json={"muted": False}, headers=mute_headers)
            if resp.status_code == 200:
                print("  ✓ Gemini unmuted (Interactive mode restored)")
            else:
                print(f"  ⚠ Failed to restore Gemini (Status {resp.status_code})")
        except Exception as e:
            print(f"  ⚠ Could not contact unmuting endpoint: {e}")


async def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]

    if not args:
        print(__doc__)
        sys.exit(1)

    audio_path = args[0]
    if not os.path.exists(audio_path):
        print(f"File not found: {audio_path}")
        sys.exit(1)

    space_id = args[1] if len(args) > 1 else os.environ.get("SPACE", "")
    if not space_id:
        print("Auto-detecting active session...")
        space_id = await get_active_space()
    if not space_id:
        print("No active session. Open a Meet call and start the add-on first.")
        sys.exit(1)

    speed = 2.0 if "--fast" in flags else 1.0

    pcm = convert_to_pcm(audio_path)
    await stream(space_id, pcm, speed=speed)


if __name__ == "__main__":
    asyncio.run(main())
