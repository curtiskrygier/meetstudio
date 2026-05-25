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
import './internal/components/gdm_stage_captions';
import './internal/components/gdm_stage_grid';
import './internal/components/gdm_stage_image_panel';
import './internal/components/gdm_stage_video_panel';
import './internal/components/gdm_stage_iframe_panel';
import './internal/components/gdm_transcript_view';
import './internal/components/gdm_stage_telemetry';
import './internal/components/gdm_stage_radar';
import './internal/components/gdm_stage_poll';
import './internal/components/gdm_stage_notepad';
import './internal/components/gdm_stage_emoji_burst';
import './internal/components/gdm_stage_camera_panel';
import './internal/components/gdm_stage_draw_overlay';
import './internal/components/gdm_stage_pointer';
import './internal/components/gdm_stage_terminal_panel';
import './internal/components/gdm_stage_doc_panel';
import './internal/components/gdm_stage_diagram';

const root = document.getElementById('a2ui-stage-root');
const contentLayer = document.getElementById('content-layer');

const engine = new A2UIEngine((components: A2UIComponent[]) => {
  try {
    renderA2UI(components);
  } catch (err) {
    reportError(err, 'A2UIEngine Callback');
  }
});

function reportError(error: any, context?: string) {
  const message = error instanceof Error ? error.message : String(error);
  const stack = error instanceof Error ? error.stack : '';
  console.error(`[stage-a2ui] Error in ${context || 'render'}:`, error);
  
  const ws = (window as any).__stageWS as WebSocket | undefined;
  if (ws && ws.readyState === WebSocket.OPEN) {
    try {
      ws.send(JSON.stringify({
        type: 'a2ui_error',
        error: message,
        stack: stack,
        context: context || 'renderA2UI'
      }));
    } catch (e) {
      console.error('[stage-a2ui] Failed to send error to backend:', e);
    }
  }
}

function renderA2UI(components: A2UIComponent[]) {
  try {
    if (!root) {
      console.error("[stage-a2ui] Error: #a2ui-stage-root element not found!");
      return;
    }

    if (!Array.isArray(components)) {
      components = [];
    }

    // Hide legacy content-layer when A2UI is active so it doesn't bleed through
    if (contentLayer) {
      contentLayer.style.visibility = components.length > 0 ? 'hidden' : '';
    }

    // 1. Map existing elements in the DOM by their A2UI ID attribute
    const existingMap = new Map<string, HTMLElement>();
    const existingEls = root.querySelectorAll('[data-a2ui-id]');
    existingEls.forEach((el) => {
      const id = el.getAttribute('data-a2ui-id');
      if (id) {
        existingMap.set(id, el as HTMLElement);
      }
    });

    const elementMap = new Map<string, HTMLElement>();

    // 2. Create or reuse elements and update their properties
    for (const comp of components) {
      if (!comp || !comp.id || !comp.element) {
        console.warn('[stage-a2ui] Skipping invalid component representation:', comp);
        continue;
      }

      let el = existingMap.get(comp.id);

      if (el && el.tagName.toLowerCase() === comp.element.toLowerCase()) {
        // Reuse existing element! Remove from existingMap so we don't delete it
        existingMap.delete(comp.id);
      } else {
        // Create new element if it doesn't exist or has wrong tag
        if (el) {
          el.remove();
          existingMap.delete(comp.id);
        }
        el = document.createElement(comp.element) as HTMLElement;
        el.setAttribute('data-a2ui-id', comp.id);
        el.id = comp.id; // Also set standard DOM ID for convenience
      }

      // Update properties/attributes on the element
      const props = comp.props || {};
      for (const [k, v] of Object.entries(props)) {
        if (k === 'children' || k === 'child') continue; // structural
        
        const anyEl = el as any;
        try {
          if (v === true || v === 'true') {
            if (!el.hasAttribute(k) || anyEl[k] !== true) {
              el.setAttribute(k, '');
              try { anyEl[k] = true; } catch (e) { /* ignore read-only */ }
            }
          } else if (v === false || v === 'false') {
            if (el.hasAttribute(k) || anyEl[k] !== false) {
              el.removeAttribute(k);
              try { anyEl[k] = false; } catch (e) { /* ignore read-only */ }
            }
          } else {
            if (anyEl[k] !== v) {
              try { anyEl[k] = v; } catch (e) { /* ignore read-only */ }
            }
          }
        } catch (err) {
          console.warn(`[stage-a2ui] Failed to set prop/attr ${k} on ${comp.element}:`, err);
        }
      }
      elementMap.set(comp.id, el);
    }

    // 3. Remove any remaining elements from the DOM (they are no longer active)
    existingMap.forEach((el) => {
      el.remove();
    });

    // 4. Establish nesting relationships
    const nestedIds = new Set<string>();

    for (const comp of components) {
      if (!comp || !comp.id) continue;
      const parentEl = elementMap.get(comp.id);
      if (!parentEl) continue;

      const childrenList = comp.props?.children?.explicitList;
      if (Array.isArray(childrenList)) {
        childrenList.forEach((childId: string, index: number) => {
          const childEl = elementMap.get(childId);
          if (childEl) {
            if (childEl.parentNode !== parentEl) {
              parentEl.appendChild(childEl);
            }
            nestedIds.add(childId);

            // If the parent is gdm-stage-grid, assign slot based on the list position
            const expectedSlot = `panel-${index + 1}`;
            if (comp.element === 'gdm-stage-grid' && childEl.getAttribute('slot') !== expectedSlot) {
              childEl.setAttribute('slot', expectedSlot);
            }
          }
        });
        
        // Clean up any extra child elements that shouldn't be here anymore
        const activeChildEls = new Set(childrenList.map(id => elementMap.get(id)).filter((el): el is HTMLElement => !!el));
        Array.from(parentEl.children).forEach(child => {
          if (child.getAttribute('data-a2ui-id') && !activeChildEls.has(child as HTMLElement)) {
            child.remove();
          }
        });

      } else if (comp.props?.child) {
        const childId = comp.props.child;
        const childEl = elementMap.get(childId);
        if (childEl) {
          if (childEl.parentNode !== parentEl) {
            parentEl.appendChild(childEl);
          }
          nestedIds.add(childId);
        }
        
        // Clean up any extra child elements that shouldn't be here anymore
        Array.from(parentEl.children).forEach(child => {
          if (child.getAttribute('data-a2ui-id') && child !== childEl) {
            child.remove();
          }
        });
      }
    }

    // 5. Append top-level (root) elements to the stage container
    const chatCards = components.filter(comp => comp && comp.id && !nestedIds.has(comp.id) && comp.element === 'gdm-chat-card');
    const totalChats = chatCards.length;
    let chatIndex = 0;
    for (const comp of components) {
      if (!comp || !comp.id) continue;
      if (!nestedIds.has(comp.id)) {
        const el = elementMap.get(comp.id);
        if (el) {
          if (el.parentNode !== root) {
            root.appendChild(el);
          }
          if (comp.element === 'gdm-chat-card') {
            // Absolute float coordinates with stacking offsets for overlays
            el.style.position = 'fixed';
            el.style.left = '40px';
            const revIndex = totalChats - 1 - chatIndex;
            el.style.bottom = `${100 + revIndex * 86}px`;
            el.style.zIndex = '800';
            chatIndex++;
          }
        }
      }
    }
  } catch (err) {
    reportError(err, 'renderA2UI');
  }
}

// Expose on window so the non-module main_stage.js can forward A2UI messages
// to the engine before its own switch statement handles imperative events.
(window as any).__a2uiEngine = engine;

// Forward component action events to the stage WebSocket so the server can
// react to user interactions within A2UI Lit components.
if (root) {
  root.addEventListener('target-lock', (e: Event) => sendAction('target-lock', (e as CustomEvent).detail));
  root.addEventListener('zoom-change', (e: Event) => sendAction('zoom-change', (e as CustomEvent).detail));
  root.addEventListener('tab-select',  (e: Event) => sendAction('tab-select',  (e as CustomEvent).detail));
  root.addEventListener('poll-vote',   (e: Event) => sendAction('poll-vote',   (e as CustomEvent).detail));
}

interface ActionPatch {
  element: string;
  prop?: string;
  extract?: (d: any) => any;
}

const ACTION_PROP_MAP: Record<string, ActionPatch> = {
  'target-lock': { element: 'gdm-radar-view',          prop: 'lockedCallsign', extract: d => d?.callsign ?? '' },
  'tab-select':  { element: 'gdm-telemetry-dashboard', prop: 'activeTabId',    extract: d => d?.tabId ?? '' },
  'zoom-change': { element: 'gdm-radar-view' },
  'poll-vote':   { element: 'gdm-poll-overlay' },
};

function sendAction(type: string, detail: any) {
  const ws = (window as any).__stageWS as WebSocket | undefined;
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'a2ui_action', action: type, detail }));
  }
  if (!root) return;
  const patch = ACTION_PROP_MAP[type];
  if (!patch) return;
  const el = root.querySelector(patch.element) as any;
  if (!el) return;

  if (type === 'zoom-change') {
    const cur = typeof el.zoom === 'number' ? el.zoom : 10.0;
    el.zoom = Math.max(1, Math.min(100, cur + (detail?.delta ?? 0)));
    return;
  }
  if (type === 'poll-vote') {
    const idx = detail?.optionIndex;
    if (typeof idx === 'number' && Array.isArray(el.values)) {
      const v = [...el.values];
      v[idx] = (v[idx] || 0) + 1;
      el.values = v;
    }
    return;
  }
  if (patch.prop && patch.extract) {
    el[patch.prop] = patch.extract(detail);
  }
}

console.log('[stage-a2ui] Phase 1 — engine + gdm-stage-card ready');
