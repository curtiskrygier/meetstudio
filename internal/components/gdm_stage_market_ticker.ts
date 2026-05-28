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
 * gdm-market-ticker — Upgraded "Global Market Scan" board with premium 3D animations and interaction.
 *
 * A realtime market-scanning showcase: a flip-clock time/date, a sweep scan-line,
 * a flexible grid of market sections (a big spread of instruments), and an
 * auto-computed "Ones to Watch" strip surfacing the biggest movers.
 *
 * Upgraded with:
 * 1. Passive 3D perspective slow float drift and tilt.
 * 2. Real-time interactive 3D pointer tracking (tilts board dynamically to follow cursor).
 * 3. Dynamic Specular Light / Specular Glass Highlight overlay.
 * 4. Ultra-smooth requestAnimationFrame interpolation.
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

  // 3D Perspective & Specular Glow animation state
  private _animId?: number;
  private _isHovered = false;

  private _targetTiltX = 0;
  private _targetTiltY = 0;
  private _targetTiltZ = 0;
  private _targetGlowX = 0;
  private _targetGlowY = 0;
  private _targetGlowOpacity = 0;

  private _curTiltX = 0;
  private _curTiltY = 0;
  private _curTiltZ = 0;
  private _curGlowX = 0;
  private _curGlowY = 0;
  private _curGlowOpacity = 0;

  connectedCallback() {
    super.connectedCallback();
    this._now = new Date();
    this.clockInterval = window.setInterval(() => { this._now = new Date(); }, 1000);
    this._start3DLoop();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.clockInterval) clearInterval(this.clockInterval);
    if (this._animId) cancelAnimationFrame(this._animId);
  }

  private _start3DLoop() {
    const loop = () => {
      if (!this._isHovered) {
        // Slow majestic floating animation in 3D perspective space
        const time = Date.now() * 0.001;
        this._targetTiltX = Math.sin(time * 0.8) * 2.8; 
        this._targetTiltY = Math.cos(time * 0.6) * 2.8; 
        this._targetTiltZ = Math.sin(time * 0.4) * 8;   // Depth float
        this._targetGlowOpacity = 0.12 + Math.sin(time * 1.5) * 0.04; // pulsing glass reflection

        // Orbit the glow position slowly over the board
        const rect = this.getBoundingClientRect();
        if (rect && rect.width > 0) {
          this._targetGlowX = rect.width / 2 + Math.sin(time * 0.4) * (rect.width * 0.18);
          this._targetGlowY = rect.height / 2 + Math.cos(time * 0.4) * (rect.height * 0.18);
        }
      }

      // Smooth interpolation ease
      const ease = 0.08;
      this._curTiltX += (this._targetTiltX - this._curTiltX) * ease;
      this._curTiltY += (this._targetTiltY - this._curTiltY) * ease;
      this._curTiltZ += (this._targetTiltZ - this._curTiltZ) * ease;
      this._curGlowX += (this._targetGlowX - this._curGlowX) * 0.12;
      this._curGlowY += (this._targetGlowY - this._curGlowY) * 0.12;
      this._curGlowOpacity += (this._targetGlowOpacity - this._curGlowOpacity) * ease;

      // Apply styles to shadow DOM `.board` wrapper
      const board = this.shadowRoot?.querySelector('.board') as HTMLElement;
      if (board) {
        board.style.setProperty('--tilt-x', `${this._curTiltX.toFixed(3)}deg`);
        board.style.setProperty('--tilt-y', `${this._curTiltY.toFixed(3)}deg`);
        board.style.setProperty('--tilt-z', `${this._curTiltZ.toFixed(2)}px`);
        board.style.setProperty('--glow-x', `${this._curGlowX.toFixed(1)}px`);
        board.style.setProperty('--glow-y', `${this._curGlowY.toFixed(1)}px`);
        board.style.setProperty('--glow-opacity', `${this._curGlowOpacity.toFixed(3)}`);
      }

      this._animId = requestAnimationFrame(loop);
    };
    this._animId = requestAnimationFrame(loop);
  }

  private _onPointerEnter() {
    this._isHovered = true;
    this._targetGlowOpacity = 0.55; // Intensify speculative reflection on hover
  }

  private _onPointerMove(e: PointerEvent) {
    const board = e.currentTarget as HTMLElement;
    const rect = board.getBoundingClientRect();
    
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    // Normalized displacement from center (-1.0 to 1.0)
    const normX = (x / rect.width) * 2 - 1;
    const normY = (y / rect.height) * 2 - 1;
    
    // Maximum tilt parameters (7.5 degrees and 15px pull forward)
    const maxTilt = 7.5;
    this._targetTiltX = -normY * maxTilt; 
    this._targetTiltY = normX * maxTilt;  
    this._targetTiltZ = 15;               
    
    this._targetGlowX = x;
    this._targetGlowY = y;
  }

  private _onPointerLeave() {
    this._isHovered = false;
    this._targetTiltX = 0;
    this._targetTiltY = 0;
    this._targetTiltZ = 0;
    this._targetGlowOpacity = 0;
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
      perspective: 2500px; /* Enable deep 3D perspective viewport */
    }
    :host([active]) { opacity: 1; }

    .board {
      pointer-events: auto;
      width: min(1480px, 94vw);
      max-height: 90vh;
      display: flex;
      flex-direction: column;
      background: linear-gradient(160deg, rgba(8, 12, 28, 0.95), rgba(4, 6, 16, 0.97));
      border: 1px solid rgba(0, 242, 255, 0.22);
      border-radius: 18px;
      box-shadow: 0 35px 95px rgba(0, 0, 0, 0.75), 0 0 50px rgba(0, 242, 255, 0.05);
      backdrop-filter: blur(32px);
      -webkit-backdrop-filter: blur(32px);
      overflow: hidden;
      position: relative;
      transform-style: preserve-3d;
      
      /* 3D Transform driven by JS animation loop properties */
      transform: translateY(24px) scale(0.975) rotateX(0deg) rotateY(0deg) translateZ(0px);
      transition: transform 0.6s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.3s ease, box-shadow 0.3s ease;
    }
    :host([active]) .board {
      transform: rotateX(var(--tilt-x, 0deg)) rotateY(var(--tilt-y, 0deg)) translateZ(var(--tilt-z, 0px));
      transition: border-color 0.3s ease, box-shadow 0.3s ease;
    }
    :host([active]) .board:hover {
      border-color: rgba(0, 242, 255, 0.45);
      box-shadow: 0 45px 110px rgba(0, 0, 0, 0.82), 0 0 65px rgba(0, 242, 255, 0.12);
    }

    /* Specular Reflection Highlighting Glow Overlay */
    .specular-glow {
      position: absolute;
      inset: 0;
      pointer-events: none;
      z-index: 4;
      background: radial-gradient(circle at var(--glow-x, 50%) var(--glow-y, 50%), rgba(0, 242, 255, 0.14) 0%, transparent 60%);
      opacity: var(--glow-opacity, 0);
      mix-blend-mode: screen;
    }

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
      <div 
        class="board" 
        style="--accent:${this.accentColor}"
        @pointermove=${this._onPointerMove}
        @pointerenter=${this._onPointerEnter}
        @pointerleave=${this._onPointerLeave}
      >
        <div class="specular-glow"></div>
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
