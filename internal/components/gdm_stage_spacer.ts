import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

/**
 * gdm-spacer — layout filler. With no `size` it grows to absorb free space in a
 * flex container (push-apart); with `size` it's a fixed gap.
 */
@customElement('gdm-spacer')
export class GdmSpacer extends LitElement {
  @property({ type: String }) size = '';        // e.g. "24px"; empty => flex-grow
  @property({ type: String }) axis = 'both';    // 'horizontal' | 'vertical' | 'both'

  static styles = css`:host { display: block; }`;

  updated() {
    if (this.size) {
      this.style.flex = '0 0 auto';
      this.style.width = (this.axis === 'vertical') ? '' : this.size;
      this.style.height = (this.axis === 'horizontal') ? '' : this.size;
    } else {
      this.style.flex = '1 1 auto';
      this.style.width = '';
      this.style.height = '';
    }
  }

  render() { return html``; }
}
