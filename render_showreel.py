#!/usr/bin/env python3
"""Capability showreel — three acts driven by atoms + molecules with a
consistent panel-frame and staged entrances. Each act clears + renders so the
reveal choreography replays.

  Act 0  Title card  — hero headline composed from atoms (badge + flip-text + clock)
  Act 1  Market scan — the dense board (reuses render_dense.dense_board)
  Act 5  Architecture — D2 → SVG, framed as a molecule (no new TS, all composed)
"""
import asyncio, os, sys, glob, subprocess, datetime, re
_base = os.path.dirname(os.path.abspath(__file__))
for _vd in glob.glob(os.path.join(_base, "venv", "lib", "python3.*", "site-packages")):
    if _vd not in sys.path: sys.path.insert(0, _vd)
import httpx
from render_dense import dense_board

API   = os.environ.get("CONCIERGE_API_URL", "http://127.0.0.1:8085")
KEY   = os.environ.get("STAGE_API_KEY", "meet-live_STAGE_SECURE_v1_zG9fN8qL7vP2mX6tY9wK4jC5bS8xQ7hZ3uW0rA")
SPACE = os.environ.get("CAPTURE_SPACE", "default")

def C(cid, el, props): return {"id": cid, "component": {el: props}}

# ────────────────────────────────────────────────────────────────────────────
# Act 0 — Title card
# ────────────────────────────────────────────────────────────────────────────
def act_title(_tick: int):
    return [
        C("root", "gdm-stage-grid", {"layout": "hero", "children": {"explicitList": ["scrim"]}}),
        C("scrim", "gdm-container", {"direction": "column", "justify": "center", "align": "center",
                                     "width": "100%", "height": "100%", "padding": "40px",
                                     "reveal": "scale-in", "revealDelay": 0,
                                     "children": {"explicitList": ["card"]}}),
        C("card", "gdm-container", {"direction": "column", "align": "center", "gap": "18px",
                                    "padding": "44px 56px", "glass": True, "borderRadius": "22px",
                                    "children": {"explicitList": ["badge", "ttl1", "ttl2", "sub", "clock"]}}),
        C("badge", "gdm-badge", {"text": "LIVE · GOOGLE MEET MAINSTAGE", "type": "danger", "pulse": True}),
        C("ttl1",  "gdm-text",  {"content": "▲ A2UI POSSIBILITIES", "size": "44px",
                                 "color": "accent", "uppercase": True, "weight": "800", "align": "center",
                                 "letterSpacing": "0.06em"}),
        C("ttl2",  "gdm-text",  {"content": "COMPOSED LIVE BY THE AGENT", "size": "72px",
                                 "color": "white", "uppercase": True, "weight": "900",
                                 "font": "mono", "flip": True, "align": "center"}),
        C("sub",   "gdm-text",  {"content": "one catalogue of primitives  ·  realtime  ·  multi-domain",
                                 "size": "caption", "color": "mute", "uppercase": True,
                                 "letterSpacing": "0.2em", "align": "center"}),
        C("clock", "gdm-clock", {"showClock": True, "showDate": True, "variant": "flip", "accentColor": "accent"}),
    ]

# ────────────────────────────────────────────────────────────────────────────
# Act 1 — Market scan (the existing dense board, already framed)
# ────────────────────────────────────────────────────────────────────────────
def act_market(tick: int):
    return dense_board(tick)

# ────────────────────────────────────────────────────────────────────────────
# Act 5 — Architecture diagram, framed as a molecule (composition, no new TS)
# ────────────────────────────────────────────────────────────────────────────
# Polished icon library + D2 tier classes — one design language across the stage
# (gdm-icon) and diagrams. White-stroke monochrome SVGs sit on dark coloured-stroke
# panels; the tier class dictates the accent (ext cyan · core red · data gold · llm magenta).
ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "d2", "icons")

# (node_id, label, icon, tier)
# Tier palette aligns with the ultimate_showcase trading_svg: cyan = edges
# (data sources / clients), magenta = core (the brain), green = data tier
# (where state is rendered / executed), purple = LLM. Each tier gets its
# own glow filter in _polish_d2_svg().
NODES = [
    ("user",    "User",                       "user",     "ext"),
    ("meet",    "Google Meet",                "browser",  "ext"),
    ("addon",   "Stage Add-on",               "bolt",     "core"),
    ("backend", "Cloud Run\\nFastAPI + MCP",  "server",   "core"),
    ("gemini",  "Gemini Live",                "llm",      "llm"),
    ("stage",   "A2UI Stage",                 "globe",    "data"),
    ("feeds",   "Realtime Feeds",             "database", "ext"),
]
EDGES = [
    ("user",    "meet",    ""),
    ("meet",    "addon",   "panel"),
    ("addon",   "backend", "WebSocket"),
    ("backend", "gemini",  "Live API"),
    ("backend", "stage",   "render_stage"),
    ("feeds",   "backend", "stream"),
    ("stage",   "meet",    "displays"),
]

# Tier accent colours — referenced both in the d2 classes: block (so d2 sets
# them as stroke="..." on each node) AND in _polish_d2_svg() (so we can target
# them via [stroke="..."] attribute selectors to attach glow filters). Keep
# these in sync if you re-skin.
_TIER_COLOURS = {
    "ext":  "#00f2ff",  # cyan — edges, data sources, clients
    "core": "#f000ff",  # magenta — the central brain
    "data": "#00ff88",  # green — where state is rendered / executed
    "llm":  "#b388ff",  # purple — language models
}

def _build_d2() -> str:
    # NB: d2's stroke-width must be an integer 0–15. Floats (e.g. 2.5) fail
    # parse with: 'expected "stroke-width" to be a number between 0 and 15'.
    cls_line = ('  {name}: {{ style: {{ fill: "{fill}"; stroke: "{stroke}"; '
                'stroke-width: {sw}; border-radius: {br}; font-color: "#ffffff" }} }}')
    lines = [
        "direction: right",
        "",
        "classes: {",
        cls_line.format(name="ext",  fill="#0c1120", stroke=_TIER_COLOURS["ext"],  sw=3, br=10),
        cls_line.format(name="core", fill="#1a0a26", stroke=_TIER_COLOURS["core"], sw=3, br=12),
        cls_line.format(name="data", fill="#0a1f15", stroke=_TIER_COLOURS["data"], sw=3, br=10),
        cls_line.format(name="llm",  fill="#1a0e2a", stroke=_TIER_COLOURS["llm"],  sw=3, br=10),
        "}",
        "",
    ]
    for nid, label, icon, cls in NODES:
        lines.append(f'{nid}: "{label}" {{ icon: {ICON_DIR}/{icon}.svg; class: {cls} }}')
    lines.append("")
    # Edges are dashed at the d2 level so the polish-layer marching-ants CSS
    # has something to march on (it animates stroke-dashoffset on any path
    # that already carries a stroke-dasharray).
    for src, dst, lbl in EDGES:
        suffix = "{ style.stroke-dash: 4 }"
        lines.append(f'{src} -> {dst}: "{lbl}" {suffix}' if lbl else f'{src} -> {dst}: {suffix}')
    return "\n".join(lines)


def _polish_d2_svg(svg: str) -> str:
    """Inject cyberpunk polish into a d2-generated SVG, hand-tuned style
    without losing d2's auto-layout: glow filters per tier (via stroke-colour
    CSS selectors), marching-ants animation on dashed edges, a dot-grid
    background. Decoupled from d2's internal class naming — we target by
    stroke colour, which we control in the classes: block above."""
    polish = (
        '<defs>'
        # Glow filters — same feGaussianBlur+feMerge pattern as the
        # ultimate_showcase trading_svg, one per tier.
        '<filter id="glow-ext" x="-25%" y="-25%" width="150%" height="150%">'
        '<feGaussianBlur stdDeviation="3.5" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
        '</filter>'
        '<filter id="glow-core" x="-25%" y="-25%" width="150%" height="150%">'
        '<feGaussianBlur stdDeviation="6" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
        '</filter>'
        '<filter id="glow-data" x="-25%" y="-25%" width="150%" height="150%">'
        '<feGaussianBlur stdDeviation="4" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
        '</filter>'
        '<filter id="glow-llm" x="-25%" y="-25%" width="150%" height="150%">'
        '<feGaussianBlur stdDeviation="4" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>'
        '</filter>'
        # Subtle blueprint-style dot grid overlay.
        '<pattern id="bg-dots" width="24" height="24" patternUnits="userSpaceOnUse">'
        '<circle cx="2" cy="2" r="1.1" fill="rgba(0,242,255,0.08)"/>'
        '</pattern>'
        '</defs>'
        '<style>'
        # Glow attachment by stroke colour — works regardless of d2 version
        # since we control the colours via the classes: block.
        f'[stroke="{_TIER_COLOURS["ext"]}"]  {{ filter: url(#glow-ext); }}'
        f'[stroke="{_TIER_COLOURS["core"]}"] {{ filter: url(#glow-core); }}'
        f'[stroke="{_TIER_COLOURS["data"]}"] {{ filter: url(#glow-data); }}'
        f'[stroke="{_TIER_COLOURS["llm"]}"]  {{ filter: url(#glow-llm); }}'
        # Marching ants on dashed edges — d2 emits the dash pattern as either
        # an attribute or inline style depending on version; cover both.
        'path[stroke-dasharray], path[style*="stroke-dasharray"] {'
        ' animation: march 1.4s linear infinite;'
        '}'
        '@keyframes march { to { stroke-dashoffset: -120; } }'
        '</style>'
        # Dot-grid backdrop — pointer-events:none so it never intercepts hover.
        '<rect width="100%" height="100%" fill="url(#bg-dots)" pointer-events="none"/>'
    )
    return re.sub(r'(<svg[^>]*>)', lambda m: m.group(1) + polish, svg, count=1)

D2_SRC = _build_d2()

_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")
_INTER   = os.path.join(_FONT_DIR, "InterVariable.ttf")
_JB_REG  = os.path.join(_FONT_DIR, "JetBrainsMono-Regular.ttf")
_JB_BOLD = os.path.join(_FONT_DIR, "JetBrainsMono-Bold.ttf")

def _gen_svg() -> str:
    # Match the stage catalogue typography: Inter for labels (sans),
    # JetBrains Mono for mono-styled elements — same fonts gdm-text uses.
    cmd = ["d2", "-t", "200"]
    if os.path.exists(_INTER):
        cmd += ["--font-regular", _INTER, "--font-bold", _INTER,
                "--font-italic", _INTER, "--font-semibold", _INTER]
    if os.path.exists(_JB_REG):
        cmd += ["--font-mono", _JB_REG]
    if os.path.exists(_JB_BOLD):
        cmd += ["--font-mono-bold", _JB_BOLD]
    cmd += ["-", "-"]
    try:
        r = subprocess.run(cmd, input=D2_SRC, capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            return _polish_d2_svg(r.stdout)
    except Exception as e:
        print(f"d2 generation failed: {e}", file=sys.stderr)
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200"><text x="200" y="100" fill="#fff" text-anchor="middle" font-family="monospace">[diagram unavailable]</text></svg>'

DIAGRAM_SVG = _gen_svg()

def act_diagram(_tick: int):
    # Diagram-only. The overlay mode on gdm-diagram-view pops it as a full-
    # viewport glass card across the stage, so any underlying chrome would
    # just flash for a beat before being covered — keep the surface to root
    # → diag and let the diagram be the act.
    return [
        C("root", "gdm-stage-grid", {"layout": "hero", "children": {"explicitList": ["diag"]}}),
        C("diag", "gdm-diagram-view", {"diagId": "showreel-arch", "svg": DIAGRAM_SVG, "version": 1,
                                       "overlay": True}),
    ]

def _cap(text: str, flip: bool, show_prev: bool = True):
    # Stable id 'cap' so main_stage REUSES the caption element across renders
    # within an act — that's what lets us flip the mode (flip ↔ plain) without
    # the entrance choreography of the act re-playing. showPrev=False suppresses
    # the small faded prior-line pill (cleaner narration for staged demos).
    return C("cap", "gdm-captions", {"text": text, "speaker": "", "active": True, "flip": flip, "showPrev": show_prev})

# Two-caption pattern: a centered FLIP HEADLINE introduces each topic, then it
# fades out (active:False) and a BOTTOM PLAIN caption takes over for ongoing
# narration. Distinct stable ids so both elements can coexist and toggle active.
def _headline_cap(text: str, active: bool = True):
    return C("headline", "gdm-captions", {
        "text": text, "speaker": "", "active": active,
        "flip": True, "showPrev": False, "position": "center", "fontSize": 60,
    })

def _bottom_cap(text: str, active: bool = True, flip: bool = False):
    return C("cap", "gdm-captions", {
        "text": text, "speaker": "", "active": active,
        "flip": flip, "showPrev": False, "position": "bottom",
    })

# ────────────────────────────────────────────────────────────────────────────
# Act 2 — Final Approach (ATC)
# Focused 3D + realtime: airspace fills the hero; caption carries the next
# lander's live touchdown countdown; flip headlines fire on events.
# ────────────────────────────────────────────────────────────────────────────
def _fmt_mmss(s: int) -> str:
    s = max(0, int(s))
    return f"{s // 60:02d}:{s % 60:02d}"

def _initial_planes():
    return [
        {"callsign": "AFR6129", "alt": 1500, "speed": 160, "eta": 28, "origin": "PAR"},
        {"callsign": "BAW373",  "alt": 3200, "speed": 210, "eta": 118, "origin": "LHR"},
        {"callsign": "EZY4218", "alt": 5400, "speed": 260, "eta": 208, "origin": "GVA"},
    ]

_NEW_ARRIVALS = [
    {"callsign": "DLH11A",  "alt": 5400, "speed": 260, "eta": 220, "origin": "FRA"},
    {"callsign": "RYR109B", "alt": 5400, "speed": 260, "eta": 230, "origin": "DUB"},
]

def act_atc(planes):
    top = planes[0]
    n = len(planes)
    return [
        C("root", "gdm-stage-grid", {"layout": "hero", "children": {"explicitList": ["main"]}}),
        C("main", "gdm-container", {"direction": "column", "padding": "16px", "gap": "12px",
                                    "width": "100%", "height": "100%", "glass": True,
                                    "reveal": "scale-in", "revealDelay": 0,
                                    "children": {"explicitList": ["hdr", "hdrdiv", "airspace"]}}),
        C("hdr", "gdm-container", {"direction": "row", "align": "center", "width": "100%",
                                   "reveal": "fade-up", "revealDelay": 0.15,
                                   "children": {"explicitList": ["titlecol", "sp", "flightsbadge", "windbadge", "clock"]}}),
        C("titlecol", "gdm-container", {"direction": "column", "gap": "3px",
                                        "children": {"explicitList": ["badge", "title", "callsign", "sub"]}}),
        C("badge", "gdm-badge", {"text": "TLS · RWY 32 · CAVOK", "type": "warning", "pulse": True}),
        C("title", "gdm-text", {"content": "▲ FINAL APPROACH", "size": "h1", "color": "accent", "uppercase": True}),
        # Hero callsign — flips when the queue rotates so the next lander reads instantly.
        C("callsign", "gdm-text", {"content": top["callsign"], "size": "56px", "color": "white",
                                   "weight": "900", "font": "mono", "uppercase": True,
                                   "letterSpacing": "0.04em", "flip": True}),
        C("sub",   "gdm-text", {"content": f"next lander · {top['origin']} → TLS",
                                "size": "20px", "color": "#cfd8e8", "uppercase": True,
                                "weight": "700", "letterSpacing": "0.14em"}),
        C("sp", "gdm-spacer", {}),
        # Live flight count — pulses so its dynamism reads on the chrome.
        C("flightsbadge", "gdm-badge", {"text": f"{n} ON FINAL", "type": "danger", "pulse": True}),
        C("windbadge", "gdm-badge", {"text": "WIND 120° / 6 KT", "type": "info", "outline": True}),
        C("clock", "gdm-clock", {"showClock": True, "showDate": False, "variant": "flip", "accentColor": "accent"}),
        C("hdrdiv", "gdm-divider", {"color": "rgba(255,214,10,0.18)"}),
        C("airspace", "gdm-3d-airspace", {
            "flights": [{"callsign": p["callsign"], "altitude": p["alt"], "speed": p["speed"],
                         "vrate": -600, "origin": p["origin"], "destination": "TLS"} for p in planes],
            "lockedCallsign": top["callsign"],
            "cameraPitch": 22, "cameraYaw": 40,
            "showGlideSlope": True, "showTerrain": True,
            "zoom": 14, "cinematicOrbit": False, "autoTrack": True,
            "compact": True,  # hides molecule's internal title/side-panel/lock-card so the outer composition owns all chrome
        }),
    ]

async def play_atc(c, H, duration: float = 32.0):
    """ATC act with a live countdown. Surface is CACHED per planes-state so the
    airspace doesn't re-render every tick (only the caption swaps); rebuilds the
    surface only when the queue rotates after a touchdown.

    Narration: bottom caption alternates between the live touchdown countdown
    and short explanation lines, so viewers understand what they're looking at
    (the 3D molecule, the realtime push path) rather than just the data."""
    planes = _initial_planes()
    surface = act_atc(planes)
    arrivals_used = 0

    # Explanation lines woven into the countdown — same cadence as the other
    # acts' body lines, but interleaved with the live ETA so the data keeps
    # ticking. Kept short, uppercase, mono-cadence to match the surface chrome.
    EXPLAIN = [
        "3D AIRSPACE · gdm-3d-airspace molecule",
        "ONE COMPONENT · LIVE FLIGHTS, TERRAIN, GLIDESLOPE",
        "DATA STREAMS STRAIGHT TO THE STAGE · NO LLM IN THE LOOP",
        "QUEUE REBUILDS ON TOUCHDOWN · NEXT LANDER LOCKS",
    ]
    explain_idx = 0
    # Show countdown twice for every explanation line so viewers track the
    # live ETA but still get context.
    EXPLAIN_EVERY = 3

    await c.post(f"{API}/api/render-stage-clear/{SPACE}", headers=H, json={})
    await asyncio.sleep(0.25)
    # Initial render: surface + CENTERED FLIP HEADLINE + inactive bottom caption (ready to take over).
    await c.post(f"{API}/api/render-stage/{SPACE}", headers=H, json={
        "surfaceUpdate": {"components": surface + [_headline_cap("FINAL APPROACH", True), _bottom_cap("", False)]},
        "root": "root",
    })
    print("  ▶ ATC: ⟪FINAL APPROACH⟫")

    headline_hold = 3.0
    await asyncio.sleep(headline_hold)
    elapsed = headline_hold
    # Switch: fade out headline; bottom caption takes over with the live countdown.
    await c.post(f"{API}/api/render-stage/{SPACE}", headers=H, json={
        "surfaceUpdate": {"components": [_headline_cap("FINAL APPROACH", False),
                                         _bottom_cap(f"NEXT LANDER {planes[0]['callsign']} · TOUCHDOWN IN {_fmt_mmss(planes[0]['eta'])}", True, flip=False)]},
        "root": "root",
    })

    tick = 0
    while elapsed < duration:
        for p in planes:
            p["eta"] = max(0, p["eta"] - 1)
        top = planes[0]
        if top["eta"] == 0:
            # Touchdown — emphasise via flip on the bottom caption
            await c.post(f"{API}/api/render-stage/{SPACE}", headers=H, json={
                "surfaceUpdate": {"components": [_bottom_cap(f"TOUCHDOWN ✓ {top['callsign']}", True, flip=True)]},
                "root": "root",
            })
            print(f"  ▶ ATC: ⟪TOUCHDOWN ✓ {top['callsign']}⟫")
            await asyncio.sleep(3.0); elapsed += 3.0
            # Rotate queue: top departs, new arrival appended
            planes.pop(0)
            if arrivals_used < len(_NEW_ARRIVALS):
                planes.append(dict(_NEW_ARRIVALS[arrivals_used]))
                arrivals_used += 1
            surface = act_atc(planes)  # rebuild — flights/locked change → fresh
            # Re-render new surface (genuinely changed) + revert to plain bottom caption
            top = planes[0]
            await c.post(f"{API}/api/render-stage/{SPACE}", headers=H, json={
                "surfaceUpdate": {"components": surface + [_bottom_cap(f"NEXT LANDER {top['callsign']} · TOUCHDOWN IN {_fmt_mmss(top['eta'])}", True, flip=False)]},
                "root": "root",
            })
            await asyncio.sleep(1.0); elapsed += 1.0
        else:
            # Plain narration tick — partial update, ONLY the bottom caption.
            # Engine compiles airspace from buffer with _fresh:false, so main_stage
            # skips re-applying its props → user camera/pinch/preset state PERSISTS.
            # Every EXPLAIN_EVERY-th tick swap the countdown for a context line.
            # Plain text (not flip) — gdm-captions' flap cards default to 38px per
            # letter inside a .pill.active clamped to 2 lines with overflow:hidden,
            # so the longer EXPLAIN strings clip / lay out badly as flap rows.
            # Plain pill wraps cleanly with -webkit-line-clamp.
            if tick % EXPLAIN_EVERY == EXPLAIN_EVERY - 1 and EXPLAIN:
                cap_text = EXPLAIN[explain_idx % len(EXPLAIN)]
                explain_idx += 1
            else:
                cap_text = f"NEXT LANDER {top['callsign']} · TOUCHDOWN IN {_fmt_mmss(top['eta'])}"
            await c.post(f"{API}/api/render-stage/{SPACE}", headers=H, json={
                "surfaceUpdate": {"components": [_bottom_cap(cap_text, True, flip=False)]},
                "root": "root",
            })
            tick += 1
            await asyncio.sleep(1.0); elapsed += 1.0
    print("  ▶ ATC act done")

# (act_name, build_fn, headline_flip, [body_plain_lines], total_duration_s)
# ────────────────────────────────────────────────────────────────────────────
# Act — Multimodal (YouTube)
# ────────────────────────────────────────────────────────────────────────────
def act_video(_tick: int):
    return [
        C("root", "gdm-stage-grid", {"layout": "hero", "children": {"explicitList": ["main"]}}),
        C("main", "gdm-container", {"direction": "column", "padding": "16px", "gap": "12px",
                                    "width": "100%", "height": "100%", "glass": True,
                                    "reveal": "scale-in", "revealDelay": 0,
                                    "children": {"explicitList": ["hdr", "hdrdiv", "vid"]}}),
        C("hdr", "gdm-container", {"direction": "row", "align": "center", "width": "100%",
                                   "reveal": "fade-up", "revealDelay": 0.15,
                                   "children": {"explicitList": ["titlecol", "sp", "clock"]}}),
        C("titlecol", "gdm-container", {"direction": "column", "gap": "3px",
                                        "children": {"explicitList": ["badge", "title", "sub"]}}),
        C("badge", "gdm-badge", {"text": "MULTIMODAL · YOUTUBE EMBED", "type": "primary", "pulse": True}),
        C("title", "gdm-text", {"content": "▲ HIGH-QUALITY VIDEO", "size": "h1", "color": "accent", "uppercase": True}),
        C("sub", "gdm-text", {"content": "any rich media composed into the stage via gdm-video-panel", "size": "caption", "color": "mute"}),
        C("sp", "gdm-spacer", {}),
        C("clock", "gdm-clock", {"showClock": True, "showDate": False, "variant": "flip", "accentColor": "accent"}),
        C("hdrdiv", "gdm-divider", {"color": "rgba(0,242,255,0.18)"}),
        C("vid", "gdm-video-panel", {
            # OK Go — This Too Shall Pass (Rube Goldberg), t=57. Component
            # embeds via youtube.com (not youtube-nocookie.com) since some
            # music-label videos refuse the privacy-enhanced variant.
            "src": "https://youtu.be/qybUFnY7Y8w?t=57",
            "autoplay": True,
            "overlay": True,  # pop fullscreen across the stage (like the diagram act)
        }),
    ]

# ────────────────────────────────────────────────────────────────────────────
# Quad finale — 2×2 grid with one molecule per cell + a centered headline
# ────────────────────────────────────────────────────────────────────────────
def act_quad(_tick: int):
    # 4 small-ish "mini" panels — gdm-stage-grid layout="grid" assigns
    # panel-1..panel-4 slots in child order (TL, TR, BL, BR).
    # NOTE on the video URL: the previously requested LWGJA9i18Co returns
    # "Video unavailable" because its uploader disabled embedding (the t=10
    # start time is fine). Swap in any embed-allowed video to use it here.
    yt = "https://youtu.be/qybUFnY7Y8w?t=57"
    # Top-left market mini-panel — composed from primitives (NOT gdm-market-ticker,
    # which forces position:fixed; inset:0 and ignores its grid slot, leaving
    # panel-1 empty).
    rows = [
        ("SPX",    "5,310.45", "+0.42%", True,  "#00f2ff"),
        ("NDX",    "18,650.10","+0.88%", True,  "#00f2ff"),
        ("BTC",    "68,450.00","+2.65%", True,  "#ff9f0a"),
        ("ETH",    "3,820.10", "+1.10%", True,  "#ff9f0a"),
        ("EURUSD", "1.0854",   "+0.12%", True,  "#b388ff"),
        ("USDJPY", "156.82",   "−0.21%", False, "#b388ff"),
    ]
    row_ids = [f"qmkt_row{i}" for i in range(len(rows))]

    def _mkt_row(i, sym, price, chg, up, accent):
        # grow:1 lets the 6 rows share the panel's available height evenly,
        # instead of packing at content height and leaving the bottom of the
        # cell visually empty (the "half panel" issue).
        return [
            C(f"qmkt_row{i}", "gdm-container", {"direction": "row", "align": "center",
                                                "gap": "10px", "padding": "8px 4px",
                                                "grow": 1,
                                                "children": {"explicitList": [f"qmkt_sym{i}", f"qmkt_price{i}",
                                                                              f"qmkt_sp{i}", f"qmkt_chg{i}"]}}),
            C(f"qmkt_sym{i}",   "gdm-text", {"content": sym, "size": "17px", "color": "white",
                                             "font": "mono", "weight": "800", "letterSpacing": "0.06em"}),
            C(f"qmkt_price{i}", "gdm-text", {"content": price, "size": "17px", "color": "mute", "font": "mono", "flip": True}),
            C(f"qmkt_sp{i}",    "gdm-spacer", {}),
            C(f"qmkt_chg{i}",   "gdm-text", {"content": chg, "size": "16px",
                                             "color": "#19d27a" if up else "#ff5d5d",
                                             "font": "mono", "weight": "700"}),
        ]

    market_panel = [
        # grow:1 is REQUIRED here even though the parent slot already pushes
        # flex:1 on slotted children — gdm-container's updated() writes inline
        # style.flexGrow="0" (the prop default), and inline-style beats the
        # shadow DOM slot rule, so without grow:1 this panel collapses to
        # content height and leaves the bottom of the cell empty.
        C("q_mkt", "gdm-container", {"direction": "column", "padding": "16px", "gap": "6px",
                                     "glass": True, "borderRadius": "12px",
                                     "width": "100%", "height": "100%", "grow": 1,
                                     "children": {"explicitList": ["qmkt_hdr", "qmkt_div"] + row_ids}}),
        C("qmkt_hdr", "gdm-container", {"direction": "row", "align": "center", "gap": "8px",
                                        "children": {"explicitList": ["qmkt_badge", "qmkt_sp_hdr", "qmkt_title"]}}),
        C("qmkt_badge", "gdm-badge", {"text": "REALTIME", "type": "danger", "pulse": True}),
        C("qmkt_sp_hdr", "gdm-spacer", {}),
        C("qmkt_title", "gdm-text", {"content": "MARKET SCAN", "size": "13px", "color": "mute",
                                     "uppercase": True, "letterSpacing": "0.18em"}),
        C("qmkt_div", "gdm-divider", {"color": "rgba(0,242,255,0.18)"}),
    ]
    for i, (sym, price, chg, up, accent) in enumerate(rows):
        market_panel += _mkt_row(i, sym, price, chg, up, accent)
    return [
        C("root", "gdm-stage-grid", {"layout": "grid", "children": {"explicitList": ["q_mkt", "q_air", "q_diag", "q_vid"]}}),
        *market_panel,
        # TR — 3D airspace (compact, full cell)
        C("q_air", "gdm-3d-airspace", {
            "flights": [{"callsign": p["callsign"], "altitude": p["alt"], "speed": p["speed"], "vrate": -600, "origin": p["origin"], "destination": "TLS"}
                        for p in _initial_planes()],
            "lockedCallsign": "AFR6129",
            "cameraPitch": 25, "cameraYaw": 40, "zoom": 14,
            "showGlideSlope": True, "showTerrain": True, "compact": True, "autoTrack": True,
        }),
        # BL — diagram (D2 SVG)
        C("q_diag", "gdm-diagram-view", {"diagId": "quad-diag", "svg": DIAGRAM_SVG, "version": 1}),
        # BR — youtube
        C("q_vid", "gdm-video-panel", {"src": yt, "autoplay": True}),
    ]

# (name, build_fn, headline, body_lines, total_duration_s, is_atc_special)
ACTS = [
    ("title",   act_title,   "A2UI POSSIBILITIES",
     ["composed live by the agent.", "one catalogue · realtime · multi-domain."], 8.0, False),
    ("market",  act_market,  "REALTIME · MARKET",
     ["Cross-asset scan over the websocket.", "Top movers surface automatically."], 10.0, False),
    ("diagram", act_diagram, "LIVE ARCHITECTURE",
     ["D2 renders the diagram itself.", "Frame composed from primitives.",
      "Pops as a glass overlay across the stage."], 16.0, False),
    ("atc",     None,        "FINAL APPROACH",
     [], 30.0, True),  # ATC handles its own narration (live countdown)
    ("video",   act_video,   "MULTIMODAL · VIDEO",
     [], 6.0, False),  # no narration — the video itself is the act, 6s feel
    ("quad",    act_quad,    "ALL FROM GOOGLE MEET",
     [], 14.0, False),  # finale — no narration, just the headline holds
]

async def main():
    only = os.environ.get("ACT_ONLY", "")
    cycles = int(os.environ.get("CYCLES", "1"))
    async with httpx.AsyncClient(timeout=20) as c:
        H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
        if only == "atc":
            await play_atc(c, H, duration=float(os.environ.get("ATC_DURATION", "34")))
            return

        for cycle in range(cycles):
            for name, build, headline, body, dur, is_atc in ACTS:
                if is_atc:
                    await play_atc(c, H, duration=dur)
                    continue

                surface = build(cycle * 10)
                # 1. Clear + render: surface + CENTERED FLIP HEADLINE + inactive bottom caption.
                await c.post(f"{API}/api/render-stage-clear/{SPACE}", headers=H, json={})
                await asyncio.sleep(0.25)
                await c.post(f"{API}/api/render-stage/{SPACE}", headers=H, json={
                    "surfaceUpdate": {"components": surface + [_headline_cap(headline, True), _bottom_cap("", False)]},
                    "root": "root",
                })
                print(f"  ▶ act {name}: ⟪{headline}⟫")
                headline_hold = 3.0
                await asyncio.sleep(headline_hold)

                if not body:
                    # finale-style — hold the headline for the full duration
                    await asyncio.sleep(max(0, dur - headline_hold))
                    continue

                # 2. Switch: fade headline out, fade in bottom plain caption with body line 1.
                #    Partial update — only the two captions are _fresh; surface props preserved.
                pacing = max(2.5, (dur - headline_hold) / len(body))
                for i, line in enumerate(body):
                    await c.post(f"{API}/api/render-stage/{SPACE}", headers=H, json={
                        "surfaceUpdate": {"components": [_headline_cap(headline, False), _bottom_cap(line, True, flip=False)]},
                        "root": "root",
                    })
                    print(f"    · {line}")
                    await asyncio.sleep(pacing)

    print("showreel done")

if __name__ == "__main__":
    asyncio.run(main())
