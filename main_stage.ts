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
import './internal/components/gdm_stage_grid';
import './internal/components/gdm_stage_image_panel';
import './internal/components/gdm_stage_video_panel';
import './internal/components/gdm_stage_iframe_panel';
import './internal/components/gdm_transcript_view';
import './internal/components/gdm_stage_telemetry';
import './internal/components/gdm_stage_radar';
import './internal/components/gdm_stage_poll';
import './internal/components/gdm_stage_notepad';

const root = document.getElementById('a2ui-stage-root')!;
const contentLayer = document.getElementById('content-layer');

const engine = new A2UIEngine((components: A2UIComponent[]) => {
  renderA2UI(components);
});

function renderA2UI(components: A2UIComponent[]) {
  root.innerHTML = '';

  // Hide legacy content-layer when A2UI is active so it doesn't bleed through
  if (contentLayer) {
    contentLayer.style.visibility = components.length > 0 ? 'hidden' : '';
  }
  const elementMap = new Map<string, HTMLElement>();

  // 1. Create all elements and assign their properties
  for (const comp of components) {
    const el = document.createElement(comp.element) as any;
    for (const [k, v] of Object.entries(comp.props)) {
      if (k === 'children' || k === 'child') continue; // structural — handled by nesting logic below
      el[k] = v;
    }
    elementMap.set(comp.id, el);
  }

  // Keep track of elements that are nested under a parent
  const nestedIds = new Set<string>();

  // 2. Establish parent-child nesting and automatically assign slots for the grid layout
  for (const comp of components) {
    const parentEl = elementMap.get(comp.id);
    if (!parentEl) continue;

    const childrenList = comp.props.children?.explicitList;
    if (Array.isArray(childrenList)) {
      childrenList.forEach((childId: string, index: number) => {
        const childEl = elementMap.get(childId);
        if (childEl) {
          parentEl.appendChild(childEl);
          nestedIds.add(childId);

          // If the parent is gdm-stage-grid, assign slot based on the list position
          if (comp.element === 'gdm-stage-grid') {
            childEl.setAttribute('slot', `panel-${index + 1}`);
          }
        }
      });
    } else if (comp.props.child) {
      const childId = comp.props.child;
      const childEl = elementMap.get(childId);
      if (childEl) {
        parentEl.appendChild(childEl);
        nestedIds.add(childId);
      }
    }
  }

  // 3. Append only top-level (root) elements to the stage container
  for (const comp of components) {
    if (!nestedIds.has(comp.id)) {
      const el = elementMap.get(comp.id);
      if (el) {
        root.appendChild(el);
      }
    }
  }
}

// Expose on window so the non-module main_stage.js can forward A2UI messages
// to the engine before its own switch statement handles imperative events.
(window as any).__a2uiEngine = engine;

// Forward component action events to the stage WebSocket so the server can
// react to user interactions within A2UI Lit components.
root.addEventListener('target-lock', (e: Event) => sendAction('target-lock', (e as CustomEvent).detail));
root.addEventListener('zoom-change', (e: Event) => sendAction('zoom-change', (e as CustomEvent).detail));
root.addEventListener('tab-select',  (e: Event) => sendAction('tab-select',  (e as CustomEvent).detail));
root.addEventListener('poll-vote',   (e: Event) => sendAction('poll-vote',   (e as CustomEvent).detail));

function sendAction(type: string, detail: any) {
  const ws = (window as any).__stageWS as WebSocket | undefined;
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'a2ui_action', action: type, detail }));
  }
}

console.log('[stage-a2ui] Phase 1 — engine + gdm-stage-card ready');
