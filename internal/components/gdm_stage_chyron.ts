import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-chyron')
export class GdmStageChyron extends LitElement {
  @property({ type: String }) title = '';
  @property({ type: String }) subtitle = '';
  @property({ type: Boolean, reflect: true }) active = false;
  @property({ type: String }) accentColor = '#00f2ff';
  @property({ type: String }) titleColor = '#ffffff';
  @property({ type: String }) subtitleColor = 'rgba(255,255,255,0.62)';
  @property({ type: Number }) titleSize = 20;
  @property({ type: Number }) subtitleSize = 14;
  @property({ type: Number }) bottom = 48;
  @property({ type: Number }) left = 40;

  willUpdate(changed: Map<string | number | symbol, unknown>) {
    if (changed.has('bottom') || changed.has('left')) {
      this.style.bottom = `${this.bottom}px`;
      this.style.left = `${this.left}px`;
    }
  }

  connectedCallback() {
    super.connectedCallback();
    this.style.bottom = `${this.bottom}px`;
    this.style.left = `${this.left}px`;
  }

  static styles = css`
    :host {
      display: block;
      position: fixed;
      z-index: 700;
    }
    .chyron {
      display: flex; align-items: stretch;
      background: rgba(8,10,20,0.82); backdrop-filter: blur(18px) saturate(1.4);
      border: 1px solid rgba(255,255,255,0.10); border-radius: 12px;
      box-shadow: 0 0 0 1px rgba(255,255,255,0.04) inset, 0 8px 32px rgba(0,0,0,0.55), 0 0 28px -4px var(--accent-glow);
      overflow: hidden;
      transform: translateX(-110%); opacity: 0;
      transition: transform 0.4s ease, opacity 0.4s ease;
    }
    :host([active]) .chyron { transform: translateX(0); opacity: 1; }
    .accent-bar { width: 4px; flex-shrink: 0; background: var(--accent); box-shadow: 0 0 12px var(--accent); }
    .body { padding: 14px 22px 12px; }
    .title { font-family: 'Google Sans','Inter',sans-serif; font-weight: 700; color: var(--title-color); margin: 0 0 4px; white-space: nowrap; }
    .subtitle { font-family: 'Google Sans','Inter',sans-serif; color: var(--subtitle-color); margin: 0; white-space: nowrap; }
  `;

  render() {
    const chyronStyle = [
      `--accent:${this.accentColor}`,
      `--accent-glow:${this.accentColor}44`,
      `--title-color:${this.titleColor}`,
      `--subtitle-color:${this.subtitleColor}`,
    ].join(';');

    return html`<div class="chyron" style="${chyronStyle}">
      <div class="accent-bar"></div>
      <div class="body">
        ${this.title ? html`<div class="title" style="font-size:${this.titleSize}px">${this.title}</div>` : ''}
        ${this.subtitle ? html`<div class="subtitle" style="font-size:${this.subtitleSize}px">${this.subtitle}</div>` : ''}
      </div>
    </div>`;
  }
}
