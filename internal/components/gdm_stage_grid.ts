import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-stage-grid')
export class GdmStageGrid extends LitElement {
  @property({ type: String }) layout: string = 'single';
  @property({ type: Number }) focusedPanel: number = 0;

  static styles = css`
    :host {
      display: block;
      position: fixed;
      inset: 0;
      z-index: 100;
      background: #000;
    }
    .grid {
      display: grid;
      width: 100%;
      height: 100%;
      gap: 8px;
      padding: 8px;
      box-sizing: border-box;
      transition: grid-template-columns 0.6s cubic-bezier(0.16, 1, 0.3, 1),
                  grid-template-rows 0.6s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .grid.single {
      grid-template-columns: 1fr;
      grid-template-rows: 1fr;
    }
    .grid.split {
      grid-template-columns: 1fr 1fr;
      grid-template-rows: 1fr;
    }
    .grid.grid {
      grid-template-columns: 1fr 1fr;
      grid-template-rows: 1fr 1fr;
    }
    .slot {
      overflow: hidden;
      position: relative;
      background: rgba(10, 12, 24, 0.4);
      border-radius: 12px;
      border: 1px solid rgba(255, 255, 255, 0.05);
      transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .slot.focused {
      box-shadow: inset 0 0 0 2px rgba(0, 242, 255, 0.45), 0 0 30px rgba(0, 242, 255, 0.1);
      border-color: rgba(0, 242, 255, 0.3);
    }
  `;

  render() {
    return html`
      <div class="grid ${this.layout}">
        <div class="slot ${this.focusedPanel === 1 ? 'focused' : ''}">
          <slot name="panel-1"></slot>
        </div>
        <div class="slot ${this.focusedPanel === 2 ? 'focused' : ''}">
          <slot name="panel-2"></slot>
        </div>
        <div class="slot ${this.focusedPanel === 3 ? 'focused' : ''}">
          <slot name="panel-3"></slot>
        </div>
        <div class="slot ${this.focusedPanel === 4 ? 'focused' : ''}">
          <slot name="panel-4"></slot>
        </div>
      </div>
    `;
  }
}
