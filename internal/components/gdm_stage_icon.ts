import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

// Centralized SVG path definitions for critical visual elements
const ICON_PATHS: Record<string, { viewBox?: string; svg: any }> = {
  'sonar': {
    svg: html`
      <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" fill="none" opacity="0.2"/>
      <circle cx="12" cy="12" r="6" stroke="currentColor" stroke-width="2" fill="none" opacity="0.4"/>
      <circle cx="12" cy="12" r="2" stroke="currentColor" stroke-width="2" fill="currentColor"/>
      <line x1="12" y1="12" x2="20" y2="6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    `
  },
  'clock': {
    svg: html`
      <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" fill="none"/>
      <polyline points="12 6 12 12 16 14" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    `
  },
  'chart': {
    svg: html`
      <line x1="18" y1="20" x2="18" y2="10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <line x1="12" y1="20" x2="12" y2="4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <line x1="6" y1="20" x2="6" y2="14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    `
  },
  'trending-up': {
    svg: html`
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
      <polyline points="17 6 23 6 23 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    `
  },
  'trending-down': {
    svg: html`
      <polyline points="23 18 13.5 8.5 8.5 13.5 1 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
      <polyline points="17 18 23 18 23 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    `
  },
  'lock': {
    svg: html`
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" stroke="currentColor" stroke-width="2" fill="none"/>
      <path d="M7 11V7a5 5 0 0 1 10 0v4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    `
  },
  'unlock': {
    svg: html`
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" stroke="currentColor" stroke-width="2" fill="none"/>
      <path d="M7 11V7a5 5 0 0 1 9.9-1" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    `
  },
  'info': {
    svg: html`
      <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" fill="none"/>
      <line x1="12" y1="16" x2="12" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <line x1="12" y1="8" x2="12.01" y2="8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    `
  },
  'alert': {
    svg: html`
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
      <line x1="12" y1="9" x2="12" y2="13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <line x1="12" y1="17" x2="12.01" y2="17" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    `
  },
  'activity': {
    svg: html`
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    `
  },
  'database': {
    svg: html`
      <ellipse cx="12" cy="5" rx="9" ry="3" stroke="currentColor" stroke-width="2" fill="none"/>
      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" stroke="currentColor" stroke-width="2" fill="none"/>
      <path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3" stroke="currentColor" stroke-width="2" fill="none"/>
    `
  },
  'user': {
    svg: html`
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
      <circle cx="12" cy="7" r="4" stroke="currentColor" stroke-width="2" fill="none"/>
    `
  },
  'globe': {
    svg: html`
      <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" fill="none"/>
      <path d="M2 12h20" stroke="currentColor" stroke-width="2"/>
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    `
  },
  'cpu': {
    svg: html`
      <rect x="4" y="4" width="16" height="16" rx="2" ry="2" stroke="currentColor" stroke-width="2" fill="none"/>
      <rect x="9" y="9" width="6" height="6" stroke="currentColor" stroke-width="2" fill="none"/>
      <line x1="9" y1="1" x2="9" y2="4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <line x1="15" y1="1" x2="15" y2="4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <line x1="9" y1="20" x2="9" y2="23" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <line x1="15" y1="20" x2="15" y2="23" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <line x1="20" y1="9" x2="23" y2="9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <line x1="20" y1="15" x2="23" y2="15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <line x1="1" y1="9" x2="4" y2="9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <line x1="1" y1="15" x2="4" y2="15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    `
  },
  'server': {
    svg: html`
      <rect x="2" y="2" width="20" height="8" rx="2" ry="2" stroke="currentColor" stroke-width="2" fill="none"/>
      <rect x="2" y="14" width="20" height="8" rx="2" ry="2" stroke="currentColor" stroke-width="2" fill="none"/>
      <line x1="6" y1="6" x2="6.01" y2="6" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
      <line x1="6" y1="18" x2="6.01" y2="18" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
    `
  },
  'arrow-up': {
    svg: html`
      <line x1="12" y1="19" x2="12" y2="5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <polyline points="5 12 12 5 19 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    `
  },
  'arrow-down': {
    svg: html`
      <line x1="12" y1="5" x2="12" y2="19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <polyline points="19 12 12 19 5 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    `
  },
  'check': {
    svg: html`
      <polyline points="20 6 9 17 4 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    `
  },
  'close': {
    svg: html`
      <line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      <line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    `
  },
  'chevron-right': {
    svg: html`
      <polyline points="9 18 15 12 9 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    `
  },
  'chevron-left': {
    svg: html`
      <polyline points="15 18 9 12 15 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    `
  }
};

@customElement('gdm-icon')
export class GdmStageIcon extends LitElement {
  @property({ type: String }) name = 'info';
  @property({ type: String }) color = 'currentColor'; // accent, cyan, success, warning, danger or custom
  @property({ type: String }) size = '20px';

  static styles = css`
    :host {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      vertical-align: middle;
      line-height: 0;
    }
    svg {
      transition: color 0.3s ease;
    }
  `;

  render() {
    // Resolve preset colors
    let resolvedColor = this.color;
    if (this.color === 'accent' || this.color === 'cyan') resolvedColor = '#00f2ff';
    else if (this.color === 'success') resolvedColor = '#00ff88';
    else if (this.color === 'warning') resolvedColor = '#ffd60a';
    else if (this.color === 'danger') resolvedColor = '#ff3b57';

    const iconData = ICON_PATHS[this.name] || ICON_PATHS['info'];
    const viewBox = iconData.viewBox || '0 0 24 24';

    return html`
      <svg 
        width="${this.size}" 
        height="${this.size}" 
        viewBox="${viewBox}" 
        style="color: ${resolvedColor};"
      >
        ${iconData.svg}
      </svg>
    `;
  }
}
