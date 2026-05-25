import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-notepad')
export class GdmStageNotepad extends LitElement {
  @property({ type: String }) content = '';

  static styles = css`
    :host {
      display: block;
      width: 100%;
      height: 100%;
      overflow: hidden;
    }
    .container {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: rgba(2, 4, 12, 0.98);
    }
    .header {
      background: rgba(4, 8, 20, 0.95);
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      padding: 10px 18px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .header-label {
      font-size: 12px;
      font-weight: 700;
      color: rgba(255, 255, 255, 0.6);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .header-status {
      font-size: 10px;
      color: #4caf50;
    }
    .content-area {
      flex: 1;
      overflow-y: auto;
      padding: 20px 24px;
      background: rgba(2, 4, 12, 0.98);
    }
    .notes-text {
      white-space: pre-wrap;
      word-break: break-word;
      font-family: 'Google Sans Mono', 'Roboto Mono', monospace;
      font-size: 14px;
      line-height: 1.7;
      color: rgba(255, 255, 255, 0.85);
      margin: 0;
    }
    .placeholder {
      font-style: italic;
      color: rgba(255, 255, 255, 0.25);
      font-size: 13px;
    }
  `;

  render() {
    return html`
      <div class="container">
        <div class="header">
          <span class="header-label">Live Workspace Notes</span>
          <span class="header-status">Synced ✓</span>
        </div>
        <div class="content-area">
          ${this.content
            ? html`<pre class="notes-text">${this.content}</pre>`
            : html`<span class="placeholder">Waiting for notes...</span>`}
        </div>
      </div>
    `;
  }
}
