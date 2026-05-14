import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('gdm-status-view')
export class GdmStatusView extends LitElement {
  @property({ type: String }) state: 'disconnected' | 'connecting' | 'listening' | 'speaking' | 'wake' = 'disconnected';
  @property({ type: String }) status = '';
  @property({ type: String }) error = '';
  @property({ type: Boolean }) authenticated = false;

  static styles = css`
    :host { display: block; }
    .hero { padding: 40px 18px 24px; display: flex; flex-direction: column; align-items: center; gap: 14px; text-align: center; }
    .orb-wrap { position: relative; width: 112px; height: 112px; display: grid; place-items: center; }
    .orb {
      position: relative; width: 56px; height: 56px; border-radius: 50%;
      background: radial-gradient(circle at 50% 45%, rgba(255,255,255,0.10) 0%, var(--gem-2) 35%, var(--gem-1) 70%, rgba(255,255,255,0.02) 100%);
      box-shadow: 0 0 0 1px rgba(255,255,255,0.06) inset, 0 0 0 1px var(--gem-2), 0 0 24px -2px var(--gem-2);
      transition: all 400ms ease;
    }
    .orb-ring {
      position: absolute; inset: 0; margin: auto; width: 80px; height: 80px;
      border-radius: 50%; border: 1px solid rgba(255,255,255,0.05); pointer-events: none;
      transition: all 400ms ease;
    }
    .orb-ring.r2 { width: 100px; height: 100px; border-color: rgba(255,255,255,0.035); }
    .orb-ring.r3 { width: 120px; height: 120px; border-color: rgba(255,255,255,0.02); }

    :host([state="listening"]) .orb, :host([state="wake"]) .orb {
      box-shadow: 0 0 0 1px rgba(255,255,255,0.06) inset, 0 0 0 1px var(--live), 0 0 24px -2px var(--live);
    }
    :host([state="speaking"]) .orb {
      box-shadow: 0 0 0 1px rgba(255,255,255,0.08) inset, 0 0 0 1px var(--gem-2), 0 0 32px -2px var(--gem-2);
    }
    @keyframes ring-rotate { to { transform: rotate(360deg); } }
    :host([state="connecting"]) .orb-ring { animation: ring-rotate 4s linear infinite; border-style: dashed; border-color: var(--gem-2); }

    .status-pill {
      display: inline-flex; align-items: center; gap: 8px;
      height: 26px; padding: 0 12px; border-radius: 999px;
      background: var(--bg-2); border: 1px solid var(--line);
      font-size: 12px; font-weight: 500; color: var(--fg-2);
      transition: all 300ms ease;
    }
    .status-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--fg-4); }
    .status-pill.live { background: var(--live-soft); border-color: var(--live); color: #7ce0a4; }
    .status-pill.live .status-dot { background: var(--live); box-shadow: 0 0 0 3px rgba(52,210,122,0.18); }
    .status-pill.disconnected { background: rgba(244,67,54,0.08); border-color: rgba(244,67,54,0.15); color: #f3a59f; }

    .hero-title { font-size: 21px; font-weight: 700; letter-spacing: -0.02em; line-height: 1.1; margin: 4px 0 -2px; }
    .hero-title.gem { background: linear-gradient(135deg, var(--gem-1), var(--gem-2), var(--gem-3)); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
    .hero-sub { font-size: 13.5px; color: var(--fg-3); line-height: 1.5; max-width: 260px; }
    
    .error-bar { margin: 8px 0; padding: 8px 12px; background: rgba(244,67,54,0.10); border: 1px solid rgba(244,67,54,0.28); border-radius: var(--radius-sm); font-size: 12px; color: #f3a59f; }
  `;

  render() {
    return html`
      <div class="hero">
        <div class="orb-wrap">
          <div class="orb-ring r3"></div><div class="orb-ring r2"></div>
          <div class="orb-ring"></div><div class="orb"></div>
        </div>
        
        <div class="status-pill ${this.state === 'listening' || this.state === 'speaking' || this.state === 'connecting' ? 'live' : 'disconnected'}">
          <div class="status-dot"></div>
          ${this.state === 'connecting' ? 'Connecting...' : (this.authenticated ? 'Authenticated' : 'Offline')}
        </div>

        <div class="hero-title gem">${this.getHeroTitle()}</div>
        <div class="hero-sub">${this.status || this.getDefaultSub()}</div>
        
        ${this.error ? html`<div class="error-bar">⚠ ${this.error}</div>` : ''}
      </div>
    `;
  }

  private getHeroTitle() {
    if (this.state === 'connecting') return 'Starting session…';
    if (this.state === 'listening' || this.state === 'speaking' || this.state === 'wake') return 'Your AI Concierge';
    return 'Your AI Concierge';
  }

  private getDefaultSub() {
    if (this.state === 'connecting') return 'Syncing with Gemini Live...';
    return 'Voice-powered workspace assistant embedded in this meeting.';
  }
}
