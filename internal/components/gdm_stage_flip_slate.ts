import { LitElement, css, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { repeat } from 'lit/directives/repeat.js';

@customElement('gdm-flip-slate')
export class GdmStageFlipSlate extends LitElement {
  @property({ type: String }) text = '';
  @property({ type: Boolean, reflect: true }) active = false;
  @property({ type: String }) badgeText = 'A2UI REALTIME DISPLAY';
  @property({ type: String }) subtitle = 'MECHANICAL SPLIT-FLAP MATRIX';
  @property({ type: String }) accentColor = '#00f2ff';
  @property({ type: Number }) delayMs = 120; // Stagger delay between letters in ms

  // 3D Perspective & Specular Glow state
  private _animId?: number;
  private _isHovered = false;

  private _targetTiltX = 0;
  private _targetTiltY = 0;
  private _targetTiltZ = 0;
  private _targetGlowX = 0;
  private _targetGlowY = 0;
  private _targetGlowOpacity = 0;

  private _curTiltX = 0;
  private _curTiltY = 0;
  private _curTiltZ = 0;
  private _curGlowX = 0;
  private _curGlowY = 0;
  private _curGlowOpacity = 0;

  connectedCallback() {
    super.connectedCallback();
    this._start3DLoop();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._animId) cancelAnimationFrame(this._animId);
  }

  private _start3DLoop() {
    const loop = () => {
      if (!this._isHovered) {
        // Slow majestic float drift
        const time = Date.now() * 0.001;
        this._targetTiltX = Math.sin(time * 0.6) * 3.2;
        this._targetTiltY = Math.cos(time * 0.5) * 3.2;
        this._targetTiltZ = Math.sin(time * 0.3) * 12; // Z-axis drift
        this._targetGlowOpacity = 0.15 + Math.sin(time * 1.2) * 0.05;

        const rect = this.getBoundingClientRect();
        if (rect && rect.width > 0) {
          this._targetGlowX = rect.width / 2 + Math.sin(time * 0.3) * (rect.width * 0.22);
          this._targetGlowY = rect.height / 2 + Math.cos(time * 0.3) * (rect.height * 0.22);
        }
      }

      // Smooth interpolation ease-out
      const ease = 0.08;
      this._curTiltX += (this._targetTiltX - this._curTiltX) * ease;
      this._curTiltY += (this._targetTiltY - this._curTiltY) * ease;
      this._curTiltZ += (this._targetTiltZ - this._curTiltZ) * ease;
      this._curGlowX += (this._targetGlowX - this._curGlowX) * 0.12;
      this._curGlowY += (this._targetGlowY - this._curGlowY) * 0.12;
      this._curGlowOpacity += (this._targetGlowOpacity - this._curGlowOpacity) * ease;

      const board = this.shadowRoot?.querySelector('.board') as HTMLElement;
      if (board) {
        board.style.setProperty('--tilt-x', `${this._curTiltX.toFixed(3)}deg`);
        board.style.setProperty('--tilt-y', `${this._curTiltY.toFixed(3)}deg`);
        board.style.setProperty('--tilt-z', `${this._curTiltZ.toFixed(2)}px`);
        board.style.setProperty('--glow-x', `${this._curGlowX.toFixed(1)}px`);
        board.style.setProperty('--glow-y', `${this._curGlowY.toFixed(1)}px`);
        board.style.setProperty('--glow-opacity', `${this._curGlowOpacity.toFixed(3)}`);
      }

      this._animId = requestAnimationFrame(loop);
    };
    this._animId = requestAnimationFrame(loop);
  }

  private _onPointerEnter() {
    this._isHovered = true;
    this._targetGlowOpacity = 0.6;
  }

  private _onPointerMove(e: PointerEvent) {
    const board = e.currentTarget as HTMLElement;
    const rect = board.getBoundingClientRect();

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const normX = (x / rect.width) * 2 - 1;
    const normY = (y / rect.height) * 2 - 1;

    const maxTilt = 9.5; // Slightly deeper tilt for theatrical effect
    this._targetTiltX = -normY * maxTilt;
    this._targetTiltY = normX * maxTilt;
    this._targetTiltZ = 20; // Stand out significantly in Z space

    this._targetGlowX = x;
    this._targetGlowY = y;
  }

  private _onPointerLeave() {
    this._isHovered = false;
    this._targetTiltX = 0;
    this._targetTiltY = 0;
    this._targetTiltZ = 0;
    this._targetGlowOpacity = 0.15;
  }

  static styles = css`
    :host {
      position: fixed;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 765;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.5s ease;
      font-family: 'Google Sans', 'Inter', sans-serif;
      perspective: 2500px;
    }
    :host([active]) {
      opacity: 1;
      pointer-events: auto;
    }

    .board {
      width: min(1360px, 94vw);
      padding: 60px 40px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      background: linear-gradient(160deg, rgba(10, 14, 32, 0.96), rgba(4, 6, 18, 0.98));
      border: 1px solid rgba(0, 242, 255, 0.25);
      border-radius: 24px;
      box-shadow: 0 45px 115px rgba(0, 0, 0, 0.85), 0 0 70px rgba(0, 242, 255, 0.08);
      backdrop-filter: blur(40px);
      -webkit-backdrop-filter: blur(40px);
      overflow: hidden;
      position: relative;
      transform-style: preserve-3d;
      
      transform: translateY(30px) scale(0.96) rotateX(0deg) rotateY(0deg) translateZ(0px);
      transition: border-color 0.4s ease, box-shadow 0.4s ease;
    }
    :host([active]) .board {
      transform: rotateX(var(--tilt-x, 0deg)) rotateY(var(--tilt-y, 0deg)) translateZ(var(--tilt-z, 0px));
    }
    :host([active]) .board:hover {
      border-color: rgba(0, 242, 255, 0.55);
      box-shadow: 0 55px 130px rgba(0, 0, 0, 0.9), 0 0 90px rgba(0, 242, 255, 0.18);
    }

    /* Cybernetic Grid System in background */
    .cyber-grid {
      position: absolute;
      inset: 0;
      background-image: 
        linear-gradient(rgba(0, 242, 255, 0.02) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0, 242, 255, 0.02) 1px, transparent 1px);
      background-size: 50px 50px;
      background-position: center;
      opacity: 0.7;
      pointer-events: none;
      z-index: 1;
      transform: translateZ(-10px);
    }

    .specular-glow {
      position: absolute;
      inset: 0;
      pointer-events: none;
      z-index: 5;
      background: radial-gradient(circle at var(--glow-x, 50%) var(--glow-y, 50%), rgba(0, 242, 255, 0.16) 0%, transparent 55%);
      opacity: var(--glow-opacity, 0);
      mix-blend-mode: screen;
    }

    .header-block {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
      margin-bottom: 45px;
      text-align: center;
      z-index: 3;
      transform: translateZ(30px);
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.18em;
      color: var(--accent, #00f2ff);
      background: rgba(0, 242, 255, 0.08);
      border: 1px solid rgba(0, 242, 255, 0.25);
      border-radius: 30px;
      text-transform: uppercase;
    }
    .badge-dot {
      width: 6px;
      height: 6px;
      background: var(--accent, #00f2ff);
      border-radius: 50%;
      box-shadow: 0 0 8px var(--accent, #00f2ff);
      animation: blink 1s infinite alternate;
    }
    @keyframes blink { from { opacity: 0.3; } to { opacity: 1; } }

    .subtitle {
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.14em;
      color: rgba(255, 255, 255, 0.4);
      text-transform: uppercase;
    }

    /* Flip Matrix Grid */
    .matrix {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 16px 8px;
      max-width: 1000px;
      z-index: 3;
      transform: translateZ(20px);
    }

    /* Standard word wrapper to keep letters bound logically */
    .word {
      display: flex;
      gap: 4px;
      margin-right: 18px;
    }
    .word:last-child {
      margin-right: 0;
    }

    /* Premium split flap style card */
    .flap-card {
      position: relative;
      width: 58px;
      height: 86px;
      background: #0d1222;
      border-radius: 8px;
      box-shadow: 0 10px 25px rgba(0,0,0,0.6);
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
      font-size: 54px;
      font-weight: 800;
      line-height: 86px;
      color: #fff;
      text-align: center;
      perspective: 300px;
      overflow: hidden;
      border: 1px solid rgba(255,255,255,0.05);
    }

    .flap-card::before {
      content: '';
      position: absolute;
      left: 0; right: 0;
      top: 50%;
      height: 1px;
      background: rgba(0, 0, 0, 0.7);
      box-shadow: 0 1px 0 rgba(255,255,255,0.06);
      z-index: 4;
    }

    /* High-end mechanical flip open animation with sequential custom properties */
    .flap-char {
      display: block;
      width: 100%;
      height: 100%;
      transform-origin: top center;
      backface-visibility: hidden;
      opacity: 0;
      transform: rotateX(90deg);
    }

    :host([active]) .flap-char {
      animation: mech-flip 0.65s cubic-bezier(0.25, 1.3, 0.4, 1) forwards;
      animation-delay: var(--flap-delay, 0s);
    }

    @keyframes mech-flip {
      0% {
        transform: rotateX(90deg);
        opacity: 0;
        filter: brightness(0.2);
      }
      50% {
        filter: brightness(1.5);
      }
      70% {
        transform: rotateX(-18deg);
        opacity: 1;
      }
      100% {
        transform: rotateX(0deg);
        opacity: 1;
        filter: brightness(1);
        text-shadow: 0 0 15px rgba(0, 242, 255, 0.3);
      }
    }

    /* Ambient backlights */
    .ambient-glow {
      position: absolute;
      width: 300px;
      height: 300px;
      background: var(--accent, #00f2ff);
      filter: blur(140px);
      opacity: 0.08;
      border-radius: 50%;
      pointer-events: none;
      z-index: 0;
    }
    .amb-top { top: -50px; left: 10%; }
    .amb-bot { bottom: -50px; right: 10%; }
  `;

  render() {
    // Process text into words and individual characters
    const rawWords = this.text ? this.text.split(' ') : [];
    let absoluteIndex = 0;

    return html`
      <div
        class="board"
        style="--accent:${this.accentColor}"
        @pointermove=${this._onPointerMove}
        @pointerenter=${this._onPointerEnter}
        @pointerleave=${this._onPointerLeave}
      >
        <div class="cyber-grid"></div>
        <div class="specular-glow"></div>
        
        <div class="ambient-glow amb-top"></div>
        <div class="ambient-glow amb-bot"></div>

        <div class="header-block">
          <span class="badge"><span class="badge-dot"></span>${this.badgeText}</span>
          <span class="subtitle">${this.subtitle}</span>
        </div>

        <div class="matrix">
          ${rawWords.map((word) => {
            const chars = word.split('');
            return html`
              <div class="word">
                ${chars.map((ch) => {
                  const delay = `${(absoluteIndex * this.delayMs) / 1000}s`;
                  absoluteIndex++;
                  return html`
                    <div class="flap-card">
                      <span class="flap-char" style="--flap-delay: ${delay}">${ch}</span>
                    </div>
                  `;
                })}
              </div>
            `;
          })}
        </div>
      </div>
    `;
  }
}
