import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-ticker')
export class GdmStageTicker extends LitElement {
  @property({ type: String }) text = '';
  @property({ type: Boolean, reflect: true }) active = false;

  static styles = css`
    :host {
      display: block;
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      z-index: 750;
      height: 48px;
      transform: translateY(100%);
      opacity: 0;
      transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.4s ease;
    }
    :host([active]) {
      transform: translateY(0);
      opacity: 1;
    }
    .bar {
      display: flex;
      align-items: center;
      height: 48px;
      background: rgba(4, 6, 18, 0.92);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border-top: 1px solid rgba(0, 242, 255, 0.22);
      box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.4);
    }
    .badge {
      flex-shrink: 0;
      min-width: 150px;
      padding: 0 16px;
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #ff0055;
      border-right: 1px solid rgba(0, 242, 255, 0.22);
      display: flex;
      align-items: center;
      gap: 8px;
      height: 100%;
      background: rgba(255, 0, 85, 0.08);
      box-sizing: border-box;
    }
    .badge-dot {
      width: 6px;
      height: 6px;
      background-color: #ff0055;
      border-radius: 50%;
      box-shadow: 0 0 10px #ff0055;
      animation: pulse-glow 1.5s infinite alternate;
    }
    .scroll-area {
      flex: 1;
      overflow: hidden;
      height: 100%;
      position: relative;
      mask-image: linear-gradient(to right, transparent, #000 40px, #000 calc(100% - 40px), transparent);
      -webkit-mask-image: linear-gradient(to right, transparent, #000 40px, #000 calc(100% - 40px), transparent);
    }
    .scroll-text {
      display: inline-block;
      white-space: nowrap;
      padding-left: 100%;
      line-height: 48px;
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-size: 14px;
      font-weight: 600;
      letter-spacing: 0.03em;
      color: rgba(255, 255, 255, 0.95);
      animation: ticker-scroll 35s linear infinite;
    }
    @keyframes ticker-scroll {
      from { transform: translateX(0); }
      to   { transform: translateX(-100%); }
    }
    @keyframes pulse-glow {
      from { opacity: 0.4; transform: scale(0.85); }
      to   { opacity: 1; transform: scale(1.15); }
    }
  `;

  render() {
    return html`
      <div class="bar">
        <div class="badge">
          <span class="badge-dot"></span>
          LIVE FEED
        </div>
        <div class="scroll-area">
          <div class="scroll-text">${this.text}</div>
        </div>
      </div>
    `;
  }
}
