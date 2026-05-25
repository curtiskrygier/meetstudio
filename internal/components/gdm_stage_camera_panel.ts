import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

/**
 * gdm-camera-panel — A2UI panel component for live camera feed display.
 * Renders a camera frame (data URL or image URL) filling its grid cell.
 * Falls back to `src` poster when `frame` is empty; shows a placeholder
 * when neither is available.
 *
 * Props:
 *   frame    — data URL or image URL of the current camera frame (primary)
 *   src      — optional fallback poster / stream image URL
 *   label    — optional caption chip (e.g. "🎥 Live Camera")
 *   mirrored — horizontally flip the image (default: true, self-view convention)
 */
@customElement('gdm-camera-panel')
export class GdmStageCameraPanel extends LitElement {
  @property({ type: String }) frame = '';
  @property({ type: String }) src = '';
  @property({ type: String }) label = '';
  @property({ type: Boolean }) mirrored = true;

  static styles = css`
    :host {
      display: block;
      width: 100%;
      height: 100%;
      position: relative;
      overflow: hidden;
      border-radius: 12px;
      border: 1px solid rgba(255, 255, 255, 0.10);
      background: rgba(8, 10, 20, 0.85);
    }

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
      border-radius: inherit;
      transition: opacity 0.3s ease;
    }

    img.mirrored {
      transform: scaleX(-1);
    }

    /* Placeholder shown when no frame or src is available */
    .placeholder {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 12px;
      background: rgba(8, 10, 20, 0.85);
      backdrop-filter: blur(12px) saturate(1.2);
      -webkit-backdrop-filter: blur(12px) saturate(1.2);
    }

    .placeholder-icon {
      font-size: 48px;
      opacity: 0.45;
      animation: cam-pulse 2.4s ease-in-out infinite alternate;
    }

    .placeholder-text {
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-size: 13px;
      color: rgba(255, 255, 255, 0.40);
      letter-spacing: 0.02em;
    }

    @keyframes cam-pulse {
      from { opacity: 0.25; }
      to   { opacity: 0.55; }
    }

    /* Caption chip — glassmorphic pill, bottom-left, cyan accent */
    .label {
      position: absolute;
      bottom: 12px;
      left: 12px;
      background: rgba(0, 0, 0, 0.60);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      border: 1px solid rgba(0, 242, 255, 0.28);
      border-radius: 8px;
      padding: 4px 10px;
      font-size: 11px;
      font-family: 'Google Sans', 'Inter', sans-serif;
      color: rgba(0, 242, 255, 0.90);
      box-shadow: 0 0 10px rgba(0, 242, 255, 0.12);
      pointer-events: none;
    }
  `;

  render() {
    const activeSrc = this.frame || this.src;

    return html`
      ${activeSrc
        ? html`
            <img
              src=${activeSrc}
              alt=${this.label || 'Camera feed'}
              class=${this.mirrored ? 'mirrored' : ''}
            />
          `
        : html`
            <div class="placeholder">
              <span class="placeholder-icon">📷</span>
              <span class="placeholder-text">Waiting for camera feed…</span>
            </div>
          `}
      ${this.label ? html`<div class="label">${this.label}</div>` : ''}
    `;
  }
}
