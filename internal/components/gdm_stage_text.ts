import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { repeat } from 'lit/directives/repeat.js';

@customElement('gdm-text')
export class GdmStageText extends LitElement {
  @property({ type: String }) content = '';
  @property({ type: String }) size = '14px';
  @property({ type: String }) weight = 'normal';
  @property({ type: String }) color = 'rgba(255, 255, 255, 0.9)';
  @property({ type: String }) align = 'left';
  @property({ type: String }) font = 'sans';
  @property({ type: Number }) opacity = 1.0;
  @property({ type: String }) letterSpacing = 'normal';
  @property({ type: Boolean }) uppercase = false;
  @property({ type: Boolean }) pulse = false;
  @property({ type: Boolean }) flip = false;   // animate each character when content changes

  static styles = css`
    :host {
      display: inline-block;
    }
    .text {
      margin: 0;
      padding: 0;
      line-height: 1.4;
      transition: all 0.3s ease;
    }
    .font-sans {
      font-family: 'Google Sans', 'Inter', system-ui, -apple-system, sans-serif;
    }
    .font-mono {
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
    }
    .font-serif {
      font-family: 'Georgia', Cambria, serif;
    }
    .uppercase {
      text-transform: uppercase;
    }
    .pulse {
      animation: text-pulse 1.8s infinite alternate;
    }
    @keyframes text-pulse {
      0% { opacity: 0.6; text-shadow: 0 0 4px var(--pulse-color, rgba(0, 242, 255, 0.1)); }
      100% { opacity: 1; text-shadow: 0 0 12px var(--pulse-color, rgba(0, 242, 255, 0.6)); }
    }
    .flip-char {
      display: inline-block;
      transform-origin: top center;
      backface-visibility: hidden;
      animation: flip-in 0.42s cubic-bezier(0.3, 1.25, 0.5, 1);
    }
    @keyframes flip-in {
      0%   { transform: rotateX(90deg);  opacity: 0; }
      55%  { transform: rotateX(-14deg); opacity: 1; }
      100% { transform: rotateX(0deg); }
    }
  `;

  render() {
    // Resolve preset sizes
    let resolvedSize = this.size;
    if (this.size === 'h1') resolvedSize = '32px';
    else if (this.size === 'h2') resolvedSize = '24px';
    else if (this.size === 'h3') resolvedSize = '18px';
    else if (this.size === 'body') resolvedSize = '14px';
    else if (this.size === 'caption') resolvedSize = '11px';

    // Resolve preset colors
    let resolvedColor = this.color;
    if (this.color === 'accent') resolvedColor = 'var(--accent, #00f2ff)';
    else if (this.color === 'mute') resolvedColor = 'rgba(255, 255, 255, 0.45)';
    else if (this.color === 'white') resolvedColor = '#ffffff';
    else if (this.color === 'success') resolvedColor = '#00ff88';
    else if (this.color === 'warning') resolvedColor = '#ffd60a';
    else if (this.color === 'danger') resolvedColor = '#ff3b57';
    else if (this.color === 'cyan') resolvedColor = '#00f2ff';

    const inlineStyles = `
      font-size: ${resolvedSize};
      font-weight: ${this.weight};
      color: ${resolvedColor};
      text-align: ${this.align};
      opacity: ${this.opacity};
      letter-spacing: ${this.letterSpacing};
      --pulse-color: ${resolvedColor};
    `;

    const classes = [
      'text',
      `font-${this.font}`,
      this.uppercase ? 'uppercase' : '',
      this.pulse ? 'pulse' : ''
    ].filter(Boolean).join(' ');

    const body = this.flip
      ? repeat(
          String(this.content).split(''),
          (ch, i) => `${i}:${ch}`,                       // changed char re-keys → flip animation
          (ch) => ch === ' '
            ? html`<span>&nbsp;</span>`
            : html`<span class="flip-char">${ch}</span>`,
        )
      : this.content;

    return html`
      <span class="${classes}" style="${inlineStyles}">
        ${body}<slot></slot>
      </span>
    `;
  }
}
