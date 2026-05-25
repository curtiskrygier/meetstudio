import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-iframe-panel')
export class GdmStageIframePanel extends LitElement {
  @property({ type: String }) src = '';
  @property({ type: Number }) panel = 0;

  static styles = css`
    :host {
      display: block;
      width: 100%;
      height: 100%;
      position: relative;
      overflow: hidden;
      background: #000;
    }
    .frame-wrap {
      width: 100%;
      height: 100%;
      transition: opacity 0.4s ease;
    }
    .frame-wrap.hidden {
      opacity: 0;
      pointer-events: none;
    }
    iframe {
      width: 100%;
      height: 100%;
      border: none;
      display: block;
    }
    .placeholder {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 48px;
      opacity: 0.4;
    }
  `;

  render() {
    if (!this.src) {
      return html`<div class="placeholder">🌐</div>`;
    }
    return html`
      <div class="frame-wrap">
        <iframe
          src="${this.src}"
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-presentation"
          allowfullscreen
          loading="lazy"
        ></iframe>
      </div>
    `;
  }
}
