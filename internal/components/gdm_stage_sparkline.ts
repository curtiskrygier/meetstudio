import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-sparkline')
export class GdmStageSparkline extends LitElement {
  @property({ type: String }) data = ''; // Comma separated numbers e.g. "10,15,8,20,18,30"
  @property({ type: String }) color = 'accent'; // accent, success, warning, danger or custom hex
  @property({ type: String }) width = '120px';
  @property({ type: String }) height = '40px';
  @property({ type: Boolean }) fill = true;

  static styles = css`
    :host {
      display: inline-block;
      vertical-align: middle;
      line-height: 0;
    }
    .sparkline-svg {
      display: block;
      overflow: visible;
    }
  `;

  render() {
    // Resolve preset colors
    let resolvedColor = this.color;
    if (this.color === 'accent' || this.color === 'cyan') resolvedColor = '#00f2ff';
    else if (this.color === 'success') resolvedColor = '#00ff88';
    else if (this.color === 'warning') resolvedColor = '#ffd60a';
    else if (this.color === 'danger') resolvedColor = '#ff3b57';

    // Parse values
    const values = this.data
      ? this.data.split(',').map(v => parseFloat(v.trim())).filter(v => !isNaN(v))
      : [];

    if (values.length < 2) {
      return html`
        <svg width="${this.width}" height="${this.height}" class="sparkline-svg">
          <line x1="0" y1="50%" x2="100%" y2="50%" stroke="rgba(255,255,255,0.15)" stroke-width="2" stroke-dasharray="3,3"/>
        </svg>
      `;
    }

    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;

    // Viewport dimensions (we'll scale into a standard 100x40 coordinate space, then stretch with SVG attributes)
    const svgWidth = 100;
    const svgHeight = 40;
    const padding = 2; // Keep line within bounds

    // Map each value to standard SVG coordinates
    const points = values.map((val, i) => {
      const x = (i / (values.length - 1)) * svgWidth;
      // SVG coordinates: y is 0 at top, so we invert it
      const y = svgHeight - padding - ((val - min) / range) * (svgHeight - 2 * padding);
      return { x, y };
    });

    // Build path line
    const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');

    // Build fill path
    const fillPath = this.fill
      ? `${linePath} L ${svgWidth} ${svgHeight} L 0 ${svgHeight} Z`
      : '';

    // Create unique ID for the gradient to avoid collisions
    const gradientId = `spark-grad-${Math.random().toString(36).substr(2, 9)}`;

    return html`
      <svg 
        width="${this.width}" 
        height="${this.height}" 
        viewBox="0 0 ${svgWidth} ${svgHeight}" 
        class="sparkline-svg"
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id="${gradientId}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="${resolvedColor}" stop-opacity="0.35"/>
            <stop offset="100%" stop-color="${resolvedColor}" stop-opacity="0.0"/>
          </linearGradient>
        </defs>

        ${this.fill 
          ? html`<path d="${fillPath}" fill="url(#${gradientId})" />` 
          : ''
        }

        <path 
          d="${linePath}" 
          fill="none" 
          stroke="${resolvedColor}" 
          stroke-width="1.8" 
          stroke-linecap="round" 
          stroke-linejoin="round"
        />
      </svg>
    `;
  }
}
