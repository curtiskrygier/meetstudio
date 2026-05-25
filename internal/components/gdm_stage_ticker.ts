import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-ticker')
export class GdmStageTicker extends LitElement {
  @property({ type: String }) text = '';
  @property({ type: Boolean }) active = false;

  static styles = css`
    :host {
      display: block;
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      z-index: 750;
      height: 36px;
      transform: translateY(100%);
      opacity: 0;
      transition: transform 0.35s ease, opacity 0.35s ease;
    }
    :host([active]) {
      transform: translateY(0);
      opacity: 1;
    }
    .bar {
      display: flex;
      align-items: center;
      height: 36px;
      background: rgba(4, 6, 15, 0.88);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
    }
    .badge {
      flex-shrink: 0;
      min-width: 160px;
      padding: 0 16px;
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #00f2ff;
      border-right: 1px solid rgba(0, 242, 255, 0.25);
      display: flex;
      align-items: center;
      height: 100%;
    }
    .scroll-area {
      flex: 1;
      overflow: hidden;
      height: 100%;
      display: flex;
      align-items: center;
    }
    .scroll-text {
      white-space: nowrap;
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-size: 13px;
      font-weight: 500;
      color: rgba(255, 255, 255, 0.90);
      animation: ticker-scroll 20s linear infinite;
    }
    @keyframes ticker-scroll {
      from { transform: translateX(100%); }
      to   { transform: translateX(-100%); }
    }
  `;

  render() {
    return html`
      <div class="bar">
        <div class="badge">Announcement</div>
        <div class="scroll-area">
          <div class="scroll-text">${this.text}</div>
        </div>
      </div>
    `;
  }
}
