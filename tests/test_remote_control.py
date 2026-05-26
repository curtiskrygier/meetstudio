import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from main import app

client = TestClient(app)

@pytest.fixture
def mock_broadcast():
    with patch("main.broadcast_to_stage", new_callable=AsyncMock) as mock:
        yield mock

@pytest.fixture
def mock_auth_key():
    with patch("app.auth._STAGE_API_KEY", "test-key-123"):
        yield "test-key-123"

def test_unauthorized_access(mock_auth_key):
    # Testing endpoints without the Bearer token must return 401
    endpoints = [
        ("/api/pointer/spaces/test", {"x": 50, "y": 50}),
        ("/api/draw/spaces/test", {"action": "clear"}),
        ("/api/notepad/spaces/test", {"action": "overwrite", "text": "Hello"}),
        ("/api/layout-config/spaces/test", {"layout": "split"}),
        ("/api/theme-config/spaces/test", {"theme": "cyberpunk"}),
        ("/api/stage-audio/spaces/test", {}),
    ]
    for url, payload in endpoints:
        resp = client.post(url, json=payload)
        assert resp.status_code == 401
        assert resp.json()["detail"]["error"] == "Unauthorized"

def test_pointer_endpoint(mock_auth_key, mock_broadcast):
    headers = {"Authorization": f"Bearer {mock_auth_key}"}
    payload = {"x": 42.5, "y": 80.1, "active": True}
    
    resp = client.post("/api/pointer/spaces/test", json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    
    mock_broadcast.assert_called_once_with("spaces/test", {
        "type": "pointer_event",
        "x": 42.5,
        "y": 80.1,
        "active": True
    })

def test_draw_endpoint_line(mock_auth_key, mock_broadcast):
    headers = {"Authorization": f"Bearer {mock_auth_key}"}
    payload = {
        "action": "line",
        "x1": 10.0,
        "y1": 20.0,
        "x2": 30.0,
        "y2": 40.0,
        "color": "#00ff00",
        "lineWidth": 5
    }
    
    resp = client.post("/api/draw/spaces/test", json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    
    mock_broadcast.assert_called_once_with("spaces/test", {
        "type": "draw_event",
        "action": "line",
        "x1": 10.0,
        "y1": 20.0,
        "x2": 30.0,
        "y2": 40.0,
        "color": "#00ff00",
        "lineWidth": 5
    })

def test_draw_endpoint_rect(mock_auth_key, mock_broadcast):
    headers = {"Authorization": f"Bearer {mock_auth_key}"}
    payload = {
        "action": "rect",
        "x": 15.0,
        "y": 25.0,
        "w": 10.0,
        "h": 20.0,
        "color": "#ff0000"
    }
    
    resp = client.post("/api/draw/spaces/test", json=payload, headers=headers)
    assert resp.status_code == 200
    
    mock_broadcast.assert_called_once_with("spaces/test", {
        "type": "draw_event",
        "action": "rect",
        "x": 15.0,
        "y": 25.0,
        "w": 10.0,
        "h": 20.0,
        "color": "#ff0000"
    })

def test_draw_endpoint_text(mock_auth_key, mock_broadcast):
    headers = {"Authorization": f"Bearer {mock_auth_key}"}
    payload = {
        "action": "text",
        "x": 50.0,
        "y": 50.0,
        "text": "Hello, Stage!",
        "font": "16px Arial",
        "color": "#ffffff"
    }
    
    resp = client.post("/api/draw/spaces/test", json=payload, headers=headers)
    assert resp.status_code == 200
    
    mock_broadcast.assert_called_once_with("spaces/test", {
        "type": "draw_event",
        "action": "text",
        "x": 50.0,
        "y": 50.0,
        "text": "Hello, Stage!",
        "font": "16px Arial",
        "color": "#ffffff"
    })

def test_notepad_endpoint(mock_auth_key, mock_broadcast):
    headers = {"Authorization": f"Bearer {mock_auth_key}"}
    payload = {
        "action": "append",
        "text": " some extra log text"
    }
    
    resp = client.post("/api/notepad/spaces/test", json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    
    mock_broadcast.assert_called_once_with("spaces/test", {
        "type": "notepad_event",
        "action": "append",
        "text": " some extra log text"
    })

def test_layout_config_endpoint(mock_auth_key, mock_broadcast):
    headers = {"Authorization": f"Bearer {mock_auth_key}"}
    payload = {"layout": "grid"}
    
    resp = client.post("/api/layout-config/spaces/test", json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    
    mock_broadcast.assert_called_once_with("spaces/test", {
        "type": "layout_event",
        "layout": "grid"
    })

def test_theme_config_endpoint(mock_auth_key, mock_broadcast):
    headers = {"Authorization": f"Bearer {mock_auth_key}"}
    payload = {"theme": "cyberpunk"}
    
    resp = client.post("/api/theme-config/spaces/test", json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    
    mock_broadcast.assert_called_once_with("spaces/test", {
        "type": "theme_event",
        "theme": "cyberpunk"
    })

def test_stage_audio_endpoint(mock_auth_key, mock_broadcast):
    headers = {"Authorization": f"Bearer {mock_auth_key}"}
    audio_payload = b"RIFFsomethingpcmbytes"
    
    resp = client.post("/api/stage-audio/spaces/test", content=audio_payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "bytes": len(audio_payload)}
    
    import base64
    mock_broadcast.assert_called_once_with("spaces/test", {
        "type": "audio",
        "data": base64.b64encode(audio_payload).decode("utf-8")
    })

def test_stage_audio_empty_body(mock_auth_key):
    headers = {"Authorization": f"Bearer {mock_auth_key}"}
    resp = client.post("/api/stage-audio/spaces/test", content=b"", headers=headers)
    assert resp.status_code == 400
    assert "Empty body" in resp.json()["detail"]
