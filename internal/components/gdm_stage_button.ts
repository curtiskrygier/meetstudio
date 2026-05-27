import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import './gdm_stage_icon';

@customElement('gdm-button')
export class GdmStageButton extends LitElement {
  @property({ type: String }) label = '';
  @property({ type: String }) actionId = '';
  @property({ type: String }) payload = '';
  @property({ type: String }) icon = ''; // optional icon name
  @property({ type: String }) type = 'primary'; // primary, secondary, danger, ghost
  @property({ type: Boolean }) disabled = false;

  static styles = css`
    :host {
      display: inline-block;
      vertical-align: middle;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 8px 16px;
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      box-sizing: border-box;
      user-select: none;
    }
    
    .btn:active {
      transform: scale(0.96);
    }

    .btn-primary {
      background: rgba(0, 242, 255, 0.15);
      color: #00f2ff;
      border: 1px solid rgba(0, 242, 255, 0.35);
      box-shadow: 0 0 12px rgba(0, 242, 255, 0.12);
    }
    .btn-primary:hover:not(.disabled) {
      background: rgba(0, 242, 255, 0.25);
      border-color: rgba(0, 242, 255, 0.6);
      box-shadow: 0 0 20px rgba(0, 242, 255, 0.3);
    }

    .btn-secondary {
      background: rgba(255, 255, 255, 0.04);
      color: rgba(255, 255, 255, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.12);
    }
    .btn-secondary:hover:not(.disabled) {
      background: rgba(255, 255, 255, 0.08);
      border-color: rgba(255, 255, 255, 0.25);
    }

    .btn-danger {
      background: rgba(255, 59, 87, 0.15);
      color: #ff3b57;
      border: 1px solid rgba(255, 59, 87, 0.35);
      box-shadow: 0 0 12px rgba(255, 59, 87, 0.12);
    }
    .btn-danger:hover:not(.disabled) {
      background: rgba(255, 59, 87, 0.25);
      border-color: rgba(255, 59, 87, 0.6);
      box-shadow: 0 0 20px rgba(255, 59, 87, 0.3);
    }

    .btn-ghost {
      background: transparent;
      color: rgba(255, 255, 255, 0.65);
      border: 1px solid transparent;
    }
    .btn-ghost:hover:not(.disabled) {
      background: rgba(255, 255, 255, 0.05);
      color: #ffffff;
    }

    .disabled {
      opacity: 0.35;
      cursor: not-allowed;
      pointer-events: none;
      box-shadow: none !important;
    }
  `;

  private _handleClick(e: Event) {
    if (this.disabled) {
      e.preventDefault();
      return;
    }

    let parsedPayload = this.payload;
    try {
      if (this.payload && (this.payload.startsWith('{') || this.payload.startsWith('['))) {
        parsedPayload = JSON.parse(this.payload);
      }
    } catch (_) {
      // Keep as raw string if JSON parsing fails
    }

    this.dispatchEvent(new CustomEvent('gdm-button-click', {
      detail: {
        actionId: this.actionId,
        payload: parsedPayload
      },
      bubbles: true,
      composed: true
    }));
  }

  render() {
    const btnClass = `btn btn-${this.type} ${this.disabled ? 'disabled' : ''}`;

    return html`
      <div class="${btnClass}" @click="${this._handleClick}">
        ${this.icon ? html`<gdm-icon .name="${this.icon}" size="14px"></gdm-icon>` : ''}
        <span>${this.label}<slot></slot></span>
      </div>
    `;
  }
}
