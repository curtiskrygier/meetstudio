import { LitElement, css, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

interface EmojiParticle {
  id: number;
  x: number;         // % from left
  drift: number;     // px horizontal drift
  duration: number;  // ms
  delay: number;     // ms
  size: number;      // px font-size
}

let _nextId = 0;

@customElement('gdm-emoji-burst')
export class GdmStageEmojiBurst extends LitElement {
  @property({ type: String }) emoji = '👏';
  @property({ type: Number }) count = 12;
  @property({ type: Boolean, reflect: true }) active = false;

  @state() private _particles: EmojiParticle[] = [];

  private _clearTimer: ReturnType<typeof setTimeout> | null = null;

  static styles = css`
    :host {
      display: block;
      position: fixed;
      inset: 0;
      z-index: 900;
      pointer-events: none;
      overflow: hidden;
    }

    .particle {
      position: absolute;
      bottom: -60px;
      line-height: 1;
      will-change: transform, opacity;
      animation: float-up var(--duration) var(--delay) ease-out forwards;
      transform-origin: center bottom;
    }

    @keyframes float-up {
      0% {
        transform: translateY(0) translateX(0) scale(0.6);
        opacity: 0;
      }
      10% {
        opacity: 1;
        transform: translateY(-8vh) translateX(calc(var(--drift) * 0.1)) scale(1.1);
      }
      60% {
        opacity: 0.9;
        transform: translateY(-55vh) translateX(calc(var(--drift) * 0.7)) scale(1);
      }
      100% {
        transform: translateY(-95vh) translateX(var(--drift)) scale(0.5);
        opacity: 0;
      }
    }
  `;

  updated(changed: Map<string, unknown>) {
    const shouldBurst =
      (changed.has('active') && this.active) ||
      (this.active && (changed.has('emoji') || changed.has('count')));

    if (shouldBurst) {
      this._spawn();
    }

    if (changed.has('active') && !this.active) {
      this._clear();
    }
  }

  private _spawn() {
    if (this._clearTimer !== null) {
      clearTimeout(this._clearTimer);
      this._clearTimer = null;
    }

    const particles: EmojiParticle[] = [];
    let maxExpiry = 0;

    for (let i = 0; i < this.count; i++) {
      const duration = 1500 + Math.random() * 1000;   // 1500–2500 ms
      const delay    = Math.random() * 400;             // 0–400 ms stagger
      const expiry   = duration + delay;
      if (expiry > maxExpiry) maxExpiry = expiry;

      particles.push({
        id:       _nextId++,
        x:        5 + Math.random() * 90,              // 5–95 % horizontal
        drift:    (Math.random() - 0.5) * 120,         // ±60 px drift
        duration,
        delay,
        size:     24 + Math.floor(Math.random() * 24), // 24–47 px
      });
    }

    this._particles = particles;

    // Clean up DOM nodes after all animations finish
    this._clearTimer = setTimeout(() => {
      this._particles = [];
      this._clearTimer = null;
    }, maxExpiry + 100);
  }

  private _clear() {
    if (this._clearTimer !== null) {
      clearTimeout(this._clearTimer);
      this._clearTimer = null;
    }
    this._particles = [];
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._clear();
  }

  render() {
    return html`
      ${this._particles.map(p => html`
        <span
          class="particle"
          style="
            left: ${p.x}%;
            font-size: ${p.size}px;
            --duration: ${p.duration}ms;
            --delay: ${p.delay}ms;
            --drift: ${p.drift}px;
          "
        >${this.emoji}</span>
      `)}
    `;
  }
}
