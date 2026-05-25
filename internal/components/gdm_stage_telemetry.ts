import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

interface Tab {
  id: string;
  label: string;
}

interface Metric {
  label: string;
  value: string;
  color?: string;
  data?: unknown;
}

@customElement('gdm-telemetry-dashboard')
export class GdmStageTelemetry extends LitElement {
  @property({ type: String }) title = 'Live Telemetry';
  @property({ type: Array }) tabs: Tab[] = [];
  @property({ type: String }) activeTabId = '';
  @property({ type: String }) viewType = 'both';
  @property({ type: Array }) metrics: Metric[] = [];
  @property({ type: Array }) chartData: number[] = [];

  willUpdate(changedProperties: Map<string | number | symbol, unknown>) {
    // Defensive parsing for stringified properties
    if (changedProperties.has('tabs') && typeof this.tabs === 'string') {
      try {
        this.tabs = JSON.parse(this.tabs);
      } catch (e) {
        console.error('[gdm-telemetry-dashboard] Failed to parse tabs:', e);
        this.tabs = [];
      }
    }
    // Unpack wrapped tabs object if needed
    if (this.tabs && !Array.isArray(this.tabs) && typeof this.tabs === 'object') {
      const anyTabs = this.tabs as any;
      if (Array.isArray(anyTabs.tabs)) {
        this.tabs = anyTabs.tabs;
      } else if (Array.isArray(anyTabs.explicitList)) {
        this.tabs = anyTabs.explicitList;
      }
    }

    if (changedProperties.has('metrics') && typeof this.metrics === 'string') {
      try {
        this.metrics = JSON.parse(this.metrics);
      } catch (e) {
        console.error('[gdm-telemetry-dashboard] Failed to parse metrics:', e);
        this.metrics = [];
      }
    }
    // Unpack wrapped metrics object if needed
    if (this.metrics && !Array.isArray(this.metrics) && typeof this.metrics === 'object') {
      const anyMetrics = this.metrics as any;
      if (Array.isArray(anyMetrics.metrics)) {
        this.metrics = anyMetrics.metrics;
      } else if (Array.isArray(anyMetrics.explicitList)) {
        this.metrics = anyMetrics.explicitList;
      }
    }

    if (changedProperties.has('chartData') && typeof this.chartData === 'string') {
      try {
        this.chartData = JSON.parse(this.chartData);
      } catch (e) {
        console.error('[gdm-telemetry-dashboard] Failed to parse chartData:', e);
        this.chartData = [];
      }
    }
    // Unpack wrapped chartData object if needed
    if (this.chartData && !Array.isArray(this.chartData) && typeof this.chartData === 'object') {
      const anyChart = this.chartData as any;
      if (Array.isArray(anyChart.chartData)) {
        this.chartData = anyChart.chartData;
      } else if (Array.isArray(anyChart.values)) {
        this.chartData = anyChart.values;
      } else if (Array.isArray(anyChart.explicitList)) {
        this.chartData = anyChart.explicitList;
      }
    }

    // Ensure types are always arrays
    if (!Array.isArray(this.tabs)) this.tabs = [];
    if (!Array.isArray(this.metrics)) this.metrics = [];
    if (!Array.isArray(this.chartData)) this.chartData = [];
  }

  static styles = css`
    :host {
      display: block;
      width: 100%;
      height: 100%;
      overflow: hidden;
      font-family: 'Google Sans', 'Inter', system-ui, -apple-system, sans-serif;
    }

    .dashboard {
      background: linear-gradient(160deg, rgba(6, 10, 24, 0.96) 0%, rgba(10, 15, 36, 0.98) 100%);
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
      border: 1px solid rgba(0, 242, 255, 0.20);
      border-radius: 16px;
      display: flex;
      flex-direction: column;
      height: 100%;
      box-sizing: border-box;
      box-shadow: 
        0 24px 64px rgba(0, 0, 0, 0.75), 
        inset 0 1px 0 rgba(255, 255, 255, 0.08),
        0 0 40px rgba(0, 242, 255, 0.04);
      position: relative;
    }

    /* Cyber grid overlay effect */
    .dashboard::after {
      content: '';
      position: absolute;
      inset: 0;
      background-image: radial-gradient(rgba(0, 242, 255, 0.03) 1px, transparent 1px);
      background-size: 16px 16px;
      pointer-events: none;
      border-radius: 16px;
      z-index: 0;
    }

    /* Moving scanline overlay */
    .scanlines {
      position: absolute;
      inset: 0;
      background: linear-gradient(
        to bottom,
        rgba(255,255,255,0),
        rgba(255,255,255,0) 50%,
        rgba(0, 242, 255, 0.02) 50%,
        rgba(0, 242, 255, 0.02)
      );
      background-size: 100% 4px;
      pointer-events: none;
      z-index: 5;
      opacity: 0.8;
      border-radius: 16px;
    }

    .scanlines::before {
      content: '';
      position: absolute;
      inset: 0;
      background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.15) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.03), rgba(0, 255, 0, 0.01), rgba(0, 0, 255, 0.03));
      background-size: 100% 2px, 3px 100%;
      pointer-events: none;
      border-radius: 16px;
    }

    .scanline-beam {
      position: absolute;
      top: -100px; left: 0; width: 100%; height: 100px;
      background: linear-gradient(to bottom, rgba(0, 242, 255, 0) 0%, rgba(0, 242, 255, 0.04) 100%);
      animation: scanline-move 8s linear infinite;
      pointer-events: none;
      z-index: 5;
    }

    @keyframes scanline-move {
      0% { top: -100px; }
      100% { top: 100%; }
    }

    .deck-subheader {
      display: flex;
      gap: 16px;
      padding: 6px 20px;
      background: rgba(0, 242, 255, 0.03);
      border-bottom: 1px solid rgba(0, 242, 255, 0.1);
      font-family: monospace;
      font-size: 9px;
      letter-spacing: 0.08em;
      color: rgba(255, 255, 255, 0.4);
      z-index: 1;
      flex-shrink: 0;
      overflow-x: auto;
      white-space: nowrap;
    }

    .deck-subheader::-webkit-scrollbar {
      display: none;
    }

    .sub-item {
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .sub-label {
      color: rgba(0, 242, 255, 0.5);
      font-weight: bold;
    }

    .sub-val {
      font-weight: 700;
    }

    .text-green { color: #00ffaa; text-shadow: 0 0 6px rgba(0, 255, 170, 0.3); }
    .text-blue { color: #00f2ff; text-shadow: 0 0 6px rgba(0, 242, 255, 0.3); }
    .text-yellow { color: #ffaa00; text-shadow: 0 0 6px rgba(255, 170, 0, 0.3); }

    .dashboard-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 20px;
      border-bottom: 1px solid rgba(0, 242, 255, 0.15);
      flex-shrink: 0;
      background: rgba(255, 255, 255, 0.015);
      z-index: 1;
    }

    .dashboard-title-wrapper {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .pulse-dot {
      width: 8px;
      height: 8px;
      background-color: #00ffaa;
      border-radius: 50%;
      box-shadow: 0 0 12px #00ffaa;
      animation: pulse-glow 1.5s infinite alternate;
    }

    .dashboard-title {
      font-size: 13px;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      background: linear-gradient(90deg, #00f2ff, #00ffaa);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      text-shadow: 0 0 20px rgba(0, 242, 255, 0.15);
    }

    .tabs {
      display: flex;
      gap: 8px;
    }

    .tab-btn {
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 20px;
      padding: 6px 14px;
      font-size: 10px;
      font-weight: 800;
      color: rgba(255, 255, 255, 0.50);
      cursor: pointer;
      font-family: inherit;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .tab-btn:hover {
      background: rgba(255, 255, 255, 0.08);
      color: rgba(255, 255, 255, 0.9);
      border-color: rgba(255, 255, 255, 0.18);
    }

    .tab-btn.active {
      background: rgba(0, 242, 255, 0.12);
      border-color: rgba(0, 242, 255, 0.50);
      color: #00f2ff;
      box-shadow: 0 0 16px rgba(0, 242, 255, 0.20);
      text-shadow: 0 0 8px rgba(0, 242, 255, 0.4);
    }

    .dashboard-content {
      flex: 1;
      padding: 16px 20px 20px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 16px;
      z-index: 1;
    }

    .cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 12px;
    }

    .metric-card {
      background: linear-gradient(135deg, rgba(16, 22, 44, 0.6) 0%, rgba(10, 14, 30, 0.8) 100%),
                  radial-gradient(rgba(var(--metric-glow, 0, 242, 255), 0.03) 1px, transparent 1px);
      background-size: auto, 6px 6px;
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 14px;
      padding: 14px 16px;
      transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
      position: relative;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      min-height: 92px;
      box-shadow: 
        0 4px 16px rgba(0, 0, 0, 0.25),
        inset 0 1px 0 rgba(255, 255, 255, 0.03);
    }

    /* HUD Corner brackets */
    .metric-card::after {
      content: '';
      position: absolute;
      inset: 0;
      pointer-events: none;
      background-image: 
        /* Top-Left */
        linear-gradient(to right, var(--metric-color, #00f2ff) 8px, transparent 8px),
        linear-gradient(to bottom, var(--metric-color, #00f2ff) 8px, transparent 8px),
        /* Top-Right */
        linear-gradient(to left, var(--metric-color, #00f2ff) 8px, transparent 8px),
        linear-gradient(to bottom, var(--metric-color, #00f2ff) 8px, transparent 8px),
        /* Bottom-Left */
        linear-gradient(to right, var(--metric-color, #00f2ff) 8px, transparent 8px),
        linear-gradient(to top, var(--metric-color, #00f2ff) 8px, transparent 8px),
        /* Bottom-Right */
        linear-gradient(to left, var(--metric-color, #00f2ff) 8px, transparent 8px),
        linear-gradient(to top, var(--metric-color, #00f2ff) 8px, transparent 8px);
      background-position: 
        top left, top left,
        top right, top right,
        bottom left, bottom left,
        bottom right, bottom right;
      background-size: 
        12px 2px, 2px 12px,
        12px 2px, 2px 12px,
        12px 2px, 2px 12px,
        12px 2px, 2px 12px;
      background-repeat: no-repeat;
      opacity: 0.25;
      transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
      z-index: 1;
    }

    /* Vibrant neon side bar accent */
    .metric-card::before {
      content: '';
      position: absolute;
      top: 0; left: 0; bottom: 0; width: 3px;
      background: var(--metric-color, #00f2ff);
      opacity: 0.4;
      transition: opacity 0.35s, width 0.35s;
      z-index: 2;
    }

    .metric-card:hover {
      background: linear-gradient(135deg, rgba(24, 32, 60, 0.75) 0%, rgba(14, 20, 42, 0.95) 100%),
                  radial-gradient(rgba(var(--metric-glow, 0, 242, 255), 0.06) 1px, transparent 1px);
      background-size: auto, 6px 6px;
      border-color: var(--metric-color, rgba(0, 242, 255, 0.45));
      transform: translateY(-4px) scale(1.02);
      box-shadow: 
        0 16px 36px rgba(0, 0, 0, 0.55), 
        0 0 24px rgba(var(--metric-glow, 0, 242, 255), 0.25);
    }

    .metric-card:hover::before {
      opacity: 1;
      width: 4px;
    }

    .metric-card:hover::after {
      opacity: 0.9;
      background-size: 
        18px 2px, 2px 18px,
        18px 2px, 2px 18px,
        18px 2px, 2px 18px,
        18px 2px, 2px 18px;
    }

    .metric-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      width: 100%;
      gap: 4px;
      z-index: 2;
    }

    .metric-label-wrapper {
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    .metric-label {
      font-size: 9px;
      font-weight: 800;
      color: rgba(255, 255, 255, 0.40);
      text-transform: uppercase;
      letter-spacing: 0.10em;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .metric-trend-pill {
      font-size: 8px;
      font-weight: 800;
      padding: 2px 6px;
      border-radius: 10px;
      font-family: monospace;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.05);
      flex-shrink: 0;
    }

    .metric-trend-pill.up {
      color: #00ffaa;
      background: rgba(0, 255, 170, 0.08);
      border-color: rgba(0, 255, 170, 0.15);
    }

    .metric-trend-pill.down {
      color: #ff3b30;
      background: rgba(255, 59, 48, 0.08);
      border-color: rgba(255, 59, 48, 0.15);
    }

    .metric-value-wrapper {
      display: flex;
      align-items: baseline;
      gap: 6px;
      margin-top: 10px;
      z-index: 2;
    }

    .metric-value {
      font-size: 28px;
      font-weight: 900;
      color: #ffffff;
      letter-spacing: -0.01em;
      font-family: 'Orbitron', 'Share Tech Mono', 'Roboto Mono', 'SF Mono', monospace;
      text-shadow: 
        0 0 4px var(--metric-color, rgba(0, 242, 255, 0.5)),
        0 0 12px var(--metric-color, rgba(0, 242, 255, 0.3)),
        0 0 24px var(--metric-color, rgba(0, 242, 255, 0.1));
      transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .metric-card:hover .metric-value {
      text-shadow: 
        0 0 8px var(--metric-color, rgba(0, 242, 255, 0.8)),
        0 0 18px var(--metric-color, rgba(0, 242, 255, 0.5)),
        0 0 32px var(--metric-color, rgba(0, 242, 255, 0.25));
    }

    .metric-arrow {
      font-size: 14px;
      font-weight: 900;
      font-family: system-ui;
    }

    .metric-arrow.up {
      color: #00ffaa;
      text-shadow: 0 0 8px rgba(0, 255, 170, 0.5);
    }

    .metric-arrow.down {
      color: #ff3b30;
      text-shadow: 0 0 8px rgba(255, 59, 48, 0.5);
    }

    .no-data {
      font-size: 11px;
      color: rgba(255, 255, 255, 0.3);
      align-self: center;
      margin: auto;
      letter-spacing: 0.04em;
    }

    .chart-wrapper {
      flex: 1;
      min-height: 120px;
      background: rgba(4, 6, 18, 0.5);
      border: 1px solid rgba(0, 242, 255, 0.12);
      border-radius: 14px;
      padding: 14px 16px;
      box-sizing: border-box;
      display: flex;
      flex-direction: column;
      position: relative;
      overflow: hidden;
      box-shadow: inset 0 2px 12px rgba(0, 0, 0, 0.4);
    }

    .chart-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      width: 100%;
      margin-bottom: 8px;
    }

    .chart-title {
      font-size: 9px;
      font-weight: 800;
      color: rgba(0, 242, 255, 0.6);
      text-transform: uppercase;
      letter-spacing: 0.1em;
    }

    .chart-stats {
      display: flex;
      gap: 12px;
      font-size: 9px;
      font-family: monospace;
      color: rgba(255, 255, 255, 0.4);
    }

    .chart-stat-value {
      font-weight: bold;
    }

    .chart-stat-value.high {
      color: #00ffaa;
    }

    .chart-stat-value.low {
      color: #ff3b30;
    }

    .chart-svg-container {
      flex: 1;
      width: 100%;
      position: relative;
    }

    .chart-svg-container svg {
      width: 100%;
      height: 100%;
      overflow: visible;
    }

    @keyframes pulse-glow {
      from { opacity: 0.5; transform: scale(0.9); }
      to { opacity: 1; transform: scale(1.1); }
    }

    @keyframes chart-dash {
      to {
        stroke-dashoffset: 0;
      }
    }
  `;

  private _onTabClick(tabId: string) {
    this.dispatchEvent(new CustomEvent('tab-select', {
      detail: { tabId },
      bubbles: true,
      composed: true,
    }));
  }

  private _parseMetric(m: Metric) {
    const label = m.label || '';
    const value = m.value || '';
    
    // Extract ticker name and change percentage, e.g. "NVDA (+2.50%)"
    let displayLabel = label;
    let trendPercent = '';
    let isStock = false;

    const parenIndex = label.indexOf('(');
    if (parenIndex !== -1) {
      displayLabel = label.substring(0, parenIndex).trim();
      trendPercent = label.substring(parenIndex + 1, label.length - 1).trim();
      isStock = true;
    }

    // Extract value and arrow trend symbol, e.g. "$914.85 ▲"
    let displayValue = value;
    let trendDirection: 'up' | 'down' | '' = '';

    if (value.includes('▲')) {
      displayValue = value.replace('▲', '').trim();
      trendDirection = 'up';
    } else if (value.includes('▼')) {
      displayValue = value.replace('▼', '').trim();
      trendDirection = 'down';
    }

    return { displayLabel, trendPercent, displayValue, trendDirection, isStock };
  }

  private _renderCards() {
    if (!this.metrics || this.metrics.length === 0) {
      return html`<div class="no-data">No active telemetry available</div>`;
    }
    return html`
      <div class="cards-grid">
        ${this.metrics.map(m => {
          const hex = m.color || '#fff';
          const { displayLabel, trendPercent, displayValue, trendDirection, isStock } = this._parseMetric(m);
          
          // Parse glow rgb
          let glowRgb = '0, 242, 255';
          if (hex.startsWith('#')) {
            const cleaned = hex.substring(1);
            if (cleaned.length === 6) {
              const r = parseInt(cleaned.substring(0, 2), 16);
              const g = parseInt(cleaned.substring(2, 4), 16);
              const b = parseInt(cleaned.substring(4, 6), 16);
              glowRgb = `${r}, ${g}, ${b}`;
            }
          }

          return html`
            <div class="metric-card" style="--metric-color: ${hex}; --metric-glow: ${glowRgb}">
              <div class="metric-header">
                <div class="metric-label-wrapper">
                  <div class="metric-label">${displayLabel}</div>
                </div>
                ${trendPercent 
                  ? html`
                      <div class="metric-trend-pill ${trendDirection}">
                        ${trendPercent}
                      </div>
                    ` 
                  : ''
                }
              </div>
              <div class="metric-value-wrapper">
                <div class="metric-value" style="color: ${hex}">${displayValue}</div>
                ${trendDirection === 'up' ? html`<span class="metric-arrow up">▲</span>` : ''}
                ${trendDirection === 'down' ? html`<span class="metric-arrow down">▼</span>` : ''}
              </div>
            </div>
          `;
        })}
      </div>
    `;
  }

  private _renderChart() {
    const data = this.chartData && this.chartData.length > 0 ? this.chartData : [0, 0];
    const count = data.length;
    
    // Calculate min and max for scaling
    const maxVal = Math.max(...data, 10);
    const minVal = Math.min(...data, 0);
    const range = maxVal - minVal || 1;
    
    // Scale coordinate logic
    const points = data.map((v, i) => {
      const x = count === 1 ? 150 : (i / (count - 1)) * 300;
      // Scale y between 8 and 72 (height 80)
      const y = 72 - ((v - minVal) / range) * 64;
      return { x, y, value: v };
    });

    const polylinePoints = points.map(p => `${p.x},${p.y}`).join(' ');
    const areaPoints = `0,80 ${polylinePoints} 300,80`;
    
    const latestPoint = points[points.length - 1] || { x: 300, y: 40, value: 0 };

    return html`
      <div class="chart-wrapper">
        <div class="chart-header">
          <div class="chart-title">Real-Time Sparkline</div>
          <div class="chart-stats">
            <div>MIN: <span class="chart-stat-value low">${minVal.toFixed(1)}</span></div>
            <div>MAX: <span class="chart-stat-value high">${maxVal.toFixed(1)}</span></div>
            <div>CUR: <span class="chart-stat-value" style="color: #00f2ff">${latestPoint.value.toFixed(1)}</span></div>
          </div>
        </div>
        <div class="chart-svg-container">
          <svg viewBox="0 0 300 80" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none">
            <defs>
              <linearGradient id="spark-grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#00f2ff" stop-opacity="0.30"/>
                <stop offset="100%" stop-color="#00f2ff" stop-opacity="0"/>
              </linearGradient>
              <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>
            
            <!-- Sleek background gridlines -->
            <line x1="0" y1="20" x2="300" y2="20" stroke="rgba(0, 242, 255, 0.05)" stroke-width="0.75" stroke-dasharray="3,3"/>
            <line x1="0" y1="40" x2="300" y2="40" stroke="rgba(0, 242, 255, 0.05)" stroke-width="0.75" stroke-dasharray="3,3"/>
            <line x1="0" y1="60" x2="300" y2="60" stroke="rgba(0, 242, 255, 0.05)" stroke-width="0.75" stroke-dasharray="3,3"/>
            
            <!-- Area fill under sparkline -->
            <polygon points="${areaPoints}" fill="url(#spark-grad)"/>
            
            <!-- High-tech grid vertical ticks -->
            <line x1="75" y1="0" x2="75" y2="80" stroke="rgba(255,255,255,0.015)" stroke-width="0.5"/>
            <line x1="150" y1="0" x2="150" y2="80" stroke="rgba(255,255,255,0.015)" stroke-width="0.5"/>
            <line x1="225" y1="0" x2="225" y2="80" stroke="rgba(255,255,255,0.015)" stroke-width="0.5"/>

            <!-- Glowing sparkline -->
            <polyline
              points="${polylinePoints}"
              fill="none"
              stroke="#00f2ff"
              stroke-width="2.2"
              stroke-linejoin="round"
              stroke-linecap="round"
              filter="url(#glow)"
            />

            <!-- Pulse tracker at the latest tick -->
            <circle
              cx="${latestPoint.x}"
              cy="${latestPoint.y}"
              r="4.5"
              fill="#00f2ff"
              stroke="#ffffff"
              stroke-width="1.5"
              style="box-shadow: 0 0 10px #00f2ff"
            />
            <circle
              cx="${latestPoint.x}"
              cy="${latestPoint.y}"
              r="10"
              fill="none"
              stroke="#00f2ff"
              stroke-width="1.5"
              opacity="0.6"
              style="transform-origin: ${latestPoint.x}px ${latestPoint.y}px; animation: pulse-glow 1.2s infinite alternate"
            />
          </svg>
        </div>
      </div>
    `;
  }

  render() {
    return html`
      <div class="dashboard">
        <div class="scanlines"></div>
        <div class="scanline-beam"></div>
        <div class="dashboard-header">
          <div class="dashboard-title-wrapper">
            <span class="pulse-dot"></span>
            <div class="dashboard-title">${this.title}</div>
          </div>
          <div class="tabs">
            ${this.tabs.map(tab => html`
              <button
                class="tab-btn ${tab.id === this.activeTabId ? 'active' : ''}"
                @click=${() => this._onTabClick(tab.id)}
              >${tab.label}</button>
            `)}
          </div>
        </div>
        <div class="deck-subheader">
          <div class="sub-item"><span class="sub-label">SYS_REF:</span> <span class="sub-val">A2UI_v0.8//SECURE_STAGE</span></div>
          <div class="sub-item"><span class="sub-label">LATENCY:</span> <span class="sub-val text-green">14ms</span></div>
          <div class="sub-item"><span class="sub-label">DATALINK:</span> <span class="sub-val text-blue">ONLINE [100%]</span></div>
          <div class="sub-item"><span class="sub-label">STK_FEED:</span> <span class="sub-val text-yellow">${this.activeTabId ? this.activeTabId.toUpperCase() : 'MULTICAST'}</span></div>
        </div>
        <div class="dashboard-content">
          ${this.viewType === 'chart' ? this._renderChart() : ''}
          ${this.viewType === 'cards' ? this._renderCards() : ''}
          ${this.viewType === 'both' ? html`${this._renderCards()}${this._renderChart()}` : ''}
        </div>
      </div>
    `;
  }
}
