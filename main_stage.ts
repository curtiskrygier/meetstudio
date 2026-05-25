/**
 * main_stage.ts — Stage Vite entry (A2UI layer)
 *
 * Owns the A2UIEngine and the #a2ui-stage-root overlay div.
 * The legacy main_stage.js WebSocket handler checks window.__a2uiEngine
 * before its own switch — A2UI messages are consumed here; imperative
 * messages (pointer, draw, audio, etc.) pass through to the legacy handler.
 *
 * Component imports register Lit custom elements globally so the engine's
 * renderA2UI can createElement() them by name.
 */
import { A2UIEngine, A2UIComponent } from './internal/a2ui/engine';

// Stage catalog — one import per supported gdm-* component
import './internal/components/gdm_stage_card';
import './internal/components/gdm_stage_chyron';
import './internal/components/gdm_stage_ticker';
import './internal/components/gdm_stage_standby';
import './internal/components/gdm_stage_chat_card';

const root = document.getElementById('a2ui-stage-root')!;

const engine = new A2UIEngine((components: A2UIComponent[]) => {
  renderA2UI(components);
});

function renderA2UI(components: A2UIComponent[]) {
  root.innerHTML = '';
  for (const comp of components) {
    const el = document.createElement(comp.element) as any;
    // Assign as Lit properties (not attributes) so reactive updates work
    for (const [k, v] of Object.entries(comp.props)) {
      el[k] = v;
    }
    root.appendChild(el);
  }
}

// Expose on window so the non-module main_stage.js can forward A2UI messages
// to the engine before its own switch statement handles imperative events.
(window as any).__a2uiEngine = engine;

console.log('[stage-a2ui] Phase 1 — engine + gdm-stage-card ready');
