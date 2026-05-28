import { LitElement, css, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

@customElement('gdm-standby-slate')
export class GdmStageStandby extends LitElement {
  @property({ type: String }) badge = 'STANDBY / INTERMISSION';
  @property({ type: String }) title = 'Session Will Resume Shortly';
  @property({ type: String }) description = '';
  @property({ type: Number }) seconds = 0;
  @property({ type: Boolean, reflect: true }) active = false;
  @property({ type: Boolean, reflect: true }) fullscreen = false;

  @state() private _currentSeconds = 0;
  private _timerId: any = null;

  willUpdate(changedProperties: Map<string | number | symbol, unknown>) {
    // Use Lit's native change tracking. Restart whenever the slate becomes
    // active or the countdown duration changes — robust to element reuse.
    if (changedProperties.has('active') || changedProperties.has('seconds')) {
      if (this.active && this.seconds > 0) {
        this._currentSeconds = this.seconds;
        this._startCountdown();
      } else {
        this._stopCountdown();
        if (!this.active) this._currentSeconds = 0;
      }
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._stopCountdown();
  }

  private _startCountdown() {
    this._stopCountdown();
    this._timerId = setInterval(() => {
      if (this._currentSeconds > 1) {
        this._currentSeconds--;
      } else {
        this._currentSeconds = 0;
        this._stopCountdown();
        // Auto-dismiss the intermission slate when the countdown completes so
        // it never lingers on stage blocking subsequent content.
        this.active = false;
        this.dispatchEvent(new CustomEvent('standby-complete', { bubbles: true, composed: true }));
      }
    }, 1000);
  }

  private _stopCountdown() {
    if (this._timerId !== null) {
      clearInterval(this._timerId);
      this._timerId = null;
    }
  }

  static styles = css`
    :host {
      display: block !important;
      position: fixed !important;
      top: 0 !important;
      left: 0 !important;
      width: 100vw !important;
      height: 100vh !important;
      z-index: 99999 !important;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.5s ease;
    }
    :host([active]) {
      opacity: 1 !important;
      pointer-events: auto !important;
    }
    .backdrop {
      width: 100% !important;
      height: 100% !important;
      background:
        radial-gradient(ellipse 60% 50% at 50% 50%, rgba(0,242,255,0.06) 0%, transparent 70%),
        rgba(4, 6, 15, 0.95) !important;
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
      box-sizing: border-box !important;
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
      transition: all 0.3s ease;
    }
    :host([fullscreen]) .card {
      max-width: none !important;
      width: 100% !important;
      height: 100% !important;
      margin: 0 !important;
      border: none !important;
      border-radius: 0 !important;
      background: rgba(8, 10, 22, 0.6) !important;
      backdrop-filter: blur(32px) saturate(1.6) !important;
      -webkit-backdrop-filter: blur(32px) saturate(1.6) !important;
      justify-content: center !important;
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
          ${this._currentSeconds > 0 ? html`
            <div class="countdown">${this.formatSeconds(this._currentSeconds)}</div>
            <div class="pulse-line"></div>
          ` : ''}
        </div>
      </div>
    `;
  }
}
