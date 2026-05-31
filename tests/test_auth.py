import pytest
import httpx
from app.auth import validate_google_token, check_producer_auth
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request

@pytest.mark.asyncio
async def test_validate_token_missing():
    assert await validate_google_token("") is False
    assert await validate_google_token(None) is False

@pytest.mark.asyncio
async def test_validate_token_success():
    # Patch the value where it's used
    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"aud": "test-client-id"}
    
    with patch("app.auth.CLIENT_ID", "test-client-id"):
        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            result = await validate_google_token("valid-token")
            assert result is True

@pytest.mark.asyncio
async def test_validate_token_failure():
    mock_resp = AsyncMock()
    mock_resp.status_code = 401
    mock_resp.text = "invalid token"
    
    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        assert await validate_google_token("invalid-token") is False

@pytest.mark.asyncio
async def test_validate_token_audience_mismatch():
    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"aud": "wrong-client-id"}
    
    with patch("app.auth.CLIENT_ID", "test-client-id"):
        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            assert await validate_google_token("valid-token-wrong-aud") is False

@pytest.mark.asyncio
async def test_validate_token_exception():
    with patch("httpx.AsyncClient.get", side_effect=Exception("network error")):
        assert await validate_google_token("any-token") is False


# ── check_producer_auth tests ───────────────────────────

@pytest.mark.asyncio
async def test_check_producer_auth_valid_google_token():
    # Test that check_producer_auth accepts a valid Google token
    mock_request = MagicMock(spec=Request)
    mock_request.query_params = {"ticket": "valid-google-token"}
    mock_request.headers = {}
    mock_request.client = MagicMock()
    mock_request.client.host = "1.2.3.4"
    
    with patch("app.auth.validate_google_token", new_callable=AsyncMock) as mock_validate:
        mock_validate.return_value = True
        # Should not raise HTTPException
        await check_producer_auth(mock_request)
        mock_validate.assert_called_once_with("valid-google-token")

