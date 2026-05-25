import { LitElement, css, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

/**
 * gdm-captions — first-class A2UI lower-third caption overlay.
 *
 * Unlike the legacy #transcript-layer (driven by out-of-band `transcript`
 * WebSocket messages), this component is composed through `render_stage` like
 * any other A2UI component: the agent sets `text` to the current caption point
 * and it renders as a large lower-third pill, keeping the prior line faded above
 * it so each sentence reads clearly, one at a time.
 */
@customElement('gdm-captions')
export class GdmStageCaptions extends LitElement {
  @property({ type: String }) text = '';
  @property({ type: String }) speaker = 'Speaker';
  @property({ type: Boolean, reflect: true }) active = false;
  @property({ type: String }) accentColor = '#00f2ff';

  // Internally remember the previous caption so a new `text` pushes the old
  // line up as a faded "previous" pill — no external history prop required.
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
  }

  static styles = css`
    :host {
      position: fixed;
      left: 0;
      right: 0;
      /* Sit above the ticker lane (shares the same safe-zone var the caption
         footer uses) so captions and the ticker never overlap. */
      bottom: calc(var(--ticker-safe-zone, 56px) + 28px);
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      padding: 0 24px;
      box-sizing: border-box;
      z-index: 740;
      pointer-events: none;
      opacity: 0;
      transform: translateY(12px);
      transition: opacity 0.4s ease, transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    }
    :host([active]) {
      opacity: 1;
      transform: translateY(0);
    }
    .pill {
      max-width: min(1000px, 90%);
      text-align: center;
      border-radius: 14px;
      background: rgba(15, 15, 20, 0.85);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border: 1px solid rgba(0, 242, 255, 0.2);
      color: #fff;
      word-wrap: break-word;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    }
    .pill.prev {
      padding: 8px 22px;
      font-size: var(--prev-font-size, 24px);
      opacity: 0.5;
      transform: scale(0.97);
    }
    .pill.active {
      padding: 12px 28px;
      font-size: var(--active-font-size, 32px);
      font-weight: 600;
      animation: caption-rise 0.3s ease-out;
    }
    .speaker {
      display: block;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      margin-bottom: 4px;
    }
    .content {
      text-shadow: 0 0 6px rgba(0, 242, 255, 0.4);
      line-height: 1.3;
    }
    @keyframes caption-rise {
      from { opacity: 0; transform: translateY(10px) scale(0.97); }
      to   { opacity: 1; transform: translateY(0) scale(1); }
    }
  `;

  render() {
    return html`
      ${this._prev
        ? html`<div class="pill prev"><span class="content">${this._prev}</span></div>`
        : ''}
      <div class="pill active">
        <span class="speaker" style="color:${this.accentColor}">${this.speaker}</span>
        <span class="content">${this.text}</span>
      </div>
    `;
  }
}
