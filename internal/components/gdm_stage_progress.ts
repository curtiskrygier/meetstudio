import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-progress')
export class GdmStageProgress extends LitElement {
  @property({ type: Number }) value = 0; // 0 to 100
  @property({ type: String }) color = 'accent'; // accent, success, warning, danger, cyan or custom
  @property({ type: String }) height = '8px';
  @property({ type: Boolean }) animated = false;
  @property({ type: Boolean }) glow = true;

  static styles = css`
    :host {
      display: block;
      width: 100%;
      box-sizing: border-box;
      margin: 8px 0;
    }
    .track {
      width: 100%;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 10px;
      overflow: hidden;
      position: relative;
      box-sizing: border-box;
    }
    .fill {
      height: 100%;
      border-radius: 10px;
      transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
      position: relative;
      overflow: hidden;
    }
    
    /* Flow animation background pattern */
    .fill::after {
      content: '';
      position: absolute;
      top: 0; left: 0; bottom: 0; right: 0;
      background-image: linear-gradient(
        -45deg,
        rgba(255, 255, 255, 0.15) 25%,
        transparent 25%,
        transparent 50%,
        rgba(255, 255, 255, 0.15) 50%,
        rgba(255, 255, 255, 0.15) 75%,
        transparent 75%,
        transparent
      );
      background-size: 40px 40px;
      opacity: 0;
      transition: opacity 0.3s ease;
    }

    .animated .fill::after {
      opacity: 1;
      animation: progress-bar-stripes 1.5s linear infinite;
    }

    @keyframes progress-bar-stripes {
      from { background-position: 40px 0; }
      to { background-position: 0 0; }
    }
  `;

  render() {
    // Resolve preset/custom colors
    let resolvedColor = this.color;
    if (this.color === 'accent' || this.color === 'cyan') resolvedColor = '#00f2ff';
    else if (this.color === 'success') resolvedColor = '#00ff88';
    else if (this.color === 'warning') resolvedColor = '#ffd60a';
    else if (this.color === 'danger') resolvedColor = '#ff3b57';

    // Constrain value
    const percent = Math.max(0, Math.min(100, this.value));

    const fillStyle = `
      width: ${percent}%;
      background-color: ${resolvedColor};
      box-shadow: ${this.glow ? `0 0 12px ${resolvedColor}bb` : 'none'};
    `;

    return html`
      <div class="track ${this.animated ? 'animated' : ''}" style="height: ${this.height};">
        <div class="fill" style="${fillStyle}"></div>
      </div>
    `;
  }
}
