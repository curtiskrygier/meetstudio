import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-scroller')
export class GdmStageScroller extends LitElement {
  @property({ type: String }) speed = '20s'; // CSS animation duration e.g. "15s" or "25s"
  @property({ type: String }) direction = 'left'; // left, right
  @property({ type: Boolean }) active = true;

  static styles = css`
    :host {
      display: block;
      width: 100%;
      overflow: hidden;
      box-sizing: border-box;
    }
    
    .scroller-viewport {
      display: flex;
      width: 100%;
      overflow: hidden;
      position: relative;
      mask-image: linear-gradient(to right, transparent, #000 8%, #000 92%, transparent);
      -webkit-mask-image: linear-gradient(to right, transparent, #000 8%, #000 92%, transparent);
      box-sizing: border-box;
    }

    .track {
      display: flex;
      gap: 16px;
      white-space: nowrap;
      box-sizing: border-box;
    }

    .animated-left {
      animation: scroll-left var(--scroller-duration, 20s) linear infinite;
    }

    .animated-right {
      animation: scroll-right var(--scroller-duration, 20s) linear infinite;
    }

    .paused {
      animation-play-state: paused !important;
    }

    /* We render two slots side by side so that the infinite looping looks seamless and has no gaps */
    @keyframes scroll-left {
      0% {
        transform: translate3d(0, 0, 0);
      }
      100% {
        transform: translate3d(-50%, 0, 0);
      }
    }

    @keyframes scroll-right {
      0% {
        transform: translate3d(-50%, 0, 0);
      }
      100% {
        transform: translate3d(0, 0, 0);
      }
    }
  `;

  render() {
    let duration = this.speed;
    if (typeof duration === 'number' || !isNaN(Number(duration))) {
      duration = `${duration}s`;
    }

    const directionClass = this.direction === 'right' ? 'animated-right' : 'animated-left';
    const activeClass = this.active ? '' : 'paused';

    return html`
      <div class="scroller-viewport">
        <!-- Render double track to create a seamless infinite loop -->
        <div 
          class="track ${directionClass} ${activeClass}" 
          style="--scroller-duration: ${duration};"
        >
          <slot></slot>
          <!-- Duplicate content block so the carousel has wrapping elements -->
          <slot name="repeat"></slot>
        </div>
      </div>
    `;
  }
}
