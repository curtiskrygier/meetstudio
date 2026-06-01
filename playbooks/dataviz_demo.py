"""DataViz Demo — production-grade data visualization for Meet stage.

6 slides: hero metrics, growth, velocity, reliability, channels, insights.
Dramatic data stories, stat cards with deltas, sophisticated layouts.
Dark gradient theme with green/red/blue color strategy.

Fire:
    curl -X POST http://127.0.0.1:8000/api/playbook/fire/dataviz_demo/cover/default
"""
import sys
sys.path.insert(0, "/home/curtis/a2ui-catalogue")

from renderers.web_article import render as wa_render
from playbooks.manager import Slide, playbook_manager

PLAYBOOK = "dataviz_demo"

def C(cid, el, props):
    return {"id": cid, "component": el,
            **{k: v for k, v in props.items() if k not in ("id", "component")}}

def fire(slide_id, space_id):
    return {"functionCall": {"call": "fireEndpoint",
                             "args": {"endpoint": f"/api/playbook/fire/{PLAYBOOK}/{slide_id}/{space_id}"}}}

# ── Premium dark theme with visual hierarchy ──────────────────────────────
_CSS = (
    "<style>"
    "*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}"
    "html,body{width:100%;height:100%;background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);color:#e2e8f0;"
    "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Helvetica Neue',sans-serif;overflow:auto;padding:48px;}"
    "h1{font-size:36px;font-weight:800;margin-bottom:8px;letter-spacing:-0.6px;color:#f1f5f9}"
    ".subtitle{font-size:14px;color:#cbd5e1;margin-bottom:40px;font-weight:400}"
    ".hero-stat{background:rgba(15,23,42,0.8);border-left:4px solid #3b82f6;padding:20px;margin-bottom:24px;border-radius:6px}"
    ".hero-label{font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px}"
    ".hero-value{font-size:32px;font-weight:800;color:#f1f5f9;margin-bottom:8px}"
    ".hero-delta{font-size:13px;font-weight:600;color:#10b981}"
    ".hero-delta.danger{color:#ef4444}"
    ".grid-2x1{display:grid;grid-template-columns:1fr 1fr;gap:32px;margin-bottom:32px}"
    ".grid-stat-chart{display:grid;grid-template-columns:240px 1fr;gap:28px;align-items:start}"
    ".accent-box{background:rgba(16,185,129,0.08);border-left:3px solid #10b981;padding:18px;border-radius:6px;margin-bottom:24px;font-size:14px;line-height:1.6;color:#d1fae5}"
    ".accent-box.danger{background:rgba(239,68,68,0.08);border-left-color:#ef4444;color:#fee2e2}"
    ".insight{background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.2);padding:16px;border-radius:6px;margin-bottom:16px;font-size:13px;color:#93c5fd;line-height:1.5}"
    "</style>"
)

def html_slide(atoms: list, title: str, subtitle: str="", hero_stat: dict=None, prev_id: str=None, next_id: str=None, back_id="cover"):
    """Build a premium gdm-html-panel slide with title, optional hero stat, subtitle + atoms."""
    html_content = _CSS + f"""
    <div style="margin-bottom:32px">
        <h1>{title}</h1>
        {f'<div class="subtitle">{subtitle}</div>' if subtitle else ''}
    </div>
    """
    if hero_stat:
        html_content += f"""
    <div class="hero-stat">
        <div class="hero-label">{hero_stat['label']}</div>
        <div class="hero-value">{hero_stat['value']}</div>
        <div class="hero-delta {'danger' if hero_stat.get('delta_is_down') else ''}">{hero_stat['delta']}</div>
    </div>
    """
    html_content += "".join(wa_render([{**d}]) for d in atoms)

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
            C("btn_back", "gdm-button", {"text": "⬡ DataViz", "action": fire(back_id, space_id)}),
            C("lbl", "gdm-text", {"content": "", "size": "11px", "color": "#64748b"}),
        ]
        if prev_id:
            comps.append(C("btn_prev", "gdm-button", {"text": "←", "action": fire(prev_id, space_id)}))
        if next_id:
            comps.append(C("btn_next", "gdm-button", {"text": "→", "action": fire(next_id, space_id)}))
        return comps
    return builder

# ── Cover ─────────────────────────────────────────────────────────────────

def build_cover(space_id, tick=0):
    comps = [
        C("root", "gdm-stage-grid", {"layout": "hero", "children": ["main"]}),
        C("main", "gdm-container", {
            "direction": "column", "justify": "center", "align": "center",
            "grow": 1, "gap": "48px", "padding": "80px",
            "width": "100%", "height": "100%",
            "children": ["title", "sub", "grid"],
        }),
        C("title", "gdm-text", {
            "content": "METRICS THAT MATTER",
            "size": "60px", "weight": "800", "font": "mono",
            "color": "#f1f5f9", "letterSpacing": "-0.03em",
        }),
        C("sub", "gdm-text", {
            "content": "Production SaaS metrics — dramatic data, actionable insights",
            "size": "18px", "color": "#cbd5e1", "weight": "400",
        }),
        C("grid", "gdm-container", {
            "direction": "column", "justify": "center", "align": "center",
            "gap": "16px",
            "children": ["btn_hero", "btn_growth", "btn_velocity", "btn_reliability", "btn_channels"],
        }),
        C("btn_hero", "gdm-button", {
            "text": "⭐ The Story (KPIs)",
            "size": "lg",
            "action": fire("hero", space_id),
        }),
        C("btn_growth", "gdm-button", {
            "text": "📈 Revenue & Churn",
            "size": "lg",
            "action": fire("growth", space_id),
        }),
        C("btn_velocity", "gdm-button", {
            "text": "🚀 Engineering Velocity",
            "size": "lg",
            "action": fire("velocity", space_id),
        }),
        C("btn_reliability", "gdm-button", {
            "text": "⚡ Performance & Uptime",
            "size": "lg",
            "action": fire("reliability", space_id),
        }),
        C("btn_channels", "gdm-button", {
            "text": "📊 Channels & Segments",
            "size": "lg",
            "action": fire("channels", space_id),
        }),
    ]
    return comps

# ── Slide 1: The Story (Hero KPIs) ────────────────────────────────────────

hero_atoms = [
    {"type": "stat_card", "stats": [
        {"label": "MRR", "value": "$1.85M", "delta": "+256% YoY"},
        {"label": "Churn", "value": "1.7%", "delta": "-59% YoY"},
        {"label": "CAC Payback", "value": "4mo", "delta": "-71% YoY"},
    ]},
    {"type": "donut_stat", "label": "Q2 MRR Target Progress", "value": 1850, "max_value": 2000, "unit": "k", "color": "#3b82f6"},
    {"type": "key_takeaways", "items": [
        {"text": "Revenue growth outpacing churn decline — magic number > 1x achieved"},
        {"text": "CAC payback improved dramatically through retention focus"},
        {"text": "Compound growth trajectory: 12% → 35% YoY (month-on-month)"},
    ]},
]

# ── Slide 2: Revenue & Growth Trajectory ──────────────────────────────────

growth_atoms = [
    {"type": "chartjs_line",
     "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
     "datasets": [
         {"label": "Monthly Recurring Revenue ($k)", "data": [520, 580, 640, 720, 810, 920, 1050, 1180, 1320, 1480, 1650, 1850]},
     ]},
    {"type": "mini_sparkline_set", "series": [
        {"label": "YoY Growth %", "data": [12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 35]},
        {"label": "Churn Rate % (↓ good)", "data": [4.2, 4.0, 3.8, 3.5, 3.2, 3.0, 2.8, 2.5, 2.3, 2.1, 1.9, 1.7]},
        {"label": "CAC Payback mo (↓ good)", "data": [14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 5, 4]},
    ]},
]

# ── Slide 3: Engineering Velocity ─────────────────────────────────────────

velocity_atoms = [
    {"type": "metric_comparison_card", "label": "Monthly Deployments", "value": 38, "previous": 12},
    {"type": "chartjs_bar",
     "labels": ["Q1", "Q2", "Q3", "Q4"],
     "datasets": [
         {"label": "Deployments", "data": [28, 34, 42, 50]},
         {"label": "Features shipped", "data": [12, 18, 24, 31]},
     ]},
    {"type": "heatmap",
     "labels_x": ["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "W9", "W10", "W11", "W12"],
     "labels_y": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
     "unit": " deploys",
     "color_scale": ["#1e293b", "#0f766e", "#10b981", "#34d399"],
     "data": [
         [3, 5, 2, 6, 8, 4, 7, 5, 9, 3, 4, 6],
         [4, 2, 7, 3, 5, 9, 4, 6, 8, 2, 5, 7],
         [5, 8, 4, 6, 2, 4, 8, 3, 5, 9, 2, 4],
         [6, 3, 9, 2, 7, 5, 3, 8, 4, 6, 7, 8],
         [7, 9, 3, 5, 8, 2, 6, 4, 7, 8, 9, 5],
         [1, 0, 2, 0, 3, 1, 0, 2, 1, 0, 3, 2],
         [0, 0, 1, 0, 0, 2, 0, 1, 0, 0, 1, 0],
     ]},
    {"type": "badge_group", "badges": [
        {"text": "Velocity +312%", "color": "#10b981"},
        {"text": "Hotfixes -87%", "color": "#10b981"},
        {"text": "Review cycle 3x faster", "color": "#10b981"},
    ]},
]

# ── Slide 4: Reliability & Performance ────────────────────────────────────

reliability_atoms = [
    {"type": "uptime_timeline", "uptime": 99.97, "days": 30},
    {"type": "mini_sparkline_set", "series": [
        {"label": "p95 Latency ms (↓ good)", "data": [120, 118, 115, 112, 108, 105, 102, 99, 95, 91, 88, 85]},
        {"label": "Error Rate ‰ (↓ good)", "data": [2.4, 2.1, 1.9, 1.7, 1.5, 1.3, 1.1, 0.9, 0.8, 0.7, 0.6, 0.5]},
        {"label": "API Success % (↑ good)", "data": [99.75, 99.77, 99.79, 99.81, 99.83, 99.85, 99.87, 99.88, 99.90, 99.91, 99.92, 99.95]},
    ]},
]

# ── Slide 5: Channels & Monetization ──────────────────────────────────────

channels_atoms = [
    {"type": "key_takeaways", "items": [
        {"text": "Web: 47% of users, only 18% revenue → scale play"},
        {"text": "Enterprise: 6% of users, 42% revenue → 7x ARPU multiplier"},
        {"text": "Mobile growing fastest but API has cleanest margins"},
    ]},
    {"type": "chartjs_bar",
     "labels": ["Web", "Mobile", "API", "Enterprise"],
     "datasets": [
         {"label": "Monthly Active Users (k)", "data": [240, 180, 85, 35]},
         {"label": "ARPU ($)", "data": [45, 52, 120, 850]},
     ]},
    {"type": "badge_group", "badges": [
        {"text": "Web: 47%", "color": "#3b82f6"},
        {"text": "Mobile: 35%", "color": "#8b5cf6"},
        {"text": "API: 12%", "color": "#06b6d4"},
        {"text": "Enterprise: 6%", "color": "#f59e0b"},
    ]},
]

# ── Build all slides ──────────────────────────────────────────────────────

SLIDES = [
    Slide("cover", "Metrics Dashboard", build_cover),

    Slide("hero", "The Story",
          html_slide(hero_atoms, "📊 Annual Summary",
                    "Revenue up 256%, churn down 59%, improving unit economics",
                    prev_id=None, next_id="growth")),

    Slide("growth", "Revenue & Churn",
          html_slide(growth_atoms, "📈 Growth Trajectory",
                    "12-month MRR climb with churn collapsing and CAC payback improving",
                    prev_id="hero", next_id="velocity")),

    Slide("velocity", "Engineering Velocity",
          html_slide(velocity_atoms, "🚀 Deployment Cadence",
                    "Frequency +312% (12→38/mo), hotfixes eliminated, iteration velocity",
                    prev_id="growth", next_id="reliability")),

    Slide("reliability", "Performance & Reliability",
          html_slide(reliability_atoms, "⚡ System Health",
                    "99.97% uptime, p95 latency -29%, error rate -79%, API success 99.95%",
                    prev_id="velocity", next_id="channels")),

    Slide("channels", "Channel Strategy",
          html_slide(channels_atoms, "📊 Monetization Mix",
                    "Web scales volume, Enterprise drives revenue — balanced growth",
                    prev_id="reliability", next_id=None)),
]

playbook_manager.register_playbook(PLAYBOOK, SLIDES)
