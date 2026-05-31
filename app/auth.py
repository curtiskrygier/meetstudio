import os
import logging
import httpx
from datetime import datetime
from fastapi import Request, HTTPException
from app.config import CLIENT_ID

logger = logging.getLogger("concierge")

# Shared in-memory active stage/auth ticket store to prevent circular/double import issues
auth_tickets: dict[str, tuple[str, datetime]] = {}


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


def validate_google_token_sync(token: str) -> bool:
    """Validate that the token is active and issued for our Client ID synchronously."""
    if not token:
        return False
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(
                "https://www.googleapis.com/oauth2/v3/tokeninfo",
                params={"access_token": token}
            )
            if resp.status_code != 200:
                logger.warning(f"[auth] sync token validation failed: {resp.status_code}")
                return False
            
            info = resp.json()
            if not CLIENT_ID:
                logger.warning("[auth] CLIENT_ID not configured — rejecting all tokens in sync validate")
                return False
            aud = info.get("aud")
            azp = info.get("azp")
            if aud != CLIENT_ID and azp != CLIENT_ID:
                logger.warning(f"[auth] sync token mismatch: aud={aud}, azp={azp}, expected {CLIENT_ID}")
                return False
                
            return True
    except Exception as e:
        logger.error(f"[auth] error during sync validation: {e}")
        return False


def check_producer_auth(request: Request):
    """Enforce Bearer STAGE_API_KEY on all producer endpoints,
    or a valid active stage/auth ticket, or a valid Google OAuth token.

    Returns 503 if the key is not configured server-side (misconfigured deploy).
    Returns 401 if the key/ticket/token is wrong (bad caller).
    """
    # Bypass auth for localhost — only when NOT running on Cloud Run
    # (K_SERVICE is set by Cloud Run; if present, bypass is always skipped)
    if not os.environ.get("K_SERVICE") and request.client and request.client.host in ("127.0.0.1", "localhost"):
        return

    # 1. Try ticket-based or Google OAuth token authentication first
    # Accept ticket/token via query parameters (?ticket=...) or as Bearer token
    ticket = request.query_params.get("ticket")
    auth_header = request.headers.get("Authorization", "")
    if not ticket and auth_header.startswith("Bearer "):
        ticket = auth_header[7:]

    if ticket:
        from datetime import timezone
        # Check active stage ticket
        ticket_data = auth_tickets.get(ticket)
        if ticket_data and ticket_data[1] >= datetime.now(timezone.utc):
            # Valid active ticket! Allow the request
            return
        
        # Check valid Google OAuth token
        if validate_google_token_sync(ticket):
            return

    # 2. Fall back to STAGE_API_KEY
    if not _STAGE_API_KEY:
        raise HTTPException(
            status_code=503,
            detail={"error": "Producer API not configured", "hint": "STAGE_API_KEY is not set on the server or no valid ticket/token provided"}
        )
    if auth_header != f"Bearer {_STAGE_API_KEY}":
        raise HTTPException(
            status_code=401,
            detail={"error": "Unauthorized", "hint": "Set Authorization: Bearer <STAGE_API_KEY> or provide a valid ticket/token"}
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
