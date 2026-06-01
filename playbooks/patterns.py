"""Playbook Patterns — selector + 6 pre-mapped pattern demos.

Cover slide shows 6 buttons. Each fires a mini demo of that pattern.
All demos have a ← Patterns button to return to the cover.

Fire:
    curl -X POST http://127.0.0.1:8000/api/playbook/fire/patterns/cover/default
"""
import sys
sys.path.insert(0, "/home/curtis/a2ui-catalogue")

import yaml
from renderers.web_article import render as wa_render
from playbooks.manager import Slide, playbook_manager

PLAYBOOK = "patterns"

# ── Component helpers ─────────────────────────────────────────────────────────

def C(cid, el, props):
    return {"id": cid, "component": el,
            **{k: v for k, v in props.items() if k not in ("id", "component")}}

def fire(slide_id, space_id):
    return {"functionCall": {"call": "fireEndpoint",
                             "args": {"endpoint": f"/api/playbook/fire/{PLAYBOOK}/{slide_id}/{space_id}"}}}

# ── HTML panel builder ────────────────────────────────────────────────────────

_CSS = ("<style>*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}"
        "html,body{width:100%;height:100%;background:#fff;color:#111827;"
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
        "overflow:auto;padding:16px;}</style>")

def html_slide(atoms: list, prev_id: str, next_id: str, back_id="cover"):
    """Build a gdm-stage-grid slide with an html-panel + native nav buttons."""
    html_content = _CSS + "".join(wa_render([{**d}]) for d in atoms)

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
                                       "justify": "center", "padding": "6px 16px",
                                       "gap": "10px", "shrink": 0, "children": footer}),
            C("btn_back", "gdm-button", {"text": "⬡ Patterns", "action": fire(back_id, space_id)}),
            C("lbl", "gdm-text", {"content": "", "size": "11px", "color": "#e5e7eb"}),
        ]
        if prev_id:
            comps.append(C("btn_prev", "gdm-button", {"text": "←", "action": fire(prev_id, space_id)}))
        if next_id:
            comps.append(C("btn_next", "gdm-button", {"text": "→", "action": fire(next_id, space_id)}))
        return comps
    return builder

# ── Cover — pattern selector ──────────────────────────────────────────────────

PATTERNS = [
    ("sprint",   "Sprint Review",        "#7c3aed"),
    ("arch",     "Architecture",         "#2563eb"),
    ("demo",     "Demo / Launch",        "#059669"),
    ("standup",  "Team Standup",         "#dc2626"),
    ("tech",     "Technical Briefing",   "#0891b2"),
    ("data",     "Data Review",          "#d97706"),
]

def build_cover(space_id, tick=0):
    btn_ids = [f"btn_{p[0]}" for p in PATTERNS]
    comps = [
        C("root", "gdm-stage-grid", {"layout": "hero", "children": ["main"]}),
        C("main", "gdm-container", {
            "direction": "column", "justify": "center", "align": "center",
            "grow": 1, "gap": "24px", "padding": "40px",
            "width": "100%", "height": "100%",
            "children": ["title", "sub", "grid"],
        }),
        C("title", "gdm-text", {
            "content": "PLAYBOOK PATTERNS",
            "size": "36px", "weight": "800", "font": "mono",
            "color": "white", "letterSpacing": "0.04em",
        }),
        C("sub", "gdm-text", {
            "content": "Select a pattern to see a stage demo",
            "size": "14px", "color": "#9ca3af",
        }),
        C("grid", "gdm-container", {
            "direction": "row", "justify": "center", "align": "center",
            "gap": "12px", "columns": 3,
            "children": btn_ids,
        }),
    ]
    for slug, label, color in PATTERNS:
        comps.append(C(f"btn_{slug}", "gdm-button", {
            "text": label,
            "size": "lg",
            "action": fire(f"{slug}_1", space_id),
        }))
    return comps

# ── Sprint Review ─────────────────────────────────────────────────────────────

sprint_1_atoms = [
    {"type": "stat_card", "stats": [
        {"label": "Velocity", "value": "42 pts", "delta": "+8%"},
        {"label": "Completion", "value": "87%", "delta": "+5%"},
        {"label": "Bug count", "value": "3", "delta": "-60%"},
    ]},
    {"type": "progress_bar", "label": "Sprint completion", "percentage": 87},
]

sprint_2_atoms = [
    {"type": "chartjs_line", "labels": ["W1","W2","W3","W4","W5"],
     "datasets": [{"label": "Velocity (story pts)", "data": [28, 34, 38, 40, 42]}]},
    {"type": "mini_sparkline_set", "series": [
        {"label": "Bugs opened", "data": [8, 6, 5, 4, 3]},
        {"label": "PRs merged", "data": [12, 15, 18, 14, 20]},
    ]},
]

sprint_3_atoms = [
    {"type": "table",
     "headers": ["Story", "Owner", "Status", "Pts"],
     "rows": [
         ["Auth refactor", "Alice", "✅ Done", "8"],
         ["API rate limiting", "Bob", "🔄 In review", "5"],
         ["Dashboard charts", "Carol", "✅ Done", "13"],
         ["Mobile push", "Dave", "⚠ Blocked", "8"],
     ]},
    {"type": "prerequisite_checklist", "items": [
        {"text": "Retrospective scheduled", "completed": True},
        {"text": "Sprint demo recorded", "completed": True},
        {"text": "Backlog groomed for next sprint", "completed": False},
    ]},
]

# ── Architecture Session ──────────────────────────────────────────────────────

arch_1_atoms = [
    {"type": "file_tree", "nodes": [{"name": "my-service/", "children": [
        {"name": "api/", "children": [
            {"name": "handlers.py"}, {"name": "models.py"}, {"name": "auth.py"}
        ]},
        {"name": "workers/", "children": [
            {"name": "processor.py"}, {"name": "scheduler.py"}
        ]},
        {"name": "Dockerfile"}, {"name": "cloudbuild.yaml"},
    ]}]},
]

arch_2_atoms = [
    {"type": "http_request_block", "method": "POST", "url": "/api/v1/render",
     "description": "Submit a block list for HTML rendering"},
    {"type": "api_param_table", "params": [
        {"name": "blocks", "type": "array", "required": True, "description": "List of typed atom blocks"},
        {"name": "theme",  "type": "string", "required": False, "description": "light | dark (default: light)"},
        {"name": "surface","type": "string", "required": False, "description": "web | meet-stage | email"},
    ]},
]

arch_3_atoms = [
    {"type": "before_after",
     "before_url": "https://picsum.photos/seed/arch_before/400/220",
     "after_url":  "https://picsum.photos/seed/arch_after/400/220",
     "alt": "Architecture evolution"},
    {"type": "badge_group", "badges": [
        {"text": "Cloud Run",   "color": "#4285f4"},
        {"text": "Firestore",   "color": "#f59e0b"},
        {"text": "Pub/Sub",     "color": "#34a853"},
        {"text": "BigQuery",    "color": "#7c3aed"},
        {"text": "Gemini",      "color": "#ea4335"},
    ]},
]

# ── Demo / Launch ─────────────────────────────────────────────────────────────

demo_1_atoms = [
    {"type": "metric_comparison_card", "label": "Response time (ms)", "value": 42, "previous": 180},
    {"type": "uptime_timeline", "uptime": 99.95, "days": 30},
]

demo_2_atoms = [
    {"type": "carousel", "slides": [
        {"url": "https://picsum.photos/seed/demo1/600/300", "label": "Feature A", "description": "Instant rendering"},
        {"url": "https://picsum.photos/seed/demo2/600/300", "label": "Feature B", "description": "Multi-surface support"},
        {"url": "https://picsum.photos/seed/demo3/600/300", "label": "Feature C", "description": "Live data binding"},
    ]},
]

demo_3_atoms = [
    {"type": "chartjs_bar", "labels": ["Q1","Q2","Q3","Q4"],
     "datasets": [{"label": "Deployments", "data": [12, 28, 44, 67]}]},
    {"type": "badge_group", "badges": [
        {"text": "✅ SOC 2",     "color": "#059669"},
        {"text": "✅ GDPR",      "color": "#059669"},
        {"text": "🚀 GA",        "color": "#7c3aed"},
        {"text": "99.95% SLA",   "color": "#2563eb"},
    ]},
]

# ── Team Standup ──────────────────────────────────────────────────────────────

standup_1_atoms = [
    {"type": "author_bio_card", "name": "Alice Chen",
     "bio": "Working on auth refactor. Done with unit tests, PR up for review.",
     "image": "https://picsum.photos/seed/alice/60/60"},
    {"type": "author_bio_card", "name": "Bob Martinez",
     "bio": "Deployed API rate limiting to staging. Running load tests today.",
     "image": "https://picsum.photos/seed/bob/60/60"},
    {"type": "author_bio_card", "name": "Carol Thompson",
     "bio": "Dashboard charts merged. Starting mobile push notifications.",
     "image": "https://picsum.photos/seed/carol/60/60"},
]

standup_2_atoms = [
    {"type": "prerequisite_checklist", "items": [
        {"text": "Auth refactor — PR merged",           "completed": True},
        {"text": "Rate limiting — staging deployed",    "completed": True},
        {"text": "Dashboard charts — shipped",          "completed": True},
        {"text": "Mobile push — in progress",           "completed": False},
        {"text": "Load test sign-off",                  "completed": False},
    ]},
    {"type": "badge_group", "badges": [
        {"text": "3 Done",     "color": "#059669"},
        {"text": "2 In progress", "color": "#f59e0b"},
        {"text": "1 Blocked",  "color": "#dc2626"},
    ]},
]

# ── Technical Briefing ────────────────────────────────────────────────────────

tech_1_atoms = [
    {"type": "tabs", "tabs": [
        {"label": "Python", "blocks": [
            {"type": "code", "language": "python",
             "text": "from renderers.web_article import render\n\nblocks = [\n    {\"type\": \"stat_card\", \"stats\": [{\"label\": \"Users\", \"value\": \"1.2k\"}]},\n    {\"type\": \"callout\", \"style\": \"info\", \"text\": \"Deploy complete.\"},\n]\n\nhtml = render(blocks)"}
        ]},
        {"label": "CLI", "blocks": [
            {"type": "terminal_block",
             "text": "$ a2ui render schema.yaml --format html\n✓ 170 atoms validated\n✓ Output: article.html (136kb, 0.3s)"}
        ]},
    ]},
]

tech_2_atoms = [
    {"type": "cli_command", "command": "curl -X POST http://localhost:8000/api/render", "description": "Fire a render to the stage"},
    {"type": "keyboard_shortcut", "keys": ["⌘", "K"]},
    {"type": "key_takeaways", "items": [
        {"text": "Atoms validate against schema.yaml before render"},
        {"text": "compact_description drives vector retrieval — keep it under 10 tokens"},
        {"text": "works_on / degraded_on flags control surface compatibility"},
        {"text": "Runbook path covers ~80% of real sessions — zero deliberation"},
    ]},
]

# ── Data Review ───────────────────────────────────────────────────────────────

data_1_atoms = [
    {"type": "chartjs_line",
     "labels": ["Jan","Feb","Mar","Apr","May","Jun"],
     "datasets": [
         {"label": "Revenue ($k)", "data": [420, 480, 510, 540, 590, 640]},
     ]},
    {"type": "metric_comparison_card", "label": "MoM growth", "value": 640, "previous": 590},
]

data_2_atoms = [
    {"type": "chartjs_bar",
     "labels": ["Web","Mobile","API","Embed"],
     "datasets": [{"label": "Sessions (k)", "data": [84, 52, 31, 18]}]},
    {"type": "mini_sparkline_set", "series": [
        {"label": "P50 latency (ms)", "data": [42, 38, 44, 41, 39, 36]},
        {"label": "Error rate (%)",   "data": [0.8, 0.6, 0.9, 0.5, 0.4, 0.3]},
        {"label": "Active users (k)", "data": [18, 21, 19, 24, 26, 28]},
        {"label": "API calls (M)",    "data": [1.2, 1.4, 1.3, 1.6, 1.8, 2.1]},
    ]},
]

data_3_atoms = [
    {"type": "uptime_timeline", "uptime": 99.7, "days": 30},
    {"type": "badge_group", "badges": [
        {"text": "SLA: 99.7%",  "color": "#059669"},
        {"text": "MTTR: 4m",    "color": "#2563eb"},
        {"text": "Incidents: 2","color": "#f59e0b"},
        {"text": "P0 bugs: 0",  "color": "#059669"},
    ]},
]

# ── Build all slides ──────────────────────────────────────────────────────────

SLIDES = [
    Slide("cover",    "Pattern Selector",     build_cover),

    Slide("sprint_1", "Sprint — Overview",    html_slide(sprint_1_atoms,  None,       "sprint_2")),
    Slide("sprint_2", "Sprint — Burn-down",   html_slide(sprint_2_atoms,  "sprint_1", "sprint_3")),
    Slide("sprint_3", "Sprint — Backlog",     html_slide(sprint_3_atoms,  "sprint_2", None)),

    Slide("arch_1",   "Architecture — Tree",  html_slide(arch_1_atoms,    None,       "arch_2")),
    Slide("arch_2",   "Architecture — API",   html_slide(arch_2_atoms,    "arch_1",   "arch_3")),
    Slide("arch_3",   "Architecture — Delta", html_slide(arch_3_atoms,    "arch_2",   None)),

    Slide("demo_1",   "Demo — Metrics",       html_slide(demo_1_atoms,    None,       "demo_2")),
    Slide("demo_2",   "Demo — Showcase",      html_slide(demo_2_atoms,    "demo_1",   "demo_3")),
    Slide("demo_3",   "Demo — Growth",        html_slide(demo_3_atoms,    "demo_2",   None)),

    Slide("standup_1","Standup — Team",       html_slide(standup_1_atoms, None,       "standup_2")),
    Slide("standup_2","Standup — Status",     html_slide(standup_2_atoms, "standup_1",None)),

    Slide("tech_1",   "Tech — Code",          html_slide(tech_1_atoms,    None,       "tech_2")),
    Slide("tech_2",   "Tech — Reference",     html_slide(tech_2_atoms,    "tech_1",   None)),

    Slide("data_1",   "Data — Trends",        html_slide(data_1_atoms,    None,       "data_2")),
    Slide("data_2",   "Data — Breakdown",     html_slide(data_2_atoms,    "data_1",   "data_3")),
    Slide("data_3",   "Data — Reliability",   html_slide(data_3_atoms,    "data_2",   None)),
]

playbook_manager.register_playbook(PLAYBOOK, SLIDES)
