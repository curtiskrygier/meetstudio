import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-poll-view')
export class GdmPollView extends LitElement {
  @property({ type: String }) question = '';
  @property({ type: Array }) options = [];
  @property({ type: String }) selectedId = '';

  static styles = css`
    :host { display: block; }
    .poll-card {
      background: var(--bg-1);
      border: 1px solid var(--line-soft);
      border-radius: var(--radius);
      padding: 16px;
      animation: pulse-border 2s infinite alternate;
    }
    @keyframes pulse-border {
      from { border-color: var(--line-soft); box-shadow: 0 0 0px var(--gem-2); }
      to { border-color: var(--gem-2); box-shadow: 0 0 12px -4px var(--gem-2); }
    }
    .question {
      font-size: 14px;
      font-weight: 600;
      color: var(--fg);
      margin-bottom: 12px;
      line-height: 1.4;
    }
    .options { display: flex; flex-direction: column; gap: 8px; }
    .opt-btn {
      height: 40px;
      border-radius: 10px;
      border: 1px solid var(--line);
      background: var(--bg-2);
      color: var(--fg-2);
      font-family: inherit;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      display: flex;
      align-items: center;
      padding: 0 14px;
      transition: all 150ms;
    }
    .opt-btn:hover { background: var(--bg-3); border-color: var(--fg-4); }
    .opt-btn[data-selected="true"] {
      background: var(--gem-2);
      border-color: var(--gem-2);
      color: white;
    }
    .opt-btn.red { border-left: 4px solid #ea4335; }
    .opt-btn.blue { border-left: 4px solid #4285f4; }
  `;

  render() {
    return html`
      <div class="poll-card">
        <div class="question">${this.question}</div>
        <div class="options">
          ${this.options.map((opt: any) => html`
            <button 
              class="opt-btn ${opt.toLowerCase().includes('red') ? 'red' : (opt.toLowerCase().includes('blue') ? 'blue' : '')}"
              ?data-selected=${this.selectedId === opt}
              @click=${() => this.handleSelect(opt)}>
              ${opt}
            </button>
          `)}
        </div>
      </div>
    `;
  }

  private handleSelect(option: string) {
    this.selectedId = option;
    this.dispatchEvent(new CustomEvent('poll-select', {
      detail: { option },
      bubbles: true,
      composed: true
    }));
  }
}
