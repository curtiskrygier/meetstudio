import os
import logging
import httpx
from fastapi import Request, HTTPException
from app.config import CLIENT_ID

logger = logging.getLogger("concierge")

# ── Producer API auth (STAGE_API_KEY) ─────────────────────────────────────────

_STAGE_API_KEY = os.environ.get("STAGE_API_KEY", "")

if not _STAGE_API_KEY:
    logger.warning("STAGE_API_KEY not set — producer API endpoints are OPEN to the world")


def check_producer_auth(request: Request):
    """Enforce Bearer STAGE_API_KEY on all producer endpoints.

    Returns 503 if the key is not configured server-side (misconfigured deploy).
    Returns 401 if the key is wrong (bad caller).
    """
    if not _STAGE_API_KEY:
        raise HTTPException(
            status_code=503,
            detail={"error": "Producer API not configured", "hint": "STAGE_API_KEY is not set on the server"}
        )
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {_STAGE_API_KEY}":
        raise HTTPException(
            status_code=401,
            detail={"error": "Unauthorized", "hint": "Set Authorization: Bearer <STAGE_API_KEY>"}
        )

async def validate_google_token(token: str) -> bool:
    """Validate that the token is active and issued for our Client ID."""
    if not token:
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/tokeninfo",
                params={"access_token": token}
            )
            if resp.status_code != 200:
                logger.warning(f"[auth] token validation failed: {resp.status_code}")
                return False
            
            info = resp.json()
            if not CLIENT_ID:
                logger.warning("[auth] CLIENT_ID not configured — rejecting all tokens")
                return False
            aud = info.get("aud")
            azp = info.get("azp")
            if aud != CLIENT_ID and azp != CLIENT_ID:
                logger.warning(f"[auth] token mismatch: aud={aud}, azp={azp}, expected {CLIENT_ID}")
                return False
                
            return True
    except Exception as e:
        logger.error(f"[auth] error during validation: {e}")
        return False
