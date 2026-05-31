import pytest
import httpx
from app.auth import validate_google_token, validate_google_token_sync, check_producer_auth
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


# ── Sync validation and check_producer_auth tests ───────────────────────────

def test_validate_token_sync_missing():
    assert validate_google_token_sync("") is False
    assert validate_google_token_sync(None) is False

def test_validate_token_sync_success():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"aud": "test-client-id"}
    
    with patch("app.auth.CLIENT_ID", "test-client-id"):
        with patch("httpx.Client.get", return_value=mock_resp):
            result = validate_google_token_sync("valid-token")
            assert result is True

def test_check_producer_auth_valid_google_token():
    # Test that check_producer_auth accepts a valid Google token
    mock_request = MagicMock(spec=Request)
    mock_request.query_params = {"ticket": "valid-google-token"}
    mock_request.headers = {}
    mock_request.client = MagicMock()
    mock_request.client.host = "1.2.3.4"
    
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"aud": "test-client-id"}
    
    with patch("app.auth.CLIENT_ID", "test-client-id"):
        with patch("httpx.Client.get", return_value=mock_resp):
            # Should not raise HTTPException
            check_producer_auth(mock_request)
