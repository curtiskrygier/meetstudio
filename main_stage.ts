/**
 * main_stage.ts — Stage Vite entry (A2UI layer)
 *
 * Phase 0: imports the shared A2UIEngine and claims the #a2ui-stage-root
 * container. The existing main_stage.js legacy renderer runs in parallel
 * (dual-protocol). A2UI WebSocket wiring and component rendering arrive
 * in Phase 1.
 */
import { A2UIEngine, A2UIComponent } from './internal/a2ui/engine';

const root = document.getElementById('a2ui-stage-root')!;

const engine = new A2UIEngine((components: A2UIComponent[]) => {
  renderA2UI(components);
});

function renderA2UI(components: A2UIComponent[]) {
  // Phase 1: walk components and write gdm-* custom elements into root.
  // For now, log to confirm the engine callback fires.
  console.log('[stage-a2ui] render', components.length, 'component(s)');
  root.innerHTML = '';
  for (const comp of components) {
    const el = document.createElement(comp.element);
    for (const [k, v] of Object.entries(comp.props)) {
      if (typeof v === 'string') el.setAttribute(k, v);
    }
    root.appendChild(el);
  }
}

// Expose engine on window so main_stage.js can forward A2UI messages to it
// during the dual-protocol phase without a module bundler dependency.
(window as any).__a2uiEngine = engine;

console.log('[stage-a2ui] Phase 0 — A2UIEngine ready on window.__a2uiEngine');
