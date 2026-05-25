import { LitElement, css, html, svg } from 'lit';
import { customElement, property } from 'lit/decorators.js';

interface Flight {
  callsign: string;
  altitude: number;
  speed: number;
  vrate: number;
  origin?: string;
  destination?: string;
}

@customElement('gdm-radar-view')
export class GdmStageRadar extends LitElement {
  @property({ type: Array }) flights: Flight[] = [];
  @property({ type: String }) lockedCallsign = '';
  @property({ type: Number }) zoom = 10.0;
  @property({ type: Boolean }) stretched = false;

  willUpdate(changedProperties: Map<string | number | symbol, unknown>) {
    if (typeof this.zoom !== 'number' || isNaN(this.zoom)) {
      const parsed = parseFloat(this.zoom as any);
      this.zoom = isNaN(parsed) ? 10.0 : parsed;
    }

    if (changedProperties.has('flights') && typeof this.flights === 'string') {
      try {
        const parsed = JSON.parse(this.flights);
        if (Array.isArray(parsed)) {
          this.flights = parsed;
        } else if (parsed && typeof parsed === 'object' && Array.isArray((parsed as any).flights)) {
          this.flights = (parsed as any).flights;
        } else {
          this.flights = [];
        }
      } catch (e) {
        console.error('[gdm-radar-view] Failed to parse flights string:', e);
        this.flights = [];
      }
    } else if (this.flights && typeof this.flights === 'object' && !Array.isArray(this.flights)) {
      if (Array.isArray((this.flights as any).flights)) {
        this.flights = (this.flights as any).flights;
      } else {
        this.flights = [];
      }
    }
    if (!Array.isArray(this.flights)) {
      this.flights = [];
    }
  }

  static styles = css`
    :host {
      display: block;
      width: 100%;
      height: 100%;
      position: relative;
      overflow: hidden;
      background: rgba(4, 8, 20, 0.95);
      font-family: 'Google Sans', 'Inter', monospace;
    }

    .compact-layout {
      display: flex;
      flex-direction: column;
      align-items: center;
      height: 100%;
      padding: 12px;
      box-sizing: border-box;
      gap: 12px;
    }

    .wide-layout {
      display: flex;
      flex-direction: row;
      align-items: flex-start;
      height: 100%;
      padding: 12px;
      box-sizing: border-box;
      gap: 16px;
    }

    .radar-wrapper {
      display: flex;
      justify-content: center;
      align-items: center;
      width: 100%;
      min-height: 0;
      min-width: 0;
      flex-shrink: 1;
    }

    .radar-svg {
      display: block;
      max-width: 100%;
      max-height: 100%;
      width: auto;
      height: auto;
    }

    .radar-svg * {
      pointer-events: none;
    }

    .radar-svg .blip-group,
    .radar-svg .blip-group * {
      pointer-events: auto !important;
      cursor: pointer;
    }

    @keyframes sweep {
      to { transform: rotate(360deg); }
    }

    .sweep {
      transform-origin: 100px 100px;
      animation: sweep 4s linear infinite;
    }

    .sweep-secondary {
      transform-origin: 150px 60px;
      animation: sweep 4s linear infinite;
    }

    .inventory {
      flex: 1;
      overflow-y: auto;
      max-height: 100%;
      display: flex;
      flex-direction: column;
      gap: 4px;
      min-width: 0;
    }

    .inventory-header {
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: rgba(0, 242, 255, 0.6);
      padding: 4px 8px;
      border-bottom: 1px solid rgba(0, 242, 255, 0.15);
      margin-bottom: 4px;
      flex-shrink: 0;
    }

    .flight-row {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 8px;
      border-radius: 4px;
      cursor: pointer;
      transition: background 0.15s ease;
      background: rgba(0, 242, 255, 0.03);
    }

    .flight-row:hover {
      background: rgba(0, 242, 255, 0.08);
    }

    .flight-row.locked {
      background: rgba(0, 242, 255, 0.12);
      border: 1px solid rgba(0, 242, 255, 0.3);
    }

    .flight-callsign {
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.06em;
      min-width: 70px;
    }

    .flight-fl {
      font-size: 11px;
      color: rgba(255, 255, 255, 0.75);
      min-width: 40px;
    }

    .flight-speed {
      font-size: 11px;
      color: rgba(255, 255, 255, 0.6);
      min-width: 50px;
    }

    .flight-vrate {
      font-size: 12px;
    }

    .lock-card {
      position: absolute;
      bottom: 16px;
      left: 16px;
      background: rgba(4, 12, 28, 0.85);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid rgba(0, 242, 255, 0.35);
      border-radius: 8px;
      padding: 14px 16px;
      min-width: 180px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), 0 0 16px rgba(0, 242, 255, 0.08);
      z-index: 100;
    }

    .lock-callsign {
      font-size: 20px;
      font-weight: 700;
      letter-spacing: 0.08em;
      color: #00f2ff;
      margin-bottom: 10px;
    }

    .lock-details {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .lock-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
    }

    .lock-label {
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: rgba(0, 242, 255, 0.55);
    }

    .lock-value {
      font-size: 13px;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.92);
    }

    .lock-close {
      position: absolute;
      top: 8px;
      right: 8px;
      background: none;
      border: none;
      color: rgba(0, 242, 255, 0.5);
      font-size: 14px;
      cursor: pointer;
      padding: 2px 6px;
      border-radius: 3px;
      line-height: 1;
      transition: color 0.15s ease;
    }

    .lock-close:hover {
      color: rgba(0, 242, 255, 0.9);
    }

    .zoom-controls {
      position: absolute;
      top: 12px;
      right: 12px;
      display: flex;
      flex-direction: column;
      gap: 4px;
      z-index: 100;
    }

    .zoom-btn {
      background: rgba(0, 242, 255, 0.08);
      border: 1px solid rgba(0, 242, 255, 0.25);
      color: rgba(0, 242, 255, 0.85);
      font-size: 16px;
      width: 28px;
      height: 28px;
      border-radius: 4px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.15s ease;
      line-height: 1;
      padding: 0;
    }

    .zoom-btn:hover {
      background: rgba(0, 242, 255, 0.18);
    }

    .zoom-label {
      font-size: 9px;
      text-align: center;
      color: rgba(0, 242, 255, 0.5);
      letter-spacing: 0.05em;
    }

    .inventory::-webkit-scrollbar {
      width: 4px;
    }
    .inventory::-webkit-scrollbar-track {
      background: rgba(0, 242, 255, 0.04);
    }
    .inventory::-webkit-scrollbar-thumb {
      background: rgba(0, 242, 255, 0.2);
      border-radius: 2px;
    }
  `;

  private _blipColor(vrate: number): string {
    const vr = typeof vrate === 'number' ? vrate : 0;
    if (vr < -250) return '#00ff88';
    if (vr > 250) return '#ffd60a';
    return '#00f2ff';
  }

  private _fl(altitude: number): number {
    const alt = typeof altitude === 'number' ? altitude : 30000;
    return Math.round(alt * 3.28084 / 100);
  }

  private _vrateSymbol(vrate: number): string {
    const vr = typeof vrate === 'number' ? vrate : 0;
    if (vr > 250) return '▲';
    if (vr < -250) return '▼';
    return '—';
  }

  private _blipPos(index: number, total: number, cx: number, cy: number, maxR: number): { x: number; y: number } {
    const zoomVal = typeof this.zoom === 'number' && !isNaN(this.zoom) ? this.zoom : parseFloat(this.zoom as any) || 10.0;
    const count = total || 1;
    const angle = (index / count) * 2 * Math.PI + zoomVal * 0.1;
    const flight = this.flights[index];
    const baseDist = 30 + (index * 15) % (maxR - 20);
    const altitude = (flight && typeof flight.altitude === 'number') ? flight.altitude : 30000;
    const altMod = (altitude % 1000) * 0.03;
    const dist = Math.min(Math.max(20, baseDist + altMod), maxR);
    return {
      x: cx + dist * Math.cos(angle),
      y: cy + dist * Math.sin(angle),
    };
  }

  private _diamondPoints(cx: number, cy: number, size: number): string {
    return `${cx},${cy - size} ${cx + size},${cy} ${cx},${cy + size} ${cx - size},${cy}`;
  }

  private _renderRadarSvg(viewW: number, viewH: number, cx: number, cy: number, r: number, secondary = false) {
    const sweepClass = secondary ? 'sweep-secondary' : 'sweep';
    const sweepOriginX = cx;
    const sweepOriginY = cy;
    const rings = [r * 0.316, r * 0.632, r * 0.947].map(rr => Math.round(rr));

    return svg`
      <svg
        class="radar-svg"
        viewBox="0 0 ${viewW} ${viewH}"
        width="${viewW}"
        height="${viewH}"
        xmlns="http://www.w3.org/2000/svg"
        style="transform-origin: ${sweepOriginX}px ${sweepOriginY}px"
      >
        <defs>
          <radialGradient
            id="${secondary ? 'sweep-grad-s' : 'sweep-grad'}"
            gradientUnits="userSpaceOnUse"
            cx="${cx}"
            cy="${cy}"
            r="${r}"
          >
            <stop offset="0%" stop-color="rgba(0, 242, 255, 0.45)"/>
            <stop offset="60%" stop-color="rgba(0, 242, 255, 0.15)"/>
            <stop offset="100%" stop-color="rgba(0, 242, 255, 0)"/>
          </radialGradient>
          <clipPath id="${secondary ? 'radar-clip-s' : 'radar-clip'}">
            <circle cx="${cx}" cy="${cy}" r="${r}"/>
          </clipPath>
        </defs>

        <circle cx="${cx}" cy="${cy}" r="${r}" fill="rgba(0,15,8,0.95)" stroke="rgba(0,242,255,0.25)" stroke-width="1"/>

        ${rings.map(rr => svg`
          <circle cx="${cx}" cy="${cy}" r="${rr}" fill="none" stroke="rgba(0,242,255,0.15)" stroke-width="0.5"/>
        `)}

        <line x1="${cx}" y1="${cy - r}" x2="${cx}" y2="${cy + r}" stroke="rgba(0,242,255,0.12)" stroke-width="0.5"/>
        <line x1="${cx - r}" y1="${cy}" x2="${cx + r}" y2="${cy}" stroke="rgba(0,242,255,0.12)" stroke-width="0.5"/>

        <path
          d="M ${cx} ${cy} L ${cx} ${cy - r} A ${r} ${r} 0 0 1 ${cx + r * 0.7071} ${cy - r * 0.7071} Z"
          fill="url(#${secondary ? 'sweep-grad-s' : 'sweep-grad'})"
          opacity="0.35"
          class="${sweepClass}"
          style="transform-origin: ${sweepOriginX}px ${sweepOriginY}px"
        />

        <line
          x1="${cx}" y1="${cy}"
          x2="${cx}" y2="${cy - r}"
          stroke="rgba(0,242,255,0.45)"
          stroke-width="1.5"
          class="${sweepClass}"
          style="transform-origin: ${sweepOriginX}px ${sweepOriginY}px"
        />

        <text x="${cx + 4}" y="${cy - r + 10}" fill="rgba(0,242,255,0.4)" font-size="6" font-family="monospace">32L/R</text>
        <text x="${cx + 4}" y="${cy + r - 4}" fill="rgba(0,242,255,0.4)" font-size="6" font-family="monospace">14L/R</text>

        <g clip-path="url(#${secondary ? 'radar-clip-s' : 'radar-clip'})">
          ${this.flights.map((f, i) => {
            const maxR = r - 10;
            const pos = this._blipPos(i, this.flights.length, cx, cy, maxR);
            const color = this._blipColor(f.vrate);
            const locked = f.callsign === this.lockedCallsign;
            const size = locked ? 6 : 4;
            const filterStyle = locked ? `filter: drop-shadow(0 0 4px ${color})` : '';
            return svg`
              <g class="blip-group" style="${filterStyle}" @click="${() => this._lockFlight(f.callsign)}">
                <polygon
                  points="${this._diamondPoints(pos.x, pos.y, size)}"
                  fill="${color}"
                  opacity="${locked ? 1.0 : 0.85}"
                />
                <text
                  x="${pos.x + size + 2}"
                  y="${pos.y + 3}"
                  fill="${color}"
                  font-size="7"
                  font-family="monospace"
                  opacity="0.9"
                >${f.callsign}</text>
              </g>
            `;
          })}
        </g>

        <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="rgba(0,242,255,0.3)" stroke-width="1"/>
        <text x="${cx}" y="${viewH - 4}" fill="rgba(0,242,255,0.35)" font-size="6" font-family="monospace" text-anchor="middle">LFBO · ${this.zoom.toFixed(1)}nm</text>
      </svg>
    `;
  }

  private _renderInventory() {
    return html`
      <div class="inventory">
        <div class="inventory-header">Traffic — ${this.flights.length} contacts</div>
        ${this.flights.map(f => {
          const color = this._blipColor(f.vrate);
          const locked = f.callsign === this.lockedCallsign;
          return html`
            <div
              class="flight-row ${locked ? 'locked' : ''}"
              @click="${() => this._lockFlight(f.callsign)}"
            >
              <span class="flight-callsign" style="color: ${color}">${f.callsign}</span>
              <span class="flight-fl">FL${this._fl(f.altitude).toString().padStart(3, '0')}</span>
              <span class="flight-speed">${f.speed}kt</span>
              <span class="flight-vrate" style="color: ${color}">${this._vrateSymbol(f.vrate)}</span>
            </div>
          `;
        })}
      </div>
    `;
  }

  private _renderLockCard() {
    if (!this.lockedCallsign) return html``;
    const f = this.flights.find(fl => fl.callsign === this.lockedCallsign);
    if (!f) return html``;
    const color = this._blipColor(f.vrate);
    return html`
      <div class="lock-card">
        <button class="lock-close" @click="${this._clearLock}">✕</button>
        <div class="lock-callsign" style="color: ${color}">${f.callsign}</div>
        <div class="lock-details">
          <div class="lock-row">
            <span class="lock-label">FL</span>
            <span class="lock-value">FL${this._fl(f.altitude).toString().padStart(3, '0')}</span>
          </div>
          <div class="lock-row">
            <span class="lock-label">Speed</span>
            <span class="lock-value">${f.speed} kt</span>
          </div>
          <div class="lock-row">
            <span class="lock-label">V/S</span>
            <span class="lock-value" style="color: ${color}">${this._vrateSymbol(f.vrate)} ${Math.abs(f.vrate)} fpm</span>
          </div>
          ${f.origin ? html`
            <div class="lock-row">
              <span class="lock-label">From</span>
              <span class="lock-value">${f.origin}</span>
            </div>
          ` : ''}
          ${f.destination ? html`
            <div class="lock-row">
              <span class="lock-label">To</span>
              <span class="lock-value">${f.destination}</span>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }

  private _renderZoomControls() {
    return html`
      <div class="zoom-controls">
        <button class="zoom-btn" @click="${() => this._zoomChange(-1)}">−</button>
        <div class="zoom-label">${this.zoom.toFixed(0)}nm</div>
        <button class="zoom-btn" @click="${() => this._zoomChange(+1)}">+</button>
      </div>
    `;
  }

  private _lockFlight(callsign: string) {
    this.dispatchEvent(new CustomEvent('target-lock', {
      detail: { callsign },
      bubbles: true,
      composed: true,
    }));
  }

  private _clearLock() {
    this.dispatchEvent(new CustomEvent('target-lock', {
      detail: { callsign: '' },
      bubbles: true,
      composed: true,
    }));
  }

  private _zoomChange(delta: number) {
    this.dispatchEvent(new CustomEvent('zoom-change', {
      detail: { delta },
      bubbles: true,
      composed: true,
    }));
  }

  render() {
    if (this.stretched) {
      return html`
        <div class="wide-layout">
          <div class="radar-wrapper">
            ${this._renderRadarSvg(200, 200, 100, 100, 95)}
          </div>
          <div class="radar-wrapper">
            ${this._renderRadarSvg(300, 120, 150, 60, 55, true)}
          </div>
          ${this._renderInventory()}
        </div>
        ${this._renderLockCard()}
        ${this._renderZoomControls()}
      `;
    }

    return html`
      <div class="compact-layout">
        <div class="radar-wrapper">
          ${this._renderRadarSvg(200, 200, 100, 100, 95)}
        </div>
        ${this._renderInventory()}
      </div>
      ${this._renderLockCard()}
      ${this._renderZoomControls()}
    `;
  }
}
