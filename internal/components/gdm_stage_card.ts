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
  @property({ type: String, reflect: true }) mode: 'default' | 'hero' = 'default';

  static styles = css`
    :host {
      display: block;
      position: fixed;
      z-index: 800;
      animation: slide-in 0.6s cubic-bezier(0.22, 1, 0.36, 1) both;
    }

    :host([mode="default"]), :host(:not([mode])) {
      bottom: 48px;
      right: 40px;
      max-width: 440px; /* Increased from 380px */
    }

    :host([mode="hero"]) {
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      background: radial-gradient(circle at center, rgba(0, 242, 255, 0.05) 0%, transparent 70%);
      pointer-events: none;
    }

    :host([mode="hero"]) .card {
      max-width: 640px;
      padding: 40px;
      pointer-events: auto;
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    @keyframes slide-in {
      from { opacity: 0; transform: translateY(30px) scale(0.95); }
      to   { opacity: 1; transform: translateY(0) scale(1); }
    }

    .card {
      background: rgba(10, 12, 24, 0.82);
      backdrop-filter: blur(24px) saturate(1.6);
      -webkit-backdrop-filter: blur(24px) saturate(1.6);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 24px;
      padding: 24px 28px;
      box-shadow:
        0 0 0 1px rgba(255,255,255,0.05) inset,
        0 12px 48px rgba(0,0,0,0.65),
        0 0 40px -10px var(--accent-glow, rgba(0,242,255,0.25));
    }

    .accent-bar {
      width: 48px;
      height: 4px;
      border-radius: 99px;
      background: var(--accent-color, #00f2ff);
      margin-bottom: 20px;
      box-shadow: 0 0 15px var(--accent-color, #00f2ff);
    }

    .title {
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-size: 22px; /* Increased from 17px */
      font-weight: 800;
      letter-spacing: -0.02em;
      color: #fff;
      margin: 0 0 12px;
      line-height: 1.2;
    }

    :host([mode="hero"]) .title {
      font-size: 32px;
    }

    .text {
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-size: 15px; /* Increased from 13.5px */
      color: rgba(255, 255, 255, 0.75);
      line-height: 1.6;
      margin: 0;
    }

    :host([mode="hero"]) .text {
      font-size: 18px;
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
