import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-controls-view')
export class GdmControlsView extends LitElement {
  @property({ type: Boolean }) audioEnabled = true;
  @property({ type: Boolean }) videoEnabled = false;
  @property({ type: Boolean }) diagramMode = false;
  @property({ type: Boolean }) transcriptMode = false;

  static styles = css`
    :host { display: block; }
    .controls-row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
    .ctrl {
      background: var(--bg-1); border: 1px solid var(--line-soft); border-radius: 12px;
      padding: 10px 8px 9px; display: flex; flex-direction: column; align-items: center; gap: 6px;
      cursor: pointer; color: var(--fg-2); transition: all 200ms ease;
    }
    .ctrl:hover { background: var(--bg-2); }
    .ctrl[data-active="true"] { background: rgba(52,210,122,0.10); border-color: rgba(52,210,122,0.32); color: #9bedb9; }
    .ctrl[data-active="false"] { background: rgba(244,67,54,0.08); border-color: rgba(244,67,54,0.28); color: #f3a59f; }
    .ctrl-icon { width: 30px; height: 30px; border-radius: 8px; display: grid; place-items: center; background: var(--bg-3); }
    .ctrl[data-active="true"] .ctrl-icon { background: rgba(52,210,122,0.16); }
    .ctrl[data-active="false"] .ctrl-icon { background: rgba(244,67,54,0.14); }
    .ctrl-icon svg { width: 15px; height: 15px; }
    .ctrl-label { font-size: 11.5px; font-weight: 500; }
    .ctrl-state { font-size: 10.5px; color: var(--fg-4); }
    .ctrl[data-active="true"] .ctrl-state { color: #7ce0a4; }
    .ctrl[data-active="false"] .ctrl-state { color: #f3a59f; }
    
    .secondary-row { display: flex; gap: 8px; margin-top: 8px; }
    .mode-btn {
      flex: 1; height: 32px; border-radius: 8px; border: 1px solid var(--line-soft);
      background: var(--bg-1); color: var(--fg-2); font-size: 11px; font-weight: 600;
      cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px;
      transition: all 200ms ease;
    }
    .mode-btn[data-active="true"] { background: var(--gem-2); color: white; border-color: var(--gem-2); }
  `;

  render() {
    return html`
      <div class="controls-row">
        <div class="ctrl" data-active="${this.audioEnabled}" @click=${() => this.emit('toggle-audio')}>
          <div class="ctrl-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              ${this.audioEnabled ? html`<path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>` : html`<line x1="1" y1="1" x2="23" y2="23"/><path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6"/><path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>`}
            </svg>
          </div>
          <div class="ctrl-label">Mic</div>
          <div class="ctrl-state">${this.audioEnabled ? 'Active' : 'Muted'}</div>
        </div>

        <div class="ctrl" data-active="${this.videoEnabled}" @click=${() => this.emit('toggle-video')}>
          <div class="ctrl-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              ${this.videoEnabled ? html`<polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>` : html`<line x1="1" y1="1" x2="23" y2="23"/><path d="M16 11.37L23 7v10l-2.11-1.32"/><path d="M15 15.38a8.5 8.5 0 0 1-7.63 1.62M4 4.62a8.5 8.5 0 0 1 7.63-1.62"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>`}
            </svg>
          </div>
          <div class="ctrl-label">Video</div>
          <div class="ctrl-state">${this.videoEnabled ? 'Streaming' : 'Off'}</div>
        </div>

        <div class="ctrl" data-active="${this.diagramMode}" @click=${() => this.emit('toggle-diagram')}>
          <div class="ctrl-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
            </svg>
          </div>
          <div class="ctrl-label">Architect</div>
          <div class="ctrl-state">${this.diagramMode ? 'Live' : 'Ready'}</div>
        </div>
      </div>

      <div class="secondary-row">
        <button class="mode-btn" data-active="${this.transcriptMode}" @click=${() => this.emit('toggle-transcript')}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          Stage Captions
        </button>
      </div>
    `;
  }

  private emit(name: string) {
    this.dispatchEvent(new CustomEvent(name, { bubbles: true, composed: true }));
  }
}
