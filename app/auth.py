import httpx
from app.config import CLIENT_ID, MARKETPLACE_CLIENT_ID

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
                print(f"[auth] token validation failed: {resp.status_code}", flush=True)
                return False
            
            info = resp.json()
            aud = info.get("aud")
            # Check if token is for our Client ID (if configured)
            allowed_auds = [CLIENT_ID, MARKETPLACE_CLIENT_ID]
            if aud not in allowed_auds:
                print(f"[auth] token audience mismatch: got {aud}, expected one of {allowed_auds}", flush=True)
                return False
                
            return True
    except Exception as e:
        print(f"[auth] error during validation: {e}", flush=True)
        return False
