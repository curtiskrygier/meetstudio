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
    }
    .grid.single {
      grid-template-columns: 1fr;
      grid-template-rows: 1fr;
      gap: 0;
      padding: 0;
    }
    .grid.single .slot:not(:first-child) {
      display: none;
    }
    .grid.single .slot:first-child {
      border-radius: 0;
      border: none;
      background: transparent;
    }
    .grid.split {
      grid-template-columns: 1fr 1fr;
      grid-template-rows: 1fr;
    }
    @media (max-aspect-ratio: 1/1), (max-width: 768px) {
      .grid.split {
        grid-template-columns: 1fr;
        grid-template-rows: 1fr 1fr;
      }
    }
    .grid.split .slot:nth-child(n+3) {
      display: none;
    }
    .grid.presentation {
      grid-template-columns: 2.2fr 1fr;
      grid-template-rows: 1fr;
    }
    @media (max-aspect-ratio: 1/1), (max-width: 768px) {
      .grid.presentation {
        grid-template-columns: 1fr;
        grid-template-rows: 2.2fr 1fr;
      }
    }
    .grid.presentation .slot:nth-child(n+3) {
      display: none;
    }
    .grid.grid {
      grid-template-columns: 1fr 1fr;
      grid-template-rows: 1fr 1fr;
    }
    /* hero: panel-1 fills the entire stage; other panels hidden */
    .grid.hero {
      grid-template-columns: 1fr 1fr;
      grid-template-rows: 1fr 1fr;
    }
    .grid.hero .slot:first-child {
      grid-column: 1 / -1;
      grid-row: 1 / -1;
      z-index: 2;
    }
    .grid.hero .slot:not(:first-child) {
      display: none;
    }
    .slot {
      overflow: hidden;
      position: relative;
      background: rgba(10, 12, 24, 0.4);
      border-radius: 12px;
      border: 1px solid rgba(255, 255, 255, 0.05);
      display: flex;
      flex-direction: column;
      align-items: stretch;
      justify-content: stretch;
    }
    .slot ::slotted(*) {
      flex: 1;
      width: 100%;
      height: 100%;
      display: flex !important;
      flex-direction: column;
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
