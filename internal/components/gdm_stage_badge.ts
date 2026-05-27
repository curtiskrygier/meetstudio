import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-badge')
export class GdmStageBadge extends LitElement {
  @property({ type: String }) text = '';
  @property({ type: String }) type = 'primary'; // success, warning, danger, primary, info, cyan
  @property({ type: Boolean }) pulse = false;
  @property({ type: Boolean }) outline = false;

  static styles = css`
    :host {
      display: inline-block;
      vertical-align: middle;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: 20px;
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      box-sizing: border-box;
    }
    
    /* Preset Colors */
    .type-primary {
      --badge-color: #00f2ff;
      --badge-bg: rgba(0, 242, 255, 0.1);
      --badge-border: rgba(0, 242, 255, 0.25);
    }
    .type-cyan {
      --badge-color: #00f2ff;
      --badge-bg: rgba(0, 242, 255, 0.1);
      --badge-border: rgba(0, 242, 255, 0.25);
    }
    .type-info {
      --badge-color: #00c0ff;
      --badge-bg: rgba(0, 192, 255, 0.1);
      --badge-border: rgba(0, 192, 255, 0.25);
    }
    .type-success {
      --badge-color: #00ff88;
      --badge-bg: rgba(0, 255, 136, 0.10);
      --badge-border: rgba(0, 255, 136, 0.25);
    }
    .type-warning {
      --badge-color: #ffd60a;
      --badge-bg: rgba(255, 214, 10, 0.1);
      --badge-border: rgba(255, 214, 10, 0.25);
    }
    .type-danger {
      --badge-color: #ff3b57;
      --badge-bg: rgba(255, 59, 87, 0.12);
      --badge-border: rgba(255, 59, 87, 0.25);
    }

    /* Rendering Modes */
    .solid {
      background: var(--badge-bg);
      color: var(--badge-color);
      border: 1px solid var(--badge-border);
      box-shadow: 0 0 10px var(--badge-bg);
    }
    .outline {
      background: transparent;
      color: var(--badge-color);
      border: 1px solid var(--badge-color);
      box-shadow: 0 0 4px var(--badge-bg);
    }

    /* Pulse Dot */
    .dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background-color: var(--badge-color);
      box-shadow: 0 0 8px var(--badge-color);
    }
    .pulsing-dot {
      animation: blink 1.2s infinite alternate;
    }

    @keyframes blink {
      0% {
        opacity: 0.3;
        transform: scale(0.85);
        box-shadow: 0 0 2px var(--badge-color);
      }
      100% {
        opacity: 1;
        transform: scale(1.15);
        box-shadow: 0 0 10px var(--badge-color);
      }
    }
  `;

  render() {
    const presetClass = `type-${this.type}`;
    const modeClass = this.outline ? 'outline' : 'solid';

    return html`
      <div class="badge ${presetClass} ${modeClass}">
        ${this.pulse ? html`<span class="dot pulsing-dot"></span>` : ''}
        <span>${this.text}<slot></slot></span>
      </div>
    `;
  }
}
