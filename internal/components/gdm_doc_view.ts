import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { unsafeHTML } from 'lit/directives/unsafe-html.js';
import DOMPurify from 'dompurify';

@customElement('gdm-doc-view')
export class GdmDocView extends LitElement {
  @property({ type: String }) title = '';
  @property({ type: String }) htmlContent = '';

  static styles = css`
    :host { display: block; background: #131418; border: 1px solid #262932; border-radius: 12px; padding: 20px; margin-top: 12px; max-height: 400px; overflow-y: auto; }
    .doc-title { font-size: 16px; font-weight: 600; color: #fff; border-bottom: 1px solid #262932; padding-bottom: 12px; margin-bottom: 12px; }
    .markdown-body { font-size: 13px; color: #b8bcc4; line-height: 1.6; }
    .markdown-body h1, .markdown-body h2, .markdown-body h3 { color: #f2f3f5; margin-top: 16px; margin-bottom: 8px; }
    .markdown-body p { margin-bottom: 12px; }
    .markdown-body ul, .markdown-body ol { margin-left: 20px; margin-bottom: 12px; }
    .markdown-body strong { color: #fff; }
    .markdown-body code, .markdown-body pre { background: #1d2027; padding: 4px 6px; border-radius: 4px; font-family: monospace; color: #9B6DFF; }
  `;

  render() {
    return html`
      ${this.title ? html`<div class="doc-title">📄 ${this.title}</div>` : ''}
      <div class="markdown-body">${unsafeHTML(DOMPurify.sanitize(this.htmlContent) || '<em>No content provided.</em>')}</div>
    `;
  }
}
