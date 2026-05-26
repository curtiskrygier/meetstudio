import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-chat-card')
export class GdmStageChatCard extends LitElement {
  @property({ type: String }) sender = '';
  @property({ type: String }) text = '';
  @property({ type: String }) avatar = '';
  /** Seconds before the card auto-dismisses. 0 = never. */
  @property({ type: Number }) duration = 10;

  private _dismissTimer: any = null;

  connectedCallback() {
    super.connectedCallback();
    if (this.duration > 0) {
      this._dismissTimer = setTimeout(() => this._dismiss(), this.duration * 1000);
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._dismissTimer !== null) {
      clearTimeout(this._dismissTimer);
      this._dismissTimer = null;
    }
  }

  private _dismiss() {
    // Collapse height and fade out, then signal the host so it can skip re-adding
    this.style.transition = 'opacity 0.5s ease, max-height 0.5s ease 0.3s, margin 0.5s ease 0.3s';
    this.style.opacity = '0';
    this.style.maxHeight = '0';
    this.style.overflow = 'hidden';
    this.style.margin = '0';
    setTimeout(() => {
      this.dispatchEvent(new CustomEvent('chat-dismiss', { bubbles: true, composed: true }));
      this.remove();
    }, 900);
  }

  static styles = css`
    :host {
      display: block;
      max-height: 200px;
    }
    .card {
      display: flex;
      flex-direction: row;
      align-items: flex-start;
      background: rgba(12, 16, 32, 0.75);
      backdrop-filter: blur(20px) saturate(1.8);
      -webkit-backdrop-filter: blur(20px) saturate(1.8);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 18px;
      padding: 14px 18px;
      min-width: 280px;
      max-width: 400px;
      animation: chat-slide-in 0.45s cubic-bezier(0.16, 1, 0.3, 1) both;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
      box-sizing: border-box;
    }
    @keyframes chat-slide-in {
      from {
        opacity: 0;
        transform: translateX(60px) scale(0.94);
        filter: blur(3px);
      }
      to {
        opacity: 1;
        transform: translateX(0) scale(1);
        filter: blur(0);
      }
    }
    .avatar {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      overflow: hidden;
      flex-shrink: 0;
      margin-right: 10px;
      background: linear-gradient(135deg, #4285F4, #9B59B6);
      color: #fff;
      font-size: 13px;
      font-weight: 700;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .avatar img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }
    .content {
      display: flex;
      flex-direction: column;
      min-width: 0;
    }
    .sender {
      font-size: 12px;
      font-weight: 700;
      color: #00f2ff;
      margin-bottom: 3px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .text {
      font-size: 13px;
      color: rgba(255, 255, 255, 0.85);
      line-height: 1.45;
      word-break: break-word;
    }
  `;

  private get _initials(): string {
    return this.sender ? this.sender.charAt(0).toUpperCase() : '?';
  }

  render() {
    return html`
      <div class="card">
        <div class="avatar">
          ${this.avatar
            ? html`<img src=${this.avatar} alt=${this.sender} />`
            : this._initials}
        </div>
        <div class="content">
          <div class="sender">${this.sender}</div>
          <div class="text">${this.text}</div>
        </div>
      </div>
    `;
  }
}
