import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-pointer')
export class GdmStagePointer extends LitElement {
  @property({ type: Number }) x = 0.5;
  @property({ type: Number }) y = 0.5;
  @property({ type: Boolean, reflect: true }) active = false;
  @property({ type: String }) color = '#ff3b30';
  @property({ type: String }) label = '';

  static styles = css`
    :host {
      display: block;
      position: fixed;
      inset: 0;
      z-index: 760;
      pointer-events: none;
      opacity: 0;
      transition: opacity 0.35s ease;
    }
    :host([active]) {
      opacity: 1;
    }

    .dot-anchor {
      position: absolute;
      width: 0;
      height: 0;
      /* left / top set via inline style from x,y */
      transition: left 0.25s ease, top 0.25s ease;
    }

    /* outer soft ring */
    .ring {
      position: absolute;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      border: 2px solid var(--ptr-color);
      opacity: 0.35;
      transform: translate(-50%, -50%);
      animation: pulse-ring 1.6s ease-out infinite;
    }

    /* inner glowing dot */
    .dot {
      position: absolute;
      width: 14px;
      height: 14px;
      border-radius: 50%;
      background: var(--ptr-color);
      box-shadow:
        0 0 6px 2px var(--ptr-color),
        0 0 18px 4px var(--ptr-glow);
      transform: translate(-50%, -50%);
      animation: pulse-dot 1.6s ease-in-out infinite;
    }

    /* label pill */
    .label {
      position: absolute;
      left: 14px;
      top: -22px;
      white-space: nowrap;
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.04em;
      color: var(--ptr-color);
      background: rgba(4, 6, 18, 0.78);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border: 1px solid var(--ptr-color-30);
      border-radius: 8px;
      padding: 3px 10px;
      box-shadow:
        0 2px 12px rgba(0, 0, 0, 0.45),
        0 0 8px -2px var(--ptr-glow);
      pointer-events: none;
    }

    @keyframes pulse-dot {
      0%, 100% { transform: translate(-50%, -50%) scale(1);   opacity: 1; }
      50%       { transform: translate(-50%, -50%) scale(0.88); opacity: 0.85; }
    }

    @keyframes pulse-ring {
      0%   { transform: translate(-50%, -50%) scale(1);   opacity: 0.35; }
      60%  { transform: translate(-50%, -50%) scale(1.8); opacity: 0; }
      100% { transform: translate(-50%, -50%) scale(1.8); opacity: 0; }
    }
  `;

  render() {
    const anchorStyle = [
      `left:${this.x * 100}%`,
      `top:${this.y * 100}%`,
      `--ptr-color:${this.color}`,
      `--ptr-glow:${this.color}88`,
      `--ptr-color-30:${this.color}4d`,
    ].join(';');

    return html`
      <div class="dot-anchor" style="${anchorStyle}">
        <div class="ring"></div>
        <div class="dot"></div>
        ${this.label ? html`<div class="label">${this.label}</div>` : ''}
      </div>
    `;
  }
}
