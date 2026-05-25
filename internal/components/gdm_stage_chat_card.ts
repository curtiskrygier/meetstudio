import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-chat-card')
export class GdmStageChatCard extends LitElement {
  @property({ type: String }) sender = '';
  @property({ type: String }) text = '';
  @property({ type: String }) avatar = '';

  static styles = css`
    :host {
      display: block;
      transition: bottom 0.45s cubic-bezier(0.16, 1, 0.3, 1);
    }
    @keyframes slide-in { from { opacity: 0; transform: translateY(20px) scale(0.97); } to { opacity: 1; transform: translateY(0) scale(1); } }
    .card {
      display: flex;
      flex-direction: row;
      align-items: flex-start;
      background: rgba(8, 10, 20, 0.80);
      backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.10);
      border-radius: 14px;
      padding: 12px 16px;
      min-width: 260px;
      max-width: 360px;
      animation: slide-in 0.35s cubic-bezier(0.22, 1, 0.36, 1) both;
      box-sizing: border-box;
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
