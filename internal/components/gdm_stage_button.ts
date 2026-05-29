import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import './gdm_stage_icon';

/**
 * gdm-button — unified action atom.
 *
 * Four action modes via the discriminated `action` prop:
 *   {type: 'link',  url, newTab?}            window.open the URL
 *   {type: 'fire',  endpoint, payload?}      POST JSON to a server endpoint
 *   {type: 'emit',  event, detail?}          dispatch a CustomEvent on the host
 *   {type: 'agent', actionId, payload?}      dispatch 'gdm-button-click' event
 *                                            (main_stage.ts forwards to the agent)
 *
 * Back-compat shorthands (preserved from earlier API — existing usages keep working):
 *   actionId set without `action`            → behaves as 'agent' mode
 *   targetUrl set without `action`           → behaves as 'link' mode (newTab=true)
 *   label set (text empty)                   → label is the button copy
 *
 * Existing demos (demo_a2ui_composable_market.py, tests/test_a2ui_stage.py)
 * use {label, actionId, payload, icon, type, disabled} and continue to work
 * unchanged — actionId routes through the new 'agent' action mode and
 * dispatches the same 'gdm-button-click' CustomEvent main_stage.ts already
 * listens for.
 */
type ButtonAction =
  | { type: 'link'; url: string; newTab?: boolean }
  | { type: 'fire'; endpoint: string; payload?: unknown }
  | { type: 'emit'; event: string; detail?: unknown }
  | { type: 'agent'; actionId: string; payload?: unknown };

@customElement('gdm-button')
export class GdmStageButton extends LitElement {
  // ── Existing API (preserved for back-compat) ──────────────────────────
  @property({ type: String })  label    = '';
  @property({ type: String })  actionId = '';
  @property({ type: String })  payload  = '';
  @property({ type: String })  icon     = '';
  @property({ type: String })  type     = 'primary'; // primary | secondary | danger | ghost | success
  @property({ type: Boolean }) disabled = false;

  // ── New API ───────────────────────────────────────────────────────────
  @property({ type: String })  text      = '';
  @property({ type: String })  size      = 'md';     // sm | md | lg | hero
  @property({ type: Boolean }) pulse     = false;
  @property({ type: Boolean }) loading   = false;
  @property({ type: Object })  action: ButtonAction | null = null;
  @property({ type: String })  targetUrl = '';

  static styles = css`
    :host {
      display: inline-block;
      vertical-align: middle;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      box-sizing: border-box;
      user-select: none;
      background: transparent;
      margin: 0;
      line-height: 1;
    }
    .btn:active:not(.disabled):not(.loading) {
      transform: scale(0.96);
    }

    /* Size variants — md = stage-default; hero = "presenter clicker" big. */
    .size-sm   { font-size: 11px; padding:  6px 12px; border-radius: 6px; }
    .size-md   { font-size: 13px; padding:  8px 16px; }
    .size-lg   { font-size: 18px; padding: 18px 36px; }
    .size-hero { font-size: 28px; padding: 28px 48px; border-radius: 14px; }

    /* Type variants — existing palette preserved + success/phosphor added. */
    .btn-primary {
      background: rgba(0, 242, 255, 0.15);
      color: #00f2ff;
      border: 1px solid rgba(0, 242, 255, 0.35);
      box-shadow: 0 0 12px rgba(0, 242, 255, 0.12);
    }
    .btn-primary:hover:not(.disabled):not(.loading) {
      background: rgba(0, 242, 255, 0.25);
      border-color: rgba(0, 242, 255, 0.6);
      box-shadow: 0 0 20px rgba(0, 242, 255, 0.3);
    }

    .btn-secondary {
      background: rgba(255, 255, 255, 0.04);
      color: rgba(255, 255, 255, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.12);
    }
    .btn-secondary:hover:not(.disabled):not(.loading) {
      background: rgba(255, 255, 255, 0.08);
      border-color: rgba(255, 255, 255, 0.25);
    }

    .btn-danger {
      background: rgba(255, 59, 87, 0.15);
      color: #ff3b57;
      border: 1px solid rgba(255, 59, 87, 0.35);
      box-shadow: 0 0 12px rgba(255, 59, 87, 0.12);
    }
    .btn-danger:hover:not(.disabled):not(.loading) {
      background: rgba(255, 59, 87, 0.25);
      border-color: rgba(255, 59, 87, 0.6);
      box-shadow: 0 0 20px rgba(255, 59, 87, 0.3);
    }

    .btn-ghost {
      background: transparent;
      color: rgba(255, 255, 255, 0.65);
      border: 1px solid transparent;
    }
    .btn-ghost:hover:not(.disabled):not(.loading) {
      background: rgba(255, 255, 255, 0.05);
      color: #ffffff;
    }

    /* New: phosphor-green success variant — matches the matrix/playbook vibe. */
    .btn-success {
      background: rgba(0, 255, 136, 0.12);
      color: #00ff88;
      border: 1px solid rgba(0, 255, 136, 0.35);
      box-shadow: 0 0 12px rgba(0, 255, 136, 0.12);
    }
    .btn-success:hover:not(.disabled):not(.loading) {
      background: rgba(0, 255, 136, 0.22);
      border-color: rgba(0, 255, 136, 0.6);
      box-shadow: 0 0 20px rgba(0, 255, 136, 0.3);
    }

    /* Pulse — type-tinted glow loop. */
    .pulse-active {
      animation: button-pulse 1.8s infinite alternate;
    }
    @keyframes button-pulse {
      0%   { box-shadow: 0 0 4px  var(--pulse-color, rgba(0,242,255,0.15)); }
      100% { box-shadow: 0 0 18px var(--pulse-color, rgba(0,242,255,0.45)); }
    }

    .disabled {
      opacity: 0.35;
      cursor: not-allowed;
      pointer-events: none;
      box-shadow: none !important;
    }
    .loading {
      cursor: not-allowed;
      opacity: 0.6;
    }

    /* Spinner — shown during fire-mode fetch in flight. */
    .spinner {
      width: 14px;
      height: 14px;
      border: 2px solid currentColor;
      border-top-color: transparent;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      display: inline-block;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
  `;

  /** Resolve which action mode this button is in given the props set. */
  private _resolveAction(): ButtonAction | null {
    if (this.action) return this.action;
    // Existing convention: `actionId` set → dispatch gdm-button-click for agent.
    if (this.actionId) {
      let parsedPayload: unknown = this.payload;
      try {
        if (this.payload && (this.payload.startsWith('{') || this.payload.startsWith('['))) {
          parsedPayload = JSON.parse(this.payload);
        }
      } catch (_) { /* keep as string */ }
      return { type: 'agent', actionId: this.actionId, payload: parsedPayload };
    }
    if (this.targetUrl) return { type: 'link', url: this.targetUrl, newTab: true };
    return null;
  }

  private async _handleClick(e: Event) {
    if (this.disabled || this.loading) { e.preventDefault(); return; }

    const action = this._resolveAction();
    if (!action) return;

    try {
      if (action.type === 'link') {
        window.open(action.url, action.newTab !== false ? '_blank' : '_self');
        return;
      }
      if (action.type === 'fire') {
        this.loading = true;
        await fetch(action.endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(action.payload ?? {}),
        });
        return;
      }
      if (action.type === 'emit') {
        this.dispatchEvent(new CustomEvent(action.event, {
          detail: action.detail, bubbles: true, composed: true,
        }));
        return;
      }
      if (action.type === 'agent') {
        // Existing convention preserved — main_stage.ts catches this and
        // forwards to the agent via sendAction(). Don't rename the event
        // name; existing handlers depend on it.
        this.dispatchEvent(new CustomEvent('gdm-button-click', {
          detail: { actionId: action.actionId, payload: action.payload },
          bubbles: true, composed: true,
        }));
        return;
      }
    } catch (err) {
      console.error('[gdm-button] action failed', err);
    } finally {
      this.loading = false;
    }
  }

  render() {
    // Pulse colour follows the type variant.
    const pulseColors: Record<string, string> = {
      primary:   'rgba(0,242,255,0.45)',
      secondary: 'rgba(255,255,255,0.25)',
      danger:    'rgba(255,59,87,0.45)',
      ghost:     'rgba(255,255,255,0.15)',
      success:   'rgba(0,255,136,0.45)',
    };
    const pulseColor = pulseColors[this.type] ?? pulseColors.primary;
    const labelText = this.text || this.label;

    const classes = [
      'btn',
      `btn-${this.type}`,
      `size-${this.size}`,
      this.pulse && !this.disabled ? 'pulse-active' : '',
      this.disabled ? 'disabled' : '',
      this.loading ? 'loading' : '',
    ].filter(Boolean).join(' ');

    const inlineStyle = `--pulse-color: ${pulseColor};`;

    return html`
      <button
        class="${classes}"
        style="${inlineStyle}"
        type="button"
        ?disabled=${this.disabled}
        @click="${this._handleClick}">
        ${this.loading
          ? html`<span class="spinner"></span>`
          : html`
              ${this.icon ? html`<gdm-icon .name="${this.icon}" size="14px"></gdm-icon>` : ''}
              <span>${labelText}<slot></slot></span>
            `}
      </button>
    `;
  }
}
