import { LitElement, css, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

@customElement('gdm-captions')
export class GdmStageCaptions extends LitElement {
  @property({ type: String }) text = '';
  @property({ type: String }) speaker = 'Speaker';
  @property({ type: Boolean, reflect: true }) active = false;
  @property({ type: String }) accentColor = '#00f2ff';
  @property({ type: Number }) fontSize = 0;

  @state() private _prev = '';
  private _lastText = '';

  willUpdate(changed: Map<string | number | symbol, unknown>) {
    if (changed.has('text')) {
      const incoming = (this.text || '').trim();
      if (incoming && incoming !== this._lastText) {
        if (this._lastText) this._prev = this._lastText;
        this._lastText = incoming;
      }
    }
    if (changed.has('accentColor')) {
      this.style.setProperty('--caption-accent', this.accentColor);
    }
    if (changed.has('fontSize') && this.fontSize > 0) {
      this.style.setProperty('--gdm-cap-font-size', `${this.fontSize}px`);
    }
  }

  connectedCallback() {
    super.connectedCallback();
    this.style.setProperty('--caption-accent', this.accentColor);
    if (this.fontSize > 0) this.style.setProperty('--gdm-cap-font-size', `${this.fontSize}px`);
  }

  static styles = css`
    :host {
      position: fixed;
      left: 0;
      right: 0;
      bottom: 6px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
      padding: 0 40px;
      box-sizing: border-box;
      z-index: 740;
      pointer-events: none;
      opacity: 0;
      transform: translateY(8px);
      transition: opacity 0.35s ease, transform 0.35s cubic-bezier(0.16, 1, 0.3, 1);
    }
    :host([active]) {
      opacity: 1;
      transform: translateY(0);
    }
    .pill {
      width: 100%;
      text-align: center;
      border-radius: 8px;
      background: rgba(10, 10, 18, 0.86);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border: 1px solid rgba(0, 242, 255, 0.15);
      color: #fff;
      box-shadow: 0 2px 10px rgba(0, 0, 0, 0.4);
      box-sizing: border-box;
    }
    .pill.prev {
      padding: 3px 18px;
      font-size: var(--gdm-cap-prev-size, 11px);
      opacity: 0.32;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .pill.active {
      padding: 7px 22px;
      font-size: var(--gdm-cap-font-size, 16px);
      font-weight: 600;
      animation: caption-rise 0.25s ease-out;
      line-height: 1.45;
      overflow: hidden;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
    }
    .speaker {
      display: inline;
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      margin-right: 6px;
      color: var(--caption-accent, #00f2ff);
    }
    .content { line-height: 1.45; }
    @keyframes caption-rise {
      from { opacity: 0; transform: translateY(6px); }
      to   { opacity: 1; transform: translateY(0); }
    }
  `;

  render() {
    return html`
      ${this._prev
        ? html`<div class="pill prev"><span class="content">${this._prev}</span></div>`
        : ''}
      <div class="pill active">
        <span class="speaker">${this.speaker}:</span><span class="content">${this.text}</span>
      </div>
    `;
  }
}
