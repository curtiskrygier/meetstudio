"""
A2UI Catalog — single source of truth (dynamically loaded from JSON spec).

Everything about the A2UI component contract is loaded once from the canonical
JSON specification (gdm-v0.2.json) and derived from there:

  * `A2UI_CATALOG`            — the frozenset of valid component names
  * `COMPONENT_SCHEMAS`       — Pydantic models for prop validation (strict comps)
  * `validate_a2ui_surface*`  — surface validation
  * `render_catalog_prompt()` — the catalogue prose injected into the system prompt
  * `render_mcp_component_summary()` — the supported-component blurb for the MCP tool

Validation follows the A2UI paradigm: the catalogue *name* is the hard contract,
while prop-level warnings are non-blocking advisory findings.
"""
import os
import sys
import json
from dataclasses import dataclass, field
from typing import Optional, Union, List, Dict, Any
from collections import namedtuple
from pydantic import BaseModel, ConfigDict, ValidationError, create_model

# --- Descriptor models ------------------------------------------------------

@dataclass
class Prop:
    name: str
    type_label: Optional[str] = None   # prose type, e.g. "string"
    req: Optional[bool] = None          # True -> required, False -> optional, None -> omit
    note: str = ""
    pytype: Any = None                  # python type used for Pydantic validation
    doc: bool = True                    # include in prompt prose


@dataclass
class Comp:
    group: str                          # "root" | "panel" | "overlay" | "molecule" | "atom" | "layout"
    desc: str
    props: List[Prop] = field(default_factory=list)
    strict: bool = False                # enforce extra="forbid" + typed props
    props_label: str = "Props"
    in_prompt: bool = True              # include in system prompt catalogue prose


# Nested item schema reused by gdm-market-ticker rows.
class TickerItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str
    price: float
    changePercent: float
    isUp: bool
    label: Optional[str] = None


# A binding-aware union used for variables or data-model references.
_FlightsType = Union[List[Any], Dict[str, Any], str]


# --- Dynamic Catalogue Loader -----------------------------------------------

def _load_catalog_dict() -> Dict[str, Comp]:
    """Resolve the JSON path, parse components, and construct Comp and Prop objects."""
    workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    submodule_path = os.path.join(workspace_dir, "catalogue", "spec", "gdm-v0.2.json")
    fallback_path = os.path.join(workspace_dir, "catalog", "gdm-v0.2.json")

    # Fallback resolution
    if os.path.exists(submodule_path):
        catalog_path = submodule_path
    elif os.path.exists(fallback_path):
        catalog_path = fallback_path
    else:
        raise FileNotFoundError(
            f"A2UI Catalog JSON not found. Checked submodule ({submodule_path}) "
            f"and fallback ({fallback_path})."
        )

    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog_data = json.load(f)

    # Primitive JSON -> Python type mapping
    TYPE_MAPPING = {
        "string": str,
        "boolean": bool,
        "integer": int,
        "number": float,
        "array": list,
        "object": dict,
        "any": Any,
    }

    # Overrides for the complex Union cases and explicit typed properties
    PYTYPE_OVERRIDES = {
        # gdm-radar-view
        ("gdm-radar-view", "flights"): _FlightsType,

        # gdm-3d-airspace
        ("gdm-3d-airspace", "flights"): _FlightsType,
        ("gdm-3d-airspace", "lockedCallsign"): str,
        ("gdm-3d-airspace", "cameraPitch"): float,
        ("gdm-3d-airspace", "cameraYaw"): float,
        ("gdm-3d-airspace", "showGlideSlope"): bool,
        ("gdm-3d-airspace", "showTerrain"): bool,
        ("gdm-3d-airspace", "zoom"): float,
        ("gdm-3d-airspace", "cinematicOrbit"): bool,
        ("gdm-3d-airspace", "autoTrack"): bool,
        ("gdm-3d-airspace", "compact"): bool,

        # gdm-3d-scene
        ("gdm-3d-scene", "points"): Union[List[Any], Dict[str, Any], str],
        ("gdm-3d-scene", "links"): Union[List[Any], Dict[str, Any], str],
        ("gdm-3d-scene", "camera"): dict,
        ("gdm-3d-scene", "terrain"): bool,
        ("gdm-3d-scene", "grid"): bool,
        ("gdm-3d-scene", "fog"): bool,

        # gdm-market-ticker
        ("gdm-market-ticker", "sections"): Union[List[Any], Dict[str, Any], str],
        ("gdm-market-ticker", "active"): bool,
        ("gdm-market-ticker", "badgeText"): str,
        ("gdm-market-ticker", "accentColor"): str,
        ("gdm-market-ticker", "watchCount"): int,
        ("gdm-market-ticker", "showClock"): bool,
        ("gdm-market-ticker", "showDate"): bool,

        # gdm-flip-slate
        ("gdm-flip-slate", "text"): str,
        ("gdm-flip-slate", "active"): bool,
        ("gdm-flip-slate", "badgeText"): str,
        ("gdm-flip-slate", "subtitle"): str,
        ("gdm-flip-slate", "accentColor"): str,
        ("gdm-flip-slate", "delayMs"): int,

        # gdm-table-view
        ("gdm-table-view", "headers"): Union[List[str], str],
        ("gdm-table-view", "rows"): Union[List[Any], str],

        # layout / container children
        ("gdm-stage-grid", "children"): list,
        ("gdm-container", "children"): list,
        ("gdm-scroller", "children"): list,
    }

    catalog: Dict[str, Comp] = {}
    for comp_name, comp_info in catalog_data.get("components", {}).items():
        props: List[Prop] = []
        for prop_name, prop_info in comp_info.get("properties", {}).items():
            type_label = prop_info.get("type", "any")
            req = prop_info.get("required")
            note = prop_info.get("description", "")
            doc_flag = prop_info.get("doc", True)

            # Assign pytype: Check override dictionary first, then fallback to primitive mapping
            pytype = PYTYPE_OVERRIDES.get((comp_name, prop_name))
            if pytype is None:
                pytype = TYPE_MAPPING.get(type_label, str)

            props.append(Prop(
                name=prop_name,
                type_label=type_label,
                req=True if req is True else (False if req is False else None),
                note=note,
                pytype=pytype,
                doc=doc_flag,
            ))

        props_label = "Props/Bindings" if comp_name in ("gdm-telemetry-dashboard", "gdm-radar-view") else "Props"

        catalog[comp_name] = Comp(
            group=comp_info.get("group", "panel"),
            desc=comp_info.get("description", ""),
            props=props,
            strict=comp_info.get("strict", False),
            props_label=props_label,
            in_prompt=comp_info.get("in_prompt", True),
        )

    return catalog


# Expose CATALOG as a statically module-bound dictionary matching the old signature
CATALOG: Dict[str, Comp] = _load_catalog_dict()


# --- Derived artifacts ------------------------------------------------------

A2UI_CATALOG = frozenset(CATALOG.keys())


def _build_model(name: str, comp: Comp):
    fields: Dict[str, Any] = {}
    for p in comp.props:
        pt = p.pytype if p.pytype is not None else str
        if p.req:
            fields[p.name] = (pt, ...)
        else:
            fields[p.name] = (Optional[pt], None)
    return create_model(
        name.replace("-", "_"),
        __config__=ConfigDict(extra="forbid"),
        **fields,
    )


COMPONENT_SCHEMAS: Dict[str, Any] = {
    name: _build_model(name, comp)
    for name, comp in CATALOG.items()
    if comp.strict
}


# --- Validation -------------------------------------------------------------

ValidationResult = namedtuple("ValidationResult", ["errors", "warnings"])


def validate_a2ui_surface_detailed(surface_update: dict) -> ValidationResult:
    """Validate a surfaceUpdate, splitting findings into blocking errors and
    non-blocking warnings.
    """
    errors: List[str] = []
    warnings: List[str] = []

    components = surface_update.get("components", [])
    if not components:
        errors.append("surfaceUpdate.components is empty")
        return ValidationResult(errors, warnings)

    for comp in components:
        comp_id = comp.get("id", "<no-id>")
        element_name = comp.get("component", "")
        if not element_name:
            errors.append(f"Component '{comp_id}' has no component definition")
            continue

        element_name = element_name.lower()
        if element_name not in A2UI_CATALOG:
            errors.append(f"Component '{element_name}' not in catalog (id={comp_id})")
            continue

        props = {k: v for k, v in comp.items() if k not in ("id", "component")}

        schema_cls = COMPONENT_SCHEMAS.get(element_name)
        if schema_cls is None:
            continue  # lenient component

        try:
            schema_cls(**props)
        except ValidationError as e:
            for err in e.errors():
                loc_str = ".".join(str(loc) for loc in err["loc"])
                warnings.append(
                    f"Component '{element_name}' property validation failed (id={comp_id}): "
                    f"Field '{loc_str}' {err['msg']} (type={err['type']})"
                )

    return ValidationResult(errors, warnings)


def validate_a2ui_surface(surface_update: dict) -> List[str]:
    """Backward-compatible entry point returning only BLOCKING errors."""
    return validate_a2ui_surface_detailed(surface_update).errors


# --- Prose / summary generation ---------------------------------------------

def _format_prop(p: Prop) -> str:
    if p.type_label is None:
        return f"`{p.name}` {p.note}"
    paren = p.type_label
    if p.req is True:
        paren += ", required"
    elif p.req is False:
        paren += ", optional"
    return f"`{p.name}` ({paren}): {p.note}"


def render_catalog_prompt() -> str:
    """Generate the A2UI COMPONENT CATALOG section injected into the system prompt."""
    n = sum(1 for c in CATALOG.values() if c.in_prompt)
    lines: List[str] = [
        "A2UI COMPONENT CATALOG:",
        f"The A2UI Component Catalog provides a rich vocabulary of {n} components "
        "consisting of layouts, panels, overlays, atoms, and molecules:",
        "",
    ]
    groups = [
        ("layout", "1. Layout Components (Containers and Grids):"),
        ("panel", "2. Panel Components (Children of the layout grid):"),
        ("overlay", "3. Overlays (Layers drawn on top of panels):"),
        ("atom", "4. Atom Components (Visual building blocks):"),
        ("molecule", "5. Molecule Components (Interactive rich widgets):"),
    ]
    for gkey, header in groups:
        lines.append(header)
        for name, comp in CATALOG.items():
            if not comp.in_prompt or comp.group != gkey:
                continue
            lines.append(f"   - `{name}`: {comp.desc}")
            doc_props = [p for p in comp.props if p.doc]
            if doc_props:
                lines.append(f"     - {comp.props_label}:")
                for p in doc_props:
                    lines.append("       - " + _format_prop(p))
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def render_mcp_component_summary() -> str:
    """Compact supported-component blurb for the MCP render_stage tool description."""
    parts: List[str] = []
    for name, comp in CATALOG.items():
        doc_props = [p.name for p in comp.props if p.doc]
        if doc_props:
            parts.append(f"{name} ({', '.join(doc_props)})")
        else:
            parts.append(name)
    return "Supported components in catalog: " + ", ".join(parts) + "."


def emit_json_catalog():
    """Convert dynamically loaded CATALOG back to v0.9-shaped JSON spec (if needed)."""
    version = "0.2"
    if "--version" in sys.argv:
        try:
            idx = sys.argv.index("--version")
            version = sys.argv[idx + 1]
        except (ValueError, IndexError):
            pass

    catalog_id = f"gdm-v{version}"
    catalog_data = {
        "catalogId": catalog_id,
        "description": "Google Meet Studio GDM Component Catalog",
        "components": {}
    }

    for comp_name, comp in CATALOG.items():
        props_dict = {}
        for p in comp.props:
            prop_info = {
                "type": p.type_label or "any",
                "required": p.req if p.req is not None else False,
                "description": p.note
            }
            # Only serialize if False to keep JSON specs neat
            if not p.doc:
                prop_info["doc"] = False
            props_dict[p.name] = prop_info
            
        comp_info = {
            "group": comp.group,
            "description": comp.desc,
            "strict": comp.strict,
            "properties": props_dict
        }
        if not comp.in_prompt:
            comp_info["in_prompt"] = False
            
        catalog_data["components"][comp_name] = comp_info

    workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    catalog_dir = os.path.join(workspace_dir, "catalog")
    os.makedirs(catalog_dir, exist_ok=True)
    catalog_path = os.path.join(catalog_dir, f"{catalog_id}.json")

    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog_data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Catalog JSON successfully generated and written to: {catalog_path}", file=sys.stderr)
    print(json.dumps(catalog_data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    if "--emit-json" in sys.argv:
        emit_json_catalog()
    else:
        print("Usage: python3 -m app.a2ui_catalog --emit-json")
