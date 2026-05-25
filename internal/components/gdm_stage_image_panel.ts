import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-image-panel')
export class GdmStageImagePanel extends LitElement {
  @property({ type: String }) src = '';
  @property({ type: String }) label = '';
  @property({ type: Number }) panel = 1;

  static styles = css`
    :host {
      display: block;
      width: 100%;
      height: 100%;
      position: relative;
      overflow: hidden;
      background: #000;
    }
    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
      transition: opacity 0.4s ease;
    }
    .placeholder {
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0.3;
      font-size: 48px;
      animation: pulse 2s ease-in-out infinite alternate;
    }
    @keyframes pulse {
      from { opacity: 0.15; }
      to   { opacity: 0.45; }
    }
    .label {
      position: absolute;
      bottom: 12px;
      left: 12px;
      background: rgba(0, 0, 0, 0.65);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 8px;
      padding: 4px 10px;
      font-size: 11px;
      color: rgba(255, 255, 255, 0.75);
      font-family: 'Google Sans', 'Inter', sans-serif;
    }
  `;

  render() {
    return html`
      ${this.src
        ? html`<img src=${this.src} alt=${this.label} />`
        : html`<div class="placeholder">✨</div>`}
      ${this.label ? html`<div class="label">${this.label}</div>` : ''}
    `;
  }
}
