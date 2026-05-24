import os
import logging
import httpx
from fastapi import Request, HTTPException
from app.config import CLIENT_ID

logger = logging.getLogger("concierge")

# ── Load production env if present ───────────────────────────────────────────
def _load_env_production():
    try:
        env_path = ".env.production"
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip("'").strip('"')
                        if key and key not in os.environ:
                            os.environ[key] = val
    except Exception as e:
        logger.warning(f"Failed to auto-load .env.production: {e}")

_load_env_production()

# ── Producer API auth (STAGE_API_KEY) ─────────────────────────────────────────

_STAGE_API_KEY = os.environ.get("STAGE_API_KEY", "")

# Fail-closed guard on production Cloud Run
if os.environ.get("K_SERVICE") and not _STAGE_API_KEY:
    raise RuntimeError("CRITICAL: STAGE_API_KEY must be set in Cloud Run production environment!")

if not _STAGE_API_KEY:
    logger.warning("STAGE_API_KEY not set — producer API endpoints are OPEN to the world")


def check_producer_auth(request: Request):
    """Enforce Bearer STAGE_API_KEY on all producer endpoints.

    Returns 503 if the key is not configured server-side (misconfigured deploy).
    Returns 401 if the key is wrong (bad caller).
    """
    # Bypass authentication for local requests (e.g., local demo scripts)
    if request.client and request.client.host in ("127.0.0.1", "localhost"):
        return

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
