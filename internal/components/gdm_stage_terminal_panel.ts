import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-terminal-panel')
export class GdmStageTerminalPanel extends LitElement {
  @property({ type: String }) content = '';
  @property({ type: Array }) lines: string[] = [];
  @property({ type: String }) title = 'Terminal';
  @property({ type: Boolean }) cursor = true;

  willUpdate(changedProperties: Map<string | number | symbol, unknown>) {
    // Defensive parsing for stringified lines array
    if (changedProperties.has('lines') && typeof this.lines === 'string') {
      try {
        this.lines = JSON.parse(this.lines as unknown as string);
      } catch (e) {
        console.error('[gdm-terminal-panel] Failed to parse lines:', e);
        this.lines = [];
      }
    }
    // Unpack wrapped lines object if needed
    if (this.lines && !Array.isArray(this.lines) && typeof this.lines === 'object') {
      const anyLines = this.lines as unknown as Record<string, unknown>;
      if (Array.isArray(anyLines['lines'])) {
        this.lines = anyLines['lines'] as string[];
      } else if (Array.isArray(anyLines['explicitList'])) {
        this.lines = anyLines['explicitList'] as string[];
      }
    }
    // Final safety net — ensure lines is always an array
    if (!Array.isArray(this.lines)) this.lines = [];
  }

  static styles = css`
    :host {
      display: block;
      width: 100%;
      height: 100%;
      overflow: hidden;
      font-family: 'Google Sans Mono', 'Roboto Mono', 'SF Mono', 'Menlo', 'Consolas', monospace;
    }

    .window {
      display: flex;
      flex-direction: column;
      height: 100%;
      box-sizing: border-box;
      background: #0a0c10;
      border: 1px solid rgba(255, 255, 255, 0.10);
      border-radius: 10px;
      box-shadow:
        0 8px 32px rgba(0, 0, 0, 0.70),
        inset 0 1px 0 rgba(255, 255, 255, 0.05);
      overflow: hidden;
    }

    /* ── Title bar ── */
    .title-bar {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 14px;
      background: #161920;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      flex-shrink: 0;
    }

    .traffic-lights {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-shrink: 0;
    }

    .dot {
      width: 12px;
      height: 12px;
      border-radius: 50%;
    }

    .dot-red    { background: #ff5f57; }
    .dot-amber  { background: #febc2e; }
    .dot-green  { background: #28c840; }

    .window-title {
      font-size: 11px;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.55);
      letter-spacing: 0.04em;
      user-select: none;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    /* ── Body ── */
    .body {
      flex: 1;
      overflow: auto;
      padding: 14px 18px 14px 18px;
      background: #0a0c10;
      box-sizing: border-box;
    }

    .body::-webkit-scrollbar {
      width: 6px;
    }

    .body::-webkit-scrollbar-track {
      background: transparent;
    }

    .body::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.12);
      border-radius: 3px;
    }

    .line {
      display: block;
      font-size: 13px;
      line-height: 1.65;
      color: rgba(200, 210, 200, 0.90);
      white-space: pre-wrap;
      word-break: break-all;
      min-height: 1em;
    }

    .cursor-line {
      display: inline;
    }

    .cursor {
      display: inline-block;
      width: 0.55em;
      height: 1.1em;
      vertical-align: text-bottom;
      background: rgba(200, 210, 200, 0.85);
      margin-left: 1px;
      animation: blink 1.1s step-start infinite;
    }

    @keyframes blink {
      0%, 49% { opacity: 1; }
      50%, 100% { opacity: 0; }
    }

    .empty-prompt {
      font-size: 13px;
      color: rgba(255, 255, 255, 0.25);
      font-style: italic;
    }
  `;

  private _resolvedLines(): string[] {
    if (this.lines.length > 0) return this.lines;
    if (this.content) return this.content.split('\n');
    return [];
  }

  render() {
    const resolved = this._resolvedLines();
    const hasContent = resolved.length > 0;

    return html`
      <div class="window">
        <div class="title-bar">
          <div class="traffic-lights">
            <div class="dot dot-red"></div>
            <div class="dot dot-amber"></div>
            <div class="dot dot-green"></div>
          </div>
          <span class="window-title">${this.title}</span>
        </div>
        <div class="body">
          ${hasContent
            ? resolved.map((line, i) => {
                const isLast = i === resolved.length - 1;
                return html`<span class="line">${isLast && this.cursor
                  ? html`<span class="cursor-line">${line}<span class="cursor"></span></span>`
                  : line}</span>`;
              })
            : html`<span class="empty-prompt">No output yet...</span>`}
        </div>
      </div>
    `;
  }
}
