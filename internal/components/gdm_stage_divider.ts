import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-divider')
export class GdmStageDivider extends LitElement {
  @property({ type: Boolean }) vertical = false;
  @property({ type: String }) color = 'rgba(255, 255, 255, 0.08)';
  @property({ type: String }) thickness = '1px';
  @property({ type: String }) margin = '12px';

  static styles = css`
    :host {
      display: block;
      box-sizing: border-box;
    }
    .divider {
      transition: all 0.3s ease;
      box-sizing: border-box;
    }
  `;

  render() {
    let resolvedColor = this.color;
    if (this.color === 'accent' || this.color === 'cyan') resolvedColor = '#00f2ff';
    else if (this.color === 'success') resolvedColor = '#00ff88';
    else if (this.color === 'warning') resolvedColor = '#ffd60a';
    else if (this.color === 'danger') resolvedColor = '#ff3b57';

    const inlineStyles = this.vertical
      ? `
        display: inline-block;
        width: ${this.thickness};
        height: 100%;
        background-color: ${resolvedColor};
        margin: 0 ${this.margin};
        vertical-align: middle;
      `
      : `
        width: 100%;
        height: ${this.thickness};
        background-color: ${resolvedColor};
        margin: ${this.margin} 0;
      `;

    return html`<div class="divider" style="${inlineStyles}"></div>`;
  }
}
