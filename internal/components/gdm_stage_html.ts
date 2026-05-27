import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-html-panel')
export class GdmStageHtml extends LitElement {
  @property({ type: String }) html = '';
  @property({ type: String }) title = '';
  @property({ type: Boolean, reflect: true }) overlay = false;
  @property({ type: Number }) version = 0;

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
      transition: all 300ms ease;
    }

    :host([overlay]) {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      z-index: 998;
      background: rgba(8, 10, 20, 0.7);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      padding: 40px;
      box-sizing: border-box;
      border: none;
      border-radius: 0;
      animation: backdrop-fade-in 300ms ease-out forwards;
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
      width: 100%;
      height: 100%;
      position: relative;
      overflow: hidden;
    }

    :host([overlay]) .content {
      max-width: 1200px;
      margin: 0 auto;
      background: rgba(12, 16, 32, 0.65);
      border: 1px solid rgba(0, 242, 255, 0.2);
      border-radius: 16px;
      box-shadow: 0 20px 50px rgba(0, 242, 255, 0.1), inset 0 0 20px rgba(0, 242, 255, 0.05);
      animation: scale-up 350ms cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
    }

    iframe {
      width: 100%;
      height: 100%;
      border: none;
      display: block;
      background: transparent;
    }

    .placeholder {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: 'Google Sans', 'Inter', sans-serif;
      font-size: 12px;
      color: rgba(255, 255, 255, 0.4);
      animation: pulse 2.2s ease-in-out infinite alternate;
    }

    @keyframes backdrop-fade-in {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    @keyframes scale-up {
      from {
        transform: scale(0.92);
        opacity: 0;
      }
      to {
        transform: scale(1);
        opacity: 1;
      }
    }
  `;

  render() {
    const wrappedHtml = this.html ? `
      <!DOCTYPE html>
      <html>
        <head>
          <meta charset="utf-8">
          <style>
            html, body {
              color-scheme: dark !important;
              margin: 0;
              padding: 0;
              width: 100%;
              height: 100%;
              background: #080a14 !important;
              color: #ffffff !important;
              font-family: system-ui, -apple-system, sans-serif;
              overflow: auto;
            }
            /* Universal shield to prevent auto-dark-mode inversion */
            *, html, body, div, span, h1, h2, h3, h4, h5, h6, p, a, table, th, td, tr {
              color-scheme: dark !important;
            }
            /* Cyber scrollbar theme */
            ::-webkit-scrollbar {
              width: 8px;
              height: 8px;
            }
            ::-webkit-scrollbar-track {
              background: rgba(255, 255, 255, 0.02);
            }
            ::-webkit-scrollbar-thumb {
              background: rgba(0, 242, 255, 0.2);
              border-radius: 4px;
            }
            ::-webkit-scrollbar-thumb:hover {
              background: rgba(0, 242, 255, 0.4);
            }
          </style>
        </head>
        <body>
          ${this.html}
          <style>
            /* Trailing styles to override custom inline body colors and reset background to dark */
            body {
              background: #080a14 !important;
              color: #ffffff !important;
            }
            *, div, span, h1, h2, h3, h4, h5, h6, p, table, th, td {
              color-scheme: dark !important;
            }
          </style>
        </body>
      </html>
    ` : '';

    return html`
      ${this.title && !this.overlay ? html`
        <div class="header">
          <span>${this.title}</span>
        </div>
      ` : ''}
      <div class="content">
        ${this.html ? html`
          <iframe
            .srcdoc="${wrappedHtml}"
            sandbox="allow-scripts allow-same-origin allow-popups"
            allowfullscreen
            loading="lazy"
          ></iframe>
        ` : html`
          <div class="placeholder">🌐 Awaiting HTML content...</div>
        `}
      </div>
    `;
  }
}
