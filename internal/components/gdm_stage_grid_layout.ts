import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

/**
 * gdm-grid — a CSS-grid layout atom (the structural partner to gdm-container's flex).
 *
 * `columns`/`rows` accept either a number (→ repeat(n, 1fr)) or a raw grid-template
 * string (e.g. "2fr 1fr" or "repeat(auto-fit, minmax(220px, 1fr))"). Children render
 * through the default slot. Host styling is applied imperatively (CSP-permitted).
 */
@customElement('gdm-grid')
export class GdmGrid extends LitElement {
  @property({ type: String }) columns = 'repeat(auto-fit, minmax(200px, 1fr))';
  @property({ type: String }) rows = '';
  @property({ type: String }) gap = '12px';
  @property({ type: String }) align = 'stretch';   // align-items
  @property({ type: String }) justify = 'stretch'; // justify-items
  @property({ type: String }) padding = '0';
  @property({ type: String }) width = '100%';
  @property({ type: String }) height = 'auto';

  static styles = css`:host { display: grid; box-sizing: border-box; min-width: 0; }`;

  private _tpl(v: string): string {
    return /^\d+$/.test(v.trim()) ? `repeat(${v.trim()}, 1fr)` : v;
  }

  updated() {
    this.style.display = 'grid';
    this.style.boxSizing = 'border-box';
    this.style.gridTemplateColumns = this._tpl(this.columns);
    this.style.gridTemplateRows = this.rows ? this._tpl(this.rows) : '';
    this.style.gap = this.gap;
    this.style.alignItems = this.align;
    this.style.justifyItems = this.justify;
    this.style.padding = this.padding;
    this.style.width = this.width;
    this.style.height = this.height;
  }

  render() { return html`<slot></slot>`; }
}
