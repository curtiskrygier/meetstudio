"""
A2UI Catalog configuration and validation logic.
"""

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
})

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
    return errors
