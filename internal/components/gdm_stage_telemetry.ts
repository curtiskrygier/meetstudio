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
  @property({ type: String }) viewType = 'cards';
  @property({ type: Array }) metrics: Metric[] = [];
  @property({ type: Array }) chartData: number[] = [];

  static styles = css`
    :host {
      display: block;
      width: 100%;
      height: 100%;
      overflow: hidden;
      font-family: 'Google Sans', 'Inter', sans-serif;
    }
    .dashboard {
      background: rgba(4, 8, 20, 0.92);
      backdrop-filter: blur(16px);
      border: 1px solid rgba(0, 242, 255, 0.12);
      border-radius: 12px;
      display: flex;
      flex-direction: column;
      height: 100%;
      box-sizing: border-box;
    }
    .dashboard-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 14px 6px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      flex-shrink: 0;
    }
    .dashboard-title {
      font-size: 13px;
      font-weight: 700;
      color: #00f2ff;
    }
    .tabs {
      display: flex;
      gap: 4px;
    }
    .tab-btn {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.10);
      border-radius: 6px;
      padding: 3px 10px;
      font-size: 10px;
      color: rgba(255, 255, 255, 0.5);
      cursor: pointer;
      font-family: inherit;
      transition: background 0.15s, border-color 0.15s, color 0.15s;
    }
    .tab-btn.active {
      background: rgba(0, 242, 255, 0.12);
      border-color: rgba(0, 242, 255, 0.3);
      color: #00f2ff;
    }
    .dashboard-content {
      flex: 1;
      padding: 10px 14px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
      gap: 8px;
    }
    .metric-card {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 8px;
      padding: 8px 10px;
    }
    .metric-label {
      font-size: 10px;
      color: rgba(255, 255, 255, 0.45);
      margin-bottom: 4px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .metric-value {
      font-size: 18px;
      font-weight: 700;
      color: var(--metric-color, #fff);
    }
    .no-data {
      font-size: 11px;
      color: rgba(255, 255, 255, 0.2);
      align-self: center;
      margin: auto;
    }
    .chart-wrapper {
      flex: 1;
      display: flex;
      align-items: center;
    }
    .chart-wrapper svg {
      width: 100%;
      height: auto;
    }
  `;

  private _onTabClick(tabId: string) {
    this.dispatchEvent(new CustomEvent('tab-select', {
      detail: { tabId },
      bubbles: true,
      composed: true,
    }));
  }

  private _renderCards() {
    if (!this.metrics || this.metrics.length === 0) {
      return html`<div class="no-data">No data</div>`;
    }
    return html`
      <div class="cards-grid">
        ${this.metrics.map(m => html`
          <div class="metric-card" style="--metric-color: ${m.color || '#fff'}">
            <div class="metric-label">${m.label}</div>
            <div class="metric-value">${m.value}</div>
          </div>
        `)}
      </div>
    `;
  }

  private _renderChart() {
    const data = this.chartData && this.chartData.length > 0 ? this.chartData : [0, 0];
    const count = data.length;
    const points = data.map((v, i) => {
      const x = count === 1 ? 150 : (i / (count - 1)) * 300;
      const y = 80 - v * 0.8;
      return `${x},${y}`;
    });
    const polylinePoints = points.join(' ');
    const areaPoints = `0,80 ${polylinePoints} 300,80`;

    return html`
      <div class="chart-wrapper">
        <svg viewBox="0 0 300 80" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="spark-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#00f2ff" stop-opacity="0.3"/>
              <stop offset="100%" stop-color="#00f2ff" stop-opacity="0"/>
            </linearGradient>
          </defs>
          <polygon points="${areaPoints}" fill="url(#spark-grad)"/>
          <polyline
            points="${polylinePoints}"
            fill="none"
            stroke="#00f2ff"
            stroke-width="2"
            stroke-linejoin="round"
            stroke-linecap="round"
          />
        </svg>
      </div>
    `;
  }

  render() {
    return html`
      <div class="dashboard">
        <div class="dashboard-header">
          <div class="dashboard-title">${this.title}</div>
          <div class="tabs">
            ${this.tabs.map(tab => html`
              <button
                class="tab-btn ${tab.id === this.activeTabId ? 'active' : ''}"
                @click=${() => this._onTabClick(tab.id)}
              >${tab.label}</button>
            `)}
          </div>
        </div>
        <div class="dashboard-content">
          ${this.viewType === 'chart' ? this._renderChart() : this._renderCards()}
        </div>
      </div>
    `;
  }
}
