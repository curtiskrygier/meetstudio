import pytest
import httpx
from main import validate_google_token, CLIENT_ID
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_validate_token_missing():
    assert await validate_google_token("") is False
    assert await validate_google_token(None) is False

@pytest.mark.asyncio
async def test_validate_token_success():
    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"aud": CLIENT_ID} if CLIENT_ID else {"aud": "some-id"}
    
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
    if not CLIENT_ID:
        pytest.skip("CLIENT_ID not set for this test")
        
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"aud": "wrong-client-id"}
    
    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        assert await validate_google_token("valid-token-wrong-aud") is False

@pytest.mark.asyncio
async def test_validate_token_exception():
    with patch("httpx.AsyncClient.get", side_effect=Exception("network error")):
        assert await validate_google_token("any-token") is False
