import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-chyron')
export class GdmStageChyron extends LitElement {
  @property({ type: String }) title = '';
  @property({ type: String }) subtitle = '';
  @property({ type: Boolean, reflect: true }) active = false;

  static styles = css`
    :host { display: block; position: fixed; bottom: 48px; left: 40px; z-index: 700; }
    .chyron {
      display: flex; align-items: stretch;
      background: rgba(8,10,20,0.72); backdrop-filter: blur(18px) saturate(1.4);
      border: 1px solid rgba(255,255,255,0.10); border-radius: 12px;
      box-shadow: 0 0 0 1px rgba(255,255,255,0.04) inset, 0 8px 32px rgba(0,0,0,0.55), 0 0 28px -4px rgba(0,242,255,0.22);
      overflow: hidden;
      transform: translateX(-110%); opacity: 0;
      transition: transform 0.4s ease, opacity 0.4s ease;
    }
    :host([active]) .chyron { transform: translateX(0); opacity: 1; }
    .accent-bar { width: 3px; flex-shrink: 0; background: #00f2ff; box-shadow: 0 0 10px #00f2ff; }
    .body { padding: 14px 20px 12px; }
    .title { font-family: 'Google Sans','Inter',sans-serif; font-size: 17px; font-weight: 700; color: #fff; margin: 0 0 4px; white-space: nowrap; }
    .subtitle { font-family: 'Google Sans','Inter',sans-serif; font-size: 13px; color: rgba(255,255,255,0.62); margin: 0; white-space: nowrap; }
  `;

  render() {
    return html`<div class="chyron"><div class="accent-bar"></div><div class="body">${this.title ? html`<div class="title">${this.title}</div>` : ''}${this.subtitle ? html`<div class="subtitle">${this.subtitle}</div>` : ''}</div></div>`;
  }
}
