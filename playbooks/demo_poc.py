# ═══════════════════════════════════════════════════════════════════════════
# STAGED FILE — destination: playbooks/demo_poc.py (NEW)
#
# ## TODO before apply
#   - Slide IDs (`slide_1_intro`, `slide_2_specs`, `slide_3_wrap`) — rename
#     to taste before applying. They're referenced inside button endpoints
#     within sibling slides, so search/replace all three together.
#   - Slide 3's "THE CHEF HAS LEFT THE TABLE." — metaphorical close. Change
#     copy if it doesn't land.
#   - All button endpoints are RELATIVE URLs (`/api/playbook/fire/...`) —
#     this is deliberate so the same playbook works on localhost and on
#     Cloud Run without a code change. Don't add an http://127.0.0.1 prefix.
# ═══════════════════════════════════════════════════════════════════════════
"""Three-slide PoC for the Mode C round-trip mechanism.

Slide 1 → click "Begin Briefing" → fires Slide 2
Slide 2 → click "Commit and Wrap Up" → fires Slide 3 (uses asymmetrical split)
Slide 3 → close

What this PoC validates:
  - The fire endpoint receives a POST and resolves the slide
  - The builder produces a surface, broadcast hits the audience stage
  - `surfaceUpdate` + `beginRendering` both fire so the engine repaints
  - The unified `gdm-button` atom resolves `action: {type: 'fire', ...}`
    by POSTing to the right endpoint
  - Buttons on the audience stage can drive the next render

What this PoC does NOT do (intentional, for later):
  - Put buttons on a separate /presenter URL (proper Mode C)
  - Authenticate fire endpoint clicks (audience-side currently unauthed)
  - Tick loops (slides are all static; tick infrastructure ready in the
    endpoint, just no slides exercise it yet)
"""

from playbooks.manager import Slide


def C(cid: str, el: str, props: dict) -> dict:
    """Component-tuple helper, matches the project convention."""
    return {"id": cid, "component": {el: props}}


# ────────────────────────────────────────────────────────────────────────────
# Slide 1 — Intro slate. Click button → fires slide 2.
# ────────────────────────────────────────────────────────────────────────────
def build_slide_1(space_id: str, tick: int = 0):
    return [
        C("root", "gdm-stage-grid", {"layout": "hero", "children": {"explicitList": ["main"]}}),
        C("main", "gdm-container", {"direction": "column", "justify": "center", "align": "center",
                                    "grow": 1, "gap": "24px", "padding": "60px",
                                    "width": "100%", "height": "100%",
                                    "children": {"explicitList": ["badge", "t1", "btn"]}}),
        C("badge", "gdm-badge", {"text": "MODE C PILOT", "type": "danger", "pulse": True}),
        C("t1", "gdm-text", {"content": "GOOGLE MEET STUDIO", "size": "64px", "weight": "900",
                             "font": "mono", "glitch": True, "letterSpacing": "0.04em"}),
        C("btn", "gdm-button", {
            "text": "Begin Briefing",
            "variant": "primary",
            "size": "lg",
            "pulse": True,
            "action": {
                "type": "fire",
                # Relative URL — uses the page's origin, so this works on
                # localhost AND on Cloud Run without changing the playbook.
                "endpoint": f"/api/playbook/fire/demo_poc/slide_2_specs/{space_id}",
            },
        }),
    ]


# ────────────────────────────────────────────────────────────────────────────
# Slide 2 — Asymmetrical split (left narrative · right fire trigger).
# Demonstrates the doc-split template pattern with the fire-mode button.
# ────────────────────────────────────────────────────────────────────────────
def build_slide_2(space_id: str, tick: int = 0):
    return [
        C("root", "gdm-stage-grid", {"layout": "hero", "children": {"explicitList": ["main"]}}),
        C("main", "gdm-container", {"direction": "row", "width": "100%", "height": "100%",
                                    "grow": 1, "gap": "48px", "padding": "60px",
                                    "align": "stretch",
                                    "children": {"explicitList": ["panel_left", "panel_right"]}}),
        # Left panel — narrative context
        C("panel_left", "gdm-container", {
            "direction": "column", "justify": "center", "align": "flex-start",
            "grow": 1, "glass": True, "borderRadius": "16px",
            "padding": "40px", "gap": "20px",
            "reveal": "slide-right", "revealDelay": 0.0,
            "children": {"explicitList": ["left_badge", "left_title", "left_desc"]},
        }),
        C("left_badge", "gdm-badge", {"text": "CORE SYSTEM BRIEF", "type": "primary"}),
        C("left_title", "gdm-text", {"content": "TECHNICAL DESIGN", "size": "44px",
                                     "weight": "900", "font": "mono", "glitch": True,
                                     "letterSpacing": "0.04em"}),
        C("left_desc",  "gdm-text", {"content": "Reviewing system primitives and operational "
                                                "boundaries. Click the trigger in the action "
                                                "panel to commit final checks.",
                                     "size": "16px", "font": "mono", "typeOn": True,
                                     "color": "rgba(255,255,255,0.75)"}),

        # Right panel — fire trigger
        C("panel_right", "gdm-container", {
            "direction": "column", "justify": "center", "align": "center",
            "grow": 1, "border": "1px dashed rgba(0,242,255,0.2)",
            "borderRadius": "16px", "background": "rgba(0,242,255,0.02)",
            "reveal": "scale-in", "revealDelay": 0.4,
            "children": {"explicitList": ["action_btn"]},
        }),
        C("action_btn", "gdm-button", {
            "text": "Commit and Wrap Up",
            "variant": "success",
            "size": "lg",
            "pulse": True,
            "action": {
                "type": "fire",
                "endpoint": f"/api/playbook/fire/demo_poc/slide_3_wrap/{space_id}",
            },
        }),
    ]


# ────────────────────────────────────────────────────────────────────────────
# Slide 3 — Sign-off slate (no further fire trigger — deck ends).
# ────────────────────────────────────────────────────────────────────────────
def build_slide_3(space_id: str, tick: int = 0):
    return [
        C("root", "gdm-stage-grid", {"layout": "hero", "children": {"explicitList": ["main"]}}),
        C("main", "gdm-container", {"direction": "column", "justify": "center", "align": "center",
                                    "grow": 1, "gap": "16px", "padding": "60px",
                                    "children": {"explicitList": ["badge", "t1"]}}),
        # NB: gdm-badge's type vocabulary is danger/warning/info/primary; use
        # info+outline for the muted "archived" feel (Gem originally used
        # type:"ghost" which likely doesn't exist).
        C("badge", "gdm-badge", {"text": "STATUS: ARCHIVED", "type": "info", "outline": True}),
        C("t1", "gdm-text", {"content": "THE CHEF HAS LEFT THE TABLE.", "size": "48px",
                             "weight": "900", "font": "mono", "typeOn": True,
                             "letterSpacing": "0.06em", "color": "#00ff88"}),
    ]


# Registered by playbooks/__init__.py under the name "demo_poc".
SLIDES = [
    Slide(slide_id="slide_1_intro", label="Intro Slate",  builder=build_slide_1,
          notes="Welcome card · primary fire button"),
    Slide(slide_id="slide_2_specs", label="System Specs", builder=build_slide_2,
          notes="Asymmetrical split — narrative left, success fire button right"),
    Slide(slide_id="slide_3_wrap",  label="Wrap Up",      builder=build_slide_3,
          notes="Final archive slate"),
]
