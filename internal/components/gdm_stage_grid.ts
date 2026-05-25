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
      gap: 4px;
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
    .grid.grid-3 {
      grid-template-columns: 1fr 1fr;
      grid-template-rows: 1fr 1fr;
    }
    .grid.grid-3 .slot:first-child {
      grid-column: 1 / -1;
    }
    .grid.presentation {
      grid-template-columns: 1fr;
      grid-template-rows: 1fr;
    }
    .grid.presentation .slot.focused {
      box-shadow: inset 0 0 0 3px rgba(0, 242, 255, 0.18);
    }
    .slot {
      overflow: hidden;
      position: relative;
      background: rgba(0, 0, 0, 0.4);
      transition: box-shadow 0.3s;
    }
    .slot.focused {
      box-shadow: inset 0 0 0 2px rgba(0, 242, 255, 0.45);
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
