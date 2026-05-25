import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

interface Stroke {
  points: Array<[number, number]>;
  color?: string;
  width?: number;
}

@customElement('gdm-draw-overlay')
export class GdmStageDrawOverlay extends LitElement {
  @property({ type: Array }) strokes: Stroke[] = [];
  @property({ type: Boolean, reflect: true }) active = false;
  @property({ type: String }) color = '#00f2ff';

  willUpdate(changedProperties: Map<string | number | symbol, unknown>) {
    // Defensive parsing: handle stringified JSON
    if (changedProperties.has('strokes') && typeof this.strokes === 'string') {
      try {
        this.strokes = JSON.parse(this.strokes as unknown as string);
      } catch (e) {
        console.error('[gdm-draw-overlay] Failed to parse strokes:', e);
        this.strokes = [];
      }
    }
    // Unpack wrapped strokes object if needed
    if (this.strokes && !Array.isArray(this.strokes) && typeof this.strokes === 'object') {
      const anyStrokes = this.strokes as any;
      if (Array.isArray(anyStrokes.strokes)) {
        this.strokes = anyStrokes.strokes;
      } else if (Array.isArray(anyStrokes.explicitList)) {
        this.strokes = anyStrokes.explicitList;
      }
    }
    // Ensure strokes is always an array
    if (!Array.isArray(this.strokes)) this.strokes = [];
  }

  static styles = css`
    :host {
      display: block;
      position: fixed;
      inset: 0;
      z-index: 720;
      pointer-events: none;
      opacity: 0;
      transform: translateY(-6px);
      transition: opacity 0.35s cubic-bezier(0.16, 1, 0.3, 1),
                  transform 0.35s cubic-bezier(0.16, 1, 0.3, 1);
    }
    :host([active]) {
      opacity: 1;
      transform: translateY(0);
    }
    svg {
      width: 100%;
      height: 100%;
      display: block;
    }
  `;

  private _buildFilterId(color: string): string {
    // Produce a safe id from color string for use in SVG filter references
    return 'glow-' + color.replace(/[^a-zA-Z0-9]/g, '');
  }

  render() {
    // Collect unique colors used across all strokes so we can define one filter per color
    const usedColors = new Set<string>();
    usedColors.add(this.color);
    for (const stroke of this.strokes) {
      if (stroke.color) usedColors.add(stroke.color);
    }

    const filterDefs = Array.from(usedColors).map(c => {
      const id = this._buildFilterId(c);
      return html`
        <filter id="${id}" x="-20%" y="-20%" width="140%" height="140%" color-interpolation-filters="sRGB">
          <feFlood flood-color="${c}" flood-opacity="0.55" result="flood"/>
          <feComposite in="flood" in2="SourceGraphic" operator="in" result="colored-glow"/>
          <feGaussianBlur in="colored-glow" stdDeviation="0.008" result="blur"/>
          <feMerge>
            <feMergeNode in="blur"/>
            <feMergeNode in="blur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      `;
    });

    const polylines = this.strokes.map((stroke, idx) => {
      if (!stroke.points || stroke.points.length < 2) return html``;
      const strokeColor = stroke.color || this.color;
      const strokeWidth = stroke.width != null ? stroke.width : 3;
      const filterId = this._buildFilterId(strokeColor);
      const pts = stroke.points.map(([x, y]) => `${x},${y}`).join(' ');
      return html`
        <polyline
          key="${idx}"
          points="${pts}"
          fill="none"
          stroke="${strokeColor}"
          stroke-width="${strokeWidth}px"
          stroke-linecap="round"
          stroke-linejoin="round"
          vector-effect="non-scaling-stroke"
          filter="url(#${filterId})"
        />
      `;
    });

    return html`
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 1 1"
        preserveAspectRatio="none"
      >
        <defs>${filterDefs}</defs>
        ${polylines}
      </svg>
    `;
  }
}
