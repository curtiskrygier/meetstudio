import pytest
import httpx
from app.auth import validate_google_token
import app.config as config
from unittest.mock import AsyncMock, patch

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
