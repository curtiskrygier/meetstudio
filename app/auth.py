import httpx
import logging
from app.config import CLIENT_ID

logger = logging.getLogger("concierge")

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
            if aud != CLIENT_ID:
                logger.warning(f"[auth] token audience mismatch: got {aud}, expected {CLIENT_ID}")
                return False
                
            return True
    except Exception as e:
        logger.error(f"[auth] error during validation: {e}")
        return False
