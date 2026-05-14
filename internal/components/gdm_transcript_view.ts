import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-transcript-view')
export class GdmTranscriptView extends LitElement {
  @property({ type: Array }) transcript: Array<{id: string; role: string; text: string}> = [];

  static styles = css`
    :host { display: block; }
    .transcript { display: flex; flex-direction: column; gap: 12px; }
    .turn { display: flex; gap: 12px; animation: fade-in 200ms ease-out; }
    @keyframes fade-in { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
    .avatar { 
      width: 24px; height: 24px; border-radius: 6px; 
      background: var(--bg-3); flex-shrink: 0; display: grid; 
      place-items: center; margin-top: 2px; border: 1px solid var(--line-soft);
      transition: all 200ms ease;
    }
    .avatar.gem { background: linear-gradient(135deg, var(--gem-1), var(--gem-2)); border-color: transparent; }
    .turn-body { flex: 1; min-width: 0; }
    .turn-role { font-size: 10px; font-weight: 700; color: var(--fg-4); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px; }
    .turn-role.gem { color: var(--gem-2); }
    .turn-text { font-size: 12.5px; line-height: 1.5; color: var(--fg-2); white-space: pre-wrap; }
    
    .transcript-empty { 
      padding: 24px 16px; background: var(--bg-1); 
      border: 1px dashed var(--line); border-radius: 12px; 
      text-align: center; color: var(--fg-3); font-size: 12.5px; 
      transition: all 200ms ease;
    }
  `;

  render() {
    if (this.transcript.length === 0) {
      return html`<div class="transcript-empty">Speak to Gemini Architect to see the transcript here.</div>`;
    }

    return html`
      <div class="transcript">
        ${this.transcript.map(turn => html`
          <div class="turn">
            <div class="avatar ${turn.role.includes('Gemini') ? 'gem' : ''}">
              ${turn.role.includes('Gemini') ? html`
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                </svg>
              ` : turn.role.substring(0, 1)}
            </div>
            <div class="turn-body">
              <div class="turn-role ${turn.role.includes('Gemini') ? 'gem' : ''}">${turn.role}</div>
              <div class="turn-text">${turn.text}</div>
            </div>
          </div>
        `)}
      </div>
    `;
  }
}
