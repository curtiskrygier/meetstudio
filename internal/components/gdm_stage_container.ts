import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-container')
export class GdmStageContainer extends LitElement {
  @property({ type: String }) direction = 'row';
  @property({ type: String }) justify = 'flex-start';
  @property({ type: String }) align = 'stretch';
  @property({ type: String }) gap = '0';
  @property({ type: String }) padding = '0';
  @property({ type: String }) background = 'transparent';
  @property({ type: String }) border = 'none';
  @property({ type: String }) borderRadius = '0';
  @property({ type: String }) width = 'auto';
  @property({ type: String }) height = 'auto';
  @property({ type: Boolean }) glass = false;
  @property({ type: Boolean }) scrollable = false;
  @property({ type: Number }) grow = 0;
  @property({ type: Number }) shrink = 1;
  @property({ type: String }) margin = '0';

  static styles = css`
    :host {
      display: flex;
      box-sizing: border-box;
    }
    :host(.scrollable) {
      overflow: auto;
    }
    /* Scrollbar decoration */
    :host(.scrollable):-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    :host(.scrollable)::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    :host(.scrollable)::-webkit-scrollbar-track {
      background: rgba(255, 255, 255, 0.01);
    }
    :host(.scrollable)::-webkit-scrollbar-thumb {
      background: rgba(0, 242, 255, 0.15);
      border-radius: 3px;
    }
    :host(.scrollable)::-webkit-scrollbar-thumb:hover {
      background: rgba(0, 242, 255, 0.35);
    }
  `;

  updated(changedProperties: Map<string, any>) {
    // Dynamic Host Layout styling — writes inline CSS directly onto the <gdm-container> element
    this.style.display = 'flex';
    this.style.boxSizing = 'border-box';
    this.style.flexDirection = this.direction;
    this.style.justifyContent = this.justify;
    this.style.alignItems = this.align;
    this.style.gap = this.gap;
    this.style.padding = this.padding;
    this.style.width = this.width;
    this.style.height = this.height;
    this.style.flexGrow = String(this.grow);
    this.style.flexShrink = String(this.shrink);
    this.style.margin = this.margin;

    if (this.scrollable) {
      this.classList.add('scrollable');
      this.style.overflow = 'auto';
    } else {
      this.classList.remove('scrollable');
      this.style.overflow = 'visible';
    }

    if (this.glass) {
      // Ultra-premium glassmorphism values
      this.style.background = 'rgba(10, 14, 32, 0.72)';
      this.style.backdropFilter = 'blur(20px) saturate(1.5)';
      this.style.setProperty('-webkit-backdrop-filter', 'blur(20px) saturate(1.5)');
      this.style.border = '1px solid rgba(255, 255, 255, 0.08)';
      this.style.borderRadius = this.borderRadius !== '0' ? this.borderRadius : '16px';
      this.style.boxShadow = '0 12px 40px rgba(0, 0, 0, 0.5)';
    } else {
      // Clean fallback layout styling
      this.style.background = this.background;
      this.style.border = this.border;
      this.style.borderRadius = this.borderRadius;
      
      if (changedProperties.has('glass')) {
        this.style.backdropFilter = '';
        this.style.setProperty('-webkit-backdrop-filter', '');
        this.style.boxShadow = '';
      }
    }
  }

  render() {
    return html`<slot></slot>`;
  }
}
