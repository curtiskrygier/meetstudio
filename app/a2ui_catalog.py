"""
A2UI Catalog configuration and validation logic.
"""
from pydantic import BaseModel, ConfigDict, ValidationError
from typing import Optional, Union, List, Dict, Any

A2UI_CATALOG = frozenset({
    "gdm-stage-card",
    "gdm-chyron",
    "gdm-ticker",
    "gdm-standby-slate",
    "gdm-chat-card",
    "gdm-stage-grid",
    "gdm-image-panel",
    "gdm-video-panel",
    "gdm-iframe-panel",
    "gdm-transcript-view",
    "gdm-telemetry-dashboard",
    "gdm-radar-view",
    "gdm-poll-overlay",
    "gdm-notepad",
    "gdm-captions",
    "gdm-diagram-view",
    "gdm-mermaid-panel",
    "gdm-html-panel",
    "gdm-emoji-burst",
    "gdm-camera-panel",
    "gdm-draw-overlay",
    "gdm-pointer",
    "gdm-terminal-panel",
    "gdm-doc-panel",
    "gdm-laser-sweep",
    "gdm-3d-airspace",
})

# --- Pydantic Schemas for Core Custom Elements ---

class GdmStageGrid(BaseModel):
    model_config = ConfigDict(extra="forbid")
    layout: Optional[str] = None
    focusedPanel: Optional[int] = None
    children: Optional[Dict[str, Any]] = None

class GdmStandbySlate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    badge: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    seconds: Optional[int] = None
    active: Optional[bool] = None

class GdmRadarView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    flights: Optional[Union[List[Any], Dict[str, Any], str]] = None
    lockedCallsign: Optional[str] = None
    zoom: Optional[float] = None
    stretched: Optional[bool] = None

class GdmHtmlPanel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    html: Optional[str] = None
    title: Optional[str] = None
    overlay: Optional[bool] = None
    version: Optional[int] = None

class GdmTicker(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: Optional[str] = None
    active: Optional[bool] = None
    badgeText: Optional[str] = None
    badgeColor: Optional[str] = None
    accentColor: Optional[str] = None
    textColor: Optional[str] = None
    fontSize: Optional[int] = None
    height: Optional[int] = None
    scrollSpeed: Optional[int] = None

class GdmChyron(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Optional[str] = None
    subtitle: Optional[str] = None
    active: Optional[bool] = None
    accentColor: Optional[str] = None
    titleColor: Optional[str] = None
    subtitleColor: Optional[str] = None
    titleSize: Optional[int] = None
    subtitleSize: Optional[int] = None
    bottom: Optional[int] = None
    left: Optional[int] = None

class GdmStageCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Optional[str] = None
    text: Optional[str] = None
    accent: Optional[str] = None
    mode: Optional[str] = None

class GdmChatCard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sender: Optional[str] = None
    text: Optional[str] = None
    avatar: Optional[str] = None
    duration: Optional[int] = None

class Gdm3DAirspace(BaseModel):
    model_config = ConfigDict(extra="forbid")
    flights: Optional[Union[List[Any], Dict[str, Any], str]] = None
    lockedCallsign: Optional[str] = None
    cameraPitch: Optional[float] = None
    cameraYaw: Optional[float] = None
    showGlideSlope: Optional[bool] = None
    showTerrain: Optional[bool] = None
    zoom: Optional[float] = None

# For any catalog component that does not have a strict schema modeled yet
class GenericComponent(BaseModel):
    model_config = ConfigDict(extra="allow")

COMPONENT_SCHEMAS: Dict[str, Any] = {
    "gdm-stage-grid": GdmStageGrid,
    "gdm-standby-slate": GdmStandbySlate,
    "gdm-radar-view": GdmRadarView,
    "gdm-html-panel": GdmHtmlPanel,
    "gdm-ticker": GdmTicker,
    "gdm-chyron": GdmChyron,
    "gdm-stage-card": GdmStageCard,
    "gdm-chat-card": GdmChatCard,
    "gdm-3d-airspace": Gdm3DAirspace,
}

def validate_a2ui_surface(surface_update: dict) -> list[str]:
    """Returns a list of validation errors; empty = valid."""
    errors = []
    components = surface_update.get("components", [])
    if not components:
        errors.append("surfaceUpdate.components is empty")
        return errors
    for comp in components:
        comp_id = comp.get("id", "<no-id>")
        component_def = comp.get("component", {})
        if not component_def:
            errors.append(f"Component '{comp_id}' has no component definition")
            continue
        element_name = next(iter(component_def)).lower()
        if element_name not in A2UI_CATALOG:
            errors.append(f"Component '{element_name}' not in catalog (id={comp_id})")
            continue
        
        props = component_def.get(element_name)
        if props is None:
            props = {}
        if not isinstance(props, dict):
            errors.append(f"Component '{element_name}' properties must be a dictionary (id={comp_id})")
            continue

        # Schema-based property validation using Pydantic
        schema_cls = COMPONENT_SCHEMAS.get(element_name, GenericComponent)
        try:
            schema_cls(**props)
        except ValidationError as e:
            for err in e.errors():
                # Format location gracefully (e.g. "loc_1.loc_2" or simply "field_name")
                loc_str = ".".join(str(loc) for loc in err["loc"])
                errors.append(
                    f"Component '{element_name}' property validation failed (id={comp_id}): "
                    f"Field '{loc_str}' {err['msg']} (type={err['type']})"
                )

    return errors
