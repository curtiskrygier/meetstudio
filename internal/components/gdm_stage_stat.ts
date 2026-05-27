import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

/**
 * gdm-stat — generic metric atom: label · big value · optional delta.
 *
 * The neutral, reusable building block beneath domain molecules like
 * gdm-trend-value. Styling is static shadow CSS (CSP-safe); the optional accent
 * tints the value. `delta`/`isUp` render a coloured caret pill when present.
 */
@customElement('gdm-stat')
export class GdmStat extends LitElement {
  @property({ type: String }) label = '';
  @property({ type: String }) value = '';
  @property({ type: String }) unit = '';
  @property({ type: String }) delta = '';        // e.g. "+1.24%" or "-0.4"
  @property({ type: Boolean }) isUp = true;
  @property({ type: String }) accent = '';        // optional CSS colour for the value
  @property({ type: String }) size = 'md';        // 'sm' | 'md' | 'lg'
  @property({ type: String }) align = 'left';

  static styles = css`
    :host { display: block; box-sizing: border-box; }
    .stat { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
    .label {
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: rgba(255,255,255,0.45);
      white-space: nowrap;
    }
    .value-row { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
    .value {
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
      font-weight: 800;
      color: #ffffff;
      line-height: 1.05;
      font-variant-numeric: tabular-nums;
    }
    .unit { font-size: 0.5em; font-weight: 600; color: rgba(255,255,255,0.4); }
    .size-sm .value { font-size: 18px; }
    .size-md .value { font-size: 26px; }
    .size-lg .value { font-size: 40px; }

    .delta {
      display: inline-flex; align-items: center; gap: 4px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px; font-weight: 700; line-height: 1;
      padding: 3px 8px; border-radius: 6px;
      font-variant-numeric: tabular-nums;
    }
    .delta .caret { font-size: 9px; }
    .delta.up   { color: #00ff88; background: rgba(0,255,136,0.10); box-shadow: inset 0 0 0 1px rgba(0,255,136,0.18); text-shadow: 0 0 9px rgba(0,255,136,0.35); }
    .delta.down { color: #ff3b57; background: rgba(255,59,87,0.10); box-shadow: inset 0 0 0 1px rgba(255,59,87,0.18); text-shadow: 0 0 9px rgba(255,59,87,0.35); }
  `;

  render() {
    return html`
      <div class="stat size-${this.size}" style="align-items:${this.align === 'center' ? 'center' : this.align === 'right' ? 'flex-end' : 'flex-start'}; text-align:${this.align}">
        ${this.label ? html`<span class="label">${this.label}</span>` : ''}
        <div class="value-row">
          <span class="value" style="${this.accent ? `color:${this.accent}` : ''}">${this.value}${this.unit ? html`<span class="unit">${this.unit}</span>` : ''}</span>
          ${this.delta ? html`
            <span class="delta ${this.isUp ? 'up' : 'down'}">
              <span class="caret">${this.isUp ? '▲' : '▼'}</span>${this.delta}
            </span>` : ''}
        </div>
      </div>
    `;
  }
}
