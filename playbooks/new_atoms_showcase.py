"""New Atoms Showcase Playbook — premium presentation of Donut Stat & Heatmap.

Slides:
- cover: Intro to the next-gen data visualization primitives.
- donut: Interactive quota progress gauges with neon glows.
- heatmap: Calendar matrices with color scales and micro-animations.

Fire:
    curl -X POST http://127.0.0.1:8085/api/playbook/fire/new_atoms_showcase/cover/default
"""
import sys
sys.path.insert(0, "/home/curtis/a2ui-catalogue")

from renderers.web_article import render as wa_render
from playbooks.manager import Slide, playbook_manager

PLAYBOOK = "new_atoms_showcase"

def C(cid, el, props):
    return {"id": cid, "component": el,
            **{k: v for k, v in props.items() if k not in ("id", "component")}}

def fire(slide_id, space_id):
    return {"functionCall": {"call": "fireEndpoint",
                             "args": {"endpoint": f"/api/playbook/fire/{PLAYBOOK}/{slide_id}/{space_id}"}}}

_CSS = (
    "<style>"
    "*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}"
    "html,body{width:100%;height:100%;background:linear-gradient(135deg,#0a0f1d 0%,#111827 100%);color:#f3f4f6;"
    "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;overflow:auto;padding:48px;}"
    "h1{font-size:42px;font-weight:900;margin-bottom:8px;background:linear-gradient(to right,#38bdf8,#818cf8);-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:-1px;}"
    ".subtitle{font-size:16px;color:#9ca3af;margin-bottom:32px;font-weight:400;letter-spacing:-0.2px;}"
    ".showcase-container{display:flex;flex-direction:column;gap:24px;width:100%;}"
    "</style>"
)

def html_slide(atoms: list, title: str, subtitle: str="", prev_id: str=None, next_id: str=None, back_id="cover"):
    """Build a premium gdm-html-panel slide showcasing atoms."""
    html_content = _CSS + f"""
    <div style="margin-bottom:24px">
        <h1>{title}</h1>
        {f'<div class="subtitle">{subtitle}</div>' if subtitle else ''}
    </div>
    <div class="showcase-container">
        {"".join(wa_render([{**d}]) for d in atoms)}
    </div>
    """

    def builder(space_id, tick=0):
        footer = []
        if prev_id:  footer.append("btn_prev")
        footer += ["btn_back", "lbl"]
        if next_id:  footer.append("btn_next")

        comps = [
            C("root", "gdm-stage-grid", {"layout": "hero", "children": ["wrap"]}),
            C("wrap", "gdm-container", {"direction": "column", "grow": 1,
                                         "width": "100%", "height": "100%",
                                         "children": ["panel", "ftr"]}),
            C("panel", "gdm-html-panel", {"html": html_content, "version": tick + 1}),
            C("ftr", "gdm-container", {"direction": "row", "align": "center",
                                       "justify": "center", "padding": "8px 16px",
                                       "gap": "12px", "shrink": 0, "children": footer}),
            C("btn_back", "gdm-button", {"text": "⬡ Back to Cover", "action": fire(back_id, space_id)}),
            C("lbl", "gdm-text", {"content": "Substrate-Not-Slides™", "size": "11px", "color": "#4b5563"}),
        ]
        if prev_id:
            comps.append(C("btn_prev", "gdm-button", {"text": "← " + prev_id.capitalize(), "action": fire(prev_id, space_id)}))
        if next_id:
            comps.append(C("btn_next", "gdm-button", {"text": "→ " + next_id.capitalize(), "action": fire(next_id, space_id)}))
        return comps
    return builder

# ── Cover ─────────────────────────────────────────────────────────────────

def build_cover(space_id, tick=0):
    comps = [
        C("root", "gdm-stage-grid", {"layout": "hero", "children": ["main"]}),
        C("main", "gdm-container", {
            "direction": "column", "justify": "center", "align": "center",
            "grow": 1, "gap": "32px", "padding": "80px",
            "width": "100%", "height": "100%",
            "children": ["brand", "title", "sub", "grid"],
        }),
        C("brand", "gdm-text", {
            "content": "A2UI NEW RELEASES",
            "size": "12px", "weight": "800", "font": "mono",
            "color": "#38bdf8", "letterSpacing": "0.15em",
        }),
        C("title", "gdm-text", {
            "content": "Enterprise Primitives",
            "size": "56px", "weight": "900", "font": "sans",
            "color": "#f3f4f6", "letterSpacing": "-1.5px",
        }),
        C("sub", "gdm-text", {
            "content": "Next-Gen Visualizations: Donut Progress, Heatmap, Punch Card, Sankey, Cohort Retention, Tasks & Sentiment",
            "size": "18px", "color": "#9ca3af", "weight": "400",
        }),
        C("grid", "gdm-container", {
            "direction": "row", "justify": "center", "align": "center",
            "gap": "14px",
            "children": ["btn_donut", "btn_heatmap", "btn_punch", "btn_sankey", "btn_cohort", "btn_tasks", "btn_sentiment"],
        }),
        C("btn_donut", "gdm-button", {
            "text": "🔵 Donut Progress",
            "size": "md",
            "action": fire("donut", space_id),
        }),
        C("btn_heatmap", "gdm-button", {
            "text": "🟩 Heatmap Grid",
            "size": "md",
            "action": fire("heatmap", space_id),
        }),
        C("btn_punch", "gdm-button", {
            "text": "📊 Commit Punch Card",
            "size": "md",
            "action": fire("punch", space_id),
        }),
        C("btn_sankey", "gdm-button", {
            "text": "🔀 Sankey Cashflow",
            "size": "md",
            "action": fire("sankey", space_id),
        }),
        C("btn_cohort", "gdm-button", {
            "text": "📐 SaaS Cohort Grid",
            "size": "md",
            "action": fire("cohort", space_id),
        }),
        C("btn_tasks", "gdm-button", {
            "text": "📝 Task Checklist",
            "size": "md",
            "action": fire("tasks", space_id),
        }),
        C("btn_sentiment", "gdm-button", {
            "text": "🎭 Sentiment Journey",
            "size": "md",
            "action": fire("sentiment", space_id),
        }),
    ]
    return comps

# ── Slide 1: Donut Stats Showcase ─────────────────────────────────────────

donut_atoms = [
    {"type": "donut_stat", "label": "Enterprise Segment Quota", "value": 84, "max_value": 100, "unit": "%", "color": "#10b981", "size": "150px"},
    {"type": "donut_stat", "label": "Pipeline Velocity Goal", "value": 312, "max_value": 400, "unit": "k", "color": "#38bdf8", "size": "150px"},
    {"type": "donut_stat", "label": "System Success Slices", "value": 999, "max_value": 1000, "unit": "‰", "color": "#f59e0b", "size": "150px"},
]

# ── Slide 2: Heatmap Showcase ─────────────────────────────────────────────

heatmap_atoms = [
    {"type": "heatmap",
     "labels_x": ["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "W9", "W10", "W11", "W12"],
     "labels_y": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
     "unit": " deploys",
     "color_scale": ["#111827", "#065f46", "#047857", "#10b981", "#34d399", "#6ee7b7"],
     "data": [
         [4, 8, 3, 5, 9, 2, 7, 5, 8, 1, 6, 9],
         [3, 1, 6, 8, 4, 9, 3, 7, 5, 8, 2, 4],
         [9, 4, 8, 2, 7, 1, 5, 9, 3, 6, 8, 5],
         [5, 9, 2, 6, 8, 4, 9, 2, 7, 4, 9, 8],
         [8, 2, 7, 5, 1, 8, 4, 6, 9, 5, 7, 3],
         [1, 0, 3, 1, 2, 0, 1, 0, 2, 1, 3, 0],
         [0, 1, 0, 0, 1, 2, 0, 1, 0, 0, 1, 0],
     ]}
]

# ── Slide 3: Punch Card Showcase (GitHub Repo Activity) ───────────────────

punch_card_atoms = [
    {
        "type": "punch_card",
        "title": "GitHub Commit Density Grid",
        "subtitle": "Repository: curtiskrygier/meetstudio (Last 90 Days)",
        "color": "#00f2ff",
        "data": [
            [0, 0, 0, 0, 1, 2, 4, 8, 12, 18, 15, 14, 10, 15, 20, 24, 22, 16, 12, 8, 6, 3, 1, 0],  # Mon
            [0, 0, 0, 0, 0, 3, 5, 9, 14, 20, 18, 16, 12, 17, 22, 26, 25, 19, 14, 10, 7, 4, 2, 0],  # Tue
            [0, 0, 0, 0, 1, 1, 4, 7, 11, 16, 14, 12, 9, 13, 19, 23, 21, 15, 11, 7, 5, 2, 1, 0],  # Wed
            [0, 0, 0, 0, 0, 2, 4, 8, 13, 19, 17, 15, 11, 16, 21, 25, 24, 18, 13, 9, 6, 3, 1, 0],  # Thu
            [0, 0, 0, 0, 1, 2, 3, 6, 10, 15, 13, 11, 8, 12, 16, 18, 15, 11, 8, 5, 3, 1, 0, 0],  # Fri
            [0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 4, 3, 3, 4, 5, 4, 3, 2, 2, 1, 1, 0, 0],  # Sat
            [0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 4, 3, 4, 6, 5, 4, 3, 2, 2, 1, 0, 0]   # Sun
        ]
    }
]

# ── Slide 4: Sankey Showcase (Financial Flow) ─────────────────────────────

sankey_atoms = [
    {
        "type": "sankey_flow",
        "title": "Corporate Financial Inflows & Budget Allocations",
        "nodes": [
            {"id": "revenue", "label": "ARR Subscriptions", "column": 0, "color": "#10b981"},
            {"id": "funding", "label": "Strategic Financing", "column": 0, "color": "#818cf8"},
            {"id": "rnd", "label": "Engineering & R&D", "column": 1, "color": "#00f2ff"},
            {"id": "marketing", "label": "Growth & Marketing", "column": 1, "color": "#ec4899"},
            {"id": "ops", "label": "Infrastructure & Ops", "column": 1, "color": "#f59e0b"},
            {"id": "reserve", "label": "Liquid Reserves", "column": 1, "color": "#10b981"}
        ],
        "links": [
            {"source": "revenue", "target": "rnd", "value": 75000},
            {"source": "revenue", "target": "marketing", "value": 45000},
            {"source": "revenue", "target": "ops", "value": 20000},
            {"source": "revenue", "target": "reserve", "value": 10000},
            {"source": "funding", "target": "rnd", "value": 30000},
            {"source": "funding", "target": "marketing", "value": 15000},
            {"source": "funding", "target": "ops", "value": 10000},
            {"source": "funding", "target": "reserve", "value": 5000}
        ]
    }
]

# ── Slide 5: Cohort Retention Showcase (SaaS Metrics) ────────────────────

cohort_atoms = [
    {
        "type": "cohort_retention",
        "title": "SaaS Subscription Cohort Retention Matrix (H1 2026)",
        "periods": ["Month 0", "Month 1", "Month 2", "Month 3", "Month 4", "Month 5"],
        "color_scale": ["#1e293b", "#0d9488", "#14b8a6", "#2dd4bf", "#5eead4", "#a7f3d0"],
        "cohorts": [
            {
                "cohort_name": "Jan 2026 Cohort",
                "original_size": 2500,
                "retention_rates": [100.0, 93.4, 88.1, 84.8, 80.2, 78.5]
            },
            {
                "cohort_name": "Feb 2026 Cohort",
                "original_size": 2840,
                "retention_rates": [100.0, 94.8, 89.2, 85.5, 81.9]
            },
            {
                "cohort_name": "Mar 2026 Cohort",
                "original_size": 3120,
                "retention_rates": [100.0, 95.5, 91.0, 87.2]
            },
            {
                "cohort_name": "Apr 2026 Cohort",
                "original_size": 3480,
                "retention_rates": [100.0, 96.2, 92.5]
            },
            {
                "cohort_name": "May 2026 Cohort",
                "original_size": 3890,
                "retention_rates": [100.0, 97.0]
            },
            {
                "cohort_name": "Jun 2026 Cohort",
                "original_size": 4250,
                "retention_rates": [100.0]
            }
        ]
    }
]

SLIDES = [
    Slide("cover", "Showcase Cover", build_cover),
    Slide("donut", "Donut Stats",
          html_slide(donut_atoms, "🔵 Donut Progress",
                     "Beautiful SVG circular charts with custom stroke scaling, glowing effects, and responsive frames",
                     prev_id=None, next_id="heatmap")),
    Slide("heatmap", "Heatmap Grid",
          html_slide(heatmap_atoms, "🟩 Activity Heatmaps",
                     "Stunning mathematical layouts generating grids, continuous color scale interpolation, and neon triggers",
                     prev_id="donut", next_id="punch")),
    Slide("punch", "Commit Punch Card",
          html_slide(punch_card_atoms, "📊 Repo Activity Density",
                     "Day-of-Week vs. Hour-of-Day commit patterns with scaled neon circles and automatic density metrics",
                     prev_id="heatmap", next_id="sankey")),
    Slide("sankey", "Sankey Flow",
          html_slide(sankey_atoms, "🔀 Sankey Cash Flow Allocations",
                     "Mathematical curved Bezier flow bands projecting multiple resource streams through glowing interactive nodes",
                     prev_id="punch", next_id="cohort")),
    Slide("cohort", "SaaS Cohort Retention",
          html_slide(cohort_atoms, "📐 Cohort Retention Analytics",
                     "Premium triangular subscription cohort matrix colored dynamically using continuous scale interpolation",
                     prev_id="sankey", next_id="tasks")),
]

# ── Slide 6: Google Tasks Showcase ────────────────────────────────────────

tasks_atoms = [
    {
        "type": "task_list",
        "title": "Google Tasks & Call Action Items",
        "tasks": [
            {"id": "t1", "text": "Authenticate Google Tasks OAuth flow and verify permissions", "completed": True, "priority": "high", "due_date": "Today, 5:00 PM", "assignee": "CK"},
            {"id": "t2", "text": "Draft system architecture for live audio transcribing pipeline", "completed": False, "priority": "high", "due_date": "Tomorrow", "assignee": "CK"},
            {"id": "t3", "text": "Design premium SVG gauge tracking emotion and sentiment summaries", "completed": True, "priority": "medium", "due_date": "Yesterday", "assignee": "JD"},
            {"id": "t4", "text": "Benchmark websocket streaming latency vs. long-polling under 3G", "completed": False, "priority": "low", "due_date": "Jun 5, 2026", "assignee": "AM"},
            {"id": "t5", "text": "Verify styling and fluid transitions of the call mood summary panel", "completed": False, "priority": "medium", "due_date": "Jun 6, 2026", "assignee": "CK"},
        ]
    }
]

# ── Slide 7: Sentiment Summary Showcase ───────────────────────────────────

sentiment_atoms = [
    {
        "type": "sentiment_summary",
        "title": "Executive Call Sentiment & Mood Intelligence",
        "sentiment_index": 82,
        "emotional_journey": [0.15, 0.35, -0.1, 0.45, 0.78, 0.85, 0.62, 0.92, 0.82],
        "themes": [
            {"theme": "Technical Core Alignment", "mood": "Analytical", "score": 90},
            {"theme": "UX Fluidity & Micro-interactions", "mood": "Engaged", "score": 95},
            {"theme": "Deployment Speed & Integration Cost", "mood": "Hesitant", "score": 45},
            {"theme": "Google Workspace & Tasks Sync Value", "mood": "Excited", "score": 88}
        ]
    }
]

SLIDES = [
    Slide("cover", "Showcase Cover", build_cover),
    Slide("donut", "Donut Stats",
          html_slide(donut_atoms, "🔵 Donut Progress",
                     "Beautiful SVG circular charts with custom stroke scaling, glowing effects, and responsive frames",
                     prev_id=None, next_id="heatmap")),
    Slide("heatmap", "Heatmap Grid",
          html_slide(heatmap_atoms, "🟩 Activity Heatmaps",
                     "Stunning mathematical layouts generating grids, continuous color scale interpolation, and neon triggers",
                     prev_id="donut", next_id="punch")),
    Slide("punch", "Commit Punch Card",
          html_slide(punch_card_atoms, "📊 Repo Activity Density",
                     "Day-of-Week vs. Hour-of-Day commit patterns with scaled neon circles and automatic density metrics",
                     prev_id="heatmap", next_id="sankey")),
    Slide("sankey", "Sankey Flow",
          html_slide(sankey_atoms, "🔀 Sankey Cash Flow Allocations",
                     "Mathematical curved Bezier flow bands projecting multiple resource streams through glowing interactive nodes",
                     prev_id="punch", next_id="cohort")),
    Slide("cohort", "SaaS Cohort Retention",
          html_slide(cohort_atoms, "📐 Cohort Retention Analytics",
                     "Premium triangular subscription cohort matrix colored dynamically using continuous scale interpolation",
                     prev_id="sankey", next_id="tasks")),
    Slide("tasks", "Google Task List",
          html_slide(tasks_atoms, "📝 Google Tasks Sync",
                     "Premium, glassmorphic checklist and action item tracker with completed statuses, priorities, and assignees",
                     prev_id="cohort", next_id="sentiment")),
    Slide("sentiment", "Call Sentiment",
          html_slide(sentiment_atoms, "🎭 Call Sentiment & Mood",
                     "Real-time sentiment tracker mapping positive/negative emotional timeline and call mood summaries",
                     prev_id="tasks", next_id=None)),
]

playbook_manager.register_playbook(PLAYBOOK, SLIDES)
