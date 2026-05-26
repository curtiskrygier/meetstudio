import { LitElement, css, html, PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import DOMPurify from 'dompurify';

@customElement('gdm-mermaid-panel')
export class GdmStageMermaid extends LitElement {
  @property({ type: String }) syntax = '';
  @property({ type: String }) title = '';
  @property({ type: Number }) version = 0;

  @state() private _error: string | null = null;
  @state() private _loading = true;

  private static _mermaidInitialized = false;
  private _mermaidInstance: any = null;

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: rgba(8, 10, 20, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 12px;
      box-sizing: border-box;
    }

    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 16px;
      background: rgba(12, 16, 32, 0.5);
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-size: 13px;
      font-weight: 500;
      color: rgba(255, 255, 255, 0.85);
    }

    .content {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px;
      overflow: auto;
      position: relative;
    }

    .placeholder, .error-view {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 12px;
      opacity: 0.5;
      text-align: center;
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-size: 12px;
      color: rgba(255, 255, 255, 0.6);
    }

    .error-view {
      color: #ff5252;
      opacity: 0.85;
    }

    /* Style rendered SVGs */
    .content svg {
      max-width: 100%;
      max-height: 100%;
      width: auto;
      height: auto;
      display: block;
      transition: opacity 400ms ease-out;
    }

    /* Flowchart Overrides */
    .content svg .node rect, .content svg .node circle, .content svg .node polygon, .content svg .node path {
      stroke: rgba(0, 242, 255, 0.4) !important;
      stroke-width: 1.5px !important;
      fill: rgba(18, 26, 48, 0.6) !important;
      filter: drop-shadow(0 0 2px rgba(0, 242, 255, 0.2)) !important;
    }
    .content svg .edgePath .path {
      stroke: #00f2ff !important;
      stroke-width: 1.5px !important;
      filter: drop-shadow(0 0 1px rgba(0, 242, 255, 0.3)) !important;
    }
    .content svg .edgePath .arrowheadPath {
      fill: #00f2ff !important;
      stroke: #00f2ff !important;
    }
    .content svg .labelText, .content svg text {
      fill: rgba(255, 255, 255, 0.9) !important;
      font-family: 'Google Sans', 'Inter', sans-serif !important;
      font-size: 12px !important;
    }

    /* Sequence Diagram Overrides */
    .content svg .actor, .content svg rect.actor, .content svg rect.actor-top, .content svg rect.actor-bottom {
      stroke: rgba(0, 242, 255, 0.6) !important;
      stroke-width: 2px !important;
      fill: rgba(18, 26, 48, 0.8) !important;
      filter: drop-shadow(0 0 3px rgba(0, 242, 255, 0.3)) !important;
    }
    .content svg text.actor, .content svg text.actor tspan, .content svg .actor tspan, .content svg text.actor-box tspan, .content svg .actor-man tspan {
      fill: #00f2ff !important;
      font-family: 'Google Sans', 'Inter', sans-serif !important;
      font-weight: 600 !important;
      font-size: 14px !important;
    }
    .content svg .actor-line {
      stroke: rgba(0, 242, 255, 0.3) !important;
      stroke-width: 1.2px !important;
      stroke-dasharray: 4, 4 !important;
    }
    .content svg .messageLine0, .content svg .messageLine1 {
      stroke: #00f2ff !important;
      stroke-width: 2px !important;
    }
    .content svg [id$="-arrowhead"] path, .content svg marker path, .content svg .arrowheadPath {
      fill: #00f2ff !important;
      stroke: #00f2ff !important;
    }
    .content svg .messageText {
      fill: rgba(255, 255, 255, 0.95) !important;
      stroke: none !important;
      font-family: 'Google Sans', 'Inter', sans-serif !important;
      font-size: 12px !important;
      font-weight: 500 !important;
    }
    .content svg g.note rect, .content svg rect.note {
      stroke: rgba(240, 0, 255, 0.6) !important;
      stroke-width: 2px !important;
      fill: rgba(42, 22, 68, 0.8) !important;
      filter: drop-shadow(0 0 3px rgba(240, 0, 255, 0.3)) !important;
    }
    .content svg .noteText, .content svg .noteText tspan {
      fill: rgba(255, 255, 255, 0.95) !important;
      font-family: 'Google Sans', 'Inter', sans-serif !important;
      font-size: 12px !important;
      font-weight: 500 !important;
    }
    .content svg rect.activation0, .content svg rect.activation1, .content svg rect.activation2 {
      fill: rgba(0, 242, 255, 0.35) !important;
      stroke: #00f2ff !important;
      stroke-width: 1.5px !important;
    }
    .content svg .sequenceNumber {
      fill: #121a30 !important;
      font-weight: bold !important;
    }
  `;

  async firstUpdated() {
    try {
      // Dynamic import of mermaid client-side
      const mermaidModule = await import('mermaid');
      this._mermaidInstance = mermaidModule.default;
      
      if (!GdmStageMermaid._mermaidInitialized) {
        this._mermaidInstance.initialize({
          startOnLoad: false,
          theme: 'dark',
          securityLevel: 'loose',
          themeVariables: {
            background: 'transparent',
            primaryColor: '#121a30',
            primaryTextColor: '#fff',
            lineColor: '#00f2ff',
            arrowheadColor: '#00f2ff',
          }
        });
        GdmStageMermaid._mermaidInitialized = true;
      }
      this._loading = false;
      this._renderMermaid();
    } catch (err: any) {
      this._error = `Failed to load Mermaid: ${err.message || err}`;
      this._loading = false;
    }
  }

  updated(changedProps: PropertyValues) {
    super.updated(changedProps);
    if ((changedProps.has('syntax') || changedProps.has('version')) && !this._loading) {
      this._renderMermaid();
    }
  }

  private async _renderMermaid() {
    if (!this._mermaidInstance || !this.syntax || !this.syntax.trim()) {
      return;
    }

    const container = this.shadowRoot?.querySelector('.content');
    if (!container) return;

    this._error = null;

    try {
      const uniqueId = `mermaid-${Math.random().toString(36).substring(2, 9)}`;
      
      // Clean up previous elements inside .content
      container.querySelectorAll(':not(.placeholder):not(.error-view)').forEach(el => el.remove());
      
      const { svg } = await this._mermaidInstance.render(uniqueId, this.syntax);
      
      const sanitized = DOMPurify.sanitize(svg);
      
      const hostDiv = document.createElement('div');
      hostDiv.style.width = '100%';
      hostDiv.style.height = '100%';
      hostDiv.style.display = 'flex';
      hostDiv.style.alignItems = 'center';
      hostDiv.style.justifyContent = 'center';
      hostDiv.innerHTML = sanitized;
      
      const svgEl = hostDiv.querySelector('svg');
      if (svgEl) {
        svgEl.removeAttribute('width');
        svgEl.removeAttribute('height');
        svgEl.style.maxWidth = '100%';
        svgEl.style.maxHeight = '100%';
        svgEl.style.width = 'auto';
        svgEl.style.height = 'auto';
      }
      
      container.appendChild(hostDiv);
    } catch (err: any) {
      console.error('[gdm-mermaid-panel] Render error:', err);
      this._error = err.message || 'Syntax error in Mermaid definition';
      
      // Clean up failed renders
      container.querySelectorAll(':not(.placeholder):not(.error-view)').forEach(el => el.remove());
    }
  }

  render() {
    return html`
      ${this.title ? html`
        <div class="header">
          <span>${this.title}</span>
        </div>
      ` : ''}
      <div class="content">
        ${this._loading ? html`
          <div class="placeholder">⚡ Loading engine...</div>
        ` : ''}
        ${!this._loading && !this.syntax ? html`
          <div class="placeholder">🧜‍♀️ Awaiting flow definition...</div>
        ` : ''}
        ${this._error ? html`
          <div class="error-view">
            <span>❌ Render Error</span>
            <small style="margin-top: 4px; font-family: monospace;">${this._error}</small>
          </div>
        ` : ''}
      </div>
    `;
  }
}
