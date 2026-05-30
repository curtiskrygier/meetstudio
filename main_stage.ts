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
import { meet } from '@googleworkspace/meet-addons';
import { A2UIEngine, A2UIComponent } from './internal/a2ui/engine';

const CLOUD_PROJECT_NUMBER = process.env.CLOUD_PROJECT_NUMBER;

async function initMeetSDK() {
  if (!CLOUD_PROJECT_NUMBER) {
    console.warn('[stage-a2ui] CLOUD_PROJECT_NUMBER not found, SDK init may fail');
  }
  try {
    console.log('[stage-a2ui] Initializing Meet Add-on SDK...');
    const session = await meet.addon.createAddonSession({
      cloudProjectNumber: CLOUD_PROJECT_NUMBER,
    });
    await session.createMainStageClient();
    console.log('[stage-a2ui] Meet Main Stage client ready');
  } catch (e) {
    console.error('[stage-a2ui] Meet SDK initialization failed:', e);
  }
}

initMeetSDK();

// --- WebSocket & Audio State ---
const params = new URLSearchParams(location.search);
const meetingId = params.get('meeting') || '';
const ticket = params.get('ticket') || '';
let stageWS: WebSocket | null = null;
let audioCtx: AudioContext | null = null;

function setupWebSocket() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${location.host}/ws/stage?meeting_id=${encodeURIComponent(meetingId)}&ticket=${encodeURIComponent(ticket)}`;
  console.log('[stage] Connecting to WebSocket...', wsUrl);
  
  stageWS = new WebSocket(wsUrl);
  (window as any).__stageWS = stageWS; 

  stageWS.onopen = () => {
    console.log('[stage] WebSocket connected');
    const statusBadge = document.getElementById('status-badge');
    if (statusBadge) {
      statusBadge.textContent = 'Connected';
      statusBadge.style.opacity = '1';
      statusBadge.style.color = '#00f2ff';
    }
  };

  stageWS.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      
      // 1. Give A2UI Engine priority
      if (engine && engine.handleMessage(msg)) {
        return;
      }

      // 2. Handle legacy imperative messages (Audio & Theme only)
      handleLegacyMessage(msg);
    } catch (e) {
      console.error('[stage] Message process error:', e);
    }
  };

  stageWS.onclose = () => {
    console.warn('[stage] WebSocket closed, retrying in 3s...');
    const statusBadge = document.getElementById('status-badge');
    if (statusBadge) {
      statusBadge.textContent = 'Disconnected';
      statusBadge.style.opacity = '0.4';
    }
    setTimeout(setupWebSocket, 3000);
  };
}

function handleLegacyMessage(msg: any) {
  if (msg.type === 'audio') {
    if (msg.data) playAudioChunk(msg.data);
  } else if (msg.type === 'sound_event') {
    if (msg.sound) triggerSoundEffect(msg.sound);
  } else if (msg.type === 'theme_change') {
    if (msg.tokens) {
      Object.entries(msg.tokens).forEach(([k, v]) => {
        document.documentElement.style.setProperty(k, v as string);
      });
    }
  }
}

async function playAudioChunk(base64: string) {
  try {
    if (!audioCtx) audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
    if (audioCtx.state === 'suspended') audioCtx.resume();
    
    const binString = atob(base64);
    const bytes = new Uint8Array(binString.length);
    for (let i = 0; i < binString.length; i++) bytes[i] = binString.charCodeAt(i);
    
    const buffer = await audioCtx.decodeAudioData(bytes.buffer);
    const src = audioCtx.createBufferSource();
    src.buffer = buffer;
    src.connect(audioCtx.destination);
    src.start();
  } catch (e) {
    console.warn('[stage] Audio playback error:', e);
  }
}

function triggerSoundEffect(sound: string) {
  if (!audioCtx) audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
  if (audioCtx.state === 'suspended') audioCtx.resume();
  const now = audioCtx.currentTime;

  if (sound === 'applause') {
    const bufferSize = audioCtx.sampleRate * 2;
    const buffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) data[i] = Math.random() * 2 - 1;

    const noise = audioCtx.createBufferSource();
    noise.buffer = buffer;
    const filter = audioCtx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.value = 1000;
    
    const mainGain = audioCtx.createGain();
    mainGain.gain.setValueAtTime(0, now);
    mainGain.gain.linearRampToValueAtTime(0.5, now + 0.5);
    mainGain.gain.exponentialRampToValueAtTime(0.001, now + 3.0);
    
    noise.connect(filter);
    filter.connect(mainGain);
    mainGain.connect(audioCtx.destination);
    noise.start(now);
    noise.stop(now + 3.0);
  }
}

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
import './internal/components/gdm_stage_mermaid';
import './internal/components/gdm_stage_html';
import './internal/components/gdm_stage_laser_sweep';
import './internal/components/gdm_stage_3d_airspace';
import './internal/components/gdm_stage_3d_scene';
import './internal/components/gdm_stage_market_ticker';
import './internal/components/gdm_stage_flip_slate';

// Composable Primitives / Atomic UI Layer Elements
import './internal/components/gdm_stage_container';
import './internal/components/gdm_stage_text';
import './internal/components/gdm_stage_badge';
import './internal/components/gdm_stage_progress';
import './internal/components/gdm_stage_divider';
import './internal/components/gdm_stage_icon';
import './internal/components/gdm_stage_button';
import './internal/components/gdm_stage_clock';
import './internal/components/gdm_stage_sparkline';
import './internal/components/gdm_stage_table_view';
import './internal/components/gdm_stage_trend_value';
import './internal/components/gdm_stage_scroller';
import './internal/components/gdm_stage_grid_layout';
import './internal/components/gdm_stage_stat';
import './internal/components/gdm_stage_image';
import './internal/components/gdm_stage_spacer';

const root = document.getElementById('a2ui-stage-root');
const contentLayer = document.getElementById('content-layer');

const engine = new A2UIEngine((components: A2UIComponent[]) => {
  try {
    renderA2UI(components);
  } catch (err) {
    reportError(err, 'A2UIEngine Callback');
  }
});

engine.onValidationError = (err) => {
  const ws = (window as any).__stageWS as WebSocket | undefined;
  if (ws && ws.readyState === WebSocket.OPEN) {
    try {
      ws.send(JSON.stringify({ error: err }));
    } catch (e) {
      console.error('[stage-a2ui] Failed to send validation error to backend:', e);
    }
  }
};

// Initialize WebSocket after engine is ready
setupWebSocket();

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

// Track chat card IDs that have self-dismissed so they aren't re-added on re-render
const _dismissedChatIds = new Set<string>();

function renderA2UI(components: A2UIComponent[]) {
  if (components.length === 0) _dismissedChatIds.clear();
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

      // Update properties/attributes on the element — but ONLY for components
      // marked _fresh (i.e. included in the latest surfaceUpdate). Components
      // pulled from the engine's buffer during compile (e.g. on a partial-update
      // tick that only sends the caption) are left untouched, so LOCAL
      // interactive state (camera zoom from pinch, preset toggles, etc.) is
      // preserved instead of being reset to the buffered server values.
      // Element creation/reuse + nesting (below) still runs for all components.
      const props = comp.props || {};
      const isFresh = (comp as any)._fresh !== false;
      if (isFresh) for (const [k, v] of Object.entries(props)) {
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

      const childrenList = comp.props?.children;
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
    // Create a persistent chat container — cards stack bottom-up, overflow clipped at top
    let chatContainer = root.querySelector('#gdm-chat-stack') as HTMLElement;
    if (!chatContainer) {
      chatContainer = document.createElement('div');
      chatContainer.id = 'gdm-chat-stack';
      chatContainer.style.position = 'fixed';
      chatContainer.style.right = '32px';
      chatContainer.style.bottom = '90px';
      chatContainer.style.top = '80px';
      chatContainer.style.zIndex = '800';
      chatContainer.style.display = 'flex';
      chatContainer.style.flexDirection = 'column-reverse';
      chatContainer.style.justifyContent = 'flex-start';
      chatContainer.style.alignItems = 'flex-end';
      chatContainer.style.gap = '10px';
      chatContainer.style.pointerEvents = 'none';
      chatContainer.style.overflow = 'hidden';
      // Gradient mask: top 25% fades to transparent so cards "disappear" as they float up
      chatContainer.style.webkitMaskImage = 'linear-gradient(to bottom, transparent 0%, black 28%)';
      (chatContainer.style as any).maskImage = 'linear-gradient(to bottom, transparent 0%, black 28%)';
      // Listen for self-dismiss events so we don't re-add dismissed cards on next render
      chatContainer.addEventListener('chat-dismiss', (e: Event) => {
        const el = e.target as HTMLElement;
        if (el && el.id) _dismissedChatIds.add(el.id);
      });
      root.appendChild(chatContainer);
    }

    for (const comp of components) {
      if (!comp || !comp.id) continue;
      if (!nestedIds.has(comp.id)) {
        const el = elementMap.get(comp.id);
        if (el) {
          if (comp.element === 'gdm-chat-card') {
            // Don't revive a card that has already self-dismissed
            if (_dismissedChatIds.has(comp.id)) continue;
            if (el.parentNode !== chatContainer) {
              chatContainer.appendChild(el);
            }
          } else {
            if (el.parentNode !== root) {
              root.appendChild(el);
            }
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
  root.addEventListener('a2ui-action', (e: Event) => sendAction('a2ui-action', (e as CustomEvent).detail));
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
  let el = root.querySelector(patch.element) as any;
  if (!el && patch.element === 'gdm-radar-view') {
    el = root.querySelector('gdm-3d-airspace');
  }
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
