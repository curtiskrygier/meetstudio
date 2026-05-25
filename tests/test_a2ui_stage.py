import json
import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from main import app
from app.a2ui_catalog import A2UI_CATALOG, validate_a2ui_surface
from app.mcp_server import handle_mcp

client = TestClient(app)

@pytest.fixture
def mock_broadcast():
    with patch("main.broadcast_to_stage", new_callable=AsyncMock) as mock:
        yield mock

@pytest.fixture
def mock_auth_key():
    with patch("app.auth._STAGE_API_KEY", "test-key-123"):
        yield "test-key-123"

def test_validate_a2ui_surface_valid():
    surface_update = {
        "components": [
            {
                "id": "comp-1",
                "component": {
                    "gdm-stage-card": {
                        "title": "Hello",
                        "text": "World"
                    }
                }
            }
        ]
    }
    errors = validate_a2ui_surface(surface_update)
    assert not errors

def test_validate_a2ui_surface_invalid_component():
    surface_update = {
        "components": [
            {
                "id": "comp-1",
                "component": {
                    "gdm-unknown-component": {
                        "title": "Hello"
                    }
                }
            }
        ]
    }
    errors = validate_a2ui_surface(surface_update)
    assert len(errors) == 1
    assert "gdm-unknown-component" in errors[0]

def test_validate_a2ui_surface_empty():
    surface_update = {}
    errors = validate_a2ui_surface(surface_update)
    assert len(errors) == 1
    assert "components is empty" in errors[0]

def test_validate_a2ui_surface_missing_def():
    surface_update = {
        "components": [
            {
                "id": "comp-1"
            }
        ]
    }
    errors = validate_a2ui_surface(surface_update)
    assert len(errors) == 1
    assert "has no component definition" in errors[0]

def test_api_render_stage_success(mock_auth_key, mock_broadcast):
    headers = {"Authorization": f"Bearer {mock_auth_key}"}
    payload = {
        "surfaceUpdate": {
            "components": [
                {
                    "id": "comp-1",
                    "component": {
                        "gdm-stage-card": {"title": "Hello"}
                    }
                }
            ]
        },
        "root": "comp-1",
        "dataModelUpdate": {"some": "data"}
    }
    
    resp = client.post("/api/render-stage/spaces/test", json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    
    # Broadcast order: surfaceUpdate -> dataModelUpdate -> beginRendering
    assert mock_broadcast.call_count == 3
    mock_broadcast.assert_any_call("spaces/test", {"type": "surfaceUpdate", "surfaceUpdate": payload["surfaceUpdate"]})
    mock_broadcast.assert_any_call("spaces/test", {"type": "dataModelUpdate", "dataModelUpdate": payload["dataModelUpdate"]})
    mock_broadcast.assert_any_call("spaces/test", {"type": "beginRendering", "beginRendering": {"root": "comp-1"}})

def test_api_render_stage_validation_failure(mock_auth_key):
    headers = {"Authorization": f"Bearer {mock_auth_key}"}
    payload = {
        "surfaceUpdate": {
            "components": [
                {
                    "id": "comp-1",
                    "component": {
                        "gdm-unknown-component": {"title": "Hello"}
                    }
                }
            ]
        }
    }
    
    resp = client.post("/api/render-stage/spaces/test", json=payload, headers=headers)
    assert resp.status_code == 422
    assert "errors" in resp.json()["detail"]

@pytest.mark.asyncio
async def test_mcp_render_stage_success():
    mock_request = AsyncMock(spec=Request)
    mock_request.headers = {"Authorization": "Bearer test-key-123"}
    mock_request.json = AsyncMock(return_value={
        "method": "tools/call",
        "id": 1,
        "params": {
            "name": "render_stage",
            "arguments": {
                "space_id": "spaces/test",
                "surfaceUpdate": {
                    "components": [
                        {
                            "id": "comp-1",
                            "component": {
                                "gdm-stage-card": {"title": "Hello"}
                            }
                        }
                    ]
                },
                "root": "comp-1",
                "dataModelUpdate": {"some": "data"}
            }
        }
    })

    mock_broadcast_fn = AsyncMock()
    mock_generate_diagram_fn = AsyncMock()

    with patch("app.auth._STAGE_API_KEY", "test-key-123"):
        response = await handle_mcp(
            request=mock_request,
            broadcast_fn=mock_broadcast_fn,
            generate_diagram_fn=mock_generate_diagram_fn
        )
    
    assert response.status_code == 200
    body_data = json.loads(response.body.decode("utf-8"))
    assert body_data["id"] == 1
    assert "result" in body_data
    assert "Stage rendered successfully" in body_data["result"]["content"][0]["text"]

    # Verify order of broadcast_fn calls: surfaceUpdate -> dataModelUpdate -> beginRendering
    assert mock_broadcast_fn.call_count == 3
    mock_broadcast_fn.assert_any_call("spaces/test", {"type": "surfaceUpdate", "surfaceUpdate": {
        "components": [{"id": "comp-1", "component": {"gdm-stage-card": {"title": "Hello"}}}]
    }})
    mock_broadcast_fn.assert_any_call("spaces/test", {"type": "dataModelUpdate", "dataModelUpdate": {"some": "data"}})
    mock_broadcast_fn.assert_any_call("spaces/test", {"type": "beginRendering", "beginRendering": {"root": "comp-1"}})

@pytest.mark.asyncio
async def test_mcp_clear_stage_success():
    mock_request = AsyncMock(spec=Request)
    mock_request.headers = {"Authorization": "Bearer test-key-123"}
    mock_request.json = AsyncMock(return_value={
        "method": "tools/call",
        "id": 2,
        "params": {
            "name": "clear_stage",
            "arguments": {
                "space_id": "spaces/test"
            }
        }
    })

    mock_broadcast_fn = AsyncMock()
    mock_generate_diagram_fn = AsyncMock()

    with patch("app.auth._STAGE_API_KEY", "test-key-123"):
        response = await handle_mcp(
            request=mock_request,
            broadcast_fn=mock_broadcast_fn,
            generate_diagram_fn=mock_generate_diagram_fn
        )
    
    assert response.status_code == 200
    body_data = json.loads(response.body.decode("utf-8"))
    assert body_data["id"] == 2
    assert "result" in body_data
    assert "Stage cleared successfully" in body_data["result"]["content"][0]["text"]

    # Verify broadcast of deleteSurface
    mock_broadcast_fn.assert_called_once_with("spaces/test", {"type": "deleteSurface"})
