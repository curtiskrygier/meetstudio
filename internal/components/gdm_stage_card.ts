import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

/**
 * gdm-stage-card — Phase 1 A2UI PoC component.
 * Glassmorphic overlay card rendered on the main stage by the A2UIEngine.
 * Props: title, text, accent (CSS color, default cyan).
 */
@customElement('gdm-stage-card')
export class GdmStageCard extends LitElement {
  @property({ type: String }) title = '';
  @property({ type: String }) text = '';
  @property({ type: String }) accent = '#00f2ff';

  static styles = css`
    :host {
      display: block;
      position: fixed;
      bottom: 48px;
      right: 40px;
      max-width: 380px;
      z-index: 800;
      animation: slide-in 0.4s cubic-bezier(0.22, 1, 0.36, 1) both;
    }
    @keyframes slide-in {
      from { opacity: 0; transform: translateY(20px) scale(0.97); }
      to   { opacity: 1; transform: translateY(0) scale(1); }
    }
    .card {
      background: rgba(8, 10, 20, 0.72);
      backdrop-filter: blur(18px) saturate(1.4);
      -webkit-backdrop-filter: blur(18px) saturate(1.4);
      border: 1px solid rgba(255, 255, 255, 0.10);
      border-radius: 16px;
      padding: 20px 22px 18px;
      box-shadow:
        0 0 0 1px rgba(255,255,255,0.04) inset,
        0 8px 32px rgba(0,0,0,0.55),
        0 0 28px -4px var(--accent-glow, rgba(0,242,255,0.22));
    }
    .accent-bar {
      width: 36px;
      height: 3px;
      border-radius: 99px;
      background: var(--accent-color, #00f2ff);
      margin-bottom: 12px;
      box-shadow: 0 0 10px var(--accent-color, #00f2ff);
    }
    .title {
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-size: 17px;
      font-weight: 700;
      letter-spacing: -0.01em;
      color: #fff;
      margin: 0 0 6px;
      line-height: 1.25;
    }
    .text {
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-size: 13.5px;
      color: rgba(255, 255, 255, 0.72);
      line-height: 1.55;
      margin: 0;
    }
  `;

  render() {
    return html`
      <div class="card" style="--accent-color:${this.accent};--accent-glow:${this.accent}44">
        <div class="accent-bar"></div>
        ${this.title ? html`<div class="title">${this.title}</div>` : ''}
        ${this.text  ? html`<p class="text">${this.text}</p>` : ''}
      </div>
    `;
  }
}
