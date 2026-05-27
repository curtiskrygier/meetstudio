import { LitElement, css, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { repeat } from 'lit/directives/repeat.js';

@customElement('gdm-captions')
export class GdmStageCaptions extends LitElement {
  @property({ type: String }) text = '';
  @property({ type: String }) speaker = 'Speaker';
  @property({ type: Boolean, reflect: true }) active = false;
  @property({ type: String }) accentColor = '#00f2ff';
  @property({ type: Number }) fontSize = 0;
  @property({ type: Boolean }) flip = false; // Toggle split-flap style

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
      bottom: 96px;
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
      display: inline-block;
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      margin-right: 10px;
      color: var(--caption-accent, #00f2ff);
      vertical-align: middle;
    }
    .content {
      line-height: 1.45;
      vertical-align: middle;
    }
    @keyframes caption-rise {
      from { opacity: 0; transform: translateY(6px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    /* Split-flap caption: each letter sits in a departure-board flap card and
       flips in. Cards are KEYED per character in render() so a changed char
       re-creates its card and the flip replays on every new line (not just the
       first), and they're sized to the caption font so a sentence stays readable
       (words flow and wrap) rather than becoming a wall of tiny fixed tiles. */
    .cap-line { display: inline; }
    .cap-word {
      display: inline-flex;
      gap: 2px;
      margin-right: 0.42em;
      vertical-align: middle;
    }
    .cap-word:last-child { margin-right: 0; }
    .cap-flap-card {
      position: relative;
      display: inline-block;
      min-width: 0.6em;
      padding: 2px 3px;
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
      font-size: var(--gdm-cap-font-size, 18px);
      font-weight: 800;
      line-height: 1.25;
      color: #fff;
      text-align: center;
      background: linear-gradient(180deg, #141a2e 0%, #0c1120 49.5%, #070b16 50.5%, #10162a 100%);
      border-radius: 4px;
      border: 1px solid rgba(255, 255, 255, 0.05);
      box-shadow: 0 2px 5px rgba(0, 0, 0, 0.45);
      overflow: hidden;
      perspective: 220px;
      vertical-align: middle;
    }
    .cap-flap-card::after {
      content: '';
      position: absolute;
      left: 8%; right: 8%;
      top: 50%;
      height: 1px;
      background: rgba(0, 0, 0, 0.6);
      transform: translateY(-0.5px);
      z-index: 2;
    }
    .cap-flap-char {
      display: block;
      transform-origin: top center;
      backface-visibility: hidden;
      animation: cap-flip 0.42s cubic-bezier(0.25, 1.25, 0.4, 1) both;
    }
    @keyframes cap-flip {
      0%   { transform: rotateX(90deg);  opacity: 0; }
      60%  { transform: rotateX(-12deg); opacity: 1; text-shadow: 0 0 7px var(--caption-accent, rgba(0,242,255,0.5)); }
      100% { transform: rotateX(0deg);   opacity: 1; text-shadow: none; }
    }
  `;

  render() {
    let gi = 0; // global char index → left-to-right flip stagger across the whole line
    const words = this.text ? String(this.text).split(' ') : [];
    const flipBody = html`<span class="cap-line">${words.map((word, wi) => {
      const cards = word.split('').map((ch, ci) => {
        const delay = Math.min(gi * 16, 700) / 1000;
        gi += 1;
        return { ch, ci, delay };
      });
      gi += 1; // account for the space between words in the sweep
      return html`<span class="cap-word">${repeat(
        cards,
        (e) => `${wi}-${e.ci}:${e.ch}`,                  // changed char re-keys → flip replays per line
        (e) => html`<span class="cap-flap-card"><span class="cap-flap-char" style="animation-delay:${e.delay}s">${e.ch}</span></span>`,
      )}</span>`;
    })}</span>`;

    const contentBody = this.flip
      ? flipBody
      : html`<span class="content">${this.text}</span>`;

    return html`
      ${this._prev && !this.flip
        ? html`<div class="pill prev"><span class="content">${this._prev}</span></div>`
        : ''}
      <div class="pill active">
        <span class="speaker">${this.speaker}:</span>${contentBody}
      </div>
    `;
  }
}
