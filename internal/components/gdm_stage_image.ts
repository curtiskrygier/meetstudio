import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

/**
 * gdm-image — raw image atom (fit / radius / aspect). The lightweight sibling of
 * the heavier gdm-image-panel molecule.
 */
@customElement('gdm-image')
export class GdmImage extends LitElement {
  @property({ type: String }) src = '';
  @property({ type: String }) alt = '';
  @property({ type: String }) fit = 'cover';        // object-fit
  @property({ type: String }) radius = '0';
  @property({ type: String }) width = '100%';
  @property({ type: String }) height = 'auto';
  @property({ type: String }) aspectRatio = '';     // e.g. "16/9"

  static styles = css`
    :host { display: block; box-sizing: border-box; line-height: 0; }
    img { display: block; }
  `;

  render() {
    if (!this.src) return html``;
    const style = [
      `object-fit:${this.fit}`,
      `border-radius:${this.radius}`,
      `width:${this.width}`,
      `height:${this.height}`,
      this.aspectRatio ? `aspect-ratio:${this.aspectRatio}` : '',
    ].filter(Boolean).join(';');
    return html`<img src="${this.src}" alt="${this.alt}" style="${style}" />`;
  }
}
