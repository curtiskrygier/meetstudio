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
      animation: chat-rise 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
      box-sizing: border-box;
    }
    @keyframes chat-rise {
      from { 
        opacity: 0; 
        transform: translateY(30px) scale(0.92);
        filter: blur(4px);
      }
      to { 
        opacity: 1; 
        transform: translateY(0) scale(1);
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
