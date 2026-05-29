# ═══════════════════════════════════════════════════════════════════════════
# STAGED FILE — destination: playbooks/templates.py (NEW)
#
# ## TODO before apply
#   - Templates are PURE (sync, no network, no async). Data is always
#     resolved by yaml_loader before the template runs. Don't import
#     data_sources here.
#   - Sizes/colors/letterSpacing values are tuned for the existing
#     phosphor/cyan palette. Tweak the PHOSPHOR/CYAN constants if you
#     re-skin.
#   - Adding a sixth template? (1) write the function, (2) add to TEMPLATES
#     dict at the bottom. No other file changes.
# ═══════════════════════════════════════════════════════════════════════════
"""Slide template library — the substrate.

Each template takes (slide_id, cfg, data) and returns a list of A2UI
component dicts ready for `render-stage`. Templates are pure substitution:
they pick layout, pick atoms, and fill prop values from cfg + data. They
never reach for the network — that's yaml_loader's job before us.

Five templates ship in v0:
  - title              : hero badge + glitch title + typeOn subtitle + optional next button
  - hero_stat          : single huge number + delta — data-binding flagship
  - split_with_action  : left narrative + right action button column
  - list_5             : five staggered bullet points
  - signoff            : multi-line restaurant payoff + brand callout
"""

import re
from typing import List, Dict, Any

PHOSPHOR = "#00ff88"
CYAN     = "#00f2ff"
WHITE    = "white"

# Named color shorthands accepted in YAML; raw hex strings also work.
_COLOR_NAMES = {
    "white":    "white",
    "phosphor": PHOSPHOR,
    "cyan":     CYAN,
    "mute":     "rgba(255,255,255,0.55)",
}


def C(cid: str, el: str, props: dict) -> dict:
    """A2UI component tuple — matches project convention."""
    return {"id": cid, "component": {el: props}}


def _interpolate(value, data: dict):
    """Substitute {{ KEY }} tokens in a string with values from `data`.
    Non-string scalars (int, float, bool, None) pass through untouched —
    YAML's `value: 48.2` is a valid scalar, not a template string.
    Missing keys leave the token visible so the author sees what's not
    resolving instead of silently dropping content."""
    if not isinstance(value, str):
        return value
    if "{{" not in value:
        return value
    def sub(m: re.Match) -> str:
        key = m.group(1).strip()
        return str(data[key]) if key in data else m.group(0)
    return re.sub(r"\{\{\s*([\w.]+)\s*\}\}", sub, value)


def _color(name_or_hex: str | None, default: str = "white") -> str:
    """Resolve a YAML color shorthand to a renderable value. Pass-through
    for raw hex / rgba strings."""
    if not name_or_hex:
        return default
    return _COLOR_NAMES.get(name_or_hex, name_or_hex)


def _make_action(action_cfg: dict | None, ctx: dict) -> dict | None:
    """Map YAML action shorthands to a full gdm-button `action` prop.

        { fires: slide_id }     → fire mode, endpoint computed
        { links: url }          → link mode
        { emits: event_name }   → emit mode
        { agent: action_id }    → agent mode (legacy back-compat)

    Returns None if no recognisable shorthand present."""
    if not action_cfg:
        return None
    if "fires" in action_cfg:
        return {
            "type": "fire",
            "endpoint": f"/api/playbook/fire/{ctx['playbook_name']}/{action_cfg['fires']}/{ctx['space_id']}",
        }
    if "links" in action_cfg:
        return {"type": "link", "url": action_cfg["links"],
                "newTab": action_cfg.get("newTab", True)}
    if "emits" in action_cfg:
        return {"type": "emit", "event": action_cfg["emits"],
                "detail": action_cfg.get("detail")}
    if "agent" in action_cfg:
        return {"type": "agent", "actionId": action_cfg["agent"],
                "payload": action_cfg.get("payload")}
    return None


# ────────────────────────────────────────────────────────────────────────────
# Template 1 — title
# ────────────────────────────────────────────────────────────────────────────

def title_template(slide_id: str, cfg: dict, data: dict) -> List[Dict]:
    """Hero title card. Badge above (optional), glitch headline, typeOn
    subtitle, optional next-action button below."""
    badge    = cfg.get("badge") or {}
    next_act = cfg.get("next_action") or {}
    ctx      = {"playbook_name": cfg["playbook_name"], "space_id": cfg["space_id"]}
    action   = _make_action(next_act, ctx)

    children = [f"{slide_id}_badge", f"{slide_id}_title", f"{slide_id}_sub"]
    if action:
        children.append(f"{slide_id}_btn")

    out = [
        C("root", "gdm-stage-grid", {"layout": "hero",
                                     "children": {"explicitList": ["main"]}}),
        C("main", "gdm-container", {"direction": "column", "justify": "center",
                                    "align": "center", "grow": 1,
                                    "gap": "24px", "padding": "60px",
                                    "width": "100%", "height": "100%",
                                    "children": {"explicitList": children}}),
        C(f"{slide_id}_badge", "gdm-badge", {
            "text":  badge.get("text", ""),
            "type":  badge.get("type", "primary"),
            "pulse": badge.get("pulse", False),
        }),
        C(f"{slide_id}_title", "gdm-text", {
            "content": _interpolate(cfg.get("title", ""), data),
            "size": cfg.get("title_size", "84px"),
            "color": _color(cfg.get("title_color"), "white"),
            "font": "mono", "weight": "900",
            "letterSpacing": "0.04em", "glitch": True,
        }),
        C(f"{slide_id}_sub", "gdm-text", {
            "content": _interpolate(cfg.get("subtitle", ""), data),
            "size": "22px",
            "color": "rgba(0,255,136,0.7)",
            "font": "mono", "letterSpacing": "0.18em",
            "uppercase": True, "typeOn": True,
        }),
    ]
    if action:
        out.append(C(f"{slide_id}_btn", "gdm-button", {
            "text":    next_act.get("text", "Next"),
            "variant": next_act.get("variant", "primary"),
            "size":    next_act.get("size", "lg"),
            "pulse":   next_act.get("pulse", True),
            "action":  action,
        }))
    return out


# ────────────────────────────────────────────────────────────────────────────
# Template 2 — hero_stat
# ────────────────────────────────────────────────────────────────────────────

def hero_stat_template(slide_id: str, cfg: dict, data: dict) -> List[Dict]:
    """Single dominant number + delta. flip atom on the value makes it
    shimmer character-by-character on each tick refresh."""
    badge    = cfg.get("badge") or {}
    is_up    = bool(cfg.get("is_up", True))
    next_act = cfg.get("next_action") or {}
    ctx      = {"playbook_name": cfg["playbook_name"], "space_id": cfg["space_id"]}
    action   = _make_action(next_act, ctx)

    children = [f"{slide_id}_badge", f"{slide_id}_label",
                f"{slide_id}_value", f"{slide_id}_delta"]
    if action:
        children.append(f"{slide_id}_btn")

    out = [
        C("root", "gdm-stage-grid", {"layout": "hero",
                                     "children": {"explicitList": ["main"]}}),
        C("main", "gdm-container", {"direction": "column", "justify": "center",
                                    "align": "center", "grow": 1,
                                    "gap": "18px", "padding": "60px",
                                    "width": "100%", "height": "100%",
                                    "children": {"explicitList": children}}),
        C(f"{slide_id}_badge", "gdm-badge", {
            "text":  badge.get("text", ""),
            "type":  badge.get("type", "primary"),
            "pulse": badge.get("pulse", False),
        }),
        C(f"{slide_id}_label", "gdm-text", {
            "content": cfg.get("label", ""),
            "size": "24px",
            "color": "rgba(255,255,255,0.55)",
            "font": "mono", "letterSpacing": "0.18em", "uppercase": True,
        }),
        C(f"{slide_id}_value", "gdm-text", {
            "content": str(_interpolate(cfg.get("value", ""), data)),
            "size": cfg.get("value_size", "144px"),
            "color": "white", "font": "mono", "weight": "900",
            "letterSpacing": "0.02em", "flip": True,
        }),
        C(f"{slide_id}_delta", "gdm-text", {
            "content": str(_interpolate(cfg.get("delta", ""), data)),
            "size": "40px",
            "color": "#19d27a" if is_up else "#ff5d5d",
            "font": "mono", "weight": "800", "flip": True,
        }),
    ]
    if action:
        out.append(C(f"{slide_id}_btn", "gdm-button", {
            "text":    next_act.get("text", "Next"),
            "variant": next_act.get("variant", "primary"),
            "size":    next_act.get("size", "lg"),
            "pulse":   next_act.get("pulse", True),
            "action":  action,
        }))
    return out


# ────────────────────────────────────────────────────────────────────────────
# Template 3 — split_with_action
# ────────────────────────────────────────────────────────────────────────────

def split_with_action_template(slide_id: str, cfg: dict, data: dict) -> List[Dict]:
    """Asymmetric two-panel layout. Left: narrative (badge + glitch title +
    typeOn body). Right: a column of action buttons (link / fire / agent /
    emit). Reveals stagger left-then-right."""
    left      = cfg.get("left") or {}
    right     = cfg.get("right") or {}
    l_badge   = left.get("badge") or {}
    actions   = right.get("actions") or []
    ctx       = {"playbook_name": cfg["playbook_name"], "space_id": cfg["space_id"]}

    btn_ids = [f"{slide_id}_btn_{i}" for i, _ in enumerate(actions)]

    out = [
        C("root", "gdm-stage-grid", {"layout": "hero",
                                     "children": {"explicitList": ["main"]}}),
        C("main", "gdm-container", {
            "direction": "row", "width": "100%", "height": "100%", "grow": 1,
            "gap": "48px", "padding": "60px", "align": "stretch",
            "children": {"explicitList": [f"{slide_id}_left", f"{slide_id}_right"]},
        }),
        # Left — narrative
        C(f"{slide_id}_left", "gdm-container", {
            "direction": "column", "justify": "center", "align": "flex-start",
            "grow": 1, "glass": True, "borderRadius": "16px",
            "padding": "40px", "gap": "20px",
            "reveal": "slide-right", "revealDelay": 0.0,
            "children": {"explicitList": [f"{slide_id}_l_badge",
                                          f"{slide_id}_l_title",
                                          f"{slide_id}_l_body"]},
        }),
        C(f"{slide_id}_l_badge", "gdm-badge", {
            "text":  l_badge.get("text", ""),
            "type":  l_badge.get("type", "primary"),
            "pulse": l_badge.get("pulse", False),
        }),
        C(f"{slide_id}_l_title", "gdm-text", {
            "content": _interpolate(left.get("title", ""), data),
            "size": "44px", "weight": "900", "font": "mono",
            "letterSpacing": "0.04em", "glitch": True,
        }),
        C(f"{slide_id}_l_body", "gdm-text", {
            "content": _interpolate(left.get("body", ""), data),
            "size": "16px", "font": "mono", "typeOn": True,
            "color": "rgba(255,255,255,0.75)",
        }),
        # Right — actions stack
        C(f"{slide_id}_right", "gdm-container", {
            "direction": "column", "justify": "center", "align": "center",
            "grow": 1, "gap": "16px",
            "border": "1px dashed rgba(0,242,255,0.2)",
            "borderRadius": "16px", "background": "rgba(0,242,255,0.02)",
            "reveal": "scale-in", "revealDelay": 0.4,
            "children": {"explicitList": btn_ids},
        }),
    ]
    for i, a in enumerate(actions):
        action = _make_action(a, ctx)
        if not action:
            continue
        out.append(C(btn_ids[i], "gdm-button", {
            "text":    a.get("text", "Action"),
            "variant": a.get("variant", "primary"),
            "size":    a.get("size", "lg"),
            "pulse":   a.get("pulse", True),
            "action":  action,
        }))
    return out


# ────────────────────────────────────────────────────────────────────────────
# Template 4 — list_5
# ────────────────────────────────────────────────────────────────────────────

def list_5_template(slide_id: str, cfg: dict, data: dict) -> List[Dict]:
    """Up to five points, staggered reveal. Auto-numbered with phosphor
    counters. Headline above, optional fire button below."""
    badge    = cfg.get("badge") or {}
    points   = (cfg.get("points") or [])[:5]    # cap at five — name says so
    next_act = cfg.get("next_action") or {}
    ctx      = {"playbook_name": cfg["playbook_name"], "space_id": cfg["space_id"]}
    action   = _make_action(next_act, ctx)

    point_ids = [f"{slide_id}_p_{i}" for i, _ in enumerate(points)]
    main_kids = [f"{slide_id}_badge", f"{slide_id}_title", f"{slide_id}_list"]
    if action:
        main_kids.append(f"{slide_id}_btn")

    out = [
        C("root", "gdm-stage-grid", {"layout": "hero",
                                     "children": {"explicitList": ["main"]}}),
        C("main", "gdm-container", {"direction": "column", "justify": "center",
                                    "align": "flex-start", "grow": 1,
                                    "gap": "28px", "padding": "60px",
                                    "width": "100%", "height": "100%",
                                    "children": {"explicitList": main_kids}}),
        C(f"{slide_id}_badge", "gdm-badge", {
            "text":  badge.get("text", ""),
            "type":  badge.get("type", "primary"),
            "pulse": badge.get("pulse", False),
        }),
        C(f"{slide_id}_title", "gdm-text", {
            "content": cfg.get("title", ""),
            "size": "56px", "weight": "900", "font": "mono",
            "letterSpacing": "0.04em", "glitch": True,
        }),
        C(f"{slide_id}_list", "gdm-container", {
            "direction": "column", "gap": "14px", "grow": 1, "width": "100%",
            "children": {"explicitList": point_ids},
        }),
    ]
    for i, p in enumerate(points):
        out.append(C(point_ids[i], "gdm-container", {
            "direction": "row", "align": "center", "gap": "20px",
            "reveal": "slide-right",
            "revealDelay": round(0.3 + i * 0.18, 2),
            "children": {"explicitList": [f"{point_ids[i]}_n", f"{point_ids[i]}_t"]},
        }))
        out.append(C(f"{point_ids[i]}_n", "gdm-text", {
            "content": f"{i+1:02d}",
            "size": "32px", "color": PHOSPHOR,
            "font": "mono", "weight": "900",
            "letterSpacing": "0.04em",
        }))
        out.append(C(f"{point_ids[i]}_t", "gdm-text", {
            "content": _interpolate(p, data),
            "size": "28px", "color": "white",
            "font": "mono", "weight": "600",
        }))
    if action:
        out.append(C(f"{slide_id}_btn", "gdm-button", {
            "text":    next_act.get("text", "Next"),
            "variant": next_act.get("variant", "primary"),
            "size":    next_act.get("size", "lg"),
            "pulse":   next_act.get("pulse", True),
            "action":  action,
        }))
    return out


# ────────────────────────────────────────────────────────────────────────────
# Template 5 — signoff
# ────────────────────────────────────────────────────────────────────────────

def signoff_template(slide_id: str, cfg: dict, data: dict) -> List[Dict]:
    """Multi-line glitch close + GOOGLE MEET × A2UI brand callout + matrix
    chef beat + typeOn tagline. Direct port of demo_a2ui_primitives.py's
    sign-off, parameterised."""
    lines    = cfg.get("lines") or []
    brands   = cfg.get("brands") or {}

    line_ids = [f"{slide_id}_line_{i}" for i, _ in enumerate(lines)]
    children = list(line_ids) + [f"{slide_id}_payoff"]

    out = [
        C("root", "gdm-stage-grid", {"layout": "hero",
                                     "children": {"explicitList": ["main"]}}),
        C("main", "gdm-container", {"direction": "column", "justify": "center",
                                    "align": "center", "grow": 1,
                                    "gap": "18px", "padding": "60px",
                                    "width": "100%", "height": "100%",
                                    "children": {"explicitList": children}}),
    ]
    for i, line in enumerate(lines):
        out.append(C(line_ids[i], "gdm-text", {
            "content": _interpolate(line.get("text", ""), data),
            "size":    line.get("size", "60px"),
            "color":   _color(line.get("color"), "white"),
            "font":    "mono", "weight": "900",
            "letterSpacing": "0.06em", "glitch": True,
        }))
    # Payoff cluster — brand row + badge + chef + tagline.
    payoff_kids = [f"{slide_id}_brands", f"{slide_id}_badge",
                   f"{slide_id}_chef",   f"{slide_id}_chef_sub",
                   f"{slide_id}_tag"]
    out.append(C(f"{slide_id}_payoff", "gdm-container", {
        "direction": "column", "justify": "center", "align": "center",
        "gap": "14px", "margin": "44px 0 0 0",
        "reveal": "fade-up", "revealDelay": 0.9,
        "children": {"explicitList": payoff_kids},
    }))
    out.append(C(f"{slide_id}_brands", "gdm-container", {
        "direction": "row", "align": "center", "justify": "center", "gap": "28px",
        "children": {"explicitList": [f"{slide_id}_left_b",
                                      f"{slide_id}_x",
                                      f"{slide_id}_right_b"]},
    }))
    out.append(C(f"{slide_id}_left_b", "gdm-text", {
        "content": brands.get("left", ""), "size": "64px",
        "color": "white", "font": "sans", "weight": "900",
        "letterSpacing": "0.03em", "glitch": True,
    }))
    out.append(C(f"{slide_id}_x", "gdm-text", {
        "content": "×", "size": "48px",
        "color": "rgba(255,255,255,0.35)",
        "font": "sans", "weight": "300",
    }))
    out.append(C(f"{slide_id}_right_b", "gdm-text", {
        "content": brands.get("right", ""), "size": "64px",
        "color": PHOSPHOR, "font": "sans", "weight": "900",
        "letterSpacing": "0.06em", "glitch": True,
    }))
    out.append(C(f"{slide_id}_badge", "gdm-badge", {
        "text": cfg.get("badge_text", ""),
        "type": "danger", "pulse": True,
    }))
    out.append(C(f"{slide_id}_chef", "gdm-text", {
        "content": cfg.get("chef_line", ""), "size": "60px",
        "color": PHOSPHOR, "font": "mono", "weight": "900",
        "letterSpacing": "0.06em", "typeOn": True,
    }))
    out.append(C(f"{slide_id}_chef_sub", "gdm-text", {
        "content": cfg.get("chef_sub", ""), "size": "22px",
        "color": "rgba(0,255,136,0.5)", "font": "mono",
        "letterSpacing": "0.22em", "typeOn": True,
    }))
    out.append(C(f"{slide_id}_tag", "gdm-text", {
        "content": cfg.get("tagline", ""), "size": "28px",
        "color": "rgba(255,255,255,0.7)", "font": "mono",
        "letterSpacing": "0.18em", "uppercase": True, "typeOn": True,
    }))
    return out


# ────────────────────────────────────────────────────────────────────────────
# Registry — single source of truth for what templates exist.
# Add a new template by writing the function above + one line here.
# ────────────────────────────────────────────────────────────────────────────

TEMPLATES = {
    "title":              title_template,
    "hero_stat":          hero_stat_template,
    "split_with_action":  split_with_action_template,
    "list_5":             list_5_template,
    "signoff":            signoff_template,
}
