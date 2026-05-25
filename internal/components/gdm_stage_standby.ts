import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-standby-slate')
export class GdmStageStandby extends LitElement {
  @property({ type: String }) badge = 'STANDBY / INTERMISSION';
  @property({ type: String }) title = 'Session Will Resume Shortly';
  @property({ type: String }) description = '';
  @property({ type: Number }) seconds = 0;
  @property({ type: Boolean, reflect: true }) active = false;

  static styles = css`
    :host {
      display: block;
      position: fixed;
      inset: 0;
      z-index: 900;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.5s ease;
    }
    :host([active]) {
      opacity: 1;
      pointer-events: auto;
    }
    .backdrop {
      width: 100%;
      height: 100%;
      background:
        radial-gradient(ellipse 60% 50% at 50% 50%, rgba(0,242,255,0.06) 0%, transparent 70%),
        rgba(4, 6, 15, 0.95);
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .card {
      max-width: 600px;
      width: 100%;
      margin: 0 24px;
      background: rgba(8, 10, 22, 0.72);
      backdrop-filter: blur(24px) saturate(1.4);
      -webkit-backdrop-filter: blur(24px) saturate(1.4);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 24px;
      padding: 48px;
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      box-sizing: border-box;
    }
    .badge {
      display: inline-block;
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: #00f2ff;
      border: 1px solid rgba(0, 242, 255, 0.3);
      border-radius: 99px;
      padding: 4px 14px;
      margin-bottom: 20px;
    }
    .title {
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-size: 32px;
      font-weight: 800;
      color: #fff;
      margin: 0 0 10px;
      line-height: 1.2;
    }
    .description {
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-size: 15px;
      color: rgba(255, 255, 255, 0.55);
      line-height: 1.6;
      margin: 0 0 32px;
    }
    .countdown {
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-size: 64px;
      font-weight: 800;
      color: #00f2ff;
      letter-spacing: -0.02em;
      text-shadow: 0 0 30px rgba(0, 242, 255, 0.5);
      line-height: 1;
      margin-bottom: 16px;
    }
    .pulse-line {
      width: 120px;
      height: 2px;
      background: linear-gradient(90deg, transparent, #00f2ff, transparent);
      animation: pulse 1.5s ease-in-out infinite alternate;
    }
    @keyframes pulse {
      from { opacity: 0.4; }
      to   { opacity: 1; }
    }
  `;

  private formatSeconds(s: number): string {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
  }

  render() {
    return html`
      <div class="backdrop">
        <div class="card">
          <div class="badge">${this.badge}</div>
          <div class="title">${this.title}</div>
          ${this.description ? html`<div class="description">${this.description}</div>` : ''}
          ${this.seconds > 0 ? html`
            <div class="countdown">${this.formatSeconds(this.seconds)}</div>
            <div class="pulse-line"></div>
          ` : ''}
        </div>
      </div>
    `;
  }
}
