import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-ticker')
export class GdmStageTicker extends LitElement {
  @property({ type: String }) text = '';
  @property({ type: Boolean, reflect: true }) active = false;
  @property({ type: String }) badgeText = 'LIVE FEED';
  @property({ type: String }) badgeColor = '#ff0055';
  @property({ type: String }) accentColor = '#00f2ff';
  @property({ type: String }) textColor = 'rgba(255,255,255,0.95)';
  @property({ type: Number }) fontSize = 16;
  @property({ type: Number }) height = 48;
  @property({ type: Number }) scrollSpeed = 35;

  static styles = css`
    :host {
      display: block;
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      z-index: 750;
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
      background: rgba(4, 6, 18, 0.92);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border-top: 1px solid rgba(var(--accent-rgb, 0,242,255), 0.25);
      box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.4);
      box-sizing: border-box;
    }
    .badge {
      flex-shrink: 0;
      min-width: 140px;
      padding: 0 16px;
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      border-right: 1px solid rgba(var(--accent-rgb, 0,242,255), 0.22);
      display: flex;
      align-items: center;
      gap: 8px;
      height: 100%;
      box-sizing: border-box;
    }
    .badge-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
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
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-weight: 600;
      letter-spacing: 0.03em;
      animation: ticker-scroll var(--scroll-duration, 35s) linear infinite;
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
    const barStyle = `height:${this.height}px`;
    const badgeStyle = [
      `color:${this.badgeColor}`,
      `background:${this.badgeColor}14`,
    ].join(';');
    const dotStyle = [
      `background-color:${this.badgeColor}`,
      `box-shadow:0 0 10px ${this.badgeColor}`,
    ].join(';');
    const textStyle = [
      `font-size:${this.fontSize}px`,
      `color:${this.textColor}`,
      `line-height:${this.height}px`,
      `--scroll-duration:${this.scrollSpeed}s`,
    ].join(';');

    return html`
      <div class="bar" style="${barStyle}">
        <div class="badge" style="${badgeStyle}">
          <span class="badge-dot" style="${dotStyle}"></span>
          ${this.badgeText}
        </div>
        <div class="scroll-area">
          <div class="scroll-text" style="${textStyle}">${this.text}</div>
        </div>
      </div>
    `;
  }
}
