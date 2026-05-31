#!/usr/bin/env python3
"""Primitives showcase — Anatomy of a Ticker.

Three passes:
  PASS 1 — SHOW   each primitive alone, centred, with its API label below
                  (label uses the new typeOn atom; final card uses glitch)
  PASS 2 — PLACE  all primitives animate (reveal + staggered revealDelay)
                  into formation, composing the market ticker
  PASS 3 — BREATHE the assembled ticker updates live for ~6s (flip atom on
                  prices) so the viewer sees data flow, not a freeze frame.

Matrix vibe: pass-1 labels are phosphor green mono with typeOn / glitch
atoms — the construction kit feels like code being written, not a deck.

Runs standalone against the local backend (see [[a2ui-primitives-and-devloop]]).
"""
import asyncio, os, sys, glob, datetime
_base = os.path.dirname(os.path.abspath(__file__))
for _vd in glob.glob(os.path.join(_base, "venv", "lib", "python3.*", "site-packages")):
    if _vd not in sys.path: sys.path.insert(0, _vd)
import httpx

API   = os.environ.get("CONCIERGE_API_URL", "http://127.0.0.1:8085")
KEY   = os.environ.get("STAGE_API_KEY") or exit("STAGE_API_KEY required — export it before running this script")
SPACE = os.environ.get("CAPTURE_SPACE", "default")

# Phosphor green — matrix code-editor vibe for the label lines in pass 1.
PHOSPHOR = "#00ff88"

def C(cid: str, el: str, props: dict) -> dict:
    """Build a v0.9 component dict. Strips structural keys from props to
    prevent accidental clobbering of `id` / `component` if a YAML author
    or LLM emits those as component-level attributes."""
    clean_props = {k: v for k, v in props.items() if k not in ('id', 'component')}
    return {"id": cid, "component": el, **clean_props}


# ────────────────────────────────────────────────────────────────────────────
# Pass 1 — SHOW: each primitive alone with its API label
# ────────────────────────────────────────────────────────────────────────────
def primitive_surface(prim_id: str, prim_el: str, prim_props: dict, lines: list,
                      step: int = 0, total: int = 0):
    """One primitive centre stage, mono labels below.
    `lines[0]` is the element name (rendered with typeOn — types in like code),
    subsequent lines are prop annotations in mute green.
    `step`/`total` drive the 'INGREDIENT N OF M' tasting-menu banner up top."""
    label_ids = [f"lbl_{i}" for i in range(len(lines))]
    surface = [
        C("root", "gdm-stage-grid", {"layout": "hero", "children": ["main"]}),
        C("main", "gdm-container", {"direction": "column", "justify": "center", "align": "center",
                                    "width": "100%", "height": "100%", "gap": "32px",
                                    "padding": "60px", "grow": 1,
                                    "children": ["banner", "showcase", "label_block"]}),
        # Tasting-menu banner: tonight's restaurant metaphor framing —
        # "INGREDIENT N OF M · gdm-badge". Types in so the slate feels like
        # a course being written onto a chalkboard.
        C("banner", "gdm-text", {
            "content": f"INGREDIENT {step} OF {total} · {lines[0]}",
            "size": "18px", "color": "rgba(0,255,136,0.65)", "font": "mono",
            "weight": "700", "letterSpacing": "0.32em", "uppercase": True,
            "typeOn": True,
        }),
        # Showcase frame — the primitive sits inside, with a faint outline so
        # the eye knows where to look.
        C("showcase", "gdm-container", {"direction": "row", "justify": "center", "align": "center",
                                        "padding": "40px 56px", "borderRadius": "16px",
                                        "border": "1px dashed rgba(0,255,136,0.18)",
                                        "background": "rgba(0,255,136,0.03)",
                                        "reveal": "scale-in", "revealDelay": 0.25,
                                        "children": [prim_id]}),
        C(prim_id, prim_el, prim_props),
        # Label block: API signature in phosphor mono, animated in.
        C("label_block", "gdm-container", {"direction": "column", "align": "center", "gap": "8px",
                                           "reveal": "fade-up", "revealDelay": 0.55,
                                           "children": label_ids}),
    ]
    for i, ln in enumerate(lines):
        is_name = i == 0
        surface.append(C(f"lbl_{i}", "gdm-text", {
            "content": ln,
            "size": "22px" if is_name else "16px",
            "color": PHOSPHOR if is_name else "rgba(0,255,136,0.55)",
            "font": "mono",
            "weight": "800" if is_name else "500",
            "letterSpacing": "0.08em",
        }))
    return surface


# (id, element, props, label_lines) — pass 1 sequence.
PRIMITIVES = [
    ("p_badge", "gdm-badge", {"text": "REALTIME", "type": "danger", "pulse": True},
     ["gdm-badge", "type: danger · pulse: true"]),

    ("p_sym",   "gdm-text",  {"content": "AAPL", "size": "88px", "color": "white",
                              "font": "mono", "weight": "900", "letterSpacing": "0.04em"},
     ["gdm-text", "size: 88px · font: mono · weight: 900"]),

    ("p_price", "gdm-text",  {"content": "$237.42", "size": "72px", "color": "white",
                              "font": "mono", "weight": "800", "flip": True},
     ["gdm-text  flip: true", "the flap cards animate on every content change"]),

    ("p_chg",   "gdm-text",  {"content": "↑ +1.24%", "size": "56px",
                              "color": "#19d27a", "font": "mono", "weight": "800"},
     ["gdm-text", "color: '#19d27a' (up) · '#ff5d5d' (down)"]),

    ("p_clock", "gdm-clock", {"showClock": True, "showDate": False, "variant": "flip",
                              "accentColor": PHOSPHOR},
     ["gdm-clock", "variant: flip · showClock: true"]),

    ("p_div",   "gdm-divider", {"color": "rgba(0,255,136,0.35)"},
     ["gdm-divider", "the seam between sections"]),

    # The grand finale of pass 1 — a glitched headline as a self-demo of
    # the new atom. The decrypt effect lands the "matrix" vibe.
    ("p_glitch", "gdm-text", {"content": "ONE CATALOGUE.", "size": "72px",
                              "color": PHOSPHOR, "font": "mono", "weight": "900",
                              "letterSpacing": "0.06em", "glitch": True},
     ["gdm-text  glitch: true", "matrix-style decrypt on content change"]),
]


# ────────────────────────────────────────────────────────────────────────────
# Title card
# ────────────────────────────────────────────────────────────────────────────
def title_surface():
    return [
        C("root", "gdm-stage-grid", {"layout": "hero", "children": ["main"]}),
        C("main", "gdm-container", {"direction": "column", "justify": "center", "align": "center",
                                    "width": "100%", "height": "100%", "grow": 1,
                                    "gap": "20px", "padding": "60px",
                                    "children": ["t_badge", "t_title", "t_sub"]}),
        # Restaurant metaphor: Meet = the room, Catalogue = the menu,
        # primitives/atoms/molecules = ingredients. Title slate establishes
        # the framing so pass 1's "INGREDIENT N OF M" lands.
        C("t_badge", "gdm-badge", {"text": "TONIGHT'S SPECIAL", "type": "danger", "pulse": True}),
        C("t_title", "gdm-text", {"content": "MEET. MENU. INGREDIENTS.", "size": "84px",
                                  "color": "white", "font": "mono", "weight": "900",
                                  "uppercase": True, "letterSpacing": "0.04em", "glitch": True}),
        C("t_sub",   "gdm-text", {"content": "every dish, composed on demand.",
                                  "size": "22px", "color": "rgba(0,255,136,0.7)", "font": "mono",
                                  "letterSpacing": "0.18em", "uppercase": True, "typeOn": True}),
    ]


# ────────────────────────────────────────────────────────────────────────────
# Pass 2 — PLACE: primitives assemble into the ticker (with stagger)
# ────────────────────────────────────────────────────────────────────────────
TICKER_ROWS = [
    # Col 1 — US tech mega-caps
    ("AAPL",   "$237.42",   "↑ +1.24%", True),
    ("TSLA",   "$189.50",   "↓ -2.15%", False),
    ("NVDA",   "$1,142.80", "↑ +3.42%", True),
    ("MSFT",   "$447.18",   "↑ +0.81%", True),
    ("GOOGL",  "$192.65",   "↓ -0.42%", False),
    ("AMZN",   "$218.94",   "↑ +0.96%", True),
    # Col 2 — broader market: more tech, an index, crypto, FX
    ("META",   "$612.30",   "↑ +1.58%", True),
    ("AMD",    "$168.42",   "↓ -1.07%", False),
    ("NFLX",   "$844.21",   "↑ +0.36%", True),
    ("SPX",    "5,468.10",  "↑ +0.42%", True),
    ("BTC",    "$71,820",   "↑ +2.65%", True),
    ("EURUSD", "1.0854",    "↓ -0.12%", False),
]


def _ticker_row(i: int, sym: str, price: str, chg: str, up: bool, base_delay: float):
    """Build a single ticker row + its primitives, staggered by base_delay.
    Sizes tuned for the 2×6 dense grid — smaller than the old single-column
    layout but still legible from stage distance."""
    rid = f"trow{i}"
    return [
        C(rid, "gdm-container", {"direction": "row", "align": "center", "gap": "20px",
                                 "grow": 1, "padding": "7px 6px",
                                 "reveal": "slide-right", "revealDelay": base_delay,
                                 "children": [f"sym{i}", f"price{i}",
                                              f"sp{i}", f"chg{i}"]}),
        C(f"sym{i}",   "gdm-text", {"content": sym, "size": "30px", "color": "white",
                                    "font": "mono", "weight": "900", "letterSpacing": "0.04em"}),
        C(f"price{i}", "gdm-text", {"content": price, "size": "30px", "color": "white",
                                    "font": "mono", "weight": "800", "flip": True}),
        C(f"sp{i}",    "gdm-spacer", {}),
        C(f"chg{i}",   "gdm-text", {"content": chg, "size": "26px",
                                    "color": "#19d27a" if up else "#ff5d5d",
                                    "font": "mono", "weight": "800"}),
    ]


def assembled_surface():
    # Split 12 rows into two columns of 6. Left column reveals first
    # (top-to-bottom), then right column — staggered overall so the eye
    # tracks a left-to-right assembly sweep.
    half = len(TICKER_ROWS) // 2
    left_ids  = [f"trow{i}" for i in range(half)]
    right_ids = [f"trow{i}" for i in range(half, len(TICKER_ROWS))]
    out = [
        C("root", "gdm-stage-grid", {"layout": "hero", "children": ["main"]}),
        C("main", "gdm-container", {"direction": "column", "padding": "40px 52px", "gap": "12px",
                                    "width": "100%", "height": "100%", "grow": 1,
                                    "glass": True, "borderRadius": "18px",
                                    "reveal": "scale-in", "revealDelay": 0.0,
                                    "children": ["hdr", "div", "body"]}),
        # Header: badge + clock — both primitives we just showed in pass 1.
        C("hdr", "gdm-container", {"direction": "row", "align": "center", "gap": "16px",
                                   "reveal": "fade-up", "revealDelay": 0.2,
                                   "children": ["hdr_badge", "hdr_sp", "hdr_clock"]}),
        C("hdr_badge", "gdm-badge", {"text": "REALTIME · MARKET SCAN", "type": "danger", "pulse": True}),
        C("hdr_sp",    "gdm-spacer", {}),
        C("hdr_clock", "gdm-clock", {"showClock": True, "showDate": False, "variant": "flip",
                                     "accentColor": PHOSPHOR}),
        # Divider — another primitive from the kitchen.
        C("div", "gdm-divider", {"color": "rgba(0,255,136,0.22)", "reveal": "fade-up", "revealDelay": 0.35}),
        # Body: two columns of ticker rows side by side.
        C("body", "gdm-container", {"direction": "row", "gap": "44px", "grow": 1, "width": "100%",
                                    "align": "stretch",
                                    "children": ["col_l", "col_r"]}),
        C("col_l", "gdm-container", {"direction": "column", "gap": "4px", "grow": 1,
                                     "children": left_ids}),
        C("col_r", "gdm-container", {"direction": "column", "gap": "4px", "grow": 1,
                                     "children": right_ids}),
    ]
    # Left column rows reveal first (delay 0.5 → +0.10 each), right column
    # follows after a small offset so the eye reads left-then-right.
    for i, (sym, price, chg, up) in enumerate(TICKER_ROWS):
        col_offset = 0.0 if i < half else 0.55
        idx_in_col = i if i < half else i - half
        out += _ticker_row(i, sym, price, chg, up,
                          base_delay=0.5 + col_offset + idx_in_col * 0.10)
    return out


# ────────────────────────────────────────────────────────────────────────────
# Pass 3 — BREATHE: live tick updates on the assembled ticker
# ────────────────────────────────────────────────────────────────────────────
def breathe_partial(tick: int):
    """Partial update — only the prices/chg cells, so the assembled surface
    sticks (no re-mount, no reveals replaying). Flip atom animates on every
    new content value. Sizes match _ticker_row so values don't resize on
    each tick."""
    # Walk a small synthetic random walk per row.
    out = []
    for i, (sym, price, chg, up) in enumerate(TICKER_ROWS):
        # Some non-dollar instruments (BTC, SPX, EURUSD) — strip whatever
        # currency symbol is there and reapply the same one.
        prefix = "$" if price.startswith("$") else ""
        clean = price.lstrip("$").replace(",", "")
        try:
            raw = float(clean)
        except ValueError:
            raw = 100.0
        nudge = ((tick * 7 + i * 13) % 11 - 5) * 0.04 * (1 + i * 0.2)
        new_raw = max(0.01, raw + nudge)
        # Mirror the original formatting roughly — integer-ish for big values,
        # 4dp for FX, 2dp for the rest.
        if raw < 5:                     # FX-like
            new_price = f"{prefix}{new_raw:,.4f}"
        elif raw > 10000:               # BTC, indices
            new_price = f"{prefix}{new_raw:,.0f}"
        else:
            new_price = f"{prefix}{new_raw:,.2f}"
        delta_pct = nudge / raw * 100
        is_up = nudge >= 0
        new_chg = f"{'↑' if is_up else '↓'} {'+' if is_up else ''}{delta_pct:.2f}%"
        out.append(C(f"price{i}", "gdm-text", {"content": new_price, "size": "30px", "color": "white",
                                               "font": "mono", "weight": "800", "flip": True}))
        out.append(C(f"chg{i}", "gdm-text", {"content": new_chg, "size": "26px",
                                             "color": "#19d27a" if is_up else "#ff5d5d",
                                             "font": "mono", "weight": "800"}))
    return out


# ────────────────────────────────────────────────────────────────────────────
# Sign-off card
# ────────────────────────────────────────────────────────────────────────────
def transition_surface():
    """Brief restaurant-metaphor flash between Pass 1 (ingredients shown)
    and Pass 2 (ticker assembling). 'ORDER UP.' is the kitchen shout when a
    dish is ready to plate — exactly the beat we're scripting."""
    return [
        C("root", "gdm-stage-grid", {"layout": "hero", "children": ["main"]}),
        C("main", "gdm-container", {"direction": "column", "justify": "center", "align": "center",
                                    "width": "100%", "height": "100%", "grow": 1, "gap": "14px",
                                    "padding": "60px",
                                    "children": ["tr_title", "tr_sub"]}),
        C("tr_title", "gdm-text", {"content": "ORDER UP.", "size": "120px",
                                   "color": "white", "font": "mono", "weight": "900",
                                   "letterSpacing": "0.08em", "glitch": True}),
        C("tr_sub",   "gdm-text", {"content": "kitchen → table.",
                                   "size": "26px", "color": "rgba(0,255,136,0.65)",
                                   "font": "mono", "letterSpacing": "0.22em",
                                   "uppercase": True, "typeOn": True}),
    ]


def signoff_surface():
    # The restaurant metaphor's full payoff: three lines name everyone in the
    # value chain (room · catalogue · primitives) — then a callout badge
    # makes the "this is what Meet add-ons can do" claim explicit, plus a
    # short tagline as the actual punchline.
    return [
        C("root", "gdm-stage-grid", {"layout": "hero", "children": ["main"]}),
        C("main", "gdm-container", {"direction": "column", "justify": "center", "align": "center",
                                    "width": "100%", "height": "100%", "grow": 1, "gap": "18px",
                                    "padding": "60px",
                                    "children": ["s1", "s2", "s3",
                                                                  "ext_group"]}),
        C("s1", "gdm-text", {"content": "THE RESTAURANT.", "size": "60px", "color": "white",
                             "font": "mono", "weight": "900", "letterSpacing": "0.06em",
                             "glitch": True}),
        C("s2", "gdm-text", {"content": "THE MENU.", "size": "60px", "color": PHOSPHOR,
                             "font": "mono", "weight": "900", "letterSpacing": "0.06em",
                             "glitch": True}),
        C("s3", "gdm-text", {"content": "THE INGREDIENTS.", "size": "60px", "color": "#00f2ff",
                             "font": "mono", "weight": "900", "letterSpacing": "0.06em",
                             "glitch": True}),
        # Footer cluster — GOOGLE MEET and A2UI are EQUAL hero brands, side
        # by side at the same scale with a small × between them so the eye
        # reads them as a pair. The badge underneath shortens the claim
        # (no need to repeat "A2UI" since it's already hero'd above).
        C("ext_group", "gdm-container", {"direction": "column", "justify": "center", "align": "center",
                                         "gap": "14px", "margin": "44px 0 0 0",
                                         "reveal": "fade-up", "revealDelay": 0.9,
                                         "children": ["ext_brands", "ext_badge",
                                                                       "ext_chef_group", "ext_tag"]}),
        C("ext_brands", "gdm-container", {"direction": "row", "align": "center", "justify": "center",
                                          "gap": "28px",
                                          "children": ["ext_meet", "ext_x", "ext_a2ui"]}),
        C("ext_meet",   "gdm-text", {"content": "GOOGLE MEET", "size": "64px",
                                     "color": "white", "font": "sans", "weight": "900",
                                     "letterSpacing": "0.03em", "glitch": True}),
        C("ext_x",      "gdm-text", {"content": "×", "size": "48px",
                                     "color": "rgba(255,255,255,0.35)",
                                     "font": "sans", "weight": "300"}),
        C("ext_a2ui",   "gdm-text", {"content": "A2UI", "size": "64px",
                                     "color": PHOSPHOR, "font": "sans", "weight": "900",
                                     "letterSpacing": "0.06em", "glitch": True}),
        C("ext_badge",  "gdm-badge", {"text": "FULLY EXTENSIBLE · INFINITELY COMPOSABLE",
                                      "type": "danger", "pulse": True}),
        # Chef-at-the-table — evolves the restaurant metaphor into the meeting-
        # shaped insight (agent listens IN the room, not from the kitchen).
        # Matrix-style typed-in: phosphor green, typeOn (typewriter + blinking
        # cursor), with the iconic 'follow the rabbit' callback below.
        C("ext_chef_group", "gdm-container", {"direction": "column", "align": "center",
                                              "gap": "10px", "margin": "28px 0 0 0",
                                              "children": ["ext_chef", "ext_chef_sub"]}),
        C("ext_chef",   "gdm-text", {"content": "THE CHEF IS AT THE TABLE.",
                                     "size": "60px", "color": PHOSPHOR, "font": "mono",
                                     "weight": "900", "letterSpacing": "0.06em",
                                     "typeOn": True}),
        C("ext_chef_sub", "gdm-text", {"content": "follow the rabbit.",
                                       "size": "22px", "color": "rgba(0,255,136,0.5)",
                                       "font": "mono", "letterSpacing": "0.22em",
                                       "typeOn": True}),
        C("ext_tag",    "gdm-text",  {"content": "infinite possibilities.",
                                      "size": "28px", "color": "rgba(255,255,255,0.7)",
                                      "font": "mono", "letterSpacing": "0.18em",
                                      "uppercase": True, "typeOn": True}),
    ]


# ────────────────────────────────────────────────────────────────────────────
# Driver
# ────────────────────────────────────────────────────────────────────────────
async def _render(c, H, components, root="root"):
    await c.post(f"{API}/api/render-stage/{SPACE}", headers=H, json={
        "surfaceUpdate": {"components": components},
        "root": root,
    })


async def main():
    H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=20) as c:
        # ───── Title ─────
        await c.post(f"{API}/api/render-stage-clear/{SPACE}", headers=H, json={})
        await asyncio.sleep(0.25)
        await _render(c, H, title_surface())
        print("  ▶ TITLE: MEET. MENU. INGREDIENTS.")
        await asyncio.sleep(5.5)

        # ───── Pass 1 — SHOW ─────
        total = len(PRIMITIVES)
        for step, (prim_id, prim_el, prim_props, labels) in enumerate(PRIMITIVES, start=1):
            await c.post(f"{API}/api/render-stage-clear/{SPACE}", headers=H, json={})
            await asyncio.sleep(0.25)
            await _render(c, H, primitive_surface(prim_id, prim_el, prim_props, labels,
                                                  step=step, total=total))
            print(f"  ▶ SHOW {step}/{total}  {prim_el}  ({labels[0]})")
            await asyncio.sleep(2.6)

        # ───── Transition — ORDER UP ─────
        # Brief restaurant-idiom beat between ingredients and the assembled
        # dish — lets the metaphor land before the ticker starts to compose.
        await c.post(f"{API}/api/render-stage-clear/{SPACE}", headers=H, json={})
        await asyncio.sleep(0.25)
        await _render(c, H, transition_surface())
        print("  ▶ ORDER UP — kitchen → table")
        await asyncio.sleep(1.6)

        # ───── Pass 2 — PLACE ─────
        await c.post(f"{API}/api/render-stage-clear/{SPACE}", headers=H, json={})
        await asyncio.sleep(0.25)
        await _render(c, H, assembled_surface())
        print("  ▶ PLACE: ticker assembling…")
        # Hold while staggered reveals play out (last row delay ≈ 0.5 + 4*0.18 = 1.22s).
        await asyncio.sleep(5.0)

        # ───── Pass 3 — BREATHE ─────
        for tick in range(7):
            await _render(c, H, breathe_partial(tick))
            await asyncio.sleep(1.0)
        print("  ▶ BREATHE: live updates done")

        # ───── Sign-off ─────
        await c.post(f"{API}/api/render-stage-clear/{SPACE}", headers=H, json={})
        await asyncio.sleep(0.25)
        await _render(c, H, signoff_surface())
        print("  ▶ THE KITCHEN. THE MEAL.")
        await asyncio.sleep(3.5)

    print("primitives showcase done")


if __name__ == "__main__":
    asyncio.run(main())
