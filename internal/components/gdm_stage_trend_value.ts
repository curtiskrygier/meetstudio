import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

/**
 * gdm-trend-value — a single instrument row (symbol · name · price · % change).
 *
 * All styling lives in static shadow CSS (adopted stylesheets, CSP-safe) so the
 * premium look survives the hardened Content-Security-Policy that strips inline
 * styles. Direction is conveyed with a CSS caret rather than an inline-coloured
 * icon for the same reason.
 */
@customElement('gdm-trend-value')
export class GdmStageTrendValue extends LitElement {
  @property({ type: String }) symbol = '';
  @property({ type: String }) label = '';
  @property({ type: Number }) price = 0;
  @property({ type: Number }) change = 0;
  @property({ type: Boolean }) isUp = false;
  @property({ type: Number }) precision = 2;

  static styles = css`
    :host { display: block; width: 100%; box-sizing: border-box; }

    .row {
      display: grid;
      grid-template-columns: 1fr auto;
      align-items: center;
      column-gap: 10px;
      padding: 6px 12px;
      border-radius: 9px;
      background:
        linear-gradient(90deg, rgba(255,255,255,0.035), rgba(255,255,255,0.012));
      border: 1px solid rgba(255,255,255,0.055);
      border-left: 2px solid var(--accent, rgba(255,255,255,0.12));
      box-sizing: border-box;
    }
    .row:hover { background: rgba(255,255,255,0.06); }

    .left { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
    .symbol {
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
      font-size: 13px;
      font-weight: 800;
      letter-spacing: 0.04em;
      color: #ffffff;
    }
    .label {
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-size: 9.5px;
      font-weight: 500;
      letter-spacing: 0.02em;
      color: rgba(255,255,255,0.42);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 130px;
    }

    .right { display: flex; align-items: center; gap: 10px; justify-self: end; }
    .price {
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
      font-size: 13px;
      font-weight: 700;
      color: rgba(255,255,255,0.96);
      font-variant-numeric: tabular-nums;
    }

    .pill {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      min-width: 74px;
      justify-content: flex-end;
      padding: 3px 8px;
      border-radius: 6px;
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
      font-size: 11.5px;
      font-weight: 700;
      line-height: 1;
      font-variant-numeric: tabular-nums;
    }
    .caret { font-size: 9px; line-height: 1; }

    :host([data-dir="up"]) .row,
    .row.up { --accent: rgba(0,255,136,0.55); }
    .row.up .pill {
      color: #00ff88;
      background: rgba(0,255,136,0.10);
      box-shadow: inset 0 0 0 1px rgba(0,255,136,0.18);
      text-shadow: 0 0 9px rgba(0,255,136,0.35);
    }

    .row.down { --accent: rgba(255,59,87,0.55); }
    .row.down .pill {
      color: #ff3b57;
      background: rgba(255,59,87,0.10);
      box-shadow: inset 0 0 0 1px rgba(255,59,87,0.18);
      text-shadow: 0 0 9px rgba(255,59,87,0.35);
    }
  `;

  render() {
    const up = this.isUp || this.change >= 0;
    const caret = up ? '▲' : '▼';
    const sign = up ? '+' : '';
    const price = this.price.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: this.precision,
    });

    return html`
      <div class="row ${up ? 'up' : 'down'}">
        <div class="left">
          <span class="symbol">${this.symbol}</span>
          ${this.label ? html`<span class="label">${this.label}</span>` : ''}
        </div>
        <div class="right">
          <span class="price">${price}</span>
          <span class="pill">
            <span class="caret">${caret}</span>
            <span>${sign}${this.change.toFixed(2)}%</span>
          </span>
        </div>
      </div>
    `;
  }
}
