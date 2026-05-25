import { LitElement, css, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

@customElement('gdm-poll-overlay')
export class GdmStagePoll extends LitElement {
  @property({ type: String }) question = '';
  @property({ type: Array }) options: string[] = [];
  @property({ type: Array }) values: number[] = [];
  @property({ type: String }) layout: 'rows' | 'grid' = 'rows';
  @property({ type: Boolean, reflect: true }) active = false;

  willUpdate(changedProperties: Map<string | number | symbol, unknown>) {
    if (changedProperties.has('options') && typeof this.options === 'string') {
      try {
        const parsed = JSON.parse(this.options);
        if (Array.isArray(parsed)) {
          this.options = parsed;
        } else if (parsed && typeof parsed === 'object' && Array.isArray((parsed as any).options)) {
          this.options = (parsed as any).options;
        } else {
          this.options = [];
        }
      } catch (e) {
        console.error('[gdm-poll-overlay] Failed to parse options string:', e);
        this.options = [];
      }
    } else if (this.options && typeof this.options === 'object' && !Array.isArray(this.options)) {
      if (Array.isArray((this.options as any).options)) {
        this.options = (this.options as any).options;
      } else {
        this.options = [];
      }
    }

    if (changedProperties.has('values') && typeof this.values === 'string') {
      try {
        const parsed = JSON.parse(this.values);
        if (Array.isArray(parsed)) {
          this.values = parsed;
        } else if (parsed && typeof parsed === 'object' && Array.isArray((parsed as any).values)) {
          this.values = (parsed as any).values;
        } else {
          this.values = [];
        }
      } catch (e) {
        console.error('[gdm-poll-overlay] Failed to parse values string:', e);
        this.values = [];
      }
    } else if (this.values && typeof this.values === 'object' && !Array.isArray(this.values)) {
      if (Array.isArray((this.values as any).values)) {
        this.values = (this.values as any).values;
      } else {
        this.values = [];
      }
    }

    if (!Array.isArray(this.options)) this.options = [];
    if (!Array.isArray(this.values)) this.values = [];
  }

  @state() private _voted = -1;

  static styles = css`
    :host {
      display: block;
      position: fixed;
      bottom: 140px;
      right: 40px;
      max-width: 360px;
      z-index: 810;
      opacity: 0;
      transform: translateX(110%);
      transition: opacity 0.4s ease, transform 0.4s cubic-bezier(0.22, 1, 0.36, 1);
    }
    :host([active]) {
      opacity: 1;
      transform: translateX(0);
    }
    .card {
      background: rgba(8, 10, 20, 0.82);
      backdrop-filter: blur(18px);
      -webkit-backdrop-filter: blur(18px);
      border: 1px solid rgba(255, 255, 255, 0.10);
      border-radius: 16px;
      padding: 18px 20px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.55);
      font-family: 'Google Sans', 'Inter', sans-serif;
    }
    .header-label {
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: #00f2ff;
      margin: 0 0 6px;
    }
    .question {
      font-size: 15px;
      font-weight: 700;
      color: #fff;
      margin: 0 0 14px;
      line-height: 1.3;
    }
    .rows-container {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .option-row {
      cursor: pointer;
    }
    .option-row.voted {
      cursor: default;
    }
    .option-label {
      font-size: 13px;
      color: rgba(255, 255, 255, 0.85);
      margin-bottom: 4px;
    }
    .bar-track {
      height: 8px;
      border-radius: 4px;
      background: rgba(255, 255, 255, 0.08);
      overflow: hidden;
      margin-bottom: 2px;
    }
    .bar-fill {
      height: 100%;
      border-radius: 4px;
      background: #00f2ff;
      transition: width 0.5s ease;
    }
    .bar-fill.chosen {
      background: #ff0055;
    }
    .pct-text {
      font-size: 11px;
      color: #00f2ff;
    }
    .grid-container {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    .grid-btn {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 10px;
      padding: 10px 8px;
      color: rgba(255, 255, 255, 0.85);
      font-size: 13px;
      font-family: 'Google Sans', 'Inter', sans-serif;
      cursor: pointer;
      text-align: center;
      transition: background 0.2s ease, border-color 0.2s ease;
    }
    .grid-btn:hover:not(:disabled) {
      background: rgba(0, 242, 255, 0.12);
      border-color: rgba(0, 242, 255, 0.35);
    }
    .grid-btn.chosen {
      background: rgba(255, 0, 85, 0.22);
      border-color: rgba(255, 0, 85, 0.55);
      color: #fff;
    }
    .grid-btn:disabled {
      cursor: default;
    }
  `;

  private _getPercent(index: number): number {
    const total = this.values.reduce((s, v) => s + v, 0);
    if (total === 0) return 0;
    return (this.values[index] / total) * 100;
  }

  private _handleVote(index: number) {
    if (this._voted !== -1) return;
    this._voted = index;
    this.dispatchEvent(new CustomEvent('poll-vote', {
      detail: { optionIndex: index },
      bubbles: true,
      composed: true,
    }));
  }

  private _renderRows() {
    return html`
      <div class="rows-container">
        ${this.options.map((opt, i) => {
          const pct = this._getPercent(i);
          const isChosen = this._voted === i;
          return html`
            <div
              class="option-row ${this._voted !== -1 ? 'voted' : ''}"
              @click=${() => this._handleVote(i)}
            >
              <div class="option-label">${opt}</div>
              <div class="bar-track">
                <div
                  class="bar-fill ${isChosen ? 'chosen' : ''}"
                  style="width: ${pct.toFixed(1)}%"
                ></div>
              </div>
              <div class="pct-text">${pct.toFixed(0)}%</div>
            </div>
          `;
        })}
      </div>
    `;
  }

  private _renderGrid() {
    return html`
      <div class="grid-container">
        ${this.options.map((opt, i) => {
          const isChosen = this._voted === i;
          return html`
            <button
              class="grid-btn ${isChosen ? 'chosen' : ''}"
              ?disabled=${this._voted !== -1}
              @click=${() => this._handleVote(i)}
            >${opt}</button>
          `;
        })}
      </div>
    `;
  }

  render() {
    return html`
      <div class="card">
        <div class="header-label">📊 Audience Poll</div>
        <div class="question">${this.question}</div>
        ${this.layout === 'grid' ? this._renderGrid() : this._renderRows()}
      </div>
    `;
  }
}
