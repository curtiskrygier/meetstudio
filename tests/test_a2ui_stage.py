import json
import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from main import app
from app.a2ui_catalog import A2UI_CATALOG, validate_a2ui_surface, validate_a2ui_surface_detailed
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
                "component": "gdm-stage-card",
                "title": "Hello",
                "text": "World"
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
                "component": "gdm-unknown-component",
                "title": "Hello"
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
                    "component": "gdm-stage-card",
                    "title": "Hello"
                }
            ]
        },
        "root": "comp-1",
        "dataModelUpdate": {"some": "data"}
    }
    
    resp = client.post("/api/render-stage/spaces/test", json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    
    # Broadcast order: updateComponents -> updateDataModel -> createSurface
    assert mock_broadcast.call_count == 3
    mock_broadcast.assert_any_call("spaces/test", {"updateComponents": {"components": payload["surfaceUpdate"]["components"]}})
    mock_broadcast.assert_any_call("spaces/test", {"updateDataModel": payload["dataModelUpdate"]})
    mock_broadcast.assert_any_call("spaces/test", {"createSurface": {"catalogId": "gdm-v0.2", "theme": {}, "root": "comp-1"}})

def test_api_render_stage_validation_failure(mock_auth_key):
    headers = {"Authorization": f"Bearer {mock_auth_key}"}
    payload = {
        "surfaceUpdate": {
            "components": [
                {
                    "id": "comp-1",
                    "component": "gdm-unknown-component",
                    "title": "Hello"
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
                            "component": "gdm-stage-card",
                            "title": "Hello"
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
        "components": [{"id": "comp-1", "component": "gdm-stage-card", "title": "Hello"}]
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


def test_validate_a2ui_property_level_valid():
    surface_update = {
        "components": [
            {
                "id": "slate-1",
                "component": "gdm-standby-slate",
                "badge": "INTERMISSION",
                "title": "Short Break",
                "seconds": 120,
                "active": True
            }
        ]
    }
    errors = validate_a2ui_surface(surface_update)
    assert not errors


def test_validate_a2ui_property_level_invalid_extra():
    # warn-don't-block: an extra/unknown prop is a WARNING, not a blocking error.
    surface_update = {
        "components": [
            {
                "id": "slate-1",
                "component": "gdm-standby-slate",
                "badge": "INTERMISSION",
                "countdown": 120,  # Invalid extra property! (should be 'seconds')
                "active": True
            }
        ]
    }
    errors, warnings = validate_a2ui_surface_detailed(surface_update)
    assert not errors  # does NOT block the render
    assert any("countdown" in w and "property validation failed" in w for w in warnings)
    # backward-compatible helper still returns only blocking errors
    assert validate_a2ui_surface(surface_update) == []


def test_validate_a2ui_property_level_type_mismatch():
    # warn-don't-block: a prop type mismatch is a WARNING, not a blocking error.
    surface_update = {
        "components": [
            {
                "id": "slate-1",
                "component": "gdm-standby-slate",
                "seconds": "not-a-number",  # Type mismatch! (should be int)
                "active": True
            }
        ]
    }
    errors, warnings = validate_a2ui_surface_detailed(surface_update)
    assert not errors
    assert any("seconds" in w and "property validation failed" in w for w in warnings)


def test_validate_a2ui_missing_required_prop_is_warning():
    # A missing REQUIRED prop is advisory (warning), never blocks the surface —
    # the whole surface must still render so sibling components aren't lost.
    surface_update = {
        "components": [
            {
                "id": "mt-1",
                "component": "gdm-market-ticker",
                "macroRow": [],
                "holdingsRow": [],
                # 'active' (required) omitted
            }
        ]
    }
    errors, warnings = validate_a2ui_surface_detailed(surface_update)
    assert not errors
    assert any("active" in w for w in warnings)


def test_validate_unknown_component_name_blocks():
    # An unknown component NAME is a hard error — the renderer cannot draw it.
    surface_update = {
        "components": [
            {"id": "x", "component": "gdm-does-not-exist", "foo": 1}
        ]
    }
    errors, warnings = validate_a2ui_surface_detailed(surface_update)
    assert len(errors) == 1
    assert "gdm-does-not-exist" in errors[0]


def test_validate_a2ui_property_level_backward_compatibility():
    surface_update = {
        "components": [
            {
                "id": "dashboard-1",
                "component": "gdm-telemetry-dashboard",
                "title": "System Logs",
                "any_extra_property": "is_perfectly_fine"  # Lenient fallback!
            }
        ]
    }
    errors = validate_a2ui_surface(surface_update)
    assert not errors


def test_validate_gdm_3d_airspace_valid():
    surface_update = {
        "components": [
            {
                "id": "airspace-3d",
                "component": "gdm-3d-airspace",
                "flights": [
                    {"callsign": "AFR6129", "altitude": 3000, "speed": 220, "vrate": -1000}
                ],
                "cameraPitch": 35.0,
                "cameraYaw": 45.0,
                "showGlideSlope": True,
                "showTerrain": True,
                "zoom": 12.0,
                "lockedCallsign": "AFR6129",
                "cinematicOrbit": True,
                "autoTrack": False
            }
        ]
    }
    errors = validate_a2ui_surface(surface_update)
    assert not errors


def test_validate_gdm_3d_airspace_invalid_extra():
    surface_update = {
        "components": [
            {
                "id": "airspace-3d",
                "component": "gdm-3d-airspace",
                "cameraPitch": 35.0,
                "invalid_parameter_name": "value"  # Forbidden extra field!
            }
        ]
    }
    errors, warnings = validate_a2ui_surface_detailed(surface_update)
    assert not errors
    assert len(warnings) == 1
    assert "property validation failed" in warnings[0]
    assert "invalid_parameter_name" in warnings[0]


def test_validate_gdm_3d_airspace_invalid_type():
    surface_update = {
        "components": [
            {
                "id": "airspace-3d",
                "component": "gdm-3d-airspace",
                "cameraPitch": "flat-view"  # Should be float/int, not string!
            }
        ]
    }
    errors, warnings = validate_a2ui_surface_detailed(surface_update)
    assert not errors
    assert len(warnings) == 1
    assert "property validation failed" in warnings[0]
    assert "cameraPitch" in warnings[0]


def test_validate_gdm_3d_scene_valid():
    surface_update = {
        "components": [
            {
                "id": "scene-3d",
                "component": "gdm-3d-scene",
                "points": [
                    {"id": "pt-1", "x": 10.0, "y": 20.0, "z": 5.0, "label": "Point 1", "glyph": "circle", "size": 8}
                ],
                "links": [
                    {"from": "pt-1", "to": "LFBO"}
                ],
                "camera": {
                    "pitch": 45.0,
                    "yaw": 90.0,
                    "zoom": 1.5,
                    "autoOrbit": True
                },
                "terrain": True,
                "grid": True,
                "fog": True
            }
        ]
    }
    errors = validate_a2ui_surface(surface_update)
    assert not errors


def test_validate_gdm_market_ticker_valid():
    surface_update = {
        "components": [
            {
                "id": "market-ticker-1",
                "component": "gdm-market-ticker",
                "sections": [
                    {"label": "INDICES", "items": [
                        {"symbol": "SPX", "price": 5300.0, "changePercent": 0.5, "isUp": True, "label": "S&P 500"}
                    ]},
                    {"label": "CRYPTO", "items": [
                        {"symbol": "BTC", "price": 68000.0, "changePercent": 2.6, "isUp": True}
                    ]},
                ],
                "active": True,
                "badgeText": "GLOBAL MARKET SCAN",
                "accentColor": "#00f2ff",
                "watchCount": 5
            }
        ]
    }
    errors, warnings = validate_a2ui_surface_detailed(surface_update)
    assert not errors
    assert not warnings


def test_validate_gdm_market_ticker_invalid_extra():
    surface_update = {
        "components": [
            {
                "id": "market-ticker-1",
                "component": "gdm-market-ticker",
                "active": True,
                "sections": [],
                "some_invalid_field": "value"  # Forbidden extra field!
            }
        ]
    }
    errors, warnings = validate_a2ui_surface_detailed(surface_update)
    assert not errors
    assert any("some_invalid_field" in w and "property validation failed" in w for w in warnings)


def test_validate_gdm_market_ticker_invalid_type():
    surface_update = {
        "components": [
            {
                "id": "market-ticker-1",
                "component": "gdm-market-ticker",
                "active": "maybe",  # Should be boolean, not string!
                "sections": []
            }
        ]
    }
    errors, warnings = validate_a2ui_surface_detailed(surface_update)
    assert not errors
    assert any("active" in w and "property validation failed" in w for w in warnings)


def test_validate_gdm_composable_primitives_valid():
    surface_update = {
        "components": [
            {
                "id": "composed-root",
                "component": "gdm-container",
                "direction": "column",
                "justify": "center",
                "align": "stretch",
                "gap": "12px",
                "padding": "24px",
                "background": "transparent",
                "border": "1px solid red",
                "borderRadius": "16px",
                "width": "100%",
                "height": "100%",
                "glass": True,
                "scrollable": False,
                "grow": 1.0,
                "shrink": 0.0,
                "margin": "10px",
                "children": {"explicitList": ["child-text", "child-badge"]}
            },
            {
                "id": "child-text",
                "component": "gdm-text",
                "content": "Hello Universe",
                "size": "h1",
                "weight": "bold",
                "color": "accent",
                "align": "center",
                "font": "mono",
                "opacity": 0.9,
                "letterSpacing": "1px",
                "uppercase": True,
                "pulse": True
            },
            {
                "id": "child-badge",
                "component": "gdm-badge",
                "text": "ONLINE",
                "type": "success",
                "pulse": True,
                "outline": False
            },
            {
                "id": "child-progress",
                "component": "gdm-progress",
                "value": 45.5,
                "color": "#00f2ff",
                "height": "12px",
                "animated": True,
                "glow": True
            },
            {
                "id": "child-divider",
                "component": "gdm-divider",
                "vertical": True,
                "color": "#fff",
                "thickness": "2px",
                "margin": "15px"
            },
            {
                "id": "child-icon",
                "component": "gdm-icon",
                "name": "sonar",
                "color": "success",
                "size": "32px"
            },
            {
                "id": "child-button",
                "component": "gdm-button",
                "text": "Click Me",
                "action": {
                    "event": {
                        "name": "btn_click_1"
                    }
                },
                "icon": "activity",
                "type": "primary",
                "disabled": False
            },
            {
                "id": "child-clock",
                "component": "gdm-clock",
                "showClock": True,
                "showDate": True,
                "format": "12h",
                "timezone": "America/New_York",
                "accentColor": "warning"
            },
            {
                "id": "child-sparkline",
                "component": "gdm-sparkline",
                "data": "10,20,15,30,25,40",
                "color": "accent",
                "width": "100px",
                "height": "40px",
                "fill": True
            },
            {
                "id": "child-table",
                "component": "gdm-table-view",
                "headers": ["Col 1", "Col 2"],
                "rows": [["Cell A1", "Cell B1"], ["Cell A2", "Cell B2"]],
                "accentColor": "#ff00ff"
            },
            {
                "id": "child-trend",
                "component": "gdm-trend-value",
                "symbol": "BTC",
                "label": "Bitcoin",
                "price": 68000.5,
                "change": 2.5,
                "isUp": True,
                "precision": 2
            },
            {
                "id": "child-scroller",
                "component": "gdm-scroller",
                "speed": "15s",
                "direction": "left",
                "active": True,
                "children": {"explicitList": ["child-trend"]}
            }
        ]
    }
    errors, warnings = validate_a2ui_surface_detailed(surface_update)
    assert not errors
    assert not warnings


def test_validate_gdm_composable_primitives_invalid():
    surface_update = {
        "components": [
            {
                "id": "child-badge-invalid",
                "component": "gdm-badge",
                "text": "ONLINE",
                "pulse": "maybe",
                "extra_unsupported_field": 123
            }
        ]
    }
    errors, warnings = validate_a2ui_surface_detailed(surface_update)
    assert not errors
    assert len(warnings) >= 1
    assert any("pulse" in w and "property validation failed" in w for w in warnings)
    assert any("extra_unsupported_field" in w and "property validation failed" in w for w in warnings)
