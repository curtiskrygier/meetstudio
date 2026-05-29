# Google Meet Studio — Handover

_Conversation export for continuation in another interface. Written 2026-05-29._

This document is a self-contained handover. An LLM reading this should be able to advise on or continue the project's evolution without needing the prior conversation.

---

## 1. Quick orientation

**Project name (working title):** Google Meet Studio (the user has subtly already renamed UI elements). Previously called "Live Concierge."

**Location:** `/home/curtis/gemini/addons/meet-live-concierge/`

**What it is:** A Google Meet add-on that renders an agent-driven dynamic stage in the meeting. The agent (Gemini Live) listens, composes UI surfaces via the A2UI protocol, and pushes them to a "main stage" rendered as Lit web components. Surfaces are real-time, voice-driven, composable from primitives.

**What it *actually* is, strategically (recent realisation):** A **presentation studio for Google Meet**, not a meeting concierge. Every catalogue atom is a slide primitive; every act is a slide; the agent is the presenter's silent co-pilot. See [§3 Strategic framing](#3-strategic-framing).

**Tech stack:**
- Backend: FastAPI on Cloud Run (`main.py`), connects to Gemini Live
- Frontend: Lit web components, Vite bundling (`dist/`)
- Protocol: A2UI v0.8 — agent describes a component tree, server pushes via WebSocket, client materialises
- Catalogue: `gdm-*` components in `internal/components/`
- Stage entry: `main_stage.html` (audience-facing fullscreen surface)
- Add-on side panel: `index.tsx` (presenter-facing controls)

---

## 2. Project state — what works today

### 2.1 Catalogue (primitives, atoms, molecules)

The user has built a catalogue of composable Lit components, all prefixed `gdm-`. Some atoms (small primitives), some molecules (composed mini-surfaces).

Key existing components:
- `gdm-text` — text with size, weight, color, font (sans/mono/serif), letterSpacing, uppercase, pulse, **flip** (split-flap animation on content change), **typeOn** (NEW — typewriter with cursor), **glitch** (NEW — matrix decrypt effect)
- `gdm-badge` — coloured pill with type (danger/warning/info/primary), pulse, outline, text
- `gdm-container` — flexbox layout primitive with direction, justify, align, gap, padding, glass, borderRadius, grow, margin, **reveal** + **revealDelay** (entrance animation atoms)
- `gdm-grid` — CSS grid layout
- `gdm-stage-grid` — top-level layout container with layouts: single, split, grid, hero (panel-1 fills the stage)
- `gdm-clock` — flip-clock variant or plain digital
- `gdm-stat` — labeled metric with delta, isUp, countUp atom
- `gdm-divider` — horizontal rule with color
- `gdm-spacer` — flex spacer
- `gdm-captions` — flip-flap caption pill at bottom or centre, with showPrev / flip / position
- `gdm-market-ticker` — 3D-perspective live market scan (legacy, position:fixed; inset:0 in CSS — see §5.5 gotcha)
- `gdm-3d-airspace` — 3D-rendered flights on a radar scene; uses `gdm-3d-scene` molecule
- `gdm-3d-scene` — generic 3D canvas with projected points + labels
- `gdm-diagram-view` — renders an SVG diagram, with optional overlay mode (fullscreen)
- `gdm-video-panel` — YouTube embed or local mp4, with optional overlay mode (fullscreen)
- `gdm-html-panel` — arbitrary sanitized HTML

### 2.2 Demos / showreel scripts

- `render_showreel.py` — 6-act showreel: title → market → diagram → ATC → video → quad finale. The user's flagship demo today.
- `demo_a2ui_primitives.py` — NEW. The primitives showcase ("Anatomy of a Ticker") in three passes: SHOW each primitive alone with API labels, PLACE them animating into a market ticker formation, BREATHE the assembled ticker with live updates. ~280 lines. See [§5 Key code](#5-key-code-excerpts).
- `demo_a2ui_executive_soho.py`, `demo_a2ui_ultimate_showcase.py`, `demo_a2ui_smart_facility.py` — older showcase demos. The `ultimate_showcase` contains the canonical hand-tuned `trading_svg` cyberpunk style that inspired the d2 polish layer.

### 2.3 Dev loop

The user runs everything locally. From the project root:

```bash
# 1. Backend (must set GEMINI_PROJECT first — see GOTCHAS)
source venv/bin/activate
export GEMINI_PROJECT=centered-planet-497209-r5
uvicorn main:app --port 8085 --reload

# 2. Open a stage listener in browser
./open_stage.sh                  # mints a ticket, opens main_stage.html in browser
# Or with custom space:
./open_stage.sh my-space

# 3. Run a demo script (Python only, no rebuild needed for surface changes)
python demo_a2ui_primitives.py
python render_showreel.py

# 4. If TS components changed, rebuild frontend first
npm run build                    # then hard-refresh the stage tab (Ctrl+Shift+R)
```

The `open_stage.sh` script (written during this conversation) is in the repo root.

### 2.4 GOTCHAS the LLM should know

- **`GEMINI_PROJECT` env var is required** to start uvicorn — `app/config.py:191` errors out if it's missing, even for showreel-only work that doesn't actually use Gemini.
- **`uvicorn --reload`** drops the ws connection on `.py` edits and invalidates in-memory stage tickets — must re-mint via `./open_stage.sh` and reload the stage tab.
- **Hash-based asset filenames** mean the browser tab has the old JS hash burned into its HTML. After `npm run build`, must **hard-refresh** (Ctrl+Shift+R / Cmd+Shift+R) to pick up new bundle.
- **`gdm-container` writes inline `flex-grow: <prop>` unconditionally** — defaults to `0`. Inline style beats the grid slot's `::slotted(*) { flex: 1 }` rule. **Any `gdm-container` slotted into a `gdm-stage-grid` cell that should fill the cell height needs explicit `grow: 1`.** Easy gotcha to hit.
- **Catalogue validation is warn-don't-block.** Unknown props pass with a warning. New atoms can be used in surface payloads without updating `app/a2ui_catalog.py` first.
- **`gdm-market-ticker` has `position: fixed; inset: 0` baked into its CSS** — it pops out of any grid slot it's placed in. Use a composed mini-panel of containers + text rows instead if you want it inside a grid cell.
- **`d2` requires INTEGER `stroke-width`** between 0-15. Floats like `2.5` cause parse failure → silent fallback to placeholder SVG.
- **Catch-all routes MUST be last in `main.py`.** Two things have this property and both bit during the PoC apply:
  - `app.mount("/", StaticFiles(...))` — Starlette mount, captures every URL under its prefix, GET/HEAD only. Any `@app.post(...)` declared *after* in source registers cleanly (shows in `openapi.json`) but returns 405 at request time because the mount intercepts first.
  - `@app.get("/{path:path}", include_in_schema=False)` — SPA-fallback catch-all that explicitly `raise HTTPException(404)` for `api/*` paths. Any `@app.get` declared *after* in source for an `api/*` path returns 404 even though it's registered — the catch-all wins first.
  - Symmetric rule: anything that matches greedily by path must come AFTER specific routes. Both currently live at the bottom of `main.py` — keep them there. When appending new endpoints, put them BEFORE these two blocks or move the blocks down to remain last.
- **Browser bundle caching after `npm run build`.** Vite emits hash-based asset filenames (`main_stage-{HASH}.js`). After a build, the browser tab is still loading the OLD hash from a prior session — a normal refresh re-fetches the same cached HTML which still points at the old asset. Must **hard-refresh** (`Ctrl+Shift+R` / `Cmd+Shift+R`) to get the new HTML pointing at the new hash. Symptoms when you forget: clicks dispatch old-event-mode CustomEvents with empty fields, or new atoms/props silently no-op. See §12.7 Bug 3.

---

## 3. Strategic framing

This is the most important section for an LLM picking up the conversation. The strategy is locked in via these principles:

### 3.1 The substrate principle (saved as memory)

> **Invest in substrates, not compositions.**
>
> Substrates compound when compute deflates. Compositions become free.
>
> A2UI catalogue is a substrate. So is data, identity, protocol. Everything *above* the substrate line will be regenerated on demand by the time it matters.

Test for any new feature: *"will this still be useful when the agent gets 10× more capable, or do I have to rewrite it?"* If rewrite — composition, don't over-invest. If still useful (atoms outlive screens) — substrate, build it well.

### 3.2 Three modes (saved as memory)

Same primitives, same catalogue, three completely different deployment shapes for three different audiences:

| Mode | Triggering | Audience | Friction | Value prop |
|---|---|---|---|---|
| **A. Live agent stage** | Agent listens + decides | Tech-forward / demo stage | **High** — "AI is in the room" recording indicator | Wow / vision / future of meetings |
| **B. Sidekick to trad decks** | Presenter speaks, agent suggests, presenter approves | Sales / marketing / pitches | **Medium** — agent still listening | Live data overlay on your normal PPT/Slides pitch |
| **C. Pre-prepped playbook + action buttons** | Presenter clicks button (or hits clicker) | Enterprise / regulated / high-stakes | **Zero** — no listening, no recording indicator | "Your slides are alive when *you* say so" |

**The recording-indicator friction is the iceberg under Mode A.** Mode C sidesteps it entirely and is the realistic beach-head — the version 10× more people will actually use this year.

**The three-chapter story arc** for sharing the journey:
- Chapter 1: "I built a kitchen" (primitives, atoms — the substrate)
- Chapter 2: "I built a chef" (live agent stage — the wow demo)
- Chapter 3: "I gave the menu to you" (pre-prepped playbooks + buttons — the version humans actually use)

### 3.3 The restaurant metaphor

Used throughout the primitives demo's title and sign-off:

| Metaphor | Reality |
|---|---|
| The restaurant | Google Meet — where you sit down |
| The menu | A2UI catalogue — what can be served |
| The recipe | A composed surface (ticker, ATC, diagram) — the dish |
| The ingredients | Primitives / atoms / molecules — what every dish is built from |
| The kitchen | The agent + Cloud Run + Gemini — where dishes are made on demand |
| The chef | The agent (Gemini Live deciding what to plate) |
| **The chef is at the table** | The agent is IN the room listening — the unique meeting-shaped property |

Final sign-off lines in `demo_a2ui_primitives.py`:
```
THE RESTAURANT.  /  THE MENU.  /  THE INGREDIENTS.
GOOGLE MEET × A2UI                  ← equal hero brands
[FULLY EXTENSIBLE · INFINITELY COMPOSABLE]   ← badge pulse
THE CHEF IS AT THE TABLE.                    ← typeOn matrix style (phosphor)
follow the rabbit.                           ← typeOn callback
infinite possibilities.                      ← typeOn close
```

### 3.4 A2UI × WebMCP — see `A2UI_WEBMCP_FIT.md`

Full doc lives at `A2UI_WEBMCP_FIT.md` in repo root. Summary:

- **A2UI = outbound rendering** (agent → UI; renderer materialises for human eyes)
- **WebMCP = inbound action surface** (page declares tools; renderer materialises for agent invocation)
- Both are agent-shaped at the protocol layer; differ at the *terminal consumer* (human vs machine)
- **For *this* project, WebMCP is currently redundant for the user's own Gemini Live agent** (which already has a WebSocket and can drive anything). WebMCP's value emerges when third-party agents arrive at the URL.
- **WebMCP becomes more interesting for Mode C** — the action buttons could be exposed as WebMCP tools, making the studio scriptable from a phone / Chat / external orchestrator.

Decision principle (in the doc):
> Build WebMCP when a second agent (not yours) actually wants to drive the stage, or an external orchestrator wants to script demos. Clean architecture without a consumer is decoration.

### 3.5 Why meetings are A2UI's home medium

User's insight: meetings dodge the friction A2UI hits everywhere else.

```
A2UI friction on normal websites    How meetings dodge it
─────────────────────────────────────────────────────────────────
SEO / indexability                  meetings aren't crawled
Persistence expectations            the surface ends with the meeting
Multi-step user navigation          audience watches; doesn't navigate
Agent latency vs static page        you're already at talking pace
Choosing what to show               the conversation IS the signal
Multi-user shared state             already solved at meeting protocol
Accessibility overhead              already required by meeting platform
```

Plus the structural property no other UI context has: **the audience expects to be shown what to look at.** Show-me-don't-navigate maps exactly onto agent-renders-for-audience.

---

## 4. The big open design thread — Mode C playbook

The current conversation ended on the playbook architecture for Mode C. Here is the full design we developed.

### 4.1 Architecture sketch

```
PLAYBOOK FILE                  SERVER                     PRESENTER URL               AUDIENCE STAGE
─────────────                  ──────                     ─────────────               ──────────────
playbook = [                   /api/playbook/list         /presenter/{space}          /main_stage.html
  Slide(                       /api/playbook/fire         + ticket auth               + ticket auth
    "Q3 Revenue",                                         renders buttons             receives renders
    builder=q3_revenue,                                    (one per slide)            (no change to this)
    notes="lead w/ topline",                              click → POST fire
    ticks=False,
  ),
  Slide("Market", market_fn,                              presenter clicks → server
        ticks=True, hz=1),                                                            renders via existing
  ...                                                                                /api/render-stage
]
```

### 4.2 The four pieces to build (Mode C v0)

1. **A playbook file in Python** — same shape as showreel `ACTS` list. Each `Slide` is `(id, label, builder_fn, notes, ticks, hz)`.
2. **A `gdm-button` atom** — click POSTs to a configured URL with a configured payload. ~50 lines TS.
3. **`/presenter/{space}` page** — renders a fixed A2UI surface listing buttons + current state + notes. Same dist stack, different payload.
4. **`/api/playbook/fire/{name}/{slide_id}/{space}`** — looks up the slide, runs its builder, broadcasts to the audience stage. ~20 lines on top of existing `render_stage`.

Plus a tick-loop manager: async task per active tick-enabled slide, cancelled on next fire.

Total: ~250 lines new code. A weekend.

### 4.3 The authoring story (still being designed)

The hardest part of Mode C. PowerPoint has 30 years of muscle memory. We need authoring paths that don't say "write Python":

| Starting state | Authoring path |
|---|---|
| Has notes / outline / old deck / data source | Import or markdown → templates |
| Has a brief in their head | Agent-assisted draft, user edits |
| Is the developer | Python (works today) |

**Five layers of authoring** (each adds a class of presenters):

1. **Markdown with extension syntax** — `:::stat label=ARR value=$48M delta=+18% countUp:::`. Walk markdown AST, emit playbook. ~150 lines.
2. **YAML declarative format** — cleaner for non-prose-heavy authoring.
3. **PowerPoint/Keynote import** — extract text + layout + notes from XML, map to templates.
4. **Live data binding** — slides declare data sources (bigquery, yahoo_finance, opensky, yaml file); server fetches at fire-time.
5. **Agent-assisted authoring** — the killer feature. User writes a brief; agent generates the YAML playbook. *"5 slides for my Q3 board meeting. Lead with revenue, show the ATC airspace example for ops resilience, end with a Q&A slate."* → playbook out.

**The template library** is the substrate layer between authoring formats and the catalogue:

```python
TEMPLATES = {
    "title":        title_card_template,        # large headline + subtitle
    "hero_stat":    hero_stat_template,         # single big number + delta
    "compare_two":  side_by_side_template,
    "list_5":       five_bullet_template,
    "chart_full":   fullscreen_chart_template,
    "quote":        quote_card_template,
    "code_focus":   code_highlight_template,
    "market":       market_ticker_template,
    "airspace":     airspace_template,
    "diagram":      diagram_overlay_template,
    "video":        video_panel_template,
    "qa_slate":     qa_template,
    "sign_off":     sign_off_template,
}
```

Each template accepts props and returns A2UI component lists. **Templates are the substrate; playbooks are the composition.**

### 4.4 Recommended v0 build sequence

1. Template library (~5 templates: title, hero_stat, market, ops, signoff) — ~300 lines
2. Markdown loader with `:::template:::` extension — ~150 lines
3. YAML loader — ~80 lines
4. Live data binding (3 sources: literal, bigquery, yaml) — ~200 lines
5. Agent prompt + endpoint — ~100 lines

Total ~800 lines for v0 authoring stack. One to two weeks.

---

## 5. Key code excerpts

### 5.1 New atoms on `gdm-text` — `internal/components/gdm_stage_text.ts`

Two new boolean props added: `typeOn` (typewriter with cursor) and `glitch` (matrix decrypt). Both compose with existing `flip`, `pulse`, `font`, etc. Precedence: glitch > typeOn > flip > plain.

```typescript
import { LitElement, css, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { repeat } from 'lit/directives/repeat.js';

@customElement('gdm-text')
export class GdmStageText extends LitElement {
  @property({ type: String }) content = '';
  @property({ type: String }) size = '14px';
  @property({ type: String }) weight = 'normal';
  @property({ type: String }) color = 'rgba(255, 255, 255, 0.9)';
  @property({ type: String }) align = 'left';
  @property({ type: String }) font = 'sans';
  @property({ type: Number }) opacity = 1.0;
  @property({ type: String }) letterSpacing = 'normal';
  @property({ type: Boolean }) uppercase = false;
  @property({ type: Boolean }) pulse = false;
  @property({ type: Boolean }) flip = false;
  @property({ type: Boolean }) typeOn = false;
  @property({ type: Boolean }) glitch = false;

  @state() private _typeDisplay = '';
  @state() private _glitchDisplay = '';
  private _glitchTimer: number | undefined;
  private _typeTimer: number | undefined;
  private _GLITCH_CHARSET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%&*<>/=?+';

  willUpdate(changed) {
    if (changed.has('content') || changed.has('glitch') || changed.has('typeOn')) {
      if (this.glitch && this.content) this._startGlitch();
      else if (this.typeOn && this.content) this._startType();
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._glitchTimer !== undefined) window.clearTimeout(this._glitchTimer);
    if (this._typeTimer !== undefined) window.clearTimeout(this._typeTimer);
  }

  private _startGlitch() {
    if (this._glitchTimer !== undefined) window.clearTimeout(this._glitchTimer);
    const target = String(this.content);
    const maxIters = 18;
    let iter = 0;
    const tick = () => {
      const progress = iter / maxIters;
      const settled = Math.floor(target.length * progress);
      let out = target.slice(0, settled);
      for (let i = settled; i < target.length; i++) {
        const c = target[i];
        out += c === ' ' ? ' ' : this._GLITCH_CHARSET[
          Math.floor(Math.random() * this._GLITCH_CHARSET.length)];
      }
      this._glitchDisplay = out;
      iter++;
      if (iter <= maxIters) this._glitchTimer = window.setTimeout(tick, 32);
      else this._glitchDisplay = target;
    };
    tick();
  }

  private _startType() {
    if (this._typeTimer !== undefined) window.clearTimeout(this._typeTimer);
    const target = String(this.content);
    let idx = 0;
    const tick = () => {
      idx++;
      this._typeDisplay = target.slice(0, idx);
      if (idx < target.length) this._typeTimer = window.setTimeout(tick, 35);
    };
    this._typeDisplay = '';
    tick();
  }

  // ... static styles include .typeon-cursor with blinking animation, .flip-char
  //     with flip-in keyframes, .pulse with text-pulse keyframes, etc.

  render() {
    // ... resolve preset sizes (h1=32px, body=14px, caption=11px),
    //     resolve preset colors (accent, mute, white, success, etc.) ...

    let body: any;
    if (this.glitch) {
      body = this._glitchDisplay || this.content;
    } else if (this.typeOn) {
      const typed = this._typeDisplay;
      body = html`${typed}<span class="typeon-cursor">&nbsp;</span>`;
    } else if (this.flip) {
      body = repeat(
        String(this.content).split(''),
        (ch, i) => `${i}:${ch}`,
        (ch) => ch === ' '
          ? html`<span>&nbsp;</span>`
          : html`<span class="flip-char">${ch}</span>`,
      );
    } else {
      body = this.content;
    }

    return html`<span class="${classes}" style="${inlineStyles}">${body}<slot></slot></span>`;
  }
}
```

### 5.2 The D2 polish layer — `render_showreel.py`

Post-processes d2-generated SVGs to add the cyberpunk look (glow filters per tier + marching-ants connector animation + dot-grid background). Inspired by `demo_a2ui_ultimate_showcase.py`'s hand-tuned `trading_svg`. Targets by stroke colour (set in d2 classes block) rather than d2's internal class names so it survives d2 version changes.

```python
_TIER_COLOURS = {
    "ext":  "#00f2ff",  # cyan — edges, data sources, clients
    "core": "#f000ff",  # magenta — the central brain
    "data": "#00ff88",  # green — where state is rendered / executed
    "llm":  "#b388ff",  # purple — language models
}

def _build_d2() -> str:
    # NB: d2's stroke-width must be an INTEGER 0-15. Floats fail parse.
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
    for src, dst, lbl in EDGES:
        suffix = "{ style.stroke-dash: 4 }"  # gives marching-ants polish something to march on
        lines.append(f'{src} -> {dst}: "{lbl}" {suffix}' if lbl else f'{src} -> {dst}: {suffix}')
    return "\n".join(lines)


def _polish_d2_svg(svg: str) -> str:
    """Cyberpunk polish on d2 output: glow filters per tier + marching-ants
    animation on dashed edges + dot-grid backdrop. Targets by stroke colour
    (controlled in our classes: block) rather than d2 internal class names."""
    polish = (
        '<defs>'
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
        '<pattern id="bg-dots" width="24" height="24" patternUnits="userSpaceOnUse">'
        '<circle cx="2" cy="2" r="1.1" fill="rgba(0,242,255,0.08)"/>'
        '</pattern>'
        '</defs>'
        '<style>'
        f'[stroke="{_TIER_COLOURS["ext"]}"]  {{ filter: url(#glow-ext); }}'
        f'[stroke="{_TIER_COLOURS["core"]}"] {{ filter: url(#glow-core); }}'
        f'[stroke="{_TIER_COLOURS["data"]}"] {{ filter: url(#glow-data); }}'
        f'[stroke="{_TIER_COLOURS["llm"]}"]  {{ filter: url(#glow-llm); }}'
        'path[stroke-dasharray], path[style*="stroke-dasharray"] {'
        ' animation: march 1.4s linear infinite;'
        '}'
        '@keyframes march { to { stroke-dashoffset: -120; } }'
        '</style>'
        '<rect width="100%" height="100%" fill="url(#bg-dots)" pointer-events="none"/>'
    )
    return re.sub(r'(<svg[^>]*>)', lambda m: m.group(1) + polish, svg, count=1)
```

For this to work, the diagram-view component must use the SVG DOMPurify profile + explicitly allow `<style>`:

```typescript
// internal/components/gdm_stage_diagram.ts — sanitize call
const sanitized: string = domPurify
  ? domPurify.sanitize(this.svg, {
      USE_PROFILES: { svg: true, svgFilters: true },
      ADD_TAGS: ['style'],   // d2's @font-face declarations live here too
    })
  : this.svg;
```

Without `ADD_TAGS: ['style']`, DOMPurify can drop the `<style>` block in some versions, which kills both the polish CSS and d2's embedded font-face declarations.

### 5.3 The primitives showcase — `demo_a2ui_primitives.py`

Full script. Three passes: SHOW (each primitive alone), PLACE (assemble into ticker), BREATHE (live updates). Plus title, ORDER UP transition, and restaurant-metaphor sign-off.

```python
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

Runs standalone against the local backend.
"""
import asyncio, os, sys, glob, datetime
_base = os.path.dirname(os.path.abspath(__file__))
for _vd in glob.glob(os.path.join(_base, "venv", "lib", "python3.*", "site-packages")):
    if _vd not in sys.path: sys.path.insert(0, _vd)
import httpx

API   = os.environ.get("CONCIERGE_API_URL", "http://127.0.0.1:8085")
KEY   = os.environ.get("STAGE_API_KEY", "meet-live_STAGE_SECURE_v1_zG9fN8qL7vP2mX6tY9wK4jC5bS8xQ7hZ3uW0rA")
SPACE = os.environ.get("CAPTURE_SPACE", "default")

PHOSPHOR = "#00ff88"

def C(cid, el, props):
    return {"id": cid, "component": {el: props}}


def primitive_surface(prim_id: str, prim_el: str, prim_props: dict, lines: list,
                      step: int = 0, total: int = 0):
    """One primitive centre stage, mono labels below."""
    label_ids = [f"lbl_{i}" for i in range(len(lines))]
    surface = [
        C("root", "gdm-stage-grid", {"layout": "hero", "children": {"explicitList": ["main"]}}),
        C("main", "gdm-container", {"direction": "column", "justify": "center", "align": "center",
                                    "width": "100%", "height": "100%", "gap": "32px",
                                    "padding": "60px", "grow": 1,
                                    "children": {"explicitList": ["banner", "showcase", "label_block"]}}),
        C("banner", "gdm-text", {
            "content": f"INGREDIENT {step} OF {total} · {lines[0]}",
            "size": "18px", "color": "rgba(0,255,136,0.65)", "font": "mono",
            "weight": "700", "letterSpacing": "0.32em", "uppercase": True,
            "typeOn": True,
        }),
        C("showcase", "gdm-container", {"direction": "row", "justify": "center", "align": "center",
                                        "padding": "40px 56px", "borderRadius": "16px",
                                        "border": "1px dashed rgba(0,255,136,0.18)",
                                        "background": "rgba(0,255,136,0.03)",
                                        "reveal": "scale-in", "revealDelay": 0.25,
                                        "children": {"explicitList": [prim_id]}}),
        C(prim_id, prim_el, prim_props),
        C("label_block", "gdm-container", {"direction": "column", "align": "center", "gap": "8px",
                                           "reveal": "fade-up", "revealDelay": 0.55,
                                           "children": {"explicitList": label_ids}}),
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

    ("p_glitch", "gdm-text", {"content": "ONE CATALOGUE.", "size": "72px",
                              "color": PHOSPHOR, "font": "mono", "weight": "900",
                              "letterSpacing": "0.06em", "glitch": True},
     ["gdm-text  glitch: true", "matrix-style decrypt on content change"]),
]


def title_surface():
    return [
        C("root", "gdm-stage-grid", {"layout": "hero", "children": {"explicitList": ["main"]}}),
        C("main", "gdm-container", {"direction": "column", "justify": "center", "align": "center",
                                    "width": "100%", "height": "100%", "grow": 1,
                                    "gap": "20px", "padding": "60px",
                                    "children": {"explicitList": ["t_badge", "t_title", "t_sub"]}}),
        C("t_badge", "gdm-badge", {"text": "TONIGHT'S SPECIAL", "type": "danger", "pulse": True}),
        C("t_title", "gdm-text", {"content": "MEET. MENU. INGREDIENTS.", "size": "84px",
                                  "color": "white", "font": "mono", "weight": "900",
                                  "uppercase": True, "letterSpacing": "0.04em", "glitch": True}),
        C("t_sub",   "gdm-text", {"content": "every dish, composed on demand.",
                                  "size": "22px", "color": "rgba(0,255,136,0.7)", "font": "mono",
                                  "letterSpacing": "0.18em", "uppercase": True, "typeOn": True}),
    ]


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


def _ticker_row(i, sym, price, chg, up, base_delay):
    rid = f"trow{i}"
    return [
        C(rid, "gdm-container", {"direction": "row", "align": "center", "gap": "20px",
                                 "grow": 1, "padding": "7px 6px",
                                 "reveal": "slide-right", "revealDelay": base_delay,
                                 "children": {"explicitList": [f"sym{i}", f"price{i}",
                                                               f"sp{i}", f"chg{i}"]}}),
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
    """Pass 2 — 2x6 dense ticker grid; left column reveals first, right second."""
    half = len(TICKER_ROWS) // 2
    left_ids  = [f"trow{i}" for i in range(half)]
    right_ids = [f"trow{i}" for i in range(half, len(TICKER_ROWS))]
    out = [
        C("root", "gdm-stage-grid", {"layout": "hero", "children": {"explicitList": ["main"]}}),
        C("main", "gdm-container", {"direction": "column", "padding": "40px 52px", "gap": "12px",
                                    "width": "100%", "height": "100%", "grow": 1,
                                    "glass": True, "borderRadius": "18px",
                                    "reveal": "scale-in", "revealDelay": 0.0,
                                    "children": {"explicitList": ["hdr", "div", "body"]}}),
        C("hdr", "gdm-container", {"direction": "row", "align": "center", "gap": "16px",
                                   "reveal": "fade-up", "revealDelay": 0.2,
                                   "children": {"explicitList": ["hdr_badge", "hdr_sp", "hdr_clock"]}}),
        C("hdr_badge", "gdm-badge", {"text": "REALTIME · MARKET SCAN", "type": "danger", "pulse": True}),
        C("hdr_sp",    "gdm-spacer", {}),
        C("hdr_clock", "gdm-clock", {"showClock": True, "showDate": False, "variant": "flip",
                                     "accentColor": PHOSPHOR}),
        C("div", "gdm-divider", {"color": "rgba(0,255,136,0.22)", "reveal": "fade-up", "revealDelay": 0.35}),
        C("body", "gdm-container", {"direction": "row", "gap": "44px", "grow": 1, "width": "100%",
                                    "align": "stretch",
                                    "children": {"explicitList": ["col_l", "col_r"]}}),
        C("col_l", "gdm-container", {"direction": "column", "gap": "4px", "grow": 1,
                                     "children": {"explicitList": left_ids}}),
        C("col_r", "gdm-container", {"direction": "column", "gap": "4px", "grow": 1,
                                     "children": {"explicitList": right_ids}}),
    ]
    for i, (sym, price, chg, up) in enumerate(TICKER_ROWS):
        col_offset = 0.0 if i < half else 0.55
        idx_in_col = i if i < half else i - half
        out += _ticker_row(i, sym, price, chg, up,
                          base_delay=0.5 + col_offset + idx_in_col * 0.10)
    return out


def breathe_partial(tick):
    """Pass 3 — partial update of only price/chg cells. Sizes match _ticker_row
    so values don't resize on each tick. flip atom animates each new value."""
    out = []
    for i, (sym, price, chg, up) in enumerate(TICKER_ROWS):
        prefix = "$" if price.startswith("$") else ""
        clean = price.lstrip("$").replace(",", "")
        try: raw = float(clean)
        except ValueError: raw = 100.0
        nudge = ((tick * 7 + i * 13) % 11 - 5) * 0.04 * (1 + i * 0.2)
        new_raw = max(0.01, raw + nudge)
        if raw < 5:          new_price = f"{prefix}{new_raw:,.4f}"       # FX-like
        elif raw > 10000:    new_price = f"{prefix}{new_raw:,.0f}"       # BTC/indices
        else:                new_price = f"{prefix}{new_raw:,.2f}"
        delta_pct = nudge / raw * 100
        is_up = nudge >= 0
        new_chg = f"{'↑' if is_up else '↓'} {'+' if is_up else ''}{delta_pct:.2f}%"
        out.append(C(f"price{i}", "gdm-text", {"content": new_price, "size": "30px", "color": "white",
                                               "font": "mono", "weight": "800", "flip": True}))
        out.append(C(f"chg{i}", "gdm-text", {"content": new_chg, "size": "26px",
                                             "color": "#19d27a" if is_up else "#ff5d5d",
                                             "font": "mono", "weight": "800"}))
    return out


def transition_surface():
    """ORDER UP. — restaurant-metaphor flash between Pass 1 and Pass 2."""
    return [
        C("root", "gdm-stage-grid", {"layout": "hero", "children": {"explicitList": ["main"]}}),
        C("main", "gdm-container", {"direction": "column", "justify": "center", "align": "center",
                                    "width": "100%", "height": "100%", "grow": 1, "gap": "14px",
                                    "padding": "60px",
                                    "children": {"explicitList": ["tr_title", "tr_sub"]}}),
        C("tr_title", "gdm-text", {"content": "ORDER UP.", "size": "120px",
                                   "color": "white", "font": "mono", "weight": "900",
                                   "letterSpacing": "0.08em", "glitch": True}),
        C("tr_sub",   "gdm-text", {"content": "kitchen → table.",
                                   "size": "26px", "color": "rgba(0,255,136,0.65)",
                                   "font": "mono", "letterSpacing": "0.22em",
                                   "uppercase": True, "typeOn": True}),
    ]


def signoff_surface():
    """Three-line restaurant metaphor + GOOGLE MEET × A2UI hero callout +
    chef-at-the-table matrix typed beat + tagline."""
    return [
        C("root", "gdm-stage-grid", {"layout": "hero", "children": {"explicitList": ["main"]}}),
        C("main", "gdm-container", {"direction": "column", "justify": "center", "align": "center",
                                    "width": "100%", "height": "100%", "grow": 1, "gap": "18px",
                                    "padding": "60px",
                                    "children": {"explicitList": ["s1", "s2", "s3", "ext_group"]}}),
        C("s1", "gdm-text", {"content": "THE RESTAURANT.", "size": "60px", "color": "white",
                             "font": "mono", "weight": "900", "letterSpacing": "0.06em", "glitch": True}),
        C("s2", "gdm-text", {"content": "THE MENU.", "size": "60px", "color": PHOSPHOR,
                             "font": "mono", "weight": "900", "letterSpacing": "0.06em", "glitch": True}),
        C("s3", "gdm-text", {"content": "THE INGREDIENTS.", "size": "60px", "color": "#00f2ff",
                             "font": "mono", "weight": "900", "letterSpacing": "0.06em", "glitch": True}),
        C("ext_group", "gdm-container", {"direction": "column", "justify": "center", "align": "center",
                                         "gap": "14px", "margin": "44px 0 0 0",
                                         "reveal": "fade-up", "revealDelay": 0.9,
                                         "children": {"explicitList": ["ext_brands", "ext_badge",
                                                                       "ext_chef_group", "ext_tag"]}}),
        C("ext_brands", "gdm-container", {"direction": "row", "align": "center", "justify": "center",
                                          "gap": "28px",
                                          "children": {"explicitList": ["ext_meet", "ext_x", "ext_a2ui"]}}),
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
        C("ext_chef_group", "gdm-container", {"direction": "column", "align": "center",
                                              "gap": "10px", "margin": "28px 0 0 0",
                                              "children": {"explicitList": ["ext_chef", "ext_chef_sub"]}}),
        C("ext_chef",   "gdm-text", {"content": "THE CHEF IS AT THE TABLE.",
                                     "size": "60px", "color": PHOSPHOR, "font": "mono",
                                     "weight": "900", "letterSpacing": "0.06em", "typeOn": True}),
        C("ext_chef_sub", "gdm-text", {"content": "follow the rabbit.",
                                       "size": "22px", "color": "rgba(0,255,136,0.5)",
                                       "font": "mono", "letterSpacing": "0.22em", "typeOn": True}),
        C("ext_tag",    "gdm-text",  {"content": "infinite possibilities.",
                                      "size": "28px", "color": "rgba(255,255,255,0.7)",
                                      "font": "mono", "letterSpacing": "0.18em",
                                      "uppercase": True, "typeOn": True}),
    ]


async def _render(c, H, components, root="root"):
    await c.post(f"{API}/api/render-stage/{SPACE}", headers=H, json={
        "surfaceUpdate": {"components": components},
        "root": root,
    })


async def main():
    H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=20) as c:
        # Title
        await c.post(f"{API}/api/render-stage-clear/{SPACE}", headers=H, json={})
        await asyncio.sleep(0.25)
        await _render(c, H, title_surface())
        await asyncio.sleep(5.5)

        # Pass 1 — SHOW
        total = len(PRIMITIVES)
        for step, (prim_id, prim_el, prim_props, labels) in enumerate(PRIMITIVES, start=1):
            await c.post(f"{API}/api/render-stage-clear/{SPACE}", headers=H, json={})
            await asyncio.sleep(0.25)
            await _render(c, H, primitive_surface(prim_id, prim_el, prim_props, labels,
                                                  step=step, total=total))
            await asyncio.sleep(2.6)

        # ORDER UP transition
        await c.post(f"{API}/api/render-stage-clear/{SPACE}", headers=H, json={})
        await asyncio.sleep(0.25)
        await _render(c, H, transition_surface())
        await asyncio.sleep(1.6)

        # Pass 2 — PLACE
        await c.post(f"{API}/api/render-stage-clear/{SPACE}", headers=H, json={})
        await asyncio.sleep(0.25)
        await _render(c, H, assembled_surface())
        await asyncio.sleep(5.0)

        # Pass 3 — BREATHE
        for tick in range(7):
            await _render(c, H, breathe_partial(tick))
            await asyncio.sleep(1.0)

        # Sign-off
        await c.post(f"{API}/api/render-stage-clear/{SPACE}", headers=H, json={})
        await asyncio.sleep(0.25)
        await _render(c, H, signoff_surface())
        await asyncio.sleep(3.5)


if __name__ == "__main__":
    asyncio.run(main())
```

### 5.4 The open_stage.sh helper

```bash
#!/usr/bin/env bash
# Mint a stage ticket against the local backend and open the listener URL in a browser.
# Usage: ./open_stage.sh [space]   (default space = "default")
set -euo pipefail

SPACE="${1:-default}"
API="${CONCIERGE_API_URL:-http://127.0.0.1:8085}"
KEY="${STAGE_API_KEY:-meet-live_STAGE_SECURE_v1_zG9fN8qL7vP2mX6tY9wK4jC5bS8xQ7hZ3uW0rA}"

RESP=$(curl -fsS -H "Authorization: Bearer $KEY" "$API/api/stage-ticket/$SPACE")
URL=$(printf '%s' "$RESP" | python3 -c 'import json,sys; print(json.load(sys.stdin)["stage_url"])')

echo "Stage URL: $URL"

if   command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1 &
elif command -v open     >/dev/null 2>&1; then open "$URL" >/dev/null 2>&1 &
else echo "(no xdg-open/open found — copy the URL above into a browser)"
fi
```

### 5.5 A2UI engine — `internal/a2ui/engine.ts` (high-level)

The engine is framework-agnostic. Key behaviour:

- `handleMessage(msg)` consumes A2UI protocol messages: `surfaceUpdate`, `dataModelUpdate`, `beginRendering`, `deleteSurface`
- `componentBuffer` is a Map keyed by component id; surfaceUpdate calls `.set()` on each — buffered components persist across partial updates
- `_lastUpdatedIds` tracks which ids were in the LATEST surfaceUpdate so the renderer can mark components as `_fresh: true|false`
- `compile(rootId)` walks the tree from root via `children.explicitList` or `child`; emits a flat list of components with element name, props, and `_fresh` flag
- **Overlay scan:** after the main tree, the compile function scans for buffered components of overlay types (`gdm-captions`, `gdm-diagram-view`, `gdm-html-panel`, `gdm-market-ticker`, etc.) and emits them as top-level overlays even if not in the main tree
- `main_stage.ts` is the renderer — diffs the flat component list against existing DOM, creates/reuses elements, applies props (only when `_fresh`), establishes parent/child via `slot=panel-N` for stage-grid children

### 5.6 Server endpoints (in `main.py`)

Key endpoints used by demo scripts and the agent:

- `GET /api/stage-ticket/{space_id}` — mints a 30-minute auth ticket. Returns `{ ticket, stage_url }`. Auth via `STAGE_API_KEY` bearer.
- `POST /api/render-stage/{space_id}` — emit A2UI surfaceUpdate. Body: `{ surfaceUpdate: {...}, root: "..." }`. Auth via STAGE_API_KEY or OAuth.
- `POST /api/render-stage-clear/{space_id}` — broadcast deleteSurface (clears the engine's buffer).
- `GET /main_stage.html` — serves the audience stage page from `dist/`.
- `WebSocket /ws` — main Meet add-on connection (OAuth).
- `WebSocket /ws/stage` — stage listener connection (ticket auth).

---

## 6. Memory entries saved (project-level memory)

Located at `/home/curtis/.claude/projects/-home-curtis-gemini-addons-meet-live-concierge/memory/`:

1. **`a2ui-stage-conversion.md`** — plan/status for making the main stage agent-driveable via A2UI
2. **`a2ui-first-class-components.md`** — user wants stage features as catalogue `gdm-*` components via render_stage, not side channels
3. **`a2ui-catalog-descriptor.md`** — CATALOG in a2ui_catalog.py is source of truth; validation is warn-don't-block
4. **`a2ui-primitives-and-devloop.md`** — composable atoms/molecules + headless stage dev workflow
5. **`investment-substrates-not-compositions.md`** — north-star scoping principle (see §3.1)
6. **`google-meet-studio-three-modes.md`** — product positioning + three modes (see §3.2)

`MEMORY.md` indexes all of these.

---

## 7. Reference docs in repo

- **`A2UI_WEBMCP_FIT.md`** — full analysis of how A2UI and WebMCP fit together, including the honest "reality check" section about WebMCP's current redundancy for this project (see §3.4)
- **`A2UI_STAGE_PLAN.md`** — original plan for the stage conversion
- **`A2UI_PRIMITIVES_PLAN.md`** — composable primitives layer plan (catalogue conventions, atoms vs molecules tiering, add-an-atom checklist)
- **`HANDOVER-2026-05-23.md`** — earlier handover doc
- **`HANDOVER-3D-CATALOGUE.md`** — 3D catalogue handover
- **`GEMINI-3D-KICKOFF.md`** — 3D engine kickoff notes
- **`SKILL.md`** — meet-addon-builder skill description
- **`CLAUDE.md`** at user level + project level — instructions for Claude

---

## 8. Open threads — where the conversation paused

We ended on **the authoring story for Mode C playbooks** (§4.3). The architecture (§4.1) and the four build pieces (§4.2) are designed. The authoring layer is partially designed but needs more shape before building. Specifically:

1. **Should authoring v0 be markdown + agent-assist (skipping templates initially), or templates-first?** Templates feel like the substrate move; markdown feels like the user-onboarding move. Both work; ordering matters for what the first demo looks like.

2. **What's the data-binding API shape?** YAML data sources are sketched (`source: bigquery`, `source: yahoo_finance`) but the actual fetch / cache / refresh / auth story isn't designed.

3. **Agent prompt structure** — sketched (§4.3.5) but not tested. Need to confirm that with a real template catalogue + brief, Gemini / Claude reliably emit well-formed playbooks.

4. **Presenter URL surface** — designed conceptually (§4.1) but not implemented. Could be the v0 proof-of-concept since it doesn't need templates yet.

5. **The 1-hour proof of concept** suggested at the end of §4: add `gdm-button` atom + `/api/playbook/fire` endpoint, hardcode a button on the audience stage that fires the next slide. Validates the architecture before investing in the presenter URL.

---

## 9. How to pick up the conversation

If you're an LLM picking this up in another interface, the natural next moves are:

**Option A — Build the Mode C proof of concept** (~3-4 hours)
1. Add `gdm-button` atom to `internal/components/gdm_stage_button.ts`
2. Add `/api/playbook/fire/{space}/{slide_id}` to `main.py`
3. Write a 5-slide playbook in `playbooks/demo.py`
4. Hardcode a button on the audience stage that fires the next slide
5. Test end-to-end

**Option B — Design the authoring story properly** (~1 hour of conversation)
Pick up at §4.3 / §8.1 and §8.2. Resolve the markdown-vs-templates ordering question. Sketch the data-binding API in detail. Pick a single first data source (probably YAML file → BigQuery later).

**Option C — Iterate on the primitives demo** (~30 min)
The demo currently runs end-to-end. Polish opportunities: pacing tweaks (currently ~38s total), the `INGREDIENT N OF 7` banner formatting, the `EXPLAIN_EVERY` rhythm for the ATC act in render_showreel, etc. Low-risk, high-iteration.

**Option D — Strategic positioning**
Draft the "Google Meet Studio" rename properly: README, project description, a one-paragraph positioning statement, a tagline. This was started but not completed. Builds on §3.2 three-modes framing.

**Option E — A2UI × WebMCP exploration**
If the agentic ecosystem matures faster than expected, build out the WebMCP exposure layer (see `A2UI_WEBMCP_FIT.md` for the design). Mode C action buttons could be the first WebMCP tool surface.

---

## 10. Personal context the user mentioned

- **Doesn't work for Google.** Strategic implication: stay clear of official Google brand colours and logos for "GOOGLE MEET" wordmark (current white + phosphor styling is the right call — clearly editorial, no implied endorsement).
- **Working in IT.** Senior, building this with an LLM at 11pm. The conversation tone is collaborative-strategic, not basic onboarding.
- **Wants to share the journey** publicly. The three-chapter framing (§3.2) was developed for this purpose.
- **The current build was an evening's reflective work** — strategic refinement, not raw building. The user's prior context (~25 messages) was mostly bug-fixing and visual polish on the primitives demo and showreel.

---

## 11. The final visual the user just saw

The primitives showcase ends on this sign-off (~5 lines on stage):

```
THE RESTAURANT.            (60px, white, glitch)
THE MENU.                  (60px, phosphor, glitch)
THE INGREDIENTS.           (60px, cyan, glitch)

  GOOGLE MEET × A2UI       (64px brands, white + phosphor, both glitch)
[FULLY EXTENSIBLE ...]     (badge, danger pulse)

THE CHEF IS AT THE TABLE.  (60px phosphor, typeOn — matrix style)
follow the rabbit.         (22px phosphor mono, typeOn)
infinite possibilities.    (28px white mono, typeOn)
```

The "THE CHEF IS AT THE TABLE." line is the metaphor's payoff — it captures the unique meeting-shaped property A2UI exploits (the agent is *in the room*, not in the kitchen). The "follow the rabbit." callback is a Matrix Easter egg the user requested.

---

## 12. POST-HANDOVER UPDATE — Mode C PoC APPLIED + Round 2 (YAML + templates) APPLIED

_Updated 2026-05-29. Round 1 (audience-clickable deck PoC) and Round 2 (YAML + template substrate) both applied and end-to-end verified. The kitchen now has a menu: slides are authored in YAML, compiled through templates, served via the existing fire endpoint. Five templates ship — `title`, `hero_stat`, `split_with_action`, `list_5`, `signoff` — exercised end-to-end by `playbooks/kickoff.yaml`._

### 12.1 What happened

Gemini 3.5 Pro was given the design from §4 and produced:
- A `gdm-button` Lit element
- A FastAPI fire endpoint
- A playbook manager + 3-slide demo playbook

That work was then reviewed by Claude (Opus 4.7) and corrected for:

| Bug / divergence | Fix |
|---|---|
| **Critical: no `beginRendering` broadcast** — endpoint only sent `surfaceUpdate`. Engine buffers but never repaints. | Added second broadcast for `beginRendering`. |
| **Critical: wrong broadcast envelope** — bare payload instead of `{"type": "...", ...}` envelope. | Wrapped payloads correctly to match `broadcast_to_stage` contract. |
| **`gdm-button` was a URL launcher** — Gem built `window.open(targetUrl, '_blank')`, not the action-trigger Mode C needs. | Unified into one atom with `action: {type:'link'\|'fire'\|'emit'}` discriminated union. Same primitive serves audience-stage link buttons AND presenter-URL fire buttons (substrate principle). |
| **Hardcoded `http://127.0.0.1:8085`** URLs in playbook | Relative URLs (`/api/...`) — works on localhost AND Cloud Run without code change. |
| **`type:"ghost"` badge variant likely doesn't exist** | Replaced with `type:"info" + outline:true`. |
| **`Slide.tick_loop`** never populated, calling convention split | Unified: `builder(space_id, tick)` for both initial render and tick updates, matches `render_showreel.py`. |
| **Conceptual: buttons on audience stage ≠ Mode C** | Flagged clearly. This is **PoC validating round-trip**, NOT Mode C v0 (which needs a separate /presenter URL). |

### 12.2 Files now in the project tree (applied)

| File | Origin | Purpose |
|------|--------|---------|
| `internal/components/gdm_stage_button.ts` | **MERGED** (existing + staged) | Unified gdm-button: 4 action modes (link/fire/emit/agent). Existing API preserved. |
| `app/a2ui_catalog.py` (gdm-button entry) | Updated declaration | 6 props → 12 props. `label`/`actionId` no longer required (back-compat via fallback). |
| `playbooks/manager.py` | NEW | `PlaybookManager` singleton + `Slide` NamedTuple |
| `playbooks/__init__.py` | NEW | Registers playbooks at import time |
| `playbooks/demo_poc.py` | NEW | 3-slide PoC: intro → asymmetrical split → wrap |
| `main.py` (bottom, ~lines 2485-2640) | APPENDED | `/api/playbook/fire/...` + `/api/playbook/list/...` endpoints + tick-loop manager |
| `main.py` (very last line) | MOVED | `app.mount("/", StaticFiles(...))` relocated to end-of-file. **This was the line that broke 405. Don't move it back up.** |

The original `staging/` directory remains as the historical artifact / handover reference. It's not loaded by anything.

### 12.3 Apply sequence

1. Copy `staging/gdm_stage_button.ts` → `internal/components/gdm_stage_button.ts`
2. `mkdir playbooks/`
3. Copy `staging/playbooks_manager.py` → `playbooks/manager.py`
4. Copy `staging/playbooks_init.py` → `playbooks/__init__.py`
5. Copy `staging/playbooks_demo_poc.py` → `playbooks/demo_poc.py`
6. Append contents of `staging/main_py_fire_endpoint.py` to the bottom of `main.py`
7. `npm run build` (new TS atom)
8. Restart `uvicorn` (main.py changed)
9. Hard-refresh stage tab in browser

### 12.4 Test sequence

```bash
# In one terminal: backend
export GEMINI_PROJECT=centered-planet-497209-r5
uvicorn main:app --port 8085 --reload

# In another: open audience stage in browser
./open_stage.sh default

# From a third terminal: fire slide 1 (kicks off the PoC)
curl -X POST http://127.0.0.1:8085/api/playbook/fire/demo_poc/slide_1_intro/default

# Watch the audience stage:
#   - Slide 1 appears with "Begin Briefing" button
#   - Click "Begin Briefing" in the browser → slide 2 (asymmetrical split) loads
#   - Click "Commit and Wrap Up" → slide 3 (sign-off) loads
# Each click is a fetch to /api/playbook/fire/... → server renders next slide.
```

### 12.5 What's still NOT done after this PoC lands

- **Mode C v0 proper** — buttons on a separate `/presenter/{space}` URL the audience doesn't see. ~2 hours more on top.
- **Authentication** — fire endpoint is unauthed. Localhost OK; flag before deploy.
- **Tick-driven slides** — infrastructure is in place (the endpoint runs `slide.builder(space_id, tick)` on a loop for `ticks=True` slides) but no slide in the PoC exercises it. Add one to validate.
- **Template library** — meetstudio.md §4.3 sketched the `TEMPLATES` dict mapping (title, hero_stat, market, etc.) to parameterised compositions. The PoC slides hand-build their layouts instead. Promoting to templates is the next substrate-layer move once the round-trip is proven.
- **Authoring story** — markdown/YAML loader and agent-assisted authoring still untouched.

### 12.6 Application diary — what actually went wrong during apply

Three bugs surfaced during the apply that the staging review didn't catch. All fixed; documented here so future-you (or another LLM) doesn't re-encounter them.

#### Bug 1: `gdm-button` already existed — staged version would have overwritten three working usages

`internal/components/gdm_stage_button.ts` was already in the project (created 2026-05-27) with API `{label, actionId, payload, icon, type, disabled}`, used by:
- `demo_a2ui_composable_market.py` (3 buttons)
- `main_stage.ts:446` (event listener: `gdm-button-click` → `sendAction()`)
- `app/a2ui_catalog.py:293` (catalogue declaration)
- `tests/test_a2ui_stage.py:578` (test)

Naive `cp` would have lost all four. Fix: **merge** instead of replace — discriminated `action` union extended to FOUR modes (added `agent` alongside `link`/`fire`/`emit`). Existing `actionId` shorthand now resolves to `agent` mode and dispatches the same `gdm-button-click` event the old code emitted — back-compat preserved bit-for-bit. This was the substrate principle's first real load-bearing test on this project.

#### Bug 2: POST `/api/playbook/fire/...` returned 405 even after restart

The fire endpoint was correctly registered (`openapi.json` showed it as POST), but `curl -X POST` returned **405 Method Not Allowed**. Root cause: `app.mount("/", StaticFiles(directory="dist", html=True), name="static")` at the OLD line 2485 — registered BEFORE the appended playbook endpoints. A Starlette `Mount("/")` captures every URL under that prefix, and `StaticFiles` only serves GET/HEAD → POST to anything under `/` (including `/api/...`) returned 405 because the mount intercepted before FastAPI's route resolver got to the appended `@app.post` declarations.

Fix: moved the `app.mount(...)` call to the very end of `main.py`. All `@app.get`/`@app.post` declarations now register first; mount only catches unrouted GETs (its SPA-fallback role).

**This is the gotcha that would bite ANY future endpoints appended to `main.py`.** Added to §2.4 above.

#### Bug 3: Browser served `gdm-button-click` events with empty actionId after click

After fix #2 the server endpoint accepted POST cleanly, but clicks on the audience stage still didn't transition slides. Server log showed:
```
[a2ui_action] gdm-button-click in default: {'actionId': '', 'payload': ''}
```

That's the OLD button behaviour — dispatching `gdm-button-click` with empty fields because `actionId` was unset on the merged-button-as-fire-action playbook config. The browser was loading `main_stage-ox7AdY0o.js` from cache; `dist/` had `main_stage-DLh5Hh8z.js` (the merged build with `resolveAction`, `btn-success`, `pulse-active`, `size-hero` markers all present).

Fix: **hard refresh** (`Ctrl+Shift+R`). The browser then loaded the new bundle, the merged button's `_resolveAction()` returned the `fire` action, click did a `fetch('/api/playbook/fire/...')`, server fired the next slide, audience stage repainted.

### 12.7 If you're picking up in another LLM session

Read in this order:
1. `meetstudio.md` (this file) §§1-3 for project context
2. `meetstudio.md` §4 for the playbook design
3. `staging/README.md` for what's been staged and how to apply
4. Each staged file's `## TODO before apply` comment at the top

You should be able to apply the PoC without needing the prior conversation, decide whether to extend toward Mode C v0 next, or take a different fork.

---

## 13. Round 2 applied — YAML + templates substrate live

_2026-05-29 — second apply of the day. Five-template library + YAML loader + data-source resolver + async-builder support in the fire endpoint. End-to-end verified: `playbooks/kickoff.yaml` (5 slides, 5 templates) fires cleanly; sync `demo_poc.py` builder still works alongside async YAML builders (regression-safe via `inspect.iscoroutinefunction` dual-path)._

### 13.1 What's now in the tree

```
playbooks/
├── manager.py           (Round 1 — Slide NamedTuple + PlaybookManager singleton)
├── demo_poc.py          (Round 1 — 3-slide sync PoC)
├── data_sources.py      (Round 2 — NEW: per-source resolver + cache + refresh policies)
├── templates.py         (Round 2 — NEW: 5 templates + helpers, ~600 lines)
├── yaml_loader.py       (Round 2 — NEW: YAML → Slide registration via templates)
├── __init__.py          (Round 2 — REPLACED: auto-discovers *.yaml files)
└── kickoff.yaml         (Round 2 — NEW: 5-slide example, all 5 templates)

main.py — patched: import inspect; fire endpoint dual-paths sync vs async
                   builders; catch-all GET moved to end alongside StaticFiles mount
requirements.txt — appended pyyaml>=6.0
```

### 13.2 Apply diary — one bug, same shape as before

**The catch-all `@app.get("/{path:path}")` was at line 2471, declared BEFORE the list endpoint at line ~2625.** Same architectural class as the StaticFiles mount issue from Round 1 — a greedy catch-all declared first wins for any later-declared endpoint with a matching method (GET).

Symptom: `POST /api/playbook/fire/kickoff/intro/default` returned `{"status":"fired", ...components:6}` correctly (fire is POST; catch-all is GET; routing matched the correct POST handler). But `GET /api/playbook/list/kickoff` returned 404 — the catch-all matched first, saw the `api/` prefix, and explicitly `raise HTTPException(404)`. The actual `@app.get` list endpoint never got a chance to register a match.

Fix: moved the catch-all GET to the bottom of `main.py` (next to the StaticFiles mount). Now POST + GET API endpoints declared above both catch-alls get matched in order, and only truly unmatched GETs fall through to the SPA fallback.

§2.4 gotcha updated to cover both catch-all patterns as a single symmetric rule.

### 13.3 What this unlocks

Every new slide is a YAML config block — no Python:

```yaml
- id: q3_arr
  template: hero_stat
  badge: { text: "Q3 FINANCIALS", type: primary }
  label: "Annual Recurring Revenue"
  data:
    ARR: { source: literal, value: "$48.2M" }   # swap to bigquery later
  value: "{{ ARR }}"
  is_up: true
  next_action: { text: "Next", fires: specs }
```

Templates are the only place layout knowledge lives. Adding a new template = one function + one line in the `TEMPLATES` dict. Adding a new data source = one async fetcher + one `elif` in `data_sources.py::resolve()`.

### 13.4 Next-step decision — substrate vs composition

| Move | Type | Recommended |
|---|---|---|
| **Wire `rest` source** in `data_sources.py` → first real live-data slide | **Substrate** — every future playbook can use it | ✓ first |
| **Build `/presenter/{space}` URL** → buttons on a separate page (proper Mode C) | **Composition** — uses primitives already shipped | second |

Substrate-first rationale in chat transcript end-of-session — `rest` is the bedrock for every API-backed source (GitHub, weather, OpenSky, internal ops metrics). httpx already imported. ~30 lines + cache. After that, BigQuery is ~30 more lines that drops into the same shape. Then yahoo_finance. Each source = one fetcher.

### 13.5 The architectural payoff in one sentence

> **One YAML file → 5 declarative configs → 5 template functions (substrate) → ~50 atom invocations (catalogue) → 1 protocol (A2UI) → live in Meet. No new Python per slide. The kitchen runs the same.**

---

## 14. The killer loop — doc-to-deck via Drive auth

_2026-05-29 — strategic framing that pulls everything shipped to date into one product story. Also saved as a Claude project memory (`doc-to-deck-killer-loop.md`) so future sessions load it automatically. Mirrored here so any LLM (Gem, ChatGPT, fresh Claude) opening this doc gets the same north star._

### 14.1 The loop

```
1. AGENT-AS-USER reads the doc       (Drive readonly scope on existing OAuth)
2. AGENT-AS-USER reads the data       (BigQuery, Sheets, Calendar — same auth)
3. Both flow into the same YAML       (the substrate doesn't care where bytes came from)
4. Same playbook fires on the stage   (live, voice-controlled, data-refreshed)
```

Closing this loop is the next strategic phase. Every piece either exists today or is one short bridge away from existing.

### 14.2 The pitch sentence when this lands

> ***"Paste a Google Doc link. Click Present. Your doc becomes a live, voice-controllable, real-time-data-aware presentation in Google Meet — composed by the agent, plated from the catalogue, served at the table."***

That sentence sells itself.

### 14.3 Pitch clauses → substrate state (every line maps to shipped or one-bridge code)

| Clause | Substrate state |
|---|---|
| *"Paste a Google Doc link"* | Drive readonly scope added to the existing Meet add-on OAuth — same flow, one extra scope, no new infra |
| *"Click Present"* | Mode C presenter URL (§4 + §12.5) — ~2hr build on top of shipped playbook fire endpoint |
| *"Live, voice-controllable"* | Gemini Live + side panel + main_stage WS — shipped |
| *"Real-time-data-aware"* | `playbooks/data_sources.py` resolver + new `rest`/`bigquery` fetchers — ~30 lines each |
| *"Composed by the agent"* | Doc → YAML via Gemini structured generation; the templates' prop schema is the agent's constraint set |
| *"Plated from the catalogue"* | Five templates in `playbooks/templates.py` (§13.1) + extensible by one function each |
| *"Served at the table"* | Restaurant metaphor from `demo_a2ui_primitives.py` sign-off (§11) |

### 14.4 Why the auth angle is the multiplier

OAuth-as-user is doing **two jobs at once** here:

1. **Reading the user's docs** as input to the deck (Drive readonly)
2. **Reading the user's data** as live content inside the deck (BigQuery, Sheets, Calendar)

Both run on the same Workspace OAuth flow with the user's existing permissions. The Workspace Agent Engine ships the write direction today (Doc/Sheet creation, Drive search). The read direction is the inverse — same auth, same scopes, additive change.

**Consequence:** data binding for enterprises becomes real on day one without enterprise SSO setup, custom service accounts, or new auth ceremony. The user already authenticated for Workspace; the agent inherits everything they can see.

### 14.5 Competitive framing — same input, different output class

Google Slides + AI, Notion AI, PowerPoint Copilot all do auto-generate-slides-from-doc.

```
Their output:                                 Our output:
─────────────────────────────────────         ──────────────────────────────────────────
one-shot static deck                          live agent-driven stage
user clicks through manually                  agent (or voice trigger) drives transitions
content frozen at export time                 data refreshes per slide's policy
no realtime data                              real-time BigQuery / REST / Sheets binding
post-meeting cleanup                          zero — the doc IS the deck, regenerable
```

Same input (a doc). Fundamentally different output class. That's the wedge that makes Google Meet Studio not a thin wrapper but a different product category.

### 14.6 Scoping principle this anchors

When evaluating any new feature, ask: *"does this advance the doc-to-deck loop?"*

The five tracks that do:

1. **Drive readonly auth** — direct enabler; top priority once Mode C v0 ships
2. **New data sources** in `data_sources.py` — multiplies what the agent can pull from
3. **New templates** in `templates.py` — increases the shapes the doc can resolve to
4. **Authoring UI / agent prompt** — improves doc → YAML conversion fidelity
5. **Capture / record scripts** — turn each playbook into a shareable gif/mp4 (content multiplier on top of the loop; see also §13 capture notes)

Anything that doesn't advance one of those five tracks is a composition, not a substrate move, and should be deferred unless it's directly user-facing for a near-term demo.

### 14.7 Content multiplier on top of the loop

Once a YAML playbook exists for a given topic, recording it produces a shareable artefact:

```
WRITE                 CONVERT                  RECORD                SHARE
─────                 ───────                  ──────                ─────
article.md       →    article.yaml        →    article.gif    →     LinkedIn /
(your normal          (agent or you,           (capture +           blog / docs /
 writing flow)         5 min)                   headless run)        anywhere
```

Every piece exists in repo today:
- `WRITE` — any markdown / Google Doc
- `CONVERT` — see `playbooks/article.yaml` (proof-of-conversion done 2026-05-29)
- `RECORD` — `capture_stage_screenshots.py`, `capture_atoms.py`, `record_stage.py` already shipped
- `SHARE` — outputs anywhere a gif / mp4 embeds

**Distribution unit shifts from *article* to *article + gif*.** Or three pairs from one YAML: 8s LinkedIn cut, 30s blog cut, full doc cut with data refreshes ticking. Same substrate, different render scripts.

---

---

## 15. Round 3 applied — REST data source + market_ticker template (live data substrate)

_2026-05-29 — third apply of the day. Closes the gap between "data binding promised in YAML" and "live numbers shimmering on the stage." After this round, every YAML playbook can drop in a REST-fed slide refreshed at any cadence — partially realising the §14 killer-loop pitch._

### 15.1 What landed

```
playbooks/
├── data_sources.py    Round 3 — REWRITTEN: real _fetch_rest (was stubbed),
│                                 shared httpx.AsyncClient hot-pool,
│                                 _json_path/_apply_map/_interpolate_url
│                                 helpers, multi-tenant cache key
├── yaml_loader.py     Round 3 — small delta: slide_cfg threaded into ctx
│                                 so REST resolver can interpolate {{key}}
├── templates.py       Round 3 — added market_ticker_template (~160 lines).
│                                 6 templates total now.
└── market.yaml        Round 3 — NEW standalone test playbook (3 slides:
                                 intro → live ticker → signoff)
```

### 15.2 Sparring decisions locked in code

Architectural calls debated with another LLM (Gem) and committed. Details in `staging/README.md` Round 3 section:

| Decision | Locked-in shape |
|---|---|
| JSONPath grammar | `.foo / .foo.bar / .foo[] / .foo[N] / .foo[].bar`. No filter predicates, wildcards, slices, or recursive descent — keep DSL escalation closed. |
| httpx client | Module-level shared `_SHARED_CLIENT` (hot connection pool); per-request timeout via kwargs override. Eliminates ~300ms DNS+TLS jitter on 2s polling. |
| Data normalization | `_apply_map(data, mapping)` does flat key-projection only. Computed expressions (`is_up: change >= 0`) explicitly out — derivation belongs in templates. |
| URL templating | `{{key}}` from sibling slide_cfg keys; lists join CSV. Does NOT read from `data:` (other resolved values) — no source-to-source DAG in v0. |
| Retry policy | None inline. Single failure → fallback → next tick fetches fresh. Tick loop IS the retry. Prevents thread-blocking cascades. |
| Cache key | `(space_id, slide_id, data_key)` — multi-tenant isolation. Critical: prevents data leak across Meet rooms. |

### 15.3 §14 pitch sentence — clause-by-clause state after Round 3

| Pitch clause | State |
|---|---|
| *"Paste a Google Doc link"* | Future round (Drive readonly scope) |
| *"Click Present"* | Future round (Mode C presenter URL) |
| *"Live, voice-controllable"* | ✓ shipped earlier (Gemini Live + stage WS) |
| ***"Real-time-data-aware"*** | ✓ **shipped 2026-05-29 (Round 3)** — every audience watching a slide with `refresh: Ns` sees values change live |
| *"Composed by the agent"* | Future round (doc → YAML via Gemini structured generation) |
| *"Plated from the catalogue"* | ✓ shipped earlier (6 templates now) |
| *"Served at the table"* | ✓ shipped earlier (restaurant metaphor in sign-off) |

**Four of seven clauses now have substrate behind them.** Remaining three (Drive auth, presenter URL, agent prompt) are the next strategic phase.

### 15.4 Verification at apply time

```
71 components rendered for market/pulse  (12 rows × 5 atoms + 7 chrome + 3 header + 1 button)
3 of 3 existing playbooks regression-clean (demo_poc, kickoff, article)
4 of 4 playbooks discoverable via /api/playbook/list
2s tick loop confirmed via ticks_active:true response and uvicorn logs
```

### 15.5 What's NOT in scope (sparred + closed, do not reopen without reason)

- `yahoo_finance` source as a separate verb (the generic `rest` covers it)
- `bigquery` source (still stubbed; future round)
- Filter predicates / wildcards / slices in JSONPath
- Computed expressions in `map:`
- Cross-source dependencies (Source B reads Source A)
- Retry-with-backoff inside `_fetch_rest`
- Cross-room cache sharing for paid-API quota deduplication (planned for v1 — keyed by hash of `(url, json_path, map)`)
- Stale-data visual indicator on fallback rows

---

---

## 16. v0.8 MILESTONE — checkpoint before A2UI 0.9 migration

_2026-05-29 evening. Committed and tagged as `v0.8-final`; branch
`checkpoint/a2ui-0.8` preserves this exact state. Reachable any time via
`git checkout checkpoint/a2ui-0.8` if the v0.9 migration regresses
something._

### 16.1 What's locked in at this milestone

```
SUBSTRATE LAYERS                                STATE
─────────────────────────────────────────────────────────────
catalogue (gdm-* components, atoms)             ✓ shipped
A2UI engine wire protocol (v0.8 spec)           ✓ shipped
playbook PoC (Round 1) — Python builders        ✓ shipped + applied
YAML + 5 templates (Round 2) — substrate        ✓ shipped + applied
REST source + market_ticker (Round 3) — live    ✓ shipped + applied
4 playbooks registered:                         demo_poc, kickoff,
                                                article, market (+
                                                stocks queued behind
                                                TWELVE_DATA_API_KEY)
restaurant metaphor + chef-at-the-table         ✓ in production demos
3 strategic memories anchoring scoping          ✓ saved
keep-meetstudio-md-current behavioral rule      ✓ saved
```

Everything in §13, §14, §15 is intact at this checkpoint.

### 16.2 Why the checkpoint matters now

A2UI v0.9 dropped (https://a2ui.org/specification/v0.9-evolution-guide/).
Wire-format breaking changes:
- `surfaceUpdate` → `updateComponents`
- `beginRendering` → `createSurface`
- `dataModelUpdate` → `updateDataModel`
- Component encoding flips from `{"component": {"gdm-text": {...props}}}` to
  flat `{"component": "gdm-text", ...props}`
- Data model encoding flips from typed array-of-pairs to plain JSON object

The catalogue (gdm-* names) and the substrate above it (templates, YAML,
playbook system, agent metaphors) are **unchanged by v0.9** — catalogs are
explicitly "swappable" in the new spec. Only the wire envelope changes.

Migration is mechanical (~5-7 focused hours) but until complete, NOTHING
renders. A checkpoint at v0.8-final means we can branch off, migrate,
test against all 5 playbooks, and merge only when stable. Worst case:
abandon the migration branch entirely and `git checkout checkpoint/a2ui-0.8`
to recover the last-known-good state.

### 16.3 Weekend publication plan (locked 2026-05-29)

Goal: publish a four-artefact release by Sunday night that positions this
project as the first public reference implementation of A2UI 0.9 outside
Google. First-mover window is open for maybe 1-2 weeks before someone else
stakes it.

```
1. WIRE MIGRATION (Fri evening → Sat midday, ~6h)
   - Branch off: feature/a2ui-0.9-migration
   - Rename messages in engine.ts, main.py, main_stage.ts
   - Flip component encoding in C() helper (templates inherit)
   - Flip data model encoding
   - Update agent system prompt to v0.9 message names
   - Add ValidationFailed support
   - Regression test against demo_poc, kickoff, article, market, stocks
   - Merge to main / feature branch only when all 5 green

2. PUBLIC GDM-* CATALOG (Sat afternoon, ~2h)
   - Versioned JSON document at /catalog/gdm-v0.1.json in this repo
   - Conformant to v0.9 swappable-catalog format
   - Lists all gdm-* components + props + descriptions
   - Stable URL = positioning play for other A2UI builders

3. BLOG POST (Sat afternoon → Sat evening, ~3h)
   - ~2000 words
   - Title (working): "Substrate, not slides: building Google Meet Studio on A2UI 0.9"
   - Threads: chef-at-the-table metaphor, substrate principle, working demo
   - Embeds the demo gif (#4)
   - References the public repo (next)
   - "What's next" closes: doc-to-deck killer loop + presenter URL

4. DEMO GIF / SHORT VIDEO (Sat morning, ~2h)
   - Headless capture of kickoff.yaml or article.yaml via existing
     capture_stage_screenshots.py
   - 15-30s — title → hero stat → split → list → signoff
   - mp4 + gif variants for embed everywhere

5. PUBLIC REPO (Sun morning, ~2h)
   - Clean fork of meet-live-concierge (sanitize .env, secrets,
     unrelated files like search_ha_entities.py / test_t212_direct.py)
   - README pitches the substrate principle + chef metaphor
   - Includes the v0.9-shaped /catalog/gdm-v0.1.json
   - Demo playbooks (kickoff, article) committed; market/stocks have
     placeholder API keys
   - MIT license
```

Items DEFERRED to subsequent posts (do NOT scope-creep into this weekend):
- Drive auth + doc-to-deck loop closure (§14 strategic frame)
- Mode C presenter URL build (Mode C v0 product UX)
- Agent-authored YAML from doc (the operationalisation of prompt-first)
- formatString migration (replacing custom _interpolate)
- BigQuery / Polygon data source wiring
- Comprehensive A2UI 0.8 → 0.9 migration guide for others (too ambitious;
  just demonstrate ours)

### 16.4 Recovery path if v0.9 migration fails

```bash
# At any point during the migration, instant recovery:
git checkout checkpoint/a2ui-0.8

# Or revert to this tag explicitly:
git reset --hard v0.8-final
```

The `checkpoint/a2ui-0.8` branch exists exactly so the migration is reversible.
If the weekend goes sideways, this version still works and is publishable
as-is (it's just v0.8-aligned instead of v0.9-aligned).

### 16.5 What gets carried forward unchanged into v0.9

| Layer | v0.9 impact |
|---|---|
| All YAML playbooks (kickoff.yaml, article.yaml, market.yaml, stocks.yaml) | None — YAML is above the wire format |
| All 6 templates (title, hero_stat, split_with_action, list_5, signoff, market_ticker) | None — templates emit through C() helper; helper does the migration |
| The catalogue itself (gdm-* component implementations) | None — Lit components don't care about wire format |
| Restaurant metaphor + chef-at-the-table + substrate principle | None — these are above the entire stack |
| All memories (8 entries) | None — they describe intent, not protocol |

The migration scope is narrowly the wire envelope. Everything above stays.

---

_End of handover. Pick up at §8 / §9 / §12 / §13 / §14 / §15 / §16 to continue._

_Next move: branch `feature/a2ui-0.9-migration` off `checkpoint/a2ui-0.8`, do the wire-format migration, regression-test, publish._
