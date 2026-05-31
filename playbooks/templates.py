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
    """Build a v0.9 component dict. Strips structural keys from props to
    prevent accidental clobbering of `id` / `component` if a YAML author
    or LLM emits those as component-level attributes."""
    clean_props = {k: v for k, v in props.items() if k not in ('id', 'component')}
    return {"id": cid, "component": el, **clean_props}


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
    """Build a v0.9 action dict from a YAML action/next_action declaration."""
    if not action_cfg:
        return None
    if "fires" in action_cfg:
        slide_ref = str(action_cfg["fires"])
        if not re.match(r'^[a-zA-Z0-9_-]+$', slide_ref):
            raise ValueError(f"Invalid 'fires' slide id {slide_ref!r} — only [a-zA-Z0-9_-] allowed")
        endpoint = f"/api/playbook/fire/{ctx['playbook_name']}/{slide_ref}/{ctx['space_id']}"
        return {"functionCall": {"call": "fireEndpoint", "args": {"endpoint": endpoint}}}
    if "links" in action_cfg:
        return {"functionCall": {"call": "openUrl", "args": {"url": action_cfg["links"]}}}
    if "emits" in action_cfg:
        return {"event": {"name": action_cfg["emits"]}}
    if "agent" in action_cfg:
        return {"event": {"name": action_cfg["agent"]}}
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
                                     "children": ["main"]}),
        C("main", "gdm-container", {"direction": "column", "justify": "center",
                                    "align": "center", "grow": 1,
                                    "gap": "24px", "padding": "60px",
                                    "width": "100%", "height": "100%",
                                    "children": children}),
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
                                     "children": ["main"]}),
        C("main", "gdm-container", {"direction": "column", "justify": "center",
                                    "align": "center", "grow": 1,
                                    "gap": "18px", "padding": "60px",
                                    "width": "100%", "height": "100%",
                                    "children": children}),
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
                                     "children": ["main"]}),
        C("main", "gdm-container", {
            "direction": "row", "width": "100%", "height": "100%", "grow": 1,
            "gap": "48px", "padding": "60px", "align": "stretch",
            "children": [f"{slide_id}_left", f"{slide_id}_right"],
        }),
        # Left — narrative
        C(f"{slide_id}_left", "gdm-container", {
            "direction": "column", "justify": "center", "align": "flex-start",
            "grow": 1, "glass": True, "borderRadius": "16px",
            "padding": "40px", "gap": "20px",
            "reveal": "slide-right", "revealDelay": 0.0,
            "children": [f"{slide_id}_l_badge",
                         f"{slide_id}_l_title",
                         f"{slide_id}_l_body"],
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
            "children": btn_ids,
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
                                     "children": ["main"]}),
        C("main", "gdm-container", {"direction": "column", "justify": "center",
                                    "align": "flex-start", "grow": 1,
                                    "gap": "28px", "padding": "60px",
                                    "width": "100%", "height": "100%",
                                    "children": main_kids}),
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
            "children": point_ids,
        }),
    ]
    for i, p in enumerate(points):
        out.append(C(point_ids[i], "gdm-container", {
            "direction": "row", "align": "center", "gap": "20px",
            "reveal": "slide-right",
            "revealDelay": round(0.3 + i * 0.18, 2),
            "children": [f"{point_ids[i]}_n", f"{point_ids[i]}_t"],
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
                                     "children": ["main"]}),
        C("main", "gdm-container", {"direction": "column", "justify": "center",
                                    "align": "center", "grow": 1,
                                    "gap": "18px", "padding": "60px",
                                    "width": "100%", "height": "100%",
                                    "children": children}),
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
        "children": payoff_kids,
    }))
    out.append(C(f"{slide_id}_brands", "gdm-container", {
        "direction": "row", "align": "center", "justify": "center", "gap": "28px",
        "children": [f"{slide_id}_left_b",
                     f"{slide_id}_x",
                     f"{slide_id}_right_b"],
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
# Template 6 — market_ticker (Round 3)
# ────────────────────────────────────────────────────────────────────────────

def market_ticker_template(slide_id: str, cfg: dict, data: dict) -> List[Dict]:
    """Dense multi-column market scan using the high-performance and premium
    gdm-trend-value component with native browser CSS column flow layouts.
    """
    badge    = cfg.get("badge") or {}
    symbols  = cfg.get("symbols") or []
    quotes   = data.get("quotes") or []
    next_act = cfg.get("next_action") or {}
    ctx      = {"playbook_name": cfg["playbook_name"], "space_id": cfg["space_id"]}
    action   = _make_action(next_act, ctx)

    # Map symbol → quote for O(1) lookup
    by_symbol: dict = {}
    for q in quotes:
        if isinstance(q, dict) and q.get("symbol"):
            by_symbol[str(q["symbol"]).upper()] = q
    rows = [(s, by_symbol.get(str(s).upper(), {})) for s in symbols]

    num_cols = 4 if len(rows) > 16 else 2
    row_ids = [f"{slide_id}_row_{i}" for i in range(len(rows))]

    main_kids = [f"{slide_id}_hdr", f"{slide_id}_div", f"{slide_id}_body"]
    if action:
        main_kids.append(f"{slide_id}_btn")

    out = [
        C("root", "gdm-stage-grid", {"layout": "hero",
                                     "children": ["main"]}),
        C("main", "gdm-container", {
            "direction": "column", "padding": "24px 32px", "gap": "10px",
            "width": "100%", "height": "100%", "grow": 1,
            "glass": True, "borderRadius": "18px",
            "reveal": "scale-in", "revealDelay": 0.0,
            "children": main_kids,
        }),
        C(f"{slide_id}_hdr", "gdm-container", {
            "direction": "row", "align": "center", "gap": "16px",
            "reveal": "fade-up", "revealDelay": 0.2,
            "children": [f"{slide_id}_badge",
                         f"{slide_id}_sp",
                         f"{slide_id}_clock"],
        }),
        C(f"{slide_id}_badge", "gdm-badge", {
            "text":  badge.get("text", "REALTIME · MARKETS"),
            "type":  badge.get("type", "danger"),
            "pulse": badge.get("pulse", True),
        }),
        C(f"{slide_id}_sp", "gdm-spacer", {}),
        C(f"{slide_id}_clock", "gdm-clock", {
            "showClock": True, "showDate": False,
            "variant": "flip", "accentColor": PHOSPHOR,
        }),
        C(f"{slide_id}_div", "gdm-divider", {
            "color": "rgba(0,255,136,0.22)",
            "reveal": "fade-up", "revealDelay": 0.35,
        }),
        # --- Native CSS Columns flow container! ---
        C(f"{slide_id}_body", "gdm-container", {
            "columns": num_cols,
            "columnGap": "16px",
            "gap": "5px",
            "grow": 1,
            "width": "100%",
            "children": row_ids,
        }),
    ]

    def _maybe_float(v):
        if isinstance(v, (int, float)):
            return v
        if isinstance(v, str):
            try:
                return float(v)
            except (ValueError, TypeError):
                return None
        return None

    def emit_row(rid: str, sym: str, q: dict, base_delay: float) -> list[dict]:
        price_raw = _maybe_float(q.get("price"))
        chg_raw   = _maybe_float(q.get("change"))
        is_up     = isinstance(chg_raw, (int, float)) and chg_raw >= 0

        price_val = price_raw if price_raw is not None else 0.0
        chg_val = chg_raw if chg_raw is not None else 0.0

        return [
            C(rid, "gdm-trend-value", {
                "symbol": sym,
                "price": price_val,
                "change": chg_val,
                "isUp": is_up,
                "precision": 4 if abs(price_val) < 5 else 2,
                "reveal": "slide-right", "revealDelay": base_delay,
            })
        ]

    # Emit all rows as flat children inside the CSS columns body container
    for i, (sym, q) in enumerate(rows):
        col_idx = i // ((len(rows) + num_cols - 1) // num_cols)
        row_idx_in_col = i % ((len(rows) + num_cols - 1) // num_cols)
        out += emit_row(row_ids[i], sym, q, base_delay=0.4 + col_idx * 0.12 + row_idx_in_col * 0.02)

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
# Template 7 — airspace_command_deck
# ────────────────────────────────────────────────────────────────────────────

def _make_supervisor_console_html(flights: list[dict], weather: dict) -> str:
    """Generates the live ATC Sector Supervisor Console HTML panel content."""
    rows_markup = ""
    for f in flights:
        vrate = f.get("vrate", 0)
        vr_symbol = "▼" if vrate < -250 else ("▲" if vrate > 250 else "—")
        if vrate < -250:
            color_class = "text-up"
        elif vrate > 250:
            color_class = "text-warning"
        else:
            color_class = "text-cyan"
            
        alt_m = f.get("altitude", 0)
        fl = f"{int(alt_m * 3.28084 / 100):03d}"
        
        if alt_m < 500:
            status_pill = '<span class="status-pill landed">Landed</span>'
        elif alt_m < 1000:
            status_pill = '<span class="status-pill approach">Final Approach</span>'
        elif alt_m < 2500:
            status_pill = '<span class="status-pill approach">Approach Fix</span>'
        else:
            status_pill = '<span class="status-pill established">Established</span>'
            
        rows_markup += f"""
        <tr>
            <td class="font-bold">{f.get('company', '')}</td>
            <td class="{color_class} font-bold font-mono">{f.get('callsign', '')}</td>
            <td class="font-mono">{f.get('aircraft', '')}</td>
            <td class="font-mono font-bold">{f.get('origin', '')} ➔ {f.get('destination', '')}</td>
            <td class="font-mono text-mute">{f.get('dep_time', '')}</td>
            <td class="font-mono text-warning">{f.get('eta', '')}</td>
            <td class="font-mono text-warning font-bold">{f.get('eta_relative', '')}</td>
            <td class="font-mono">FL{fl} <span class="text-mute text-xs">({alt_m}m)</span></td>
            <td class="{color_class} font-mono">{vr_symbol} {abs(vrate)} fpm</td>
            <td>{status_pill}</td>
            <td class="font-mono text-mute">{f.get('squawk', '')}</td>
        </tr>
        """
        
    return f"""
    <link rel="stylesheet" href="/stage_components.css">
    <div class="hud-container">
        <div class="hud-header">
            <div class="hud-title">
                <div class="pulse-dot"></div>
                📡 TLS-SECTOR SUPERVISOR CONSOLE
            </div>
            <div class="hud-subtitle-badge">LFBO-APP</div>
        </div>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Active Runway Corridor</div>
                <div class="metric-value text-up">ILS Runway 32L/R</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Active Wind & METAR</div>
                <div class="metric-value font-mono">{weather.get('wind', '—')} ({weather.get('temp', '—')})</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Sector Capacity</div>
                <div class="metric-value text-cyan">{len(flights)}/12 ACFT</div>
            </div>
        </div>
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>Airline</th>
                        <th>Flight No</th>
                        <th>Aircraft</th>
                        <th>Route</th>
                        <th>Departure</th>
                        <th>ETA (UTC)</th>
                        <th>Countdown</th>
                        <th>Altitude</th>
                        <th>V-Rate</th>
                        <th>Sector Status</th>
                        <th>Squawk</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_markup}
                </tbody>
            </table>
        </div>
    </div>
    """


def _make_target_profile_html(flight: dict, tick: int) -> str:
    """Generates the glowing Target Operations Profile HUD for a locked aircraft."""
    alt_m = flight.get("altitude", 0)
    altitude_ft = int(alt_m * 3.28084)
    fl = f"{int(altitude_ft / 100):03d}"
    vrate = flight.get("vrate", 0)
    speed = flight.get("speed", 0)
    
    pct_speed = int(max(0, min(100, (speed - 135) / (340 - 135) * 100)))
    glide_deviation = "ON COURSE" if alt_m > 100 else "DECELERATION ROLL"
    
    return f"""
    <link rel="stylesheet" href="/stage_components.css">
    <div class="hud-container green-theme">
        <div class="hud-header green-theme">
            <div class="hud-title green-theme">
                <div class="pulse-dot"></div>
                🎯 ACTIVE TARGET OPERATIONS PROFILE
            </div>
            <div class="hud-subtitle-badge green-theme">VECTORS LOCK ON</div>
        </div>
        
        <div class="flex-between align-start margin-bottom-md">
            <div>
                <div class="target-callsign">{flight.get('callsign', '')}</div>
                <div class="font-bold font-mono text-up text-uppercase text-xs">
                    {flight.get('company', '')} • {flight.get('origin', '')} ➔ {flight.get('destination', '')}
                </div>
            </div>
            <div class="text-right">
                <div class="font-bold text-uppercase text-mute text-xs">Squawk</div>
                <div class="font-bold font-mono text-cyan text-lg glow-cyan">{flight.get('squawk', '')}</div>
            </div>
        </div>
        
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Primary Altitude</div>
                <div class="metric-value">{alt_m}m <span class="text-mute text-xs">/ FL{fl}</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Airspeed Reference</div>
                <div class="metric-value text-up">{speed} kt</div>
                <progress value="{pct_speed}" max="100"></progress>
            </div>
            <div class="metric-card">
                <div class="metric-label">Vertical Descent Speed</div>
                <div class="metric-value text-up">{vrate} fpm</div>
            </div>
        </div>
        
        <div class="metric-grid grid-2 margin-bottom-md">
            <div class="metric-card">
                <div class="metric-label">Aircraft Type</div>
                <div class="metric-value font-mono">{flight.get('aircraft', '')}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Touchdown ETA</div>
                <div class="metric-value text-warning">{flight.get('eta_relative', '')} <span class="text-mute text-xs">({flight.get('eta', '')})</span></div>
            </div>
        </div>
        
        <div class="glidepath-visual">
            <div class="font-bold text-uppercase text-mute text-xs text-letterspace margin-bottom-sm">3-Degree Instrument Landing Corridor</div>
            <div class="font-bold text-cyan text-letterspace margin-bottom-sm">{glide_deviation}</div>
            <div class="glideslope-line">
                <div class="glide-notch"></div>
                <div class="glide-notch"></div>
                <div class="glide-diamond"></div>
                <div class="glide-notch"></div>
                <div class="glide-notch"></div>
            </div>
            <div class="font-mono text-mute text-xs margin-top-sm">ILS GS-32L FREQ: 110.10 MHz • DME LOCK: 1.8 NM</div>
        </div>
    </div>
    """


def airspace_command_deck_template(slide_id: str, cfg: dict, data: dict) -> List[Dict]:
    """Toulouse-Blagnac Airspace Command Deck Template.
    Renders:
      - gdm-stage-grid (layout: "presentation", default)
        hosting:
          - gdm-3d-airspace (left panel)
          - gdm-html-panel (right panel, displaying supervisor HUD)
      - gdm-ticker (bottom ticker, optional)
      - gdm-chyron (chyron header, optional)
      - gdm-diagram-view (overlay, optional)
      - gdm-poll-overlay (interactive poll, optional)
    """
    flights = data.get("flights") or []
    weather = data.get("weather") or {
        "wind": "310° @ 12kt",
        "temp": "16°C",
        "pressure": "1015 hPa",
        "clouds": "Few clouds 3000ft",
        "raw": "LFBO 262100Z 31012KT 9999 FEW030 16/11 Q1015"
    }

    tick = cfg.get("tick", 0)
    locked_callsign = cfg.get("lockedCallsign", "")
    fullscreen = cfg.get("fullscreen", False)
    layout_type = "single" if fullscreen else cfg.get("grid_layout", "split")

    radar_id = f"{slide_id}_radar_view"
    html_id = f"{slide_id}_html_panel"

    # 1. Base Grid and Panels
    children = [radar_id] if fullscreen else [radar_id, html_id]
    out = [
        C("root", "gdm-stage-grid", {
            "layout": layout_type,
            "children": children,
        })
    ]

    # Configure 3D Airspace component properties
    radar_props = {
        "flights": flights,
        "lockedCallsign": locked_callsign,
        "showGlideSlope": cfg.get("showGlideSlope", True),
        "showTerrain": cfg.get("showTerrain", True),
        "cinematicOrbit": cfg.get("cinematicOrbit", True),
        "autoTrack": cfg.get("autoTrack", False),
    }

    # Only set camera properties on tick 0 to let browser drag/pinch gesture interact.
    if tick == 0:
        camera = cfg.get("camera", {})
        radar_props["zoom"] = camera.get("zoom", cfg.get("zoom", 5.5))
        radar_props["cameraPitch"] = camera.get("cameraPitch", cfg.get("cameraPitch", 35.0))
        radar_props["cameraYaw"] = camera.get("cameraYaw", cfg.get("cameraYaw", 45.0))

    out.append(C(radar_id, "gdm-3d-airspace", radar_props))

    # Generate proper retro-cyber HUD for HTML panel
    panel_type = cfg.get("panel_type", "supervisor")
    if panel_type == "target" and locked_callsign:
        locked_flight = None
        for f in flights:
            if f.get("callsign") == locked_callsign:
                locked_flight = f
                break
        if locked_flight:
            html_content = _make_target_profile_html(locked_flight, tick)
        else:
            html_content = _make_supervisor_console_html(flights, weather)
    else:
        html_content = _make_supervisor_console_html(flights, weather)

    if not fullscreen:
        out.append(C(html_id, "gdm-html-panel", {
            "html": html_content,
            "title": cfg.get("panel_title", "📡 Supervisor Live Console"),
            "version": tick + 1,
        }))

    # 2. Add Standby Slate if inactive
    if cfg.get("show_slate"):
        out.append(C(f"{slide_id}_slate", "gdm-standby-slate", {
            "title": cfg.get("slate_title", ""),
            "description": cfg.get("slate_description", ""),
            "seconds": cfg.get("slate_seconds", 5),
            "fullscreen": cfg.get("slate_fullscreen", False),
            "active": cfg.get("slate_active", True),
        }))

    # 3. Bottom Ticker Overlay
    ticker_text = cfg.get("ticker_text")
    if ticker_text:
        ticker_text = _interpolate(ticker_text, data)
        out.append(C(f"{slide_id}_ticker", "gdm-ticker", {
            "text": ticker_text,
            "scrollSpeed": cfg.get("ticker_speed", 50),
            "active": True,
            "accentColor": _color(cfg.get("ticker_accent", "phosphor")),
        }))

    # 4. Top Chyron Overlay
    chyron_title = cfg.get("chyron_title")
    if chyron_title:
        out.append(C(f"{slide_id}_chyron", "gdm-chyron", {
            "title": _interpolate(chyron_title, data),
            "subtitle": _interpolate(cfg.get("chyron_subtitle", ""), data),
            "active": True,
            "accentColor": _color(cfg.get("chyron_accent", "phosphor")),
        }))

    # 5. Airway Network SVG Map Overlay
    diagram_svg = data.get("airspace_svg") or cfg.get("diagram_svg")
    if diagram_svg:
        svg_content = _interpolate(diagram_svg, data)
        out.append(C(f"{slide_id}_diagram", "gdm-diagram-view", {
            "svg": svg_content,
            "diagId": cfg.get("diagram_id", "network_overlay"),
            "overlay": True,
        }))

    # 6. Interactive Poll Overlay
    poll_question = cfg.get("poll_question")
    if poll_question:
        poll_values = data.get("poll_values") or cfg.get("poll_values") or [0, 0, 0]
        out.append(C(f"{slide_id}_poll", "gdm-poll-overlay", {
            "question": poll_question,
            "options": cfg.get("poll_options", []),
            "values": poll_values,
            "active": True,
        }))

    return out


# ────────────────────────────────────────────────────────────────────────────
# Registry — single source of truth for what templates exist.
# Add a new template by writing the function above + one line here.
# ────────────────────────────────────────────────────────────────────────────

def landing_queue_display_template(slide_id: str, cfg: dict, data: dict) -> List[Dict]:
    """Full-screen interactive landing queue with toggle to 3D track view."""
    flights = data.get("flights") or []
    mode = cfg.get("mode", "queue")
    title = cfg.get("title", "LANDING QUEUE")

    if mode == "queue":
        # Queue view: HTML table of landing flights
        html_content = f"""
        <style>
          body {{ font-family: 'JetBrains Mono', monospace; background: #080a14; color: #00f2ff; }}
          .header {{ padding: 20px; border-bottom: 2px solid #00f2ff; text-align: center; }}
          .header h1 {{ margin: 0; font-size: 28px; letter-spacing: 2px; text-shadow: 0 0 10px rgba(0, 242, 255, 0.5); }}
          .flights {{ padding: 20px; display: flex; flex-direction: column; gap: 12px; }}
          .flight {{
            padding: 15px 20px; background: rgba(0, 150, 136, 0.1); border-left: 4px solid #00f2ff;
            cursor: pointer; transition: all 300ms; display: grid;
            grid-template-columns: 1fr 1.5fr 1fr 1fr 0.8fr; gap: 20px; align-items: center;
          }}
          .flight:hover {{ background: rgba(0, 242, 255, 0.15); box-shadow: inset 0 0 10px rgba(0, 242, 255, 0.2); }}
          .airline {{ font-weight: bold; color: #00ff88; }}
          .route {{ color: #00f2ff; font-size: 14px; }}
          .time {{ color: #ffd60a; font-weight: bold; }}
          .eta {{ color: #00ff88; }}
          .status {{
            padding: 4px 12px; border-radius: 3px; font-weight: bold; font-size: 12px;
            background: rgba(100, 200, 255, 0.3); color: #64c8ff;
          }}
        </style>
        <div class="header"><h1>✈️ {title}</h1></div>
        <div class="flights">
        """

        for i, flight in enumerate(flights[:5]):
            airline = flight.get("company", "UNKNOWN")
            callsign = flight.get("callsign", "—")
            origin = flight.get("origin", "—")
            dest = flight.get("destination", "—")
            dep_time = flight.get("dep_time", "—")
            alt = int((flight.get("altitude", 0) or 0) / 100)
            vrate = flight.get("vrate", -1000)

            # Calculate ETA
            minutes = max(0, alt) / 6  # Rough estimate
            from datetime import datetime, timedelta
            eta = (datetime.now() + timedelta(minutes=minutes)).strftime("%H:%M")

            status = "DESCENDING" if alt > 30 else "LANDING"
            html_content += f"""
            <div class="flight" onclick="alert('Click: {callsign} — Toggle to 3D track')">
              <div class="airline">{airline}<br/><span style="color: #00f2ff; font-size: 12px;">{callsign}</span></div>
              <div class="route">{origin} → {dest}</div>
              <div class="time">Dep: {dep_time}</div>
              <div class="eta">ETA: {eta}</div>
              <div class="status">{status}</div>
            </div>
            """

        html_content += "</div>"
    else:
        # Track view: Show top flight with 3D context
        if flights:
            flight = flights[0]
            airline = flight.get("company", "UNKNOWN")
            callsign = flight.get("callsign", "—")
            alt = int((flight.get("altitude", 0) or 0) / 100)
            speed = int(flight.get("speed", 0) or 0)

            html_content = f"""
            <style>
              body {{ font-family: 'JetBrains Mono', monospace; background: #080a14; color: #00f2ff;
                     display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100%; }}
              .track {{ text-align: center; }}
              .track h1 {{ font-size: 32px; color: #00ff88; margin: 20px; text-shadow: 0 0 20px rgba(0, 255, 136, 0.6); }}
              .track p {{ font-size: 18px; margin: 10px; color: #00f2ff; }}
              .track button {{ padding: 10px 30px; background: #00f2ff; color: #080a14; border: none;
                              font-weight: bold; cursor: pointer; margin-top: 30px; border-radius: 4px; }}
            </style>
            <div class="track">
              <h1>🎯 TRACKING: {callsign}</h1>
              <p>{airline}</p>
              <p>Altitude: {alt}00 ft | Speed: {speed} kt</p>
              <button onclick="alert('Toggle back to queue')">← BACK TO QUEUE</button>
            </div>
            """
        else:
            html_content = "<h1 style='color: #00f2ff; text-align: center;'>No flights available</h1>"

    return [
        C("root", "gdm-stage-grid", {
            "layout": "single",
            "children": ["landing_html_panel"],
        }),
        C("landing_html_panel", "gdm-html-panel", {
            "html": html_content,
            "stage": True,
            "fullscreen": True,
            "version": 1,
        }),
    ]


def table_view_template(slide_id: str, cfg: dict, data: dict) -> List[Dict]:
    """Renders an elegant structured table view panel.
    props: badge, title, headers, rows, next_action, accentColor
    """
    badge = cfg.get("badge") or {}
    title = cfg.get("title", "")
    headers = cfg.get("headers") or []
    rows = cfg.get("rows") or []
    accent_color = cfg.get("accentColor") or CYAN
    
    next_act = cfg.get("next_action")
    action = None
    if next_act and "fires" in next_act:
        action = f"fire:{cfg['playbook_name']}/{next_act['fires']}/{cfg['space_id']}"
        
    out = [
        C("root", "gdm-stage-grid", {"layout": "single", "children": ["main_container"]}),
        C("main_container", "gdm-container", {
            "direction": "column", "width": "100%", "height": "100%", "grow": 1,
            "padding": "40px", "gap": "20px", "justify": "flex-start", "align": "stretch"
        })
    ]
    
    header_children = []
    if badge and badge.get("text"):
        out.append(C(f"{slide_id}_badge", "gdm-badge", {
            "text": badge.get("text", ""),
            "type": badge.get("type", "primary"),
            "pulse": badge.get("pulse", False)
        }))
        header_children.append(f"{slide_id}_badge")
    if title:
        out.append(C(f"{slide_id}_title", "gdm-text", {
            "text": title,
            "variant": "glitch",
            "fontSize": "24px",
            "color": accent_color
        }))
        header_children.append(f"{slide_id}_title")
        
    if header_children:
        out.append(C(f"{slide_id}_header", "gdm-container", {
            "direction": "row", "gap": "20px", "align": "center",
            "children": header_children
        }))
        out[1]["props"]["children"] = [f"{slide_id}_header"]
    else:
        out[1]["props"]["children"] = []
        
    # Table element
    out.append(C(f"{slide_id}_table", "gdm-table-view", {
        "headers": headers,
        "rows": rows,
        "accentColor": accent_color
    }))
    out[1]["props"]["children"].append(f"{slide_id}_table")
    
    # Next button
    if action:
        out.append(C(f"{slide_id}_btn", "gdm-button", {
            "text": next_act.get("text", "Next"),
            "variant": next_act.get("variant", "primary"),
            "action": action
        }))
        out[1]["props"]["children"].append(f"{slide_id}_btn")
        
    return out


TEMPLATES = {
    "title":              title_template,
    "hero_stat":          hero_stat_template,
    "split_with_action":  split_with_action_template,
    "list_5":             list_5_template,
    "signoff":            signoff_template,
    "market_ticker":      market_ticker_template,
    "airspace_command_deck": airspace_command_deck_template,
    "landing_queue_display": landing_queue_display_template,
    "table_view":         table_view_template,
}

