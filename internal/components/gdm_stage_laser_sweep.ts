import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

/**
 * Full-stage vertical laser-beam sweep overlay.
 * Animates a glowing beam from left to right, useful for split-screen reveals.
 */
@customElement('gdm-laser-sweep')
export class GdmLaserSweep extends LitElement {
  @property({ type: Boolean, reflect: true }) active = false;
  /** Seconds per sweep pass. */
  @property({ type: Number }) duration = 2.5;
  /** Hex colour of the beam, e.g. '#00f2ff'. */
  @property({ type: String }) color = '#00f2ff';
  /** Number of sweep passes before stopping. Use 'infinite' via CSS custom property override. */
  @property({ type: Number }) sweeps = 2;

  connectedCallback() {
    super.connectedCallback();
    this._applyVars();
  }

  willUpdate(changed: Map<string | number | symbol, unknown>) {
    if (changed.has('color') || changed.has('duration') || changed.has('sweeps')) {
      this._applyVars();
    }
  }

  private _applyVars() {
    this.style.setProperty('--beam-color', this.color);
    this.style.setProperty('--beam-duration', `${this.duration}s`);
    this.style.setProperty('--beam-count', String(this.sweeps));
  }

  static styles = css`
    :host {
      display: block;
      position: fixed;
      inset: 0;
      z-index: 600;
      pointer-events: none;
      overflow: hidden;
      opacity: 0;
      transition: opacity 0.2s ease;
    }
    :host([active]) {
      opacity: 1;
    }
    .beam {
      position: absolute;
      top: 0;
      bottom: 0;
      left: -4px;
      width: 4px;
      background: var(--beam-color, #00f2ff);
      box-shadow:
        0 0 8px 3px color-mix(in srgb, var(--beam-color, #00f2ff) 90%, white),
        0 0 28px 10px color-mix(in srgb, var(--beam-color, #00f2ff) 55%, transparent),
        0 0 80px 28px color-mix(in srgb, var(--beam-color, #00f2ff) 20%, transparent);
      animation: laser-sweep var(--beam-duration, 2.5s) cubic-bezier(0.4, 0, 0.2, 1)
                 var(--beam-count, 2) both;
      will-change: left;
    }
    @keyframes laser-sweep {
      0%   { left: -4px; }
      100% { left: calc(100% + 4px); }
    }
  `;

  render() {
    return html`<div class="beam"></div>`;
  }
}
