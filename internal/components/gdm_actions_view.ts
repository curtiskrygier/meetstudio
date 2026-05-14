import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-actions-view')
export class GdmActionsView extends LitElement {
  @property({ type: Array }) actions: Array<{url: string; label: string; content?: string}> = [];

  static styles = css`
    :host { display: block; }
    .action-list { display: flex; flex-direction: column; gap: 8px; }
    .action { 
      display: flex; align-items: center; gap: 10px; 
      padding: 10px 12px; background: var(--bg-1); 
      border: 1px solid var(--line-soft); border-radius: 12px; 
      cursor: pointer; transition: all 200ms ease; text-decoration: none; 
      animation: slide-up 250ms ease-out;
    }
    @keyframes slide-up { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
    .action:hover { background: var(--bg-2); border-color: var(--line); }
    .action-ico { width: 30px; height: 30px; border-radius: 8px; display: grid; place-items: center; flex-shrink: 0; color: white; }
    .action-ico.doc { background: #2b6cb0; }
    .action-ico.sheet { background: #2f855a; }
    .action-ico.img { background: #6b46c1; }
    .action-ico svg { width: 14px; height: 14px; }
    .action-body { flex: 1; min-width: 0; }
    .action-title { font-size: 12.5px; font-weight: 500; color: var(--fg); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .action-sub { font-size: 11px; color: var(--fg-4); margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  `;

  render() {
    if (this.actions.length === 0) return html``;

    return html`
      <div class="action-list">
        ${this.actions.map(action => html`
          <a class="action" href="${action.url}" target="_blank" @click=${(e: Event) => this.handleActionClick(e, action)}>
            <div class="action-ico ${this.getIconClass(action)}">
              ${this.getIconSvg(action)}
            </div>
            <div class="action-body">
              <div class="action-title">${action.label}</div>
              <div class="action-sub">${action.url.substring(0, 40)}...</div>
            </div>
          </a>
        `)}
      </div>
    `;
  }

  private getIconClass(action: any) {
    if (action.url.includes('spreadsheets')) return 'sheet';
    if (action.url.includes('docs')) return 'doc';
    return 'img';
  }

  private getIconSvg(action: any) {
    if (action.url.includes('spreadsheets')) {
      return html`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>`;
    }
    return html`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>`;
  }

  private handleActionClick(e: Event, action: any) {
    this.dispatchEvent(new CustomEvent('action-click', {
      detail: action,
      bubbles: true,
      composed: true
    }));
  }
}
