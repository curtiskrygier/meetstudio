import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-diagram-refiner')
export class GdmDiagramRefiner extends LitElement {
  @property({ type: String }) diagramStyle = 'sketch';
  @property({ type: String }) context = '';
  @property({ type: Boolean }) generating = false;
  @property({ type: Boolean }) canSave = false;

  static styles = css`
    :host { display: block; }
    .section-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
    .section-title { font-size: 11px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--fg-4); }
    .layout-switcher { display: flex; gap: 6px; margin: 8px 0 12px; }
    .style-btn { 
      flex: 1; height: 28px; border-radius: 6px; border: 1px solid var(--line); 
      background: var(--bg-1); color: var(--fg-3); font-size: 10px; font-weight: 600; 
      cursor: pointer; transition: all 200ms ease;
    }
    .style-btn[data-active] { background: var(--gem-1); border-color: var(--gem-1); color: white; }
    .style-btn:hover:not([data-active]) { background: var(--bg-2); border-color: var(--line-soft); }

    .ctx-input { 
      width: 100%; min-height: 88px; background: var(--bg-2) !important; 
      border: 1px solid var(--line); border-radius: var(--radius-sm); color: var(--fg) !important; 
      font-family: inherit; font-size: 12px; line-height: 1.5; 
      padding: 10px 12px; resize: vertical; box-sizing: border-box; 
      transition: border-color 150ms; 
    }
    .ctx-input:focus { outline: none; border-color: var(--gem-2); }

    .ctx-send { 
      flex-shrink: 0; height: 36px; padding: 0 14px; background: var(--gem-2); 
      border: none; border-radius: var(--radius-sm); color: #fff; font-family: inherit; 
      font-size: 12px; font-weight: 600; cursor: pointer; white-space: nowrap; 
      transition: all 200ms ease;
    }
    .ctx-send:hover { opacity: 0.85; }
    .ctx-send:disabled { opacity: 0.4; cursor: default; }
    .ctx-send.secondary { background: var(--bg-3); border: 1px solid var(--line); color: var(--fg-3); }
    .ctx-send.accent { background: var(--gem-1); }
  `;

  render() {
    return html`
      <div class="section-head"><span class="section-title">Diagram Visuals</span></div>
      <div class="layout-switcher">
        ${['blueprint', 'sketch', 'cyber', 'google'].map(s => html`
          <button class="style-btn" ?data-active=${this.diagramStyle === s} 
                  @click=${() => this.emit('change-style', s)}>
            ${s.toUpperCase()}
          </button>
        `)}
      </div>
      <textarea class="ctx-input" placeholder="Refine your architecture description here..."
        .value=${this.context}
        @input=${(e: any) => this.emit('update-context', e.target.value)}></textarea>
      <div style="display:flex; gap:8px; margin-top:12px">
        <button class="ctx-send" style="flex:1" ?disabled=${this.generating} @click=${() => this.emit('generate')}>
          ${this.generating ? 'Generating…' : 'Update'}
        </button>
        <button class="ctx-send secondary" style="flex:1" @click=${() => this.emit('new')}>
          New
        </button>
        <button class="ctx-send accent" style="flex:1.5" ?disabled=${!this.canSave} @click=${() => this.emit('save')}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="width:14px;height:14px;margin-right:6px;display:inline-block;vertical-align:middle;margin-top:-2px"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          Save PNG
        </button>
      </div>
    `;
  }

  private emit(name: string, detail?: any) {
    this.dispatchEvent(new CustomEvent(name, { detail, bubbles: true, composed: true }));
  }
}
