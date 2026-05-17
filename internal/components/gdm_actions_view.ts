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
      border: 1px solid var(--line); border-radius: var(--radius, 12px);
      animation: slide-up 250ms ease-out;
    }
    @keyframes slide-up { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
    .action-ico { width: 30px; height: 30px; border-radius: 8px; display: grid; place-items: center; flex-shrink: 0; color: white; }
    .action-ico.doc { background: #2b6cb0; }
    .action-ico.sheet { background: #2f855a; }
    .action-ico.auth { background: #c05621; }
    .action-ico svg { width: 14px; height: 14px; }
    .action-body { flex: 1; min-width: 0; }
    .action-title { font-size: 12.5px; font-weight: 500; color: var(--fg); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .action-sub { font-size: 11px; color: var(--fg-2); margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .action-btns { display: flex; gap: 6px; flex-shrink: 0; }
    .btn-open, .btn-stage {
      font-size: 11px; font-weight: 500; padding: 4px 10px;
      border-radius: 6px; cursor: pointer; text-decoration: none;
      border: 1px solid var(--line); background: transparent;
      color: var(--fg-2); transition: all 150ms ease; font-family: var(--font, inherit);
    }
    .btn-open:hover, .btn-stage:hover { background: var(--gem-1); color: #fff; border-color: var(--gem-1); }
    .btn-stage { color: var(--gem-1); border-color: var(--gem-1); }
    .btn-stage:hover { background: var(--gem-1); color: #fff; }
  `;

  render() {
    if (this.actions.length === 0) return html``;
    return html`
      <div class="action-list">
        ${this.actions.map(action => html`
          <div class="action">
            <div class="action-ico ${this.getIconClass(action)}">
              ${this.getIconSvg(action)}
            </div>
            <div class="action-body">
              <div class="action-title">${action.label}</div>
              <div class="action-sub">${action.url.replace('https://', '').substring(0, 38)}…</div>
            </div>
            <div class="action-btns">
              <a class="btn-open" href="${action.url}" target="_blank">Open</a>
              ${this.isGoogleDoc(action.url) ? html`
                <button class="btn-stage" @click=${(e: Event) => this.handleStage(e, action)}>Stage</button>
              ` : ''}
            </div>
          </div>
        `)}
      </div>
    `;
  }

  private isGoogleDoc(url: string) {
    return url.includes('docs.google.com') || url.includes('drive.google.com') ||
           url.includes('sheets.google.com') || url.includes('slides.google.com');
  }

  private getIconClass(action: any) {
    if (action.url.includes('spreadsheets')) return 'sheet';
    if (action.url.includes('workspace-subagent-auth')) return 'auth';
    return 'doc';
  }

  private getIconSvg(action: any) {
    if (action.url.includes('spreadsheets')) {
      return html`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>`;
    }
    if (action.url.includes('workspace-subagent-auth')) {
      return html`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>`;
    }
    return html`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>`;
  }

  private handleStage(e: Event, action: any) {
    e.preventDefault();
    this.dispatchEvent(new CustomEvent('action-click', {
      detail: action,
      bubbles: true,
      composed: true
    }));
  }
}
