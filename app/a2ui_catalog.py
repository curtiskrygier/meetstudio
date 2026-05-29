"""
A2UI Catalog — single source of truth.

Everything about the A2UI component contract is declared once in `CATALOG`
below and derived from there:

  * `A2UI_CATALOG`            — the frozenset of valid component names
  * `COMPONENT_SCHEMAS`       — Pydantic models for prop validation (strict comps)
  * `validate_a2ui_surface*`  — surface validation
  * `render_catalog_prompt()` — the catalogue prose injected into the system prompt
  * `render_mcp_component_summary()` — the supported-component blurb for the MCP tool

Validation follows the A2UI paradigm: the catalogue *name* is the hard contract
(an unknown component is a blocking ERROR, because the renderer genuinely cannot
draw it), but prop-level issues are WARNINGS, not errors — the A2UI client
renderer tolerates unknown/missing props, so the server must not be more brittle
than the client. Callers render the surface anyway on warnings and feed them back
to the agent as advisory text so it can self-correct.
"""
from dataclasses import dataclass, field
from typing import Optional, Union, List, Dict, Any
from collections import namedtuple
from pydantic import BaseModel, ConfigDict, ValidationError, create_model


# --- Descriptor model -------------------------------------------------------

@dataclass
class Prop:
    name: str
    type_label: Optional[str] = None   # prose type, e.g. "string"; None => freeform note line
    req: Optional[bool] = None          # True -> "required", False -> "optional", None -> omit marker
    note: str = ""
    pytype: Any = None                  # python type used for strict validation (defaults to str)
    doc: bool = True                    # include in the prompt prose


@dataclass
class Comp:
    group: str                          # "root" | "panel" | "overlay"
    desc: str
    props: List[Prop] = field(default_factory=list)
    strict: bool = False                # enforce extra="forbid" + typed props (else lenient, no warnings)
    props_label: str = "Props"
    in_prompt: bool = True              # include in the system-prompt catalogue prose


# Nested item schema reused by gdm-market-ticker rows.
class TickerItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str
    price: float
    changePercent: float
    isUp: bool
    label: Optional[str] = None


# A binding-aware union: A2UI props may carry a data-model binding ref like
# "{flights}" (a string) where an array/dict is otherwise expected. Such strings
# must not produce type warnings.
_FlightsType = Union[List[Any], Dict[str, Any], str]


# --- THE CATALOG (single source of truth) -----------------------------------
# Order within each group is the order rendered into the prompt prose.

CATALOG: "dict[str, Comp]" = {
    # 1. Root layout container
    "gdm-stage-grid": Comp(
        group="root", strict=True,
        desc="Layout engine container for main stage panels.",
        props=[
            Prop("layout", "string", None, 'Arrangement of panel(s). Options: `"single"`, `"split"`, `"grid"`, `"grid-3"`, `"presentation"`.', pytype=str),
            Prop("focusedPanel", "string", None, "ID of the component to focus/maximize.", pytype=str),
            Prop("children", doc=False, pytype=dict),
        ],
    ),

    # 2. Panel components (children of the layout grid)
    "gdm-image-panel": Comp(
        group="panel", desc="Renders a static or generated image.",
        props=[
            Prop("src", "string", True, "Absolute URL or asset path of the image."),
            Prop("label", "string", False, "Text caption/label."),
        ],
    ),
    "gdm-video-panel": Comp(
        group="panel", desc="Embeds and plays video content (e.g. YouTube or video streams).",
        props=[
            Prop("src", "string", True, "URL of the video embed source."),
            Prop("autoplay", "boolean", False, "Set to true to begin playback automatically."),
        ],
    ),
    "gdm-iframe-panel": Comp(
        group="panel", desc="Displays an iframe web browser.",
        props=[
            Prop("src", "string", True, "URL of the web page to load."),
        ],
    ),
    "gdm-diagram-view": Comp(
        group="panel", desc="Displays live, high-fidelity interactive D2 or SVG system architecture diagrams.",
        props=[
            Prop("diagId", "string", True, "Unique identifier for the diagram."),
            Prop("svg", "string", True, "Raw SVG markup or D2 rendering."),
            Prop("version", "integer", True, "Version counter."),
        ],
    ),
    "gdm-telemetry-dashboard": Comp(
        group="panel", desc="Renders tabbed metric views and interactive sparklines.",
        props_label="Props/Bindings",
        props=[
            Prop("metrics", "array of objects", None, "Metric telemetry objects with `label` (string) and `value` (string) fields."),
            Prop("chartData", "array of numbers", None, "Sparkline data values."),
            Prop("activeTabId", "string", None, "Active tab ID."),
            Prop("viewType", "string", False, 'One of `"cards"`, `"chart"`, or `"both"` (default).'),
        ],
    ),
    "gdm-radar-view": Comp(
        group="panel", strict=True,
        desc="Dynamic interactive radar plot mapping flight paths and telemetry.",
        props_label="Props/Bindings",
        props=[
            Prop("stretched", "boolean", None, "Stretched layout.", pytype=bool),
            Prop("zoom", "number", None, "Zoom level.", pytype=float),
            Prop("flights", "array of objects", None, "Flight coordinates and data.", pytype=_FlightsType),
            Prop("lockedCallsign", "string", None, "Locked focus flight callsign.", pytype=str),
        ],
    ),
    "gdm-notepad": Comp(
        group="panel", desc="Interactive shared notepad.",
        props=[
            Prop("content", "string", True, "Collaborative rich text/markdown notes."),
        ],
    ),
    "gdm-camera-panel": Comp(
        group="panel", desc="Displays a live camera / video feed frame.",
        props=[
            Prop("frame", "string", False, "Data URL or image URL of the current camera frame (rendered to fill the panel)."),
            Prop("src", "string", False, "Fallback poster/stream image URL used when `frame` is empty."),
            Prop("label", "string", False, 'Caption chip (e.g. `"🎥 Live Camera"`).'),
            Prop("mirrored", "boolean", False, "Horizontally flip the image for self-view (default `true`)."),
        ],
    ),
    "gdm-terminal-panel": Comp(
        group="panel", desc="A developer terminal window showing command output.",
        props=[
            Prop("content", "string", False, "Full terminal text, newline-separated (used when `lines` is empty)."),
            Prop("lines", "array of strings", False, "Explicit output lines (takes precedence over `content`)."),
            Prop("title", "string", False, 'Window title-bar text (default `"Terminal"`).'),
            Prop("cursor", "boolean", False, "Show a blinking block cursor after the last line (default `true`)."),
        ],
    ),
    "gdm-doc-panel": Comp(
        group="panel", desc="A document / file card with an optional call-to-action button.",
        props=[
            Prop("title", "string", False, 'Card heading (default `"Document Ready"`).'),
            Prop("body", "string", False, "Summary/description text (line breaks preserved)."),
            Prop("url", "string", False, "Link the button opens; the button is hidden when empty."),
            Prop("buttonLabel", "string", False, 'CTA button label (default `"Open Document"`).'),
            Prop("accent", "string", False, "Accent CSS color (default `#00f2ff`)."),
        ],
    ),
    "gdm-container": Comp(
        group="panel", strict=True,
        desc="A highly flexible layout container block supporting glassmorphism and nested compositions.",
        props=[
            Prop("direction", "string", False, 'Flexbox layout direction (`"row"` or `"column"`, default `"row"`).', pytype=str),
            Prop("justify", "string", False, 'Flexbox justify-content property (default `"flex-start"`).', pytype=str),
            Prop("align", "string", False, 'Flexbox align-items property (default `"stretch"`).', pytype=str),
            Prop("gap", "string", False, 'CSS spacing gap between nested children (e.g. `"12px"`).', pytype=str),
            Prop("padding", "string", False, 'CSS padding inside the container (e.g. `"16px"`).', pytype=str),
            Prop("background", "string", False, 'CSS background property.', pytype=str),
            Prop("border", "string", False, 'CSS border property.', pytype=str),
            Prop("borderRadius", "string", False, 'CSS border-radius (e.g. `"12px"`).', pytype=str),
            Prop("width", "string", False, 'CSS width property (default `"auto"`).', pytype=str),
            Prop("height", "string", False, 'CSS height property (default `"auto"`).', pytype=str),
            Prop("glass", "boolean", False, 'Set to true to enable premium translucent backdrops.', pytype=bool),
            Prop("scrollable", "boolean", False, 'Enables vertical/horizontal scrollbars for overflowing contents.', pytype=bool),
            Prop("grow", "number", False, 'Flexbox flex-grow factor.', pytype=float),
            Prop("shrink", "number", False, 'Flexbox flex-shrink factor.', pytype=float),
            Prop("margin", "string", False, 'CSS margin (e.g. `"8px"`).', pytype=str),
            Prop("reveal", "string", False, 'Entrance animation played once on mount: `"fade-up"`, `"scale-in"`, `"slide-left"`, `"slide-right"`, `"blur-in"`, `"flip"`.', pytype=str),
            Prop("revealDelay", "number", False, 'Seconds to delay the entrance — stagger across panels to choreograph a staged "set the stage" reveal.', pytype=float),
            Prop("children", doc=False, pytype=dict),
        ],
    ),
    "gdm-text": Comp(
        group="panel", strict=True,
        desc="A rich typography component supporting sizes, colors, pulsing glow and weights.",
        props=[
            Prop("content", "string", True, 'The raw text content.', pytype=str),
            Prop("size", "string", False, 'Font size or preset (`"h1"`, `"h2"`, `"h3"`, `"body"`, `"caption"`, or custom `"16px"`).', pytype=str),
            Prop("weight", "string", False, 'CSS font-weight or preset.', pytype=str),
            Prop("color", "string", False, 'Preset or custom CSS color (Presets: `"accent"`, `"white"`, `"success"`, `"warning"`, `"danger"`, `"mute"`).', pytype=str),
            Prop("align", "string", False, 'Text alignment (`"left"`, `"center"`, `"right"`).', pytype=str),
            Prop("font", "string", False, 'Font family selection (`"sans"`, `"mono"`, `"serif"`).', pytype=str),
            Prop("opacity", "number", False, 'Opacity scale factor (0.0 to 1.0).', pytype=float),
            Prop("letterSpacing", "string", False, 'CSS letter-spacing property.', pytype=str),
            Prop("uppercase", "boolean", False, 'Forces uppercase text transform.', pytype=bool),
            Prop("pulse", "boolean", False, 'Enables breathing glow pulsing animations.', pytype=bool),
            Prop("flip", "boolean", False, 'Animates each character with a flip when the content changes (for live values, clocks, prices).', pytype=bool),
        ],
    ),
    "gdm-grid": Comp(
        group="root", strict=False,
        desc="CSS-grid layout atom: arranges children in columns/rows. The structural partner to gdm-container.",
        props=[
            Prop("columns", "string", False, 'Grid columns: a number (→ equal columns) or a grid-template string (e.g. "2fr 1fr").', pytype=str),
            Prop("rows", "string", False, 'Grid rows: a number or a grid-template string.', pytype=str),
            Prop("gap", "string", False, 'Gap between cells (default "12px").', pytype=str),
            Prop("align", "string", False, 'align-items.', pytype=str),
            Prop("justify", "string", False, 'justify-items.', pytype=str),
            Prop("padding", "string", False, 'CSS padding.', pytype=str),
            Prop("width", "string", False, 'CSS width.', pytype=str),
            Prop("height", "string", False, 'CSS height.', pytype=str),
        ],
    ),
    "gdm-stat": Comp(
        group="panel", strict=False,
        desc="Generic metric atom: a label, a large value, and an optional coloured delta/change pill.",
        props=[
            Prop("label", "string", False, 'Small uppercase label above the value.', pytype=str),
            Prop("value", "string", True, 'The primary value to display.', pytype=str),
            Prop("unit", "string", False, 'Small unit suffix on the value.', pytype=str),
            Prop("delta", "string", False, 'Change figure shown in a caret pill (e.g. "+1.24%").', pytype=str),
            Prop("isUp", "boolean", False, 'Direction of the delta (green up / red down).', pytype=bool),
            Prop("accent", "string", False, 'Optional CSS colour tint for the value.', pytype=str),
            Prop("size", "string", False, 'Value size: "sm" | "md" | "lg".', pytype=str),
            Prop("align", "string", False, 'Alignment: "left" | "center" | "right".', pytype=str),
        ],
    ),
    "gdm-image": Comp(
        group="panel", strict=False,
        desc="Raw image atom (fit / radius / aspect-ratio). Lightweight sibling of gdm-image-panel.",
        props=[
            Prop("src", "string", True, 'Image URL or data URL.', pytype=str),
            Prop("alt", "string", False, 'Alt text.', pytype=str),
            Prop("fit", "string", False, 'object-fit ("cover" | "contain").', pytype=str),
            Prop("radius", "string", False, 'Border radius.', pytype=str),
            Prop("width", "string", False, 'CSS width.', pytype=str),
            Prop("height", "string", False, 'CSS height.', pytype=str),
            Prop("aspectRatio", "string", False, 'CSS aspect-ratio (e.g. "16/9").', pytype=str),
        ],
    ),
    "gdm-spacer": Comp(
        group="panel", strict=False,
        desc="Layout filler: grows to push siblings apart, or a fixed gap when sized.",
        props=[
            Prop("size", "string", False, 'Fixed size (e.g. "24px"); omit to grow and absorb free space.', pytype=str),
            Prop("axis", "string", False, '"horizontal" | "vertical" | "both".', pytype=str),
        ],
    ),
    "gdm-badge": Comp(
        group="panel", strict=True,
        desc="Status badge chip with dynamic neon color presets and pulsing indicators.",
        props=[
            Prop("text", "string", True, 'Badge text content.', pytype=str),
            Prop("type", "string", False, 'Badge category/theme (`"success"`, `"warning"`, `"danger"`, `"primary"`, `"info"`, `"cyan"`).', pytype=str),
            Prop("pulse", "boolean", False, 'Enables a blinking live-status dot indicator.', pytype=bool),
            Prop("outline", "boolean", False, 'Toggles transparent outline styling mode.', pytype=bool),
        ],
    ),
    "gdm-progress": Comp(
        group="panel", strict=True,
        desc="Glassmorphic linear progress bar or meter indicator.",
        props=[
            Prop("value", "number", True, 'Progress completion percentage (0 to 100).', pytype=float),
            Prop("color", "string", False, 'Bar fill color name or custom CSS color.', pytype=str),
            Prop("height", "string", False, 'Thickness of the bar track (default `"8px"`).', pytype=str),
            Prop("animated", "boolean", False, 'Enables flowing stripe patterns across the fill.', pytype=bool),
            Prop("glow", "boolean", False, 'Adds a neon glow filter around the filled progress track.', pytype=bool),
        ],
    ),
    "gdm-divider": Comp(
        group="panel", strict=True,
        desc="Structural line divider with configurable layout margins and sizing.",
        props=[
            Prop("vertical", "boolean", False, 'Toggles vertical orientation instead of horizontal.', pytype=bool),
            Prop("color", "string", False, 'Custom line color (CSS style).', pytype=str),
            Prop("thickness", "string", False, 'Thickness of the dividing line (default `"1px"`).', pytype=str),
            Prop("margin", "string", False, 'CSS margin spacing around the divider.', pytype=str),
        ],
    ),
    "gdm-icon": Comp(
        group="panel", strict=True,
        desc="Interactive vector SVG icon selector containing a robust set of symbols.",
        props=[
            Prop("name", "string", True, 'Icon name key (e.g. `"sonar"`, `"clock"`, `"chart"`, `"trending-up"`, `"trending-down"`, `"lock"`, `"unlock"`, `"info"`, `"alert"`, `"activity"`, `"database"`, `"user"`, `"globe"`, `"cpu"`, `"server"`, `"arrow-up"`, `"arrow-down"`, `"check"`, `"close"`, `"chevron-right"`, `"chevron-left"`).', pytype=str),
            Prop("color", "string", False, 'Icon stroke color preset or custom Hex.', pytype=str),
            Prop("size", "string", False, 'Icon bounding box diameter (e.g. `"24px"`).', pytype=str),
        ],
    ),
    "gdm-button": Comp(
        group="panel", strict=True,
        desc="Interactive button element with four action modes: agent (dispatches gdm-button-click event for the agent), link (opens a URL), fire (POSTs to a server endpoint — used by Mode C playbook triggers), or emit (dispatches a custom event).",
        props=[
            # Text content — either `text` or legacy `label` works; `text` wins if both set.
            Prop("text", "string", False, 'Button label (new). Falls back to legacy `label` if empty.', pytype=str),
            Prop("label", "string", False, 'Button label (legacy alias for `text`).', pytype=str),
            # Action — discriminated union for the four modes. Shorthand props
            # (`actionId`, `targetUrl`) still resolve to the right mode for back-compat.
            Prop("action", "object", False, 'Action descriptor: `{type:"link",url,newTab?}` | `{type:"fire",endpoint,payload?}` | `{type:"emit",event,detail?}` | `{type:"agent",actionId,payload?}`.', pytype=dict),
            Prop("actionId", "string", False, 'Legacy shorthand for agent mode — dispatches `gdm-button-click` with this id.', pytype=str),
            Prop("payload", "string", False, 'Legacy payload (JSON string parsed if it starts with `{` or `[`). Used only with `actionId`.', pytype=str),
            Prop("targetUrl", "string", False, 'Legacy shorthand for link mode — opens this URL in a new tab.', pytype=str),
            # Visual
            Prop("type", "string", False, 'Theme preset (`"primary"`, `"secondary"`, `"danger"`, `"ghost"`, `"success"`).', pytype=str),
            Prop("size", "string", False, 'Size variant (`"sm"`, `"md"` default, `"lg"`, `"hero"`).', pytype=str),
            Prop("icon", "string", False, 'Optional leading icon name.', pytype=str),
            Prop("pulse", "boolean", False, 'Apply continuous glow pulse animation.', pytype=bool),
            Prop("loading", "boolean", False, 'Replaces label with a spinner; auto-set during fire-mode fetch.', pytype=bool),
            Prop("disabled", "boolean", False, 'Toggles user click-ability.', pytype=bool),
        ],
    ),
    "gdm-clock": Comp(
        group="panel", strict=True,
        desc="Digital clock and date widget with dynamic timezone configurations.",
        props=[
            Prop("showClock", "boolean", False, 'Toggles time display on/off.', pytype=bool),
            Prop("showDate", "boolean", False, 'Toggles date display on/off.', pytype=bool),
            Prop("format", "string", False, 'Time display format (`"12h"` or `"24h"`).', pytype=str),
            Prop("timezone", "string", False, 'Explicit target Timezone name (e.g. `"UTC"`, `"America/New_York"`).', pytype=str),
            Prop("accentColor", "string", False, 'Neon color style used for text shadowing and clock values.', pytype=str),
        ],
    ),
    "gdm-sparkline": Comp(
        group="panel", strict=True,
        desc="Ultra-light inline SVG trend sparkline.",
        props=[
            Prop("data", "string", True, 'Comma-separated numerical datapoints.', pytype=str),
            Prop("color", "string", False, 'Trend-line stroke color preset or custom Hex.', pytype=str),
            Prop("width", "string", False, 'Sparkline viewport width.', pytype=str),
            Prop("height", "string", False, 'Sparkline viewport height.', pytype=str),
            Prop("fill", "boolean", False, 'Adds an elegant vertical backdrop area gradient under the sparkline.', pytype=bool),
        ],
    ),
    "gdm-table-view": Comp(
        group="panel", strict=True,
        desc="Structured grid table for clear dashboard visualizations.",
        props=[
            Prop("headers", "array of strings", True, 'Table column title headers.', pytype=Union[List[str], str]),
            Prop("rows", "array of arrays", True, 'Table row cells, containing numbers, strings, or formatted subtext cell objects.', pytype=Union[List[Any], str]),
            Prop("accentColor", "string", False, 'Theme color styling used for headers and lines.', pytype=str),
        ],
    ),
    "gdm-trend-value": Comp(
        group="panel", strict=True,
        desc="Compact financial ticker element with dynamic green/red direction trend arrows.",
        props=[
            Prop("symbol", "string", True, 'Asset/instrument symbol tag.', pytype=str),
            Prop("label", "string", False, 'Instrument description label.', pytype=str),
            Prop("price", "number", True, 'Current asset trading price.', pytype=float),
            Prop("change", "number", True, 'Percentage change factor.', pytype=float),
            Prop("isUp", "boolean", False, 'Explicitly override calculated positive arrow indicator.', pytype=bool),
            Prop("precision", "integer", False, 'Decimal places to round the price value to.', pytype=int),
        ],
    ),
    "gdm-scroller": Comp(
        group="panel", strict=True,
        desc="Infinite ticker/marquee container wrapping nested child elements.",
        props=[
            Prop("speed", "string", False, 'CSS animation duration (e.g. `"20s"`).', pytype=str),
            Prop("direction", "string", False, 'Scrolling direction vector (`"left"` or `"right"`).', pytype=str),
            Prop("active", "boolean", False, 'Toggles scrolling animation activity.', pytype=bool),
            Prop("children", doc=False, pytype=dict),
        ],
    ),

    # 3. Overlays (layers drawn on top of panels)
    "gdm-emoji-burst": Comp(
        group="overlay", desc="Launches a burst of floating emoji reactions across the stage.",
        props=[
            Prop("emoji", "string", False, 'The emoji to launch (default `"👏"`).'),
            Prop("count", "number", False, "How many to spawn per burst (default `12`)."),
            Prop("active", "boolean", True, "Toggle to trigger / show the burst."),
        ],
    ),
    "gdm-draw-overlay": Comp(
        group="overlay", desc="Renders freehand annotation strokes over the stage.",
        props=[
            Prop("strokes", "array of objects", True, "Stroke objects with `points` (array of `[x, y]` pairs, coordinates normalized 0–1), optional `color` (string) and `width` (number)."),
            Prop("active", "boolean", True, "Toggle overlay visibility."),
            Prop("accentColor", None, None, "is not used; per-stroke `color` defaults to the component `color` prop (default `#00f2ff`)."),
        ],
    ),
    "gdm-pointer": Comp(
        group="overlay", desc="A laser-pointer dot for indicating positions on stage.",
        props=[
            Prop("x", "number", True, "Normalized 0–1 horizontal position."),
            Prop("y", "number", True, "Normalized 0–1 vertical position."),
            Prop("active", "boolean", True, "Toggle pointer visibility."),
            Prop("color", "string", False, "Pointer color (default `#ff3b30`)."),
            Prop("label", "string", False, "Small label shown beside the dot."),
        ],
    ),
    "gdm-stage-card": Comp(
        group="overlay", strict=True,
        desc="Elegant glassmorphic title and body text message card.",
        props=[
            Prop("title", "string", True, "Card header text.", pytype=str),
            Prop("text", "string", True, "Message content.", pytype=str),
            Prop("accent", "string", False, 'Accent color style (e.g. `"primary"`, `"success"`, `"warning"`, `"danger"`).', pytype=str),
            Prop("mode", doc=False, pytype=str),
        ],
    ),
    "gdm-chat-card": Comp(
        group="overlay", strict=True,
        desc="Glassmorphic bubble showcasing a participant's chat comment.",
        props=[
            Prop("sender", "string", True, "Sender name.", pytype=str),
            Prop("text", "string", True, "Chat message content.", pytype=str),
            Prop("avatar", doc=False, pytype=str),
            Prop("duration", doc=False, pytype=int),
        ],
    ),
    "gdm-chyron": Comp(
        group="overlay", strict=True,
        desc="A classic lower-third banner for speaker names or key headlines.",
        props=[
            Prop("title", "string", True, "Primary lower-third text.", pytype=str),
            Prop("subtitle", "string", False, "Secondary context text.", pytype=str),
            Prop("active", "boolean", True, "Toggle overlay visibility.", pytype=bool),
            Prop("accentColor", "string", False, "CSS color for the accent bar and glow (default `#00f2ff`).", pytype=str),
            Prop("titleColor", "string", False, "CSS color for the title text (default `#ffffff`).", pytype=str),
            Prop("subtitleColor", "string", False, "CSS color for the subtitle text (default `rgba(255,255,255,0.62)`).", pytype=str),
            Prop("titleSize", "number", False, "Title font size in px (default `20`).", pytype=int),
            Prop("subtitleSize", "number", False, "Subtitle font size in px (default `14`).", pytype=int),
            Prop("bottom", "number", False, "Distance from bottom of screen in px (default `48`).", pytype=int),
            Prop("left", "number", False, "Distance from left of screen in px (default `40`).", pytype=int),
        ],
    ),
    "gdm-ticker": Comp(
        group="overlay", strict=True,
        desc="Bottom scrolling ticker band across the stage screen.",
        props=[
            Prop("text", "string", True, "Text content to scroll.", pytype=str),
            Prop("active", "boolean", True, "Toggle ticker visibility.", pytype=bool),
            Prop("badgeText", "string", False, "Label shown in the left badge (default `LIVE FEED`).", pytype=str),
            Prop("badgeColor", "string", False, "CSS color for the badge and dot (default `#ff0055`).", pytype=str),
            Prop("accentColor", "string", False, "CSS color for the top border accent (default `#00f2ff`).", pytype=str),
            Prop("textColor", "string", False, "CSS color for the scrolling text (default `rgba(255,255,255,0.95)`).", pytype=str),
            Prop("fontSize", "number", False, "Scrolling text font size in px (default `16`).", pytype=int),
            Prop("height", "number", False, "Bar height in px (default `48`).", pytype=int),
            Prop("scrollSpeed", "number", False, "Scroll animation duration in seconds — lower = faster (default `35`).", pytype=int),
        ],
    ),
    "gdm-standby-slate": Comp(
        group="overlay", strict=True,
        desc="High-fidelity intermission or standby screen with a countdown timer.",
        props=[
            Prop("badge", "string", False, "Category badge.", pytype=str),
            Prop("title", "string", True, "Header text.", pytype=str),
            Prop("description", "string", False, "Detail text.", pytype=str),
            Prop("seconds", "integer", False, "Timer countdown duration.", pytype=int),
            Prop("active", "boolean", True, "Toggle visibility.", pytype=bool),
            Prop("fullscreen", "boolean", False, "Stretch slate to cover the entire viewport.", pytype=bool),
        ],
    ),
    "gdm-poll-overlay": Comp(
        group="overlay", desc="Slide-in audience interactive question poll.",
        props=[
            Prop("question", "string", True, "Poll question."),
            Prop("options", "array of strings", True, "Selections."),
            Prop("active", "boolean", True, "Toggle poll."),
            Prop("values", "array of integers", False, "Response count tallies."),
        ],
    ),
    "gdm-captions": Comp(
        group="overlay",
        desc="Lower-third live caption overlay — renders the current spoken/narrated line as a large centered pill, keeping the previous line faded above it so each point reads clearly one at a time. Use this to display captions compositionally via render_stage (preferred over the out-of-band transcript stream for agent-driven caption points).",
        props=[
            Prop("text", "string", True, "The current caption line to display."),
            Prop("speaker", "string", False, 'Speaker label shown above the line (default `"Speaker"`).'),
            Prop("active", "boolean", True, "Toggle caption visibility."),
            Prop("accentColor", "string", False, "CSS color for the speaker label (default `#00f2ff`)."),
            Prop("flip", "boolean", False, "Toggle mechanical split-flap rendering.", pytype=bool),
        ],
    ),
    "gdm-transcript-view": Comp(
        group="overlay",
        desc="Overlay displaying a real-time scrolling transcript log (avatar + role + text per turn), suited to a side log rather than lower-third captions.",
        props=[
            Prop("transcript", "array of objects", True, "Turn objects with `id` (string), `role` (string), and `text` (string) fields."),
        ],
    ),

    # --- Components available to the agent but not documented in the prompt prose.
    # They are still valid catalogue names and (where strict) prop-validated.
    "gdm-mermaid-panel": Comp(
        group="panel", in_prompt=False,
        desc="Renders a Mermaid diagram from syntax (syntax, title, version).",
    ),
    "gdm-html-panel": Comp(
        group="panel", in_prompt=False, strict=True,
        desc="Renders a sandboxed HTML fragment as a panel or overlay (html, title, overlay, version).",
        props=[
            Prop("html", pytype=str),
            Prop("title", pytype=str),
            Prop("overlay", pytype=bool),
            Prop("version", pytype=int),
        ],
    ),
    "gdm-laser-sweep": Comp(
        group="overlay", in_prompt=False,
        desc="Animated laser sweep accent overlay.",
    ),
    "gdm-3d-airspace": Comp(
        group="panel", in_prompt=False, strict=True,
        desc="Interactive 3D tactical airspace / radar deck (flights, camera, glide-slope, terrain, orbit, auto-track).",
        props=[
            Prop("flights", pytype=_FlightsType),
            Prop("lockedCallsign", pytype=str),
            Prop("cameraPitch", pytype=float),
            Prop("cameraYaw", pytype=float),
            Prop("showGlideSlope", pytype=bool),
            Prop("showTerrain", pytype=bool),
            Prop("zoom", pytype=float),
            Prop("cinematicOrbit", pytype=bool),
            Prop("autoTrack", pytype=bool),
            Prop("compact", pytype=bool),  # hides internal HUD chrome for embedded compositions
        ],
    ),
    "gdm-3d-scene": Comp(
        group="panel", in_prompt=False, strict=True,
        desc="Generic high-performance interactive 3D scene engine (points, links, camera, terrain, grid, fog).",
        props=[
            Prop("points", pytype=Union[List[Any], Dict[str, Any], str]),
            Prop("links", pytype=Union[List[Any], Dict[str, Any], str]),
            Prop("camera", pytype=dict),
            Prop("terrain", pytype=bool),
            Prop("grid", pytype=bool),
            Prop("fog", pytype=bool),
        ],
    ),
    "gdm-market-ticker": Comp(
        group="overlay", in_prompt=False, strict=True,
        desc="Live global market-scan board: flip-clock time/date, market sections (a big spread of instruments), and an auto-highlighted 'ones to watch' movers strip.",
        props=[
            # sections: [{label, accent?, items:[{symbol,price,changePercent,isUp?,label?}]}]
            Prop("sections", pytype=Union[List[Any], Dict[str, Any], str]),
            Prop("active", req=True, pytype=bool),
            Prop("badgeText", pytype=str),
            Prop("accentColor", pytype=str),
            Prop("watchCount", pytype=int),
            Prop("showClock", pytype=bool),
            Prop("showDate", pytype=bool),
        ],
    ),
    "gdm-flip-slate": Comp(
        group="overlay", in_prompt=False, strict=True,
        desc="Mechanical split-flap letter presentation board.",
        props=[
            Prop("text", req=True, pytype=str),
            Prop("active", req=True, pytype=bool),
            Prop("badgeText", pytype=str),
            Prop("subtitle", pytype=str),
            Prop("accentColor", pytype=str),
            Prop("delayMs", pytype=int),
        ],
    ),
}


# --- Derived artifacts ------------------------------------------------------

A2UI_CATALOG = frozenset(CATALOG.keys())


def _build_model(name: str, comp: Comp):
    fields: Dict[str, Any] = {}
    for p in comp.props:
        pt = p.pytype if p.pytype is not None else str
        if p.req:
            fields[p.name] = (pt, ...)
        else:
            fields[p.name] = (Optional[pt], None)
    return create_model(
        name.replace("-", "_"),
        __config__=ConfigDict(extra="forbid"),
        **fields,
    )


COMPONENT_SCHEMAS: Dict[str, Any] = {
    name: _build_model(name, comp)
    for name, comp in CATALOG.items()
    if comp.strict
}


# --- Validation -------------------------------------------------------------

ValidationResult = namedtuple("ValidationResult", ["errors", "warnings"])


def validate_a2ui_surface_detailed(surface_update: dict) -> ValidationResult:
    """Validate a surfaceUpdate, splitting findings into blocking errors and
    non-blocking warnings.

    ERRORS (block the render): empty surface, missing component definition,
    unknown component name — the renderer cannot proceed.

    WARNINGS (render anyway, feed back to the agent): prop-level issues such as
    unknown/extra props, missing required props, or type mismatches on
    strictly-modeled components. The A2UI client renderer tolerates these.
    """
    errors: List[str] = []
    warnings: List[str] = []

    components = surface_update.get("components", [])
    if not components:
        errors.append("surfaceUpdate.components is empty")
        return ValidationResult(errors, warnings)

    for comp in components:
        comp_id = comp.get("id", "<no-id>")
        element_name = comp.get("component", "")
        if not element_name:
            errors.append(f"Component '{comp_id}' has no component definition")
            continue

        element_name = element_name.lower()
        if element_name not in A2UI_CATALOG:
            errors.append(f"Component '{element_name}' not in catalog (id={comp_id})")
            continue

        props = {k: v for k, v in comp.items() if k not in ("id", "component")}


        schema_cls = COMPONENT_SCHEMAS.get(element_name)
        if schema_cls is None:
            continue  # lenient component — nothing to validate

        try:
            schema_cls(**props)
        except ValidationError as e:
            for err in e.errors():
                loc_str = ".".join(str(loc) for loc in err["loc"])
                warnings.append(
                    f"Component '{element_name}' property validation failed (id={comp_id}): "
                    f"Field '{loc_str}' {err['msg']} (type={err['type']})"
                )

    return ValidationResult(errors, warnings)


def validate_a2ui_surface(surface_update: dict) -> List[str]:
    """Backward-compatible entry point: returns only BLOCKING errors.

    Prop-level issues are surfaced as warnings via
    :func:`validate_a2ui_surface_detailed` and no longer block a render.
    """
    return validate_a2ui_surface_detailed(surface_update).errors


# --- Prose / summary generation ---------------------------------------------

def _format_prop(p: Prop) -> str:
    if p.type_label is None:
        return f"`{p.name}` {p.note}"
    paren = p.type_label
    if p.req is True:
        paren += ", required"
    elif p.req is False:
        paren += ", optional"
    return f"`{p.name}` ({paren}): {p.note}"


def render_catalog_prompt() -> str:
    """Generate the A2UI COMPONENT CATALOG section injected into the system prompt."""
    n = sum(1 for c in CATALOG.values() if c.in_prompt)
    lines: List[str] = [
        "A2UI COMPONENT CATALOG:",
        f"The A2UI Component Catalog provides a rich vocabulary of {n} components "
        "consisting of a root layout container, panel elements, and overlays:",
        "",
    ]
    groups = [
        ("root", "1. Root Layout Component:"),
        ("panel", "2. Panel Components (Children of the layout grid):"),
        ("overlay", "3. Overlays (Layers drawn on top of panels):"),
    ]
    for gkey, header in groups:
        lines.append(header)
        for name, comp in CATALOG.items():
            if not comp.in_prompt or comp.group != gkey:
                continue
            lines.append(f"   - `{name}`: {comp.desc}")
            doc_props = [p for p in comp.props if p.doc]
            if doc_props:
                lines.append(f"     - {comp.props_label}:")
                for p in doc_props:
                    lines.append("       - " + _format_prop(p))
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def render_mcp_component_summary() -> str:
    """Compact supported-component blurb for the MCP render_stage tool description."""
    parts: List[str] = []
    for name, comp in CATALOG.items():
        doc_props = [p.name for p in comp.props if p.doc]
        if doc_props:
            parts.append(f"{name} ({', '.join(doc_props)})")
        else:
            parts.append(name)
    return "Supported components in catalog: " + ", ".join(parts) + "."


def emit_json_catalog():
    """Convert CATALOG to v0.9-shaped JSON and write to catalog/gdm-v0.1.json."""
    import os
    import json

    catalog_data = {
        "catalogId": "gdm-v0.1",
        "description": "Google Meet Studio GDM Component Catalog",
        "components": {}
    }

    for comp_name, comp in CATALOG.items():
        props_dict = {}
        for p in comp.props:
            prop_info = {
                "type": p.type_label or "any",
                "required": p.req if p.req is not None else False,
                "description": p.note
            }
            props_dict[p.name] = prop_info
            
        catalog_data["components"][comp_name] = {
            "group": comp.group,
            "description": comp.desc,
            "strict": comp.strict,
            "properties": props_dict
        }

    # Write to catalog/gdm-v0.1.json relative to the root directory
    workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    catalog_dir = os.path.join(workspace_dir, "catalog")
    os.makedirs(catalog_dir, exist_ok=True)
    catalog_path = os.path.join(catalog_dir, "gdm-v0.1.json")

    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog_data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Catalog JSON successfully generated and written to: {catalog_path}")


if __name__ == "__main__":
    import sys
    if "--emit-json" in sys.argv:
        emit_json_catalog()
    else:
        print("Usage: python3 -m app.a2ui_catalog --emit-json")

