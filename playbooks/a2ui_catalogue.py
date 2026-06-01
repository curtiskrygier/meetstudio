"""A2UI Atom Catalogue playbook.

One slide per category, 3 atoms per slide rendered with web_article.py examples.
Prev/Next wired via the playbook fires mechanism (native stage buttons).

Fire the cover:
  curl -X POST http://127.0.0.1:8000/api/playbook/fire/a2ui_catalogue/cover/default
"""

import sys
from pathlib import Path

# Resolve a2ui-catalogue repo
_CATALOGUE = Path("/home/curtis/a2ui-catalogue")
sys.path.insert(0, str(_CATALOGUE))

import yaml
from renderers.web_article import render as wa_render
from playbooks.manager import Slide, playbook_manager

# ── Schema ────────────────────────────────────────────────────────────────────

with open(_CATALOGUE / "atoms" / "schema.yaml") as f:
    _ALL_ATOMS = yaml.safe_load(f)["blocks"]
    _ATOMS = {a["type"]: a for a in _ALL_ATOMS}

CATEGORIES = [
    ("Foundations",          ["body", "closing", "heading", "intro", "subheading"]),
    ("Reading Experience",   ["article_hero", "article_series_nav", "post_metadata_bar", "reading_progress_bar", "scroll_to_top", "table_of_contents"]),
    ("Documentation",        ["changelog_entry", "footnote", "footnote_group", "further_reading", "glossary_term", "release_notes", "resources_list", "table", "tabs", "timeline"]),
    ("Navigation & Structure", ["anchor_list", "breadcrumb", "faq_accordion", "pagination", "stepper", "tab_bar"]),
    ("Content Structure",    ["bullet_list", "callout", "caution_block", "checklist_interactive", "divider", "key_takeaways", "key_value", "learning_objectives", "pipeline", "sidebar_note", "steps", "summary_box"]),
    ("Text & Quotes",        ["blockquote_with_avatar", "pull_stat", "quote"]),
    ("Containers & Modals",  ["accordion_item", "collapsible_panel", "css_modal", "css_slide_panel", "flip_card", "hover_card", "tooltip"]),
    ("Cards & Components",   ["badge_group", "notification_badge", "rating_stars", "star_rating_display", "stat_card", "toggle_switch"]),
    ("Code & Technical",     ["annotated_code", "api_param_table", "api_reference", "before_after", "code", "code_diff", "code_snippet_pair", "http_request_block", "tabbed_code", "terminal_block", "file_tree"]),
    ("Design Tools",         ["css_dropdown_menu", "custom_checkbox_group", "expandable_list", "poll_block", "segmented_control"]),
    ("Commerce & Pricing",   ["pricing_tier_card", "pricing_tier_group"]),
    ("Comparison & Analysis",["capability_checklist", "comparison_grid", "feature_matrix", "pros_cons_list", "product_spec_table", "rating_comparison", "side_by_side_spec", "versus_block"]),
    ("Inline Tools",         ["abbr_tooltip", "copy_to_clipboard", "expandable_text", "glossary_inline"]),
    ("Technical Reference",  ["cli_command", "copy_code_button", "env_var_list", "json_tree_viewer", "keyboard_shortcut", "log_output", "prerequisite_checklist"]),
    ("Warnings & Status",    ["alert_banner", "deprecation_notice", "experimental_banner", "status_pill", "version_badge"]),
    ("Media",                ["carousel", "color_swatch_grid", "diagram", "framed_screenshot", "gallery", "image", "image_hotspots", "image_pair", "image_with_caption", "pdf_preview", "video_card", "video_pair", "video_thumbnail", "zoomable_image"]),
    ("Data Visualization",   ["benchmark_comparison", "chartjs_bar", "chartjs_line", "data_table_sortable", "donut_stat", "heatmap", "metric_comparison_card", "metric_delta", "mini_sparkline_set", "progress_bar", "progress_circle", "sparkline", "status_dashboard", "trend_indicator", "uptime_timeline"]),
    ("Social & Engagement",  ["author_bio_card", "avatar_group", "contributor_list", "customer_logo_grid", "expert_endorsement", "follow_button", "follow_cta", "media_mention_card", "newsletter_cta", "reaction_group", "review_callout", "share_quote", "social_feed_embed", "social_share_bar", "testimonial_card"]),
    ("UI Utilities",         ["command_palette", "empty_state", "inline_feedback_message", "loading_skeleton", "search_result_card", "spinner", "toast_notification"]),
    ("Utilities & Links",    ["document_link", "github_repo_card", "repo_links"]),
    ("Video & Audio",        ["audio_link", "audio_player", "youtube"]),
    ("External Embeds",      ["embed_codepen", "embed_gist", "embed_google_slides", "embed_stackblitz", "embed_tweet", "figma_embed", "lottie_animation", "live_demo_embed"]),
]

ATOMS_PER_SLIDE = 3

GEN_DATA = {
    'body': {'text': 'Example body paragraph.\n\nA second paragraph.'},
    'heading': {'text': 'Example Section Heading'},
    'subheading': {'text': 'Example Subheading'},
    'quote': {'text': 'Well-designed systems speak for themselves.', 'attribution': 'Author'},
    'closing': {'text': 'Thanks for reading.'},
    'intro': {'series_label': 'A2UI Series', 'series_url': '#', 'note': 'Sample intro.'},
    'code': {'language': 'python', 'text': 'def greet(name):\n    return f"Hello, {name}"'},
    'pipeline': {'steps': ['Input', 'Process', 'Render', 'Output']},
    'bullet_list': {'items': [{'text': 'Atoms are reusable'}, {'text': 'Schema-validated'}, {'text': 'MIT licensed'}]},
    'divider': {},
    'callout': {'style': 'info', 'text': 'This is an informational callout.'},
    'caution_block': {'text': 'Be careful here.'},
    'checklist_interactive': {'items': [{'text': 'Install', 'checked': True}, {'text': 'Configure', 'checked': True}, {'text': 'Deploy', 'checked': False}]},
    'steps': {'items': [{'title': 'Install', 'description': 'npm install'}, {'title': 'Deploy', 'description': 'Push to cloud'}]},
    'key_takeaways': {'items': [{'text': 'Atoms are reusable'}, {'text': 'compact_description for retrieval'}]},
    'key_value': {'items': [{'key': 'Version', 'value': '2.0.0'}, {'key': 'License', 'value': 'MIT'}]},
    'learning_objectives': {'items': [{'text': 'Understand atom schema'}, {'text': 'Use renderers'}]},
    'sidebar_note': {'title': 'Pro tip', 'content': 'Use compact_description for vector retrieval.'},
    'summary_box': {'text': 'A2UI: 170 atoms, 4 surfaces, MIT licensed.'},
    'accordion_item': {'title': 'Click to expand', 'blocks': [{'type': 'body', 'text': 'Hidden content.'}]},
    'collapsible_panel': {'title': 'Panel', 'blocks': [{'type': 'body', 'text': 'Panel content.'}]},
    'css_modal': {'trigger_text': 'Open modal', 'blocks': [{'type': 'body', 'text': 'Modal content.'}]},
    'css_slide_panel': {'trigger_text': 'Open panel', 'blocks': [{'type': 'body', 'text': 'Panel content.'}]},
    'flip_card': {'front_blocks': [{'type': 'body', 'text': 'Front side'}], 'back_blocks': [{'type': 'body', 'text': 'Back side'}]},
    'hover_card': {'trigger': 'Hover me', 'blocks': [{'type': 'body', 'text': 'Card content.'}]},
    'tooltip': {'text': 'Application Programming Interface', 'target': 'API'},
    'article_hero': {'image': 'https://picsum.photos/seed/hero/400/120', 'overline': 'A2UI Series', 'title': 'My A2UI Catalogue'},
    'article_series_nav': {'title': 'A2UI Series', 'url': '#', 'prev': 'Part 1', 'next': 'Part 3'},
    'post_metadata_bar': {'author': 'Curtis Krygier', 'date': '2026-06-01', 'readTime': 8},
    'reading_progress_bar': {'percentage': 45},
    'scroll_to_top': {},
    'table_of_contents': {'items': [{'text': 'Introduction', 'level': 1}, {'text': 'Config', 'level': 2}]},
    'changelog_entry': {'version': '2.0.0', 'date': '2026-06-01', 'text': 'Added 50 new atoms.'},
    'footnote': {'id': '1', 'text': 'See schema.yaml.'},
    'footnote_group': {'footnotes': [{'id': '1', 'text': 'MIT license.'}, {'id': '2', 'text': 'Surface compat varies.'}]},
    'further_reading': {'items': [{'text': 'A2UI on GitHub', 'url': '#'}]},
    'glossary_term': {'term': 'Atom', 'definition': 'A typed, reusable UI block.'},
    'release_notes': {'version': '2.0.0', 'sections': [{'title': 'New', 'items': ['170 atoms', '4 surfaces']}]},
    'resources_list': {'items': [{'text': 'GitHub', 'url': '#'}, {'text': 'Schema', 'url': '#'}]},
    'table': {'headers': ['Field', 'Type', 'Required'], 'rows': [['type', 'string', 'Yes'], ['description', 'string', 'Yes']]},
    'tabs': {'tabs': [{'label': 'Python', 'blocks': [{'type': 'code', 'language': 'python', 'text': 'render(blocks)'}]}, {'label': 'JS', 'blocks': [{'type': 'code', 'language': 'js', 'text': 'render(blocks)'}]}]},
    'timeline': {'items': [{'date': '2024-01', 'title': 'Started'}, {'date': '2026-06', 'title': 'v2.0 — 170 atoms'}]},
    'anchor_list': {'items': [{'text': 'Overview', 'url': '#'}, {'text': 'Usage', 'url': '#'}]},
    'breadcrumb': {'items': [{'text': 'Home', 'url': '/'}, {'text': 'Blog', 'url': '/blog'}, {'text': 'A2UI'}]},
    'faq_accordion': {'items': [{'question': 'What is A2UI?', 'answer': 'Reusable UI atoms for AI agents.'}, {'question': 'How many atoms?', 'answer': '170 across 22 categories.'}]},
    'pagination': {'current': 2, 'total': 5},
    'stepper': {'current': 2, 'steps': ['Setup', 'Configure', 'Deploy']},
    'tab_bar': {'current': 'overview', 'tabs': [{'id': 'overview', 'label': 'Overview'}, {'id': 'api', 'label': 'API'}]},
    'blockquote_with_avatar': {'text': 'The catalogue-as-vocabulary model is the right abstraction.', 'author': 'Curtis', 'role': 'Author'},
    'pull_stat': {'value': '170', 'label': 'Atoms in catalogue'},
    'badge_group': {'badges': [{'text': 'GCP', 'color': '#4285f4'}, {'text': 'Python', 'color': '#3776ab'}, {'text': 'MIT', 'color': '#059669'}]},
    'notification_badge': {'text': '5', 'color': '#dc2626'},
    'rating_stars': {'rating': 4, 'max': 5},
    'star_rating_display': {'rating': 4.5, 'max': 5, 'count': 128},
    'stat_card': {'stats': [{'label': 'Atoms', 'value': '170', 'delta': '+12'}, {'label': 'Surfaces', 'value': '4'}]},
    'toggle_switch': {'label': 'Dark Mode', 'checked': True},
    'annotated_code': {'blocks': [{'type': 'code', 'language': 'python', 'text': 'render(blocks, theme="dark")'}]},
    'api_param_table': {'params': [{'name': 'type', 'type': 'string', 'required': True, 'description': 'Atom type'}]},
    'api_reference': {'endpoints': [{'method': 'GET', 'path': '/api/atoms', 'description': 'List atoms'}, {'method': 'POST', 'path': '/api/render', 'description': 'Render blocks'}]},
    'before_after': {'before_url': 'https://picsum.photos/seed/before/250/150', 'after_url': 'https://picsum.photos/seed/after/250/150'},
    'code_diff': {'old': 'const x = fetch(url)', 'new': 'const x = await fetch(url)'},
    'code_snippet_pair': {'left_language': 'python', 'left': 'render(blocks)', 'right_language': 'typescript', 'right': 'await render(blocks)'},
    'http_request_block': {'method': 'POST', 'url': '/api/render', 'description': 'Render blocks'},
    'tabbed_code': {'tabs': [{'language': 'python', 'label': 'Python', 'code': 'render(blocks)'}, {'language': 'bash', 'label': 'CLI', 'code': 'a2ui render schema.yaml'}]},
    'terminal_block': {'text': '$ a2ui render schema.yaml\n✓ 170 atoms\n✓ Output: article.html'},
    'file_tree': {'nodes': [{'name': 'a2ui-catalogue/', 'children': [{'name': 'atoms/', 'children': [{'name': 'schema.yaml'}]}, {'name': 'renderers/', 'children': [{'name': 'web_article.py'}]}]}]},
    'css_dropdown_menu': {'trigger': 'Options ▾', 'items': [{'text': 'Edit'}, {'text': 'Delete'}]},
    'custom_checkbox_group': {'items': [{'text': 'Web', 'checked': True}, {'text': 'Meet', 'checked': True}, {'text': 'Email', 'checked': False}]},
    'expandable_list': {'items': [{'text': 'Content', 'children': [{'text': 'callout'}, {'text': 'steps'}]}]},
    'poll_block': {'question': 'Which surface?', 'options': [{'text': 'Web article', 'votes': 42}, {'text': 'Meet stage', 'votes': 18}]},
    'segmented_control': {'options': [{'value': 'monthly', 'label': 'Monthly'}, {'value': 'annual', 'label': 'Annual'}], 'selected': 'annual'},
    'pricing_tier_card': {'name': 'Pro', 'price': '$49/mo', 'features': ['170 atoms', 'All surfaces']},
    'pricing_tier_group': {'tiers': [{'name': 'Free', 'price': '$0'}, {'name': 'Pro', 'price': '$49/mo'}]},
    'capability_checklist': {'capabilities': [{'text': 'Web rendering', 'included': True}, {'text': 'Email', 'included': False}]},
    'comparison_grid': {'items': [{'name': 'A2UI', 'specs': ['170 atoms', 'MIT']}, {'name': 'Other', 'specs': ['40 atoms', 'Paid']}]},
    'feature_matrix': {'features': ['Dark mode', 'Export', 'API'], 'columns': [{'name': 'Free', 'values': [True, False, False]}, {'name': 'Pro', 'values': [True, True, True]}]},
    'pros_cons_list': {'items': [{'text': 'Schema-validated', 'type': 'pro'}, {'text': 'Open source', 'type': 'pro'}, {'text': 'Early stage', 'type': 'con'}]},
    'product_spec_table': {'specs': [{'name': 'Format', 'value': 'HTML'}, {'name': 'License', 'value': 'MIT'}]},
    'rating_comparison': {'items': [{'name': 'Performance', 'rating': 5}, {'name': 'DX', 'rating': 4}]},
    'side_by_side_spec': {'left': {'title': 'v1', 'specs': ['74 atoms']}, 'right': {'title': 'v2', 'specs': ['170 atoms', '4 surfaces']}},
    'versus_block': {'left': {'title': 'Generative', 'description': 'Agent reasons which atoms fit.'}, 'right': {'title': 'Runbook', 'description': 'Pre-mapped keyword → atoms.'}},
    'abbr_tooltip': {'text': 'API', 'title': 'Application Programming Interface'},
    'copy_to_clipboard': {'text': 'pip install a2ui', 'value': 'pip install a2ui'},
    'expandable_text': {'text': 'A2UI is a catalogue...', 'expanded': 'A2UI provides 170 atoms across 4 surfaces.'},
    'glossary_inline': {'term': 'atom', 'definition': 'A single typed UI block.'},
    'cli_command': {'command': 'a2ui render --format html schema.yaml', 'description': 'Render atoms to HTML'},
    'copy_code_button': {'code': 'render(blocks, theme="dark")'},
    'env_var_list': {'vars': [{'name': 'A2UI_THEME', 'value': 'dark'}, {'name': 'A2UI_SURFACE', 'value': 'web'}]},
    'json_tree_viewer': {'json': '{"type":"stat_card","value":"170"}'},
    'keyboard_shortcut': {'keys': ['⌘', 'K']},
    'log_output': {'text': '[INFO] 170 atoms validated\n[OK]   article.html (136kb)'},
    'prerequisite_checklist': {'items': [{'text': 'Python 3.10+', 'completed': True}, {'text': 'schema.yaml', 'completed': True}]},
    'alert_banner': {'text': 'Feature in beta.', 'type': 'warning'},
    'deprecation_notice': {'text': 'inline_image deprecated. Use image_with_caption.'},
    'experimental_banner': {'text': 'chartjs_bar requires Chart.js on page.'},
    'status_pill': {'text': 'Stable', 'status': 'success'},
    'version_badge': {'version': 'v2.0.0'},
    'carousel': {'slides': [{'url': 'https://picsum.photos/seed/c1/400/180', 'label': 'Slide 1'}, {'url': 'https://picsum.photos/seed/c2/400/180', 'label': 'Slide 2'}]},
    'color_swatch_grid': {'colors': [{'name': 'Purple', 'hex': '#7c3aed'}, {'name': 'Green', 'hex': '#059669'}, {'name': 'Blue', 'hex': '#2563eb'}]},
    'diagram': {'alt': 'Architecture', 'url': 'https://picsum.photos/seed/diag/400/200'},
    'framed_screenshot': {'url': 'https://picsum.photos/seed/screen/400/200', 'alt': 'Screenshot'},
    'gallery': {'images': [{'url': 'https://picsum.photos/seed/g1/150/100', 'alt': '1'}, {'url': 'https://picsum.photos/seed/g2/150/100', 'alt': '2'}]},
    'image': {'url': 'https://picsum.photos/seed/img1/400/200', 'alt': 'Example'},
    'image_hotspots': {'url': 'https://picsum.photos/seed/hot/400/200', 'hotspots': [{'x': 30, 'y': 40, 'text': 'Point A'}]},
    'image_pair': {'left': {'url': 'https://picsum.photos/seed/p1/200/120', 'alt': 'Before', 'caption': 'Before'}, 'right': {'url': 'https://picsum.photos/seed/p2/200/120', 'alt': 'After', 'caption': 'After'}},
    'image_with_caption': {'url': 'https://picsum.photos/seed/cap/400/200', 'caption': 'Image caption.'},
    'pdf_preview': {'url': '#', 'title': 'Document.pdf'},
    'video_card': {'url': 'https://youtu.be/3AofBvbFlIk', 'title': 'Example Video', 'duration': '3:45'},
    'video_pair': {'left_url': 'https://youtu.be/3AofBvbFlIk', 'right_url': 'https://youtu.be/3AofBvbFlIk'},
    'video_thumbnail': {'url': 'https://youtu.be/3AofBvbFlIk', 'title': 'Watch this'},
    'zoomable_image': {'url': 'https://picsum.photos/seed/zoom/400/200', 'alt': 'Zoomable'},
    'embed_codepen': {'url': 'https://codepen.io/pen/abc123'},
    'embed_gist': {'url': 'https://gist.github.com/user/abc'},
    'embed_google_slides': {'url': 'https://docs.google.com/presentation/d/1'},
    'embed_stackblitz': {'url': 'https://stackblitz.com/edit/example'},
    'embed_tweet': {'url': 'https://twitter.com/AnthropicAI/status/1'},
    'figma_embed': {'embed_url': 'https://figma.com/file/ABC'},
    'lottie_animation': {'src_url': 'https://assets.lottiefiles.com/anim.json', 'loop': True},
    'live_demo_embed': {'url': '#', 'title': 'Live Demo'},
    'benchmark_comparison': {'items': [{'label': 'A2UI', 'value': 95}, {'label': 'Baseline', 'value': 120}]},
    'chartjs_bar': {'labels': ['Jan', 'Feb', 'Mar'], 'datasets': [{'label': 'Renders', 'data': [42, 65, 88]}]},
    'chartjs_line': {'labels': ['Jan', 'Feb', 'Mar'], 'datasets': [{'label': 'Uptime', 'data': [99.2, 99.8, 99.5]}]},
    'data_table_sortable': {'headers': ['Atom', 'Surfaces'], 'rows': [['stat_card', 'Web, Meet'], ['callout', 'All']]},
    'donut_stat': {'label': 'Completion', 'value': 75, 'max': 100},
    'heatmap': {'data': [[3, 7, 2], [8, 1, 6], [2, 9, 3]]},
    'metric_comparison_card': {'label': 'Response time', 'value': 95, 'previous': 120},
    'metric_delta': {'label': 'Weekly signups', 'value': '+23%'},
    'mini_sparkline_set': {'series': [{'label': 'API', 'data': [10, 14, 9, 18, 22]}, {'label': 'DB', 'data': [5, 6, 5, 7, 8]}]},
    'progress_bar': {'label': 'Migration', 'percentage': 68},
    'progress_circle': {'percentage': 82, 'label': 'Score'},
    'sparkline': {'data': [5, 8, 4, 11, 7, 14, 9]},
    'status_dashboard': {'metrics': [{'label': 'API', 'value': 'Online', 'color': '#059669'}, {'label': 'CDN', 'value': 'Degraded', 'color': '#f59e0b'}]},
    'trend_indicator': {'value': '+5.2%', 'label': 'MoM growth'},
    'uptime_timeline': {'uptime': 99.7},
    'author_bio_card': {'name': 'Curtis Krygier', 'bio': 'Building at the intersection of AI and UI.'},
    'avatar_group': {'avatars': [{'name': 'Alice'}, {'name': 'Bob'}, {'name': 'Carol'}]},
    'contributor_list': {'contributors': [{'name': 'Alice', 'role': 'Maintainer'}, {'name': 'Bob', 'role': 'Contributor'}]},
    'customer_logo_grid': {'logos': [{'name': 'Acme', 'url': 'https://picsum.photos/seed/l1/80/40'}, {'name': 'Corp', 'url': 'https://picsum.photos/seed/l2/80/40'}]},
    'expert_endorsement': {'quote': 'A2UI is transforming AI interfaces.', 'expert': 'Jane Smith', 'title': 'CTO'},
    'follow_button': {'handle': '@curtiskrygier'},
    'follow_cta': {'text': 'Follow for updates', 'url': '#'},
    'media_mention_card': {'publication': 'TechCrunch', 'title': 'A2UI Reimagines AI Interfaces', 'url': '#', 'date': '2026-05-15'},
    'newsletter_cta': {'heading': 'Stay in the loop', 'text': 'Get updates on new atoms.'},
    'reaction_group': {'reactions': [{'emoji': '👍', 'count': 24}, {'emoji': '🚀', 'count': 12}]},
    'review_callout': {'quote': 'Best UI system for AI agents.', 'author': 'Dev', 'rating': 5},
    'share_quote': {'text': 'A2UI atoms are composable vocabulary.', 'url': '#'},
    'social_feed_embed': {'url': '#'},
    'social_share_bar': {'url': '#'},
    'testimonial_card': {'quote': 'Saved us weeks of UI work.', 'author': 'Product Lead'},
    'command_palette': {'commands': [{'text': 'Open Catalogue', 'shortcut': '⌘K'}, {'text': 'Render', 'shortcut': '⌘R'}]},
    'empty_state': {'title': 'No results', 'message': 'Try adjusting your filters.'},
    'inline_feedback_message': {'text': 'Changes saved.', 'type': 'success'},
    'loading_skeleton': {'height': 60},
    'search_result_card': {'title': 'A2UI Catalogue', 'description': '170 atoms across 22 categories.', 'url': 'techmusings.krygier.fr'},
    'spinner': {},
    'toast_notification': {'text': 'Published!', 'type': 'success'},
    'document_link': {'text': 'schema.yaml', 'url': '#'},
    'github_repo_card': {'url': 'https://github.com/curtiskrygier/a2ui-catalogue'},
    'repo_links': {'items': [{'text': 'a2ui-catalogue', 'url': 'https://github.com/curtiskrygier/a2ui-catalogue'}]},
    'audio_link': {'text': 'Listen', 'url': '#audio.mp3'},
    'audio_player': {'url': '#audio.mp3', 'title': 'Episode 1'},
    'youtube': {'url': 'https://youtu.be/3AofBvbFlIk'},
}

PLAYBOOK_NAME = "a2ui_catalogue"

# ── Slide ID plan ─────────────────────────────────────────────────────────────

def _slug(text: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")

def _build_slide_plan():
    plan = [("cover", "Cover", None, [])]
    for cat_name, atom_types in CATEGORIES:
        sorted_types = sorted(atom_types)
        chunks = [sorted_types[i:i+ATOMS_PER_SLIDE] for i in range(0, len(sorted_types), ATOMS_PER_SLIDE)]
        for ci, chunk in enumerate(chunks):
            sid = _slug(cat_name) + (f"_{ci+1}" if len(chunks) > 1 else "")
            lbl = cat_name + (f" {ci+1}/{len(chunks)}" if len(chunks) > 1 else "")
            plan.append((sid, lbl, cat_name, chunk))
    return plan

_PLAN = _build_slide_plan()
_TOTAL = len(_PLAN)

# ── HTML content — full viewport, nav via <form method=POST> (no JS, CSP-safe) ──

_CSS = (
    '<style>*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}'
    'html,body{width:100vw;height:100vh;background:#fff;color:#111827;'
    'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;overflow:hidden;'
    'display:flex;flex-direction:column;}'
    '</style>'
)

def _load_stars() -> set:
    try:
        import json as _json
        with open("/home/curtis/a2ui-catalogue/starred.json") as f:
            return set(_json.load(f))
    except Exception:
        return set()

def _render_atom_card(atom_type: str, slide_id: str, space_id: str, stars: set) -> str:
    atom = _ATOMS.get(atom_type, {})
    desc = atom.get('description', '')[:80]
    try:
        data = dict(GEN_DATA.get(atom_type, {}))
        data['type'] = atom_type
        example = wa_render([data])
        if not example.strip():
            raise ValueError("empty")
    except Exception:
        example = '<em style="color:#9ca3af;font-size:0.72rem;">[ no preview ]</em>'

    starred = atom_type in stars
    star_char = "★" if starred else "☆"
    star_color = "#f59e0b" if starred else "#d1d5db"
    star_bg = "#fffbeb" if starred else "transparent"
    border_color = "#fde68a" if starred else "#e5e7eb"

    star_btn = (
        f'<a href="/api/catalogue/star/{atom_type}/{slide_id}/{space_id}" '
        f'style="background:{star_bg};border:1px solid {border_color};border-radius:4px;'
        f'padding:2px 6px;font-size:0.85rem;color:{star_color};line-height:1;'
        f'text-decoration:none;display:inline-block;">{star_char}</a>'
    )

    return (
        f'<div style="border:1px solid {"#fde68a" if starred else "#e5e7eb"};border-radius:8px;'
        f'padding:10px;background:{"#fffbeb" if starred else "#fafafa"};'
        f'display:flex;flex-direction:column;gap:6px;overflow:hidden;">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;gap:6px;">'
        f'<div style="font-family:monospace;font-size:0.72rem;color:#7c3aed;font-weight:600;'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{atom_type}</div>'
        f'{star_btn}'
        f'</div>'
        f'<div style="font-size:0.65rem;color:#6b7280;line-height:1.3;">{desc}</div>'
        f'<div style="border:1px solid #e5e7eb;border-radius:4px;padding:8px;background:#fff;'
        f'overflow:hidden;font-size:0.78rem;">{example}</div>'
        f'</div>'
    )

def _cover_panel_html() -> str:
    stat_cards = "".join(
        f'<div style="text-align:center;padding:14px 24px;background:#faf5ff;'
        f'border:1px solid #ede9fe;border-radius:10px;">'
        f'<div style="font-size:1.8rem;font-weight:700;color:#7c3aed;">{v}</div>'
        f'<div style="font-size:0.72rem;color:#6b7280;margin-top:3px;">{l}</div></div>'
        for l, v in [("Atoms", str(len(_ALL_ATOMS))), ("Categories", str(len(CATEGORIES))), ("Surfaces", "4")]
    )
    return (
        _CSS +
        f'<div style="width:100%;height:100%;display:flex;flex-direction:column;align-items:center;'
        f'justify-content:center;gap:20px;padding:32px;">'
        f'<div style="font-size:0.72rem;font-weight:600;color:#7c3aed;letter-spacing:0.1em;text-transform:uppercase;">A2UI</div>'
        f'<h1 style="font-size:2.2rem;font-weight:800;color:#111827;letter-spacing:-0.02em;margin:0;">Atom Catalogue</h1>'
        f'<p style="color:#6b7280;font-size:0.85rem;">The vocabulary your agent speaks</p>'
        f'<div style="display:flex;gap:14px;">{stat_cards}</div>'
        f'</div>'
    )

def _category_panel_html(cat_name: str, chunk: list, idx: int, slide_id: str, space_id: str) -> str:
    stars = _load_stars()
    cards = "".join(_render_atom_card(t, slide_id, space_id, stars) for t in chunk)
    cols = len(chunk)
    total_chunks = sum(1 for s in _PLAN if s[2] == cat_name)
    chunk_num    = sum(1 for s in _PLAN[:idx+1] if s[2] == cat_name)
    chunk_label  = f" ({chunk_num}/{total_chunks})" if total_chunks > 1 else ""
    return (
        _CSS +
        f'<div style="width:100%;height:100%;overflow-y:auto;padding:12px;">'
        f'<div style="font-size:0.8rem;font-weight:700;color:#7c3aed;margin-bottom:8px;">'
        f'{cat_name}{chunk_label}</div>'
        f'<div style="display:grid;grid-template-columns:repeat({cols},1fr);gap:8px;">'
        f'{cards}'
        f'</div>'
        f'</div>'
    )


def C(cid, el, props):
    return {"id": cid, "component": el,
            **{k: v for k, v in props.items() if k not in ("id", "component")}}

def _fire(slide_id: str, space_id: str) -> dict:
    return {"functionCall": {"call": "fireEndpoint",
                             "args": {"endpoint": f"/api/playbook/fire/{PLAYBOOK_NAME}/{slide_id}/{space_id}"}}}

def _make_builder(idx: int, sid: str, cat_name, chunk):
    def builder(space_id: str, tick: int = 0):
        if idx == 0:
            panel_html = _cover_panel_html()
        else:
            panel_html = _category_panel_html(cat_name, chunk, idx, sid, space_id)

        prev_id = _PLAN[idx - 1][0] if idx > 0 else None
        next_id = _PLAN[idx + 1][0] if idx < _TOTAL - 1 else None

        footer_children = []
        if prev_id:
            footer_children.append(f"prev_{sid}")
        footer_children.append(f"lbl_{sid}")
        if next_id:
            footer_children.append(f"next_{sid}")

        comps = [
            C("root", "gdm-stage-grid", {"layout": "hero", "children": ["wrap"]}),
            C("wrap", "gdm-container", {
                "direction": "column", "grow": 1,
                "width": "100%", "height": "100%",
                "children": ["panel", "ftr"],
            }),
            C("panel", "gdm-html-panel", {"html": panel_html, "version": tick + 1}),
            C("ftr", "gdm-container", {
                "direction": "row", "align": "center", "justify": "center",
                "padding": "6px 16px", "gap": "12px", "shrink": 0,
                "children": footer_children,
            }),
            C(f"lbl_{sid}", "gdm-text", {
                "content": f"{idx+1} / {_TOTAL}  ·  {_PLAN[idx][1]}",
                "size": "11px", "color": "#9ca3af",
            }),
        ]
        if prev_id:
            comps.append(C(f"prev_{sid}", "gdm-button", {
                "text": "← Prev", "action": _fire(prev_id, space_id),
            }))
        if next_id:
            comps.append(C(f"next_{sid}", "gdm-button", {
                "text": "Next →", "action": _fire(next_id, space_id),
            }))
        return comps
    return builder

SLIDES = [
    Slide(
        slide_id=sid,
        label=label,
        builder=_make_builder(i, sid, cat_name, chunk),
    )
    for i, (sid, label, cat_name, chunk) in enumerate(_PLAN)
]

playbook_manager.register_playbook(PLAYBOOK_NAME, SLIDES)
