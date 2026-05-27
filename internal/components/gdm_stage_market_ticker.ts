import { LitElement, css, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { repeat } from 'lit/directives/repeat.js';

interface ScanItem {
  symbol: string;
  price: number;
  changePercent: number;
  isUp?: boolean;
  label?: string;
}

interface ScanSection {
  label: string;
  accent?: string;
  items: ScanItem[];
}

const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
const DAYS = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];

/**
 * gdm-market-ticker — "Global Market Scan" board.
 *
 * A realtime market-scanning showcase: a flip-clock time/date, a sweep scan-line,
 * a flexible grid of market sections (a big spread of instruments), and an
 * auto-computed "Ones to Watch" strip surfacing the biggest movers. Designed to
 * highlight the live capability, not a personal portfolio.
 *
 * Flip + flash are driven by Lit's keyed `repeat`: when a digit/price changes its
 * key changes, Lit creates a fresh element, and the entrance CSS animation plays
 * once — no manual animation bookkeeping required.
 */
@customElement('gdm-market-ticker')
export class GdmStageMarketTicker extends LitElement {
  @property({ type: Array }) sections: ScanSection[] = [];
  @property({ type: Boolean, reflect: true }) active = false;
  @property({ type: String }) badgeText = 'GLOBAL MARKET SCAN';
  @property({ type: String }) accentColor = '#00f2ff';
  @property({ type: Number }) watchCount = 5;
  @property({ type: Boolean }) showClock = true;
  @property({ type: Boolean }) showDate = true;

  @state() private _now = new Date();
  private clockInterval?: number;

  connectedCallback() {
    super.connectedCallback();
    this._now = new Date();
    this.clockInterval = window.setInterval(() => { this._now = new Date(); }, 1000);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.clockInterval) clearInterval(this.clockInterval);
  }

  static styles = css`
    :host {
      position: fixed;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 760;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.5s ease;
      font-family: 'Google Sans', 'Inter', sans-serif;
    }
    :host([active]) { opacity: 1; }

    .board {
      pointer-events: auto;
      width: min(1480px, 94vw);
      max-height: 90vh;
      display: flex;
      flex-direction: column;
      background: linear-gradient(160deg, rgba(10, 14, 32, 0.94), rgba(6, 9, 22, 0.96));
      border: 1px solid rgba(0, 242, 255, 0.28);
      border-radius: 18px;
      box-shadow: 0 24px 80px rgba(0, 0, 0, 0.65), 0 0 48px rgba(0, 242, 255, 0.08);
      backdrop-filter: blur(28px);
      -webkit-backdrop-filter: blur(28px);
      overflow: hidden;
      position: relative;
      transform: translateY(24px) scale(0.985);
      transition: transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);
    }
    :host([active]) .board { transform: none; }

    /* sweeping scan line */
    .scan-line {
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 2px;
      background: linear-gradient(90deg, transparent, var(--accent, #00f2ff), transparent);
      box-shadow: 0 0 14px var(--accent, #00f2ff);
      animation: scan-sweep 4.5s linear infinite;
      z-index: 5;
      opacity: 0.7;
    }
    @keyframes scan-sweep {
      0% { transform: translateY(0); opacity: 0; }
      8% { opacity: 0.8; }
      92% { opacity: 0.8; }
      100% { transform: translateY(86vh); opacity: 0; }
    }

    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 24px;
      padding: 18px 26px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.07);
      background: rgba(0, 0, 0, 0.2);
    }
    .title-block { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
    .live {
      display: inline-flex;
      align-items: center;
      gap: 9px;
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.18em;
      color: #ff3b57;
      text-transform: uppercase;
    }
    .live-dot {
      width: 8px; height: 8px; border-radius: 50%;
      background: #ff3b57;
      box-shadow: 0 0 10px #ff3b57;
      animation: pulse 1.3s infinite alternate;
    }
    @keyframes pulse { from { opacity: 0.35; transform: scale(0.8); } to { opacity: 1; transform: scale(1.25); } }
    .title {
      font-size: 26px;
      font-weight: 800;
      letter-spacing: 0.04em;
      color: #fff;
      text-transform: uppercase;
      white-space: nowrap;
    }
    .subtitle {
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.14em;
      color: rgba(255, 255, 255, 0.45);
      text-transform: uppercase;
    }
    .subtitle b { color: var(--accent, #00f2ff); }

    /* --- flip clock --- */
    .clock-block { display: flex; flex-direction: column; align-items: flex-end; gap: 8px; flex-shrink: 0; }
    .flip-row { display: flex; align-items: center; gap: 4px; }
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
    .flip::after {
      content: '';
      position: absolute;
      left: 6%; right: 6%;
      top: 50%;
      height: 1px;
      background: rgba(0, 0, 0, 0.55);
      transform: translateY(-0.5px);
    }
    @keyframes flip-in {
      0%   { transform: rotateX(90deg);  opacity: 0; }
      55%  { transform: rotateX(-14deg); opacity: 1; }
      100% { transform: rotateX(0deg); }
    }
    .colon {
      font-family: 'JetBrains Mono', monospace;
      font-weight: 800;
      font-size: 30px;
      color: var(--accent, #00f2ff);
      animation: pulse 1s infinite alternate;
      padding: 0 1px;
    }
    .seg-label {
      font-size: 9px;
      letter-spacing: 0.1em;
      color: rgba(255,255,255,0.35);
      align-self: flex-end;
      margin-left: 6px;
      padding-bottom: 4px;
    }
    .date-row .flip {
      font-size: 18px;
      padding: 5px 9px;
      background: linear-gradient(180deg, #182238 0%, #111a2b 49.5%, #0b1322 50.5%, #141d30 100%);
    }
    .date-row .flip.word { letter-spacing: 0.06em; }

    /* --- market sections --- */
    .sections {
      flex: 1;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
      gap: 1px;
      background: rgba(255, 255, 255, 0.05);
      overflow: auto;
    }
    .section {
      background: rgba(8, 11, 24, 0.6);
      display: flex;
      flex-direction: column;
      min-width: 0;
    }
    .section-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 9px 14px;
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--sec-accent, #00f2ff);
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      background: rgba(0, 0, 0, 0.25);
    }
    .section-count { font-size: 9px; color: rgba(255,255,255,0.3); font-weight: 600; }
    .rows { display: flex; flex-direction: column; }
    .row {
      display: grid;
      grid-template-columns: 1fr auto auto;
      align-items: center;
      gap: 10px;
      padding: 7px 14px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    }
    .sym-wrap { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
    .sym { font-size: 13px; font-weight: 800; color: rgba(255,255,255,0.95); letter-spacing: 0.02em; }
    .sym-label { font-size: 9px; color: rgba(255,255,255,0.38); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .price {
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
      font-weight: 700;
      color: #fff;
      text-align: right;
    }
    .chg {
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      font-weight: 700;
      display: inline-flex;
      align-items: center;
      gap: 3px;
      padding: 2px 7px;
      border-radius: 5px;
      min-width: 64px;
      justify-content: flex-end;
    }
    .chg.up { color: #00ff88; background: rgba(0,255,136,0.08); }
    .chg.down { color: #ff3b57; background: rgba(255,59,87,0.08); }
    .chg.flash.up { animation: flash-up 0.9s ease-out; }
    .chg.flash.down { animation: flash-down 0.9s ease-out; }
    @keyframes flash-up {
      0% { background: rgba(0,255,136,0.45); box-shadow: 0 0 12px rgba(0,255,136,0.5); }
      100% { background: rgba(0,255,136,0.08); box-shadow: none; }
    }
    @keyframes flash-down {
      0% { background: rgba(255,59,87,0.45); box-shadow: 0 0 12px rgba(255,59,87,0.5); }
      100% { background: rgba(255,59,87,0.08); box-shadow: none; }
    }

    /* --- ones to watch --- */
    .watch {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 11px 22px;
      border-top: 1px solid rgba(255, 214, 10, 0.18);
      background: rgba(255, 214, 10, 0.04);
      overflow: hidden;
    }
    .watch-label {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.12em;
      color: #ffd60a;
      text-transform: uppercase;
      white-space: nowrap;
      flex-shrink: 0;
    }
    .watch-items { display: flex; gap: 22px; overflow: hidden; }
    .watch-item {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
      font-weight: 700;
      white-space: nowrap;
    }
    .watch-item .w-sym { color: #fff; }
    .watch-item.up .w-chg { color: #00ff88; }
    .watch-item.down .w-chg { color: #ff3b57; }
    .empty { padding: 40px; text-align: center; color: rgba(255,255,255,0.4); font-style: italic; }
  `;

  private _renderFlipGroup(value: string, isWord = false) {
    // each char keyed by position+value so a changed char re-creates → flip animation
    return repeat(
      value.split(''),
      (ch, i) => `${i}:${ch}`,
      (ch) => html`<span class="flip ${isWord ? 'word' : ''}">${ch}</span>`,
    );
  }

  private _renderClock() {
    const pad = (n: number) => String(n).padStart(2, '0');
    const hh = pad(this._now.getHours());
    const mm = pad(this._now.getMinutes());
    const ss = pad(this._now.getSeconds());
    const day = DAYS[this._now.getDay()];
    const dd = pad(this._now.getDate());
    const mon = MONTHS[this._now.getMonth()];

    return html`
      <div class="clock-block">
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
          <div class="flip-row date-row">
            <span class="flip word">${day}</span>
            ${this._renderFlipGroup(dd)}
            <span class="flip word">${mon}</span>
          </div>
        ` : ''}
      </div>
    `;
  }

  private _renderRow(item: ScanItem) {
    const up = item.isUp ?? (item.changePercent >= 0);
    const caret = up ? '▲' : '▼';
    const sign = up ? '+' : '';
    // adaptive precision: sub-$10 instruments (FX / small caps / cheap crypto) need more decimals
    const dp = item.price < 10 ? 4 : 2;
    const price = item.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: dp });
    return html`
      <div class="row">
        <div class="sym-wrap">
          <span class="sym">${item.symbol}</span>
          ${item.label ? html`<span class="sym-label">${item.label}</span>` : ''}
        </div>
        <span class="price">${price}</span>
        ${repeat(
          [item.changePercent],
          // key on the rounded change so a moved price re-creates the cell → flash
          (v) => `${item.symbol}:${v.toFixed(2)}:${up}`,
          (v) => html`<span class="chg flash ${up ? 'up' : 'down'}">${caret} ${sign}${v.toFixed(2)}%</span>`,
        )}
      </div>
    `;
  }

  private _movers(): ScanItem[] {
    const all = this.sections.flatMap((s) => s.items || []);
    return [...all]
      .sort((a, b) => Math.abs(b.changePercent) - Math.abs(a.changePercent))
      .slice(0, Math.max(0, this.watchCount));
  }

  render() {
    const total = this.sections.reduce((n, s) => n + (s.items?.length || 0), 0);
    const movers = this._movers();
    return html`
      <div class="board" style="--accent:${this.accentColor}">
        <div class="scan-line"></div>

        <div class="header">
          <div class="title-block">
            <span class="live"><span class="live-dot"></span>${this.badgeText}</span>
            <span class="title">Global Market Scan</span>
            <span class="subtitle">scanning <b>${total}</b> instruments · realtime feed</span>
          </div>
          ${this._renderClock()}
        </div>

        ${total === 0 ? html`<div class="empty">Awaiting market feed…</div>` : html`
          <div class="sections">
            ${this.sections.map((sec) => html`
              <div class="section" style="--sec-accent:${sec.accent || this.accentColor}">
                <div class="section-head">
                  <span>${sec.label}</span>
                  <span class="section-count">${(sec.items?.length || 0)}</span>
                </div>
                <div class="rows">
                  ${(sec.items || []).map((it) => this._renderRow(it))}
                </div>
              </div>
            `)}
          </div>

          ${movers.length ? html`
            <div class="watch">
              <span class="watch-label">⭐ Ones to Watch</span>
              <div class="watch-items">
                ${movers.map((m) => {
                  const up = m.isUp ?? (m.changePercent >= 0);
                  return html`
                    <span class="watch-item ${up ? 'up' : 'down'}">
                      <span class="w-sym">${m.symbol}</span>
                      <span class="w-chg">${up ? '▲' : '▼'} ${up ? '+' : ''}${m.changePercent.toFixed(2)}%</span>
                    </span>
                  `;
                })}
              </div>
            </div>
          ` : ''}
        `}
      </div>
    `;
  }
}
