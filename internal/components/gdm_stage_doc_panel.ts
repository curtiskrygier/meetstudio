import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

/**
 * gdm-doc-panel — A2UI panel component.
 * Fills its grid cell and centres a glassmorphic document / file card.
 * An optional call-to-action button opens a URL in a new tab.
 *
 * Props:
 *   title       — card heading (default 'Document Ready')
 *   body        — descriptive summary; white-space: pre-wrap preserves line breaks
 *   url         — if set, renders a pill CTA button that opens this URL
 *   buttonLabel — CTA label (default 'Open Document')
 *   accent      — accent colour for the top bar and button (default '#00f2ff')
 */
@customElement('gdm-doc-panel')
export class GdmStageDocPanel extends LitElement {
  @property({ type: String }) title = 'Document Ready';
  @property({ type: String }) body = '';
  @property({ type: String }) url = '';
  @property({ type: String }) buttonLabel = 'Open Document';
  @property({ type: String }) accent = '#00f2ff';

  static styles = css`
    :host {
      display: block;
      width: 100%;
      height: 100%;
      overflow: hidden;
    }

    /* Panel fills the cell and centres the card */
    .panel {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 100%;
      height: 100%;
      background: rgba(2, 4, 12, 0.98);
      box-sizing: border-box;
      padding: 24px;
    }

    /* Glassmorphic card chrome — matches gdm-stage-card conventions */
    .card {
      width: 90%;
      max-width: 720px;
      background: rgba(8, 10, 20, 0.72);
      backdrop-filter: blur(18px) saturate(1.4);
      -webkit-backdrop-filter: blur(18px) saturate(1.4);
      border: 1px solid rgba(255, 255, 255, 0.10);
      border-radius: 20px;
      padding: 32px 36px 28px;
      box-shadow:
        0 0 0 1px rgba(255, 255, 255, 0.04) inset,
        0 8px 40px rgba(0, 0, 0, 0.60),
        0 0 36px -6px var(--accent-glow, rgba(0, 242, 255, 0.22));
      display: flex;
      flex-direction: column;
      gap: 0;
      animation: fade-up 0.45s cubic-bezier(0.22, 1, 0.36, 1) both;
    }

    @keyframes fade-up {
      from { opacity: 0; transform: translateY(16px) scale(0.98); }
      to   { opacity: 1; transform: translateY(0)    scale(1);    }
    }

    /* Thin accent line at the top of the card */
    .accent-bar {
      width: 48px;
      height: 3px;
      border-radius: 99px;
      background: var(--accent-color, #00f2ff);
      box-shadow: 0 0 12px var(--accent-color, #00f2ff);
      margin-bottom: 18px;
      flex-shrink: 0;
    }

    .title {
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-size: 22px;
      font-weight: 700;
      letter-spacing: -0.015em;
      color: #fff;
      margin: 0 0 12px;
      line-height: 1.25;
    }

    .body {
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-size: 14.5px;
      color: rgba(255, 255, 255, 0.70);
      line-height: 1.65;
      margin: 0 0 24px;
      white-space: pre-wrap;
      word-break: break-word;
    }

    /* Pill CTA button — uses accent colour */
    .cta-link {
      display: inline-block;
      align-self: flex-start;
      padding: 10px 24px;
      border-radius: 99px;
      background: var(--accent-color, #00f2ff);
      color: #fff;
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-size: 14px;
      font-weight: 600;
      letter-spacing: 0.01em;
      text-decoration: none;
      box-shadow:
        0 0 18px -2px var(--accent-glow, rgba(0, 242, 255, 0.40)),
        0 2px 8px rgba(0, 0, 0, 0.45);
      transition: filter 0.2s ease, transform 0.15s ease;
    }

    .cta-link:hover {
      filter: brightness(1.15);
      transform: translateY(-1px);
    }

    .cta-link:active {
      filter: brightness(0.92);
      transform: translateY(0);
    }
  `;

  render() {
    const accentGlow = `${this.accent}55`;
    return html`
      <div class="panel">
        <div
          class="card"
          style="--accent-color:${this.accent};--accent-glow:${accentGlow}"
        >
          <div class="accent-bar"></div>
          ${this.title
            ? html`<div class="title">${this.title}</div>`
            : ''}
          ${this.body
            ? html`<p class="body">${this.body}</p>`
            : ''}
          ${this.url
            ? html`
                <a
                  class="cta-link"
                  href="${this.url}"
                  target="_blank"
                  rel="noopener noreferrer"
                >${this.buttonLabel}</a>
              `
            : ''}
        </div>
      </div>
    `;
  }
}
