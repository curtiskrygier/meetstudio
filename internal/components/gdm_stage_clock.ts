import { LitElement, css, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { repeat } from 'lit/directives/repeat.js';

const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
const DAYS = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];

@customElement('gdm-clock')
export class GdmStageClock extends LitElement {
  @property({ type: Boolean }) showClock = true;
  @property({ type: Boolean }) showDate = true;
  @property({ type: String }) format = '24h'; // '12h' or '24h'
  @property({ type: String }) timezone = ''; // empty means local browser timezone
  @property({ type: String }) accentColor = 'accent';
  @property({ type: String }) variant = 'standard'; // 'standard' or 'flip'

  @state() private _currentTime = new Date();
  private _timerInterval?: number;

  connectedCallback() {
    super.connectedCallback();
    this._currentTime = new Date();
    this._timerInterval = window.setInterval(() => {
      this._currentTime = new Date();
    }, 1000);
  }

  disconnectedCallback() {
    if (this._timerInterval) {
      window.clearInterval(this._timerInterval);
    }
    super.disconnectedCallback();
  }

  static styles = css`
    :host {
      display: inline-block;
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
      color: #ffffff;
      box-sizing: border-box;
    }
    
    /* Standard Variant */
    .clock-container {
      display: inline-flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 10px 16px;
      background: rgba(10, 14, 32, 0.45);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 12px;
      backdrop-filter: blur(10px);
      -webkit-backdrop-filter: blur(10px);
      box-sizing: border-box;
      gap: 4px;
    }
    .time {
      font-size: 26px;
      font-weight: 800;
      letter-spacing: 0.05em;
      text-shadow: 0 0 10px var(--clock-accent, rgba(0, 242, 255, 0.4));
      line-height: 1;
    }
    .date {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      opacity: 0.6;
    }

    /* Flip Variant */
    .flip-row {
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .flip {
      display: inline-block;
      position: relative;
      min-width: 0.72em;
      padding: 6px 7px;
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
      font-weight: 800;
      font-size: 34px;
      line-height: 1;
      color: #fff;
      text-align: center;
      background: linear-gradient(180deg, #1c2236 0%, #131826 49.5%, #0c1020 50.5%, #161b2c 100%);
      border-radius: 7px;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.06), 0 4px 10px rgba(0,0,0,0.5);
      transform-origin: top center;
      backface-visibility: hidden;
      animation: flip-in 0.5s cubic-bezier(0.3, 1.25, 0.5, 1);
    }
    .flip.word {
      font-size: 14px;
      padding: 5px 8px;
      font-weight: 700;
      letter-spacing: 0.05em;
      background: linear-gradient(180deg, #1f273d 0%, #111524 100%);
    }
    .flip::after {
      content: '';
      position: absolute;
      left: 6%; right: 6%;
      top: 50%;
      height: 1px;
      background: rgba(0, 0, 0, 0.35);
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }
    .colon {
      font-size: 32px;
      font-weight: 800;
      color: var(--clock-accent, #00f2ff);
      animation: flash-blink 1s infinite alternate;
      line-height: 1;
      padding-bottom: 4px;
    }
    .seg-label {
      font-size: 9px;
      font-weight: 800;
      letter-spacing: 0.12em;
      color: var(--clock-accent, #00f2ff);
      opacity: 0.8;
      margin-left: 6px;
      align-self: flex-end;
      padding-bottom: 2px;
    }

    @keyframes flip-in {
      from { transform: rotateX(-90deg); opacity: 0; }
      to { transform: none; opacity: 1; }
    }
    @keyframes flash-blink {
      from { opacity: 0.2; }
      to { opacity: 1; }
    }
  `;

  private _renderFlipGroup(value: string, isWord = false) {
    return repeat(
      value.split(''),
      (ch, i) => `${i}:${ch}`,
      (ch) => html`<span class="flip ${isWord ? 'word' : ''}">${ch}</span>`,
    );
  }

  render() {
    let resolvedAccent = this.accentColor;
    if (this.accentColor === 'accent' || this.accentColor === 'cyan') resolvedAccent = '#00f2ff';
    else if (this.accentColor === 'success') resolvedAccent = '#00ff88';
    else if (this.accentColor === 'warning') resolvedAccent = '#ffd60a';
    else if (this.accentColor === 'danger') resolvedAccent = '#ff3b57';

    // Format options
    const options: Intl.DateTimeFormatOptions = {};
    if (this.timezone) {
      options.timeZone = this.timezone;
    }

    // Build standard date/time strings if needed
    let timeStr = '';
    if (this.showClock && this.variant !== 'flip') {
      const timeOpts: Intl.DateTimeFormatOptions = {
        ...options,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: this.format === '12h'
      };
      timeStr = this._currentTime.toLocaleTimeString(undefined, timeOpts);
    }

    let dateStr = '';
    if (this.showDate && this.variant !== 'flip') {
      const dateOpts: Intl.DateTimeFormatOptions = {
        ...options,
        weekday: 'short',
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      };
      dateStr = this._currentTime.toLocaleDateString(undefined, dateOpts);
    }

    // Render flip layout
    if (this.variant === 'flip') {
      const pad = (n: number) => String(n).padStart(2, '0');
      const hh = pad(this._currentTime.getHours());
      const mm = pad(this._currentTime.getMinutes());
      const ss = pad(this._currentTime.getSeconds());
      const day = DAYS[this._currentTime.getDay()];
      const dd = pad(this._currentTime.getDate());
      const mon = MONTHS[this._currentTime.getMonth()];

      return html`
        <div class="clock-container" style="--clock-accent: ${resolvedAccent}; background: transparent; border: none; backdrop-filter: none; box-shadow: none; display: flex; flex-direction: column; align-items: flex-end; gap: 8px;">
          ${this.showClock ? html`
            <div class="flip-row">
              ${this._renderFlipGroup(hh)}
              <span class="colon">:</span>
              ${this._renderFlipGroup(mm)}
              <span class="colon">:</span>
              ${this._renderFlipGroup(ss)}
              <span class="seg-label">LOCAL</span>
            </div>
          ` : ''}
          ${this.showDate ? html`
            <div class="flip-row" style="margin-top: 4px;">
              <span class="flip word">${day}</span>
              ${this._renderFlipGroup(dd)}
              <span class="flip word">${mon}</span>
            </div>
          ` : ''}
        </div>
      `;
    }

    // Standard Render fallback
    return html`
      <div class="clock-container" style="--clock-accent: ${resolvedAccent}; border-color: rgba(255,255,255,0.06);">
        ${this.showClock ? html`<div class="time" style="color: ${resolvedAccent};">${timeStr}</div>` : ''}
        ${this.showDate ? html`<div class="date">${dateStr}</div>` : ''}
      </div>
    `;
  }
}
