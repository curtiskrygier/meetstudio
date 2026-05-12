import { LitElement, css, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { meet } from '@googleworkspace/meet-addons';
import { MeetMediaApiClientImpl } from './internal/meetmediaapiclient_impl';
import { MeetConnectionState } from './types/enums';

const CLOUD_PROJECT_NUMBER = process.env.CLOUD_PROJECT_NUMBER;
const CLIENT_ID = process.env.CLIENT_ID;

if (!CLOUD_PROJECT_NUMBER || !CLIENT_ID) {
  console.error('CLOUD_PROJECT_NUMBER and CLIENT_ID must be set at build time');
}

const GEMINI_LOGO = html`
  <svg width="28" height="28" viewBox="0 0 28 28" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="gl-grad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#4285F4"/>
        <stop offset="100%" stop-color="#9B59B6"/>
      </linearGradient>
    </defs>
    <path d="M14 1C14 8.2 8.2 14 1 14C8.2 14 14 19.8 14 27C14 19.8 19.8 14 27 14C19.8 14 14 8.2 14 1Z"
          fill="url(#gl-grad)"/>
  </svg>`;

@customElement('gdm-architect-agent')
export class GdmArchitectAgent extends LitElement {
  @state() connected = false;
  @state() connecting = false;
  @state() initialized = false;
  @state() error = '';
  @state() volume = 0;
  @state() transcript: Array<{id: string; role: string; text: string}> = [];
  @state() status = 'Initialising...';
  @state() trackCount = 0;
  @state() audioEnabled = true;
  @state() videoEnabled = false;
  @state() wakeActive = false;
  @state() actionLinks: Array<{url: string; label: string; content?: string}> = [];
  @state() diagramMode = false;
  @state() diagramming = false;
  @state() diagramStyle: 'cyber' | 'blueprint' | 'sketch' | 'google' = 'sketch';
  @state() diagramContext = '';
  @state() transcriptMode = false;
  @state() lastTranscriptFileId = '';
  @state() lastDiagramFileId = '';

  private diagramInterval: ReturnType<typeof setInterval> | null = null;

  private diagramSessionId = '';
  private diagramActivityStarted = false;
  private lastTranscriptTime = 0;
  private lastGenerationTime = 0;
  private transcriptStartIndex = 0;
  private diagramSessionStartTime: string | null = null;
  private speechSilenceTimer: ReturnType<typeof setTimeout> | null = null;

  private meetClient: MeetMediaApiClientImpl | null = null;
  private sidePanelClient: any = null;
  private isAddonInitialized = false;
  private accessToken = '';
  private meetingId = '';
  private activeTrackIds = new Set<string>();
  private activeVideoTrackIds = new Set<string>();
  private speechRecognition: any = null;
  private wakeTimeout: ReturnType<typeof setTimeout> | null = null;
  private userEmail = '';

  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private dataArray: Uint8Array | null = null;
  private animationFrameId: number | null = null;
  private workletNode: AudioWorkletNode | null = null;

  private playbackContext: AudioContext | null = null;
  private playbackNextTime = 0;

  private videoEl: HTMLVideoElement | null = null;
  private videoCanvas: HTMLCanvasElement | null = null;
  private videoFrameInterval: ReturnType<typeof setInterval> | null = null;

  private ws: WebSocket | null = null;
  private pcmBuffer: Int16Array[] = [];
  private pcmBufferSamples = 0;
  private static readonly PCM_SEND_SAMPLES = 1600; // 100ms at 16kHz

  static styles = css`
    :host {
      display: flex; flex-direction: column; height: 100%; overflow: hidden;
      background: #0c0d10; color: #f2f3f5;
      font-family: "Plus Jakarta Sans", system-ui, sans-serif;
      -webkit-font-smoothing: antialiased;
      color-scheme: dark;
      --bg-0:#0c0d10; --bg-1:#131418; --bg-2:#191b20; --bg-3:#20232a;
      --line:#262932; --line-soft:#1d2027;
      --fg:#f2f3f5; --fg-2:#b8bcc4; --fg-3:#7e828c; --fg-4:#565a64;
      --gem-1:#4285F4; --gem-2:#9B6DFF; --gem-3:#EE82A8;
      --live:#34d27a; --live-soft:#1c2c23;
      --warn:#f0a04b; --radius:14px; --radius-sm:10px;
    }
    /* Topbar */
    .topbar {
      height: 48px; display: flex; align-items: center;
      justify-content: space-between; padding: 0 14px 0 16px;
      border-bottom: 1px solid var(--line-soft);
      background: linear-gradient(180deg, rgba(255,255,255,0.02), transparent);
      flex-shrink: 0;
    }
    .brand { display: flex; align-items: center; gap: 9px; }
    .brand-mark { width: 22px; height: 22px; display: grid; place-items: center; }
    .brand-name { font-size: 13.5px; font-weight: 600; letter-spacing: -0.01em; color: var(--fg); }
    .brand-name .live { color: var(--fg-3); font-weight: 500; margin-left: 4px; }
    .topbar-actions { display: flex; align-items: center; gap: 4px; }
    .icon-btn {
      width: 30px; height: 30px; border-radius: 8px; display: grid; place-items: center;
      cursor: pointer; color: var(--fg-3); border: 1px solid transparent; background: transparent;
      transition: all 120ms;
    }
    .icon-btn:hover { background: var(--bg-2); color: var(--fg-2); border-color: var(--line-soft); }
    .icon-btn svg { width: 16px; height: 16px; }
    /* Body */
    .body { flex: 1; overflow-y: auto; overflow-x: hidden; display: flex; flex-direction: column; }
    .body::-webkit-scrollbar { width: 6px; }
    .body::-webkit-scrollbar-thumb { background: #2a2d35; border-radius: 3px; }
    /* Hero */
    .hero { padding: 20px 18px 18px; display: flex; flex-direction: column; align-items: center; gap: 14px; text-align: center; }
    .orb-wrap { position: relative; width: 112px; height: 112px; margin-top: 4px; display: grid; place-items: center; }
    .orb {
      position: relative; width: 56px; height: 56px; border-radius: 50%;
      background: radial-gradient(circle at 50% 45%, rgba(255,255,255,0.10) 0%, rgba(155,109,255,0.20) 35%, rgba(66,133,244,0.14) 70%, rgba(255,255,255,0.02) 100%);
      box-shadow: 0 0 0 1px rgba(255,255,255,0.06) inset, 0 0 0 1px rgba(155,109,255,0.18), 0 0 24px -2px rgba(155,109,255,0.25);
      animation: orb-breathe 5s ease-in-out infinite;
    }
    .orb::before {
      content: ""; position: absolute; inset: 0; margin: auto;
      width: 8px; height: 8px; border-radius: 50%;
      background: radial-gradient(circle, #fff 0%, rgba(155,109,255,0.9) 60%, transparent 100%);
      box-shadow: 0 0 12px 1px rgba(155,109,255,0.6);
    }
    .orb-ring {
      position: absolute; inset: 0; margin: auto; width: 80px; height: 80px;
      border-radius: 50%; border: 1px solid rgba(255,255,255,0.05); pointer-events: none;
    }
    .orb-ring.r2 { width: 100px; height: 100px; border-color: rgba(255,255,255,0.035); }
    .orb-ring.r3 { width: 120px; height: 120px; border-color: rgba(255,255,255,0.02); }
    /* State: listening */
    :host([data-state="listening"]) .orb, :host([data-state="wake"]) .orb {
      box-shadow: 0 0 0 1px rgba(255,255,255,0.06) inset, 0 0 0 1px rgba(52,210,122,0.32), 0 0 24px -2px rgba(52,210,122,0.30);
    }
    :host([data-state="listening"]) .orb::before, :host([data-state="wake"]) .orb::before {
      background: radial-gradient(circle, #fff 0%, rgba(52,210,122,0.9) 60%, transparent 100%);
      box-shadow: 0 0 12px 1px rgba(52,210,122,0.6);
    }
    :host([data-state="speaking"]) .orb {
      box-shadow: 0 0 0 1px rgba(255,255,255,0.08) inset, 0 0 0 1px rgba(155,109,255,0.42), 0 0 32px -2px rgba(155,109,255,0.45);
    }
    :host([data-state="wake"]) .orb-ring, :host([data-state="speaking"]) .orb-ring {
      animation: ring-ripple 2.6s ease-out infinite; border-color: rgba(155,109,255,0.30);
    }
    :host([data-state="wake"]) .orb-ring { border-color: rgba(52,210,122,0.30); }
    :host([data-state="wake"]) .orb-ring.r2, :host([data-state="speaking"]) .orb-ring.r2 { animation-delay: 0.6s; }
    :host([data-state="wake"]) .orb-ring.r3, :host([data-state="speaking"]) .orb-ring.r3 { animation-delay: 1.2s; }
    :host([data-state="connecting"]) .orb-ring { animation: ring-rotate 4s linear infinite; border-style: dashed; border-color: rgba(155,109,255,0.18); }
    :host([data-state="connecting"]) .orb-ring.r2 { animation-direction: reverse; animation-duration: 6s; }
    :host([data-state="disconnected"]) .orb { filter: saturate(0.2) brightness(0.65); }
    @keyframes orb-breathe { 0%, 100% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.04); opacity: 0.92; } }
    @keyframes ring-ripple { 0% { transform: scale(0.7); opacity: 0; } 25% { opacity: 1; } 100% { transform: scale(1.15); opacity: 0; } }
    @keyframes ring-rotate { to { transform: rotate(360deg); } }
    /* Status pill */
    .status-pill {
      display: inline-flex; align-items: center; gap: 8px;
      height: 26px; padding: 0 12px; border-radius: 999px;
      background: var(--bg-2); border: 1px solid var(--line);
      font-size: 12px; font-weight: 500; color: var(--fg-2);
    }
    .status-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--fg-4); }
    .status-pill.live { background: var(--live-soft); border-color: rgba(52,210,122,0.35); color: #7ce0a4; }
    .status-pill.live .status-dot { background: var(--live); box-shadow: 0 0 0 3px rgba(52,210,122,0.18); animation: blink 2s ease-in-out infinite; }
    .status-pill.disconnected { background: rgba(244,67,54,0.08); border-color: rgba(244,67,54,0.15); color: #f3a59f; }
    .status-pill.disconnected .status-dot { background: #f44336; opacity: 0.6; }
    @keyframes blink { 50% { opacity: 0.5; } }
    .hero-title { font-size: 21px; font-weight: 700; letter-spacing: -0.02em; line-height: 1.1; margin: 4px 0 -2px; }
    .hero-title.gem { background: linear-gradient(135deg, var(--gem-1), var(--gem-2), var(--gem-3)); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
    .hero-sub { font-size: 13.5px; color: var(--fg-3); line-height: 1.5; max-width: 260px; }
    kbd { display: inline-block; padding: 1px 6px; margin: 0 1px; font: 500 11px sans-serif; color: var(--fg-2); background: var(--bg-3); border: 1px solid var(--line); border-bottom-width: 2px; border-radius: 5px; }
    /* CTA */
    .cta {
      width: 100%; height: 46px; border: 0; cursor: pointer; border-radius: 13px;
      background: linear-gradient(180deg, #4f8cff, #2c6df1); color: white;
      font-size: 14.5px; font-weight: 600; letter-spacing: -0.005em;
      display: flex; align-items: center; justify-content: center; gap: 10px;
      box-shadow: 0 4px 12px rgba(44,109,241,0.25);
      transition: all 150ms;
    }
    .cta:hover { transform: translateY(-1px); box-shadow: 0 6px 16px rgba(44,109,241,0.35); filter: brightness(1.05); }
    .cta:active { transform: translateY(0); box-shadow: 0 2px 8px rgba(44,109,241,0.2); }
    .cta:disabled { opacity: 0.6; cursor: not-allowed; transform: none; box-shadow: none; }
    .cta.google { background: white; color: #3c4043; border: 1px solid #dadce0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .cta.google:hover { background: #f8f9fa; border-color: #d2d4d7; box-shadow: 0 2px 6px rgba(0,0,0,0.15); }
    .cta svg { width: 18px; height: 18px; }
    /* Sections */
    .section { padding: 0 16px 14px; }
    .section + .section { padding-top: 4px; }
    .section-head { display: flex; align-items: center; justify-content: space-between; margin: 14px 0 8px; }
    .mode-toggle {
      font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
      padding: 3px 7px; border-radius: 5px;
      background: var(--bg-3); border: 1px solid var(--line);
      color: var(--gem-2); cursor: pointer; transition: all 120ms;
    }
    .mode-toggle:hover { background: var(--bg-2); border-color: var(--fg-4); }
    .section-title { font-size: 11px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--fg-4); }
    /* Voice meter */
    .meter-card {
      background: var(--bg-1); border: 1px solid var(--line-soft); border-radius: var(--radius);
      padding: 12px 14px; display: flex; align-items: center; gap: 12px;
    }
    .meter-icon {
      width: 32px; height: 32px; border-radius: 9px; display: grid; place-items: center;
      background: var(--bg-3); color: var(--fg-2); border: 1px solid var(--line); flex-shrink: 0;
    }
    :host([data-state="listening"]) .meter-icon, :host([data-state="wake"]) .meter-icon { background: rgba(52,210,122,0.14); color: #7ce0a4; border-color: rgba(52,210,122,0.30); }
    :host([data-state="speaking"]) .meter-icon { background: rgba(155,109,255,0.16); color: #c5a9ff; border-color: rgba(155,109,255,0.30); }
    .meter-icon svg { width: 16px; height: 16px; }
    .meter-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
    .meter-row { display: flex; align-items: center; justify-content: space-between; }
    .meter-who { font-size: 12.5px; font-weight: 500; color: var(--fg-2); }
    .bars { display: flex; align-items: end; gap: 3px; height: 18px; }
    .bars span { width: 3px; background: linear-gradient(180deg, var(--gem-2), var(--gem-1)); border-radius: 2px; opacity: 0.85; animation: bar 0.9s ease-in-out infinite; }
    .bars span:nth-child(1){animation-delay:0.0s} .bars span:nth-child(2){animation-delay:0.1s}
    .bars span:nth-child(3){animation-delay:0.2s} .bars span:nth-child(4){animation-delay:0.3s}
    .bars span:nth-child(5){animation-delay:0.4s} .bars span:nth-child(6){animation-delay:0.5s}
    .bars span:nth-child(7){animation-delay:0.6s} .bars span:nth-child(8){animation-delay:0.7s}
    .bars span:nth-child(9){animation-delay:0.8s} .bars span:nth-child(10){animation-delay:0.9s}
    @keyframes bar { 0%, 100% { height: 4px; } 50% { height: 18px; } }
    :host([data-state="disconnected"]) .bars span, :host([data-state="connecting"]) .bars span { animation: none; height: 4px; opacity: 0.35; }
    /* Controls */
    .controls-row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
    .ctrl {
      background: var(--bg-1); border: 1px solid var(--line-soft); border-radius: 12px;
      padding: 10px 8px 9px; display: flex; flex-direction: column; align-items: center; gap: 6px;
      cursor: pointer; color: var(--fg-2); transition: all 120ms;
    }
    .ctrl:hover { background: var(--bg-2); }
    .ctrl[data-active="true"] { background: rgba(52,210,122,0.10); border-color: rgba(52,210,122,0.32); color: #9bedb9; }
    .ctrl[data-active="false"] { background: rgba(244,67,54,0.08); border-color: rgba(244,67,54,0.28); color: #f3a59f; }
    .ctrl-icon { width: 30px; height: 30px; border-radius: 8px; display: grid; place-items: center; background: var(--bg-3); }
    .ctrl[data-active="true"] .ctrl-icon { background: rgba(52,210,122,0.16); }
    .ctrl[data-active="false"] .ctrl-icon { background: rgba(244,67,54,0.14); }
    .ctrl-icon svg { width: 15px; height: 15px; }
    .ctrl-label { font-size: 11.5px; font-weight: 500; }
    .ctrl-state { font-size: 10.5px; color: var(--fg-4); }
    .ctrl[data-active="true"] .ctrl-state { color: #7ce0a4; }
    .ctrl[data-active="false"] .ctrl-state { color: #f3a59f; }
    /* Wake row */
    .wake-row { display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: var(--bg-1); border: 1px solid var(--line-soft); border-radius: 12px; }
    .wake-mark { width: 26px; height: 26px; border-radius: 50%; background: var(--bg-3); display: grid; place-items: center; color: var(--fg-3); flex-shrink: 0; }
    :host([data-state="wake"]) .wake-mark { background: var(--live); color: #062815; box-shadow: 0 0 0 4px rgba(52,210,122,0.18); }
    .wake-mark svg { width: 13px; height: 13px; }
    .wake-text { flex: 1; font-size: 12.5px; color: var(--fg-2); }
    .wake-text small { display: block; color: var(--fg-4); font-size: 11px; margin-top: 1px; }
    /* Transcript */
    .transcript { display: flex; flex-direction: column; gap: 12px; }
    .turn { display: flex; gap: 10px; align-items: flex-start; }
    .avatar { width: 26px; height: 26px; border-radius: 8px; display: grid; place-items: center; flex-shrink: 0; font-size: 11px; font-weight: 600; background: var(--bg-3); border: 1px solid var(--line); }
    .avatar.gem { background: linear-gradient(135deg, var(--gem-1), var(--gem-2)); border-color: transparent; box-shadow: 0 4px 12px -4px rgba(155,109,255,0.5); }
    .avatar.gem svg { width: 13px; height: 13px; color: white; }
    .turn-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
    .turn-name { font-size: 12px; font-weight: 600; color: var(--fg-2); }
    .turn-name.gem { background: linear-gradient(135deg, var(--gem-1), var(--gem-2)); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
    .turn-text { font-size: 13px; line-height: 1.45; color: var(--fg); }
    .transcript-empty { padding: 18px 16px; background: var(--bg-1); border: 1px dashed var(--line); border-radius: 12px; text-align: center; color: var(--fg-3); font-size: 12.5px; }
    .ctx-input { width: 100%; min-height: 88px; background: var(--bg-2) !important; border: 1px solid var(--line); border-radius: var(--radius-sm); color: var(--fg) !important; font-family: inherit; font-size: 12px; line-height: 1.5; padding: 10px 12px; resize: vertical; box-sizing: border-box; transition: border-color 150ms; }
    .ctx-input:focus { outline: none; border-color: var(--gem-2); }
    .ctx-input.has-content { border-color: rgba(52,210,122,0.5); }
    .ctx-input::placeholder { color: var(--fg-4); }
    .context-row { display: flex; gap: 8px; align-items: flex-start; }
    .context-row .ctx-input { flex: 1; }
    .ctx-send { flex-shrink: 0; height: 36px; padding: 0 14px; background: var(--gem-2); border: none; border-radius: var(--radius-sm); color: #fff; font-family: inherit; font-size: 12px; font-weight: 600; cursor: pointer; align-self: flex-end; white-space: nowrap; }
    .ctx-send:hover { opacity: 0.85; }
    .ctx-send:disabled { opacity: 0.4; cursor: default; }
    .ctx-hint { font-size: 10.5px; color: var(--fg-4); margin-top: 5px; }
    /* Action cards */
    .action-list { display: flex; flex-direction: column; gap: 6px; }
    .action { display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: var(--bg-1); border: 1px solid var(--line-soft); border-radius: 12px; cursor: pointer; transition: all 120ms; text-decoration: none; }
    .action:hover { background: var(--bg-2); border-color: var(--line); }
    .action-ico { width: 30px; height: 30px; border-radius: 8px; display: grid; place-items: center; flex-shrink: 0; color: white; }
    .action-ico.doc { background: #2b6cb0; }
    .action-ico.sheet { background: #2f855a; }
    .action-ico.img { background: #6b46c1; }
    .action-ico svg { width: 14px; height: 14px; }
    .action-body { flex: 1; min-width: 0; }
    .action-title { font-size: 12.5px; font-weight: 500; color: var(--fg); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .action-sub { font-size: 11px; color: var(--fg-4); margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    /* Connecting checklist */
    .conn-progress { width: 100%; height: 3px; background: var(--bg-2); border-radius: 2px; overflow: hidden; margin-bottom: 10px; }
    .conn-progress::after { content: ""; display: block; height: 100%; width: 30%; background: linear-gradient(90deg, transparent, var(--gem-2), transparent); animation: conn-slide 1.4s linear infinite; }
    @keyframes conn-slide { from { transform: translateX(-100%); } to { transform: translateX(400%); } }
    .checklist { display: flex; flex-direction: column; gap: 6px; }
    .check { display: flex; align-items: center; gap: 8px; padding: 7px 10px; font-size: 12px; color: var(--fg-3); background: var(--bg-1); border: 1px solid var(--line-soft); border-radius: 9px; }
    .check.done { color: var(--fg-2); }
    .check.active { color: var(--fg); border-color: rgba(155,109,255,0.32); background: rgba(155,109,255,0.06); }
    .check-tick { width: 14px; height: 14px; border-radius: 50%; border: 1.5px solid var(--fg-4); display: grid; place-items: center; flex-shrink: 0; }
    .check.done .check-tick { background: var(--live); border-color: var(--live); }
    /* Footer */
    .footer { padding: 10px 16px 14px; border-top: 1px solid var(--line-soft); background: linear-gradient(0deg, rgba(0,0,0,0.25), transparent); display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
    .footer-meta { flex: 1; font-size: 11px; color: var(--fg-4); }
    .disc-btn { height: 32px; padding: 0 12px; border-radius: 8px; background: rgba(244,67,54,0.10); color: #f3a59f; border: 1px solid rgba(244,67,54,0.28); font-size: 12px; font-weight: 500; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
    .disc-btn:hover { background: rgba(244,67,54,0.16); }
    .disc-btn svg { width: 12px; height: 12px; }
    /* Tips */
    .tips { display: flex; flex-direction: column; gap: 8px; }
    .tip { display: flex; gap: 10px; padding: 10px 12px; border-radius: 10px; background: var(--bg-1); border: 1px solid var(--line-soft); font-size: 12px; color: var(--fg-2); line-height: 1.4; }
    .tip-num { width: 18px; height: 18px; border-radius: 50%; background: var(--bg-3); border: 1px solid var(--line); display: grid; place-items: center; font-size: 10.5px; font-weight: 600; color: var(--fg-3); flex-shrink: 0; margin-top: 1px; }
    .error-bar { margin: 8px 16px; padding: 8px 12px; background: rgba(244,67,54,0.10); border: 1px solid rgba(244,67,54,0.28); border-radius: 10px; font-size: 12px; color: #f3a59f; }
    
    .layout-switcher { display: flex; gap: 6px; margin: 8px 0 12px; }
    .style-btn { 
      flex: 1; height: 28px; border-radius: 6px; border: 1px solid var(--line); 
      background: var(--bg-1); color: var(--fg-3); font-size: 10px; font-weight: 600; 
      cursor: pointer; transition: all 120ms;
    }
    .style-btn[data-active] { background: var(--gem-1); border-color: var(--gem-1); color: white; }
    .style-btn:hover:not([data-active]) { background: var(--bg-2); border-color: var(--line-soft); }

    .transcript { display: flex; flex-direction: column; gap: 12px; padding: 0 16px 16px; overflow-y: auto; flex: 1; }
    .turn { display: flex; gap: 12px; animation: fade-in 200ms ease-out; }
    @keyframes fade-in { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
    .avatar { width: 24px; height: 24px; border-radius: 6px; background: var(--bg-3); flex-shrink: 0; display: grid; place-items: center; margin-top: 2px; }
    .avatar.gem { background: linear-gradient(135deg, var(--gem-1), var(--gem-2)); }
    .turn-body { flex: 1; min-width: 0; }
    .turn-role { font-size: 10px; font-weight: 700; color: var(--fg-4); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px; }
    .turn-role.gem { color: var(--gem-2); }
    .turn-text { font-size: 12.5px; line-height: 1.5; color: var(--fg-2); white-space: pre-wrap; }
  `;


  private isActivityStarted = false;

  connectedCallback() {

    super.connectedCallback();
    window.addEventListener('unload', this.unloadHandler);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener('unload', this.unloadHandler);
    this.disconnect();
  }

  private unloadHandler = () => { this.disconnect(); };

  firstUpdated() {
    console.log('[concierge] build v18.1 — modular backend, 16:9 optimized, cinematic UX');
    this.initializeAddon();
  }

  private async initializeAddon() {
    try {
      const session = await meet.addon.createAddonSession({
        cloudProjectNumber: CLOUD_PROJECT_NUMBER,
      });
      this.sidePanelClient = await session.createSidePanelClient();
      const meetingInfo = await this.sidePanelClient.getMeetingInfo();
      this.meetingId = meetingInfo.meetingId;
      this.isAddonInitialized = true;
      this.initialized = true;

      this.sidePanelClient.on('frameToFrameMessage', (arg: any) => {
        try {
          const msg = JSON.parse(arg.payload);
          if (msg.type === 'view_change') {
            if (msg.mode === 'doc') {
              this.openInMainStage(msg.url, msg.label, msg.content);
            }
          }
        } catch (e) {}
      });

      this.status = this.accessToken ? 'Authenticated — click Connect' : 'Ready — click Connect to start';
    } catch (e: any) {
      this.error = `Add-on init failed: ${e.message || e}`;
    }
  }

  private requestOAuthToken(): Promise<void> {
    return new Promise((resolve, reject) => {
      const google = (window as any).google;
      if (!google) { reject(new Error('Google Identity Services not loaded')); return; }
      
      const client = google.accounts.oauth2.initTokenClient({
        client_id: CLIENT_ID,
        scope: [
          'https://www.googleapis.com/auth/meetings.space.created',
          'https://www.googleapis.com/auth/meetings.conference.media.readonly',
          'https://www.googleapis.com/auth/meetings.space.readonly',
          'https://www.googleapis.com/auth/chat.messages.readonly',
          'https://www.googleapis.com/auth/drive.file',
          'https://www.googleapis.com/auth/calendar.readonly',
          'openid',
          'email',
        ].join(' '),
        callback: (tokenResponse: any) => {
          if (tokenResponse.error) {
            reject(new Error(tokenResponse.error_description || tokenResponse.error));
            return;
          }
          this.accessToken = tokenResponse.access_token;
          console.log('[concierge] OAuth token acquired via popup');
          resolve();
          // Auto-connect after successful login
          this.connect();
        },
        error_callback: (err: any) => {
          reject(new Error(err.message || 'Authentication failed'));
        },
      });
      
      client.requestAccessToken({ prompt: 'consent' });
    });
  }

  private connectWebSocket() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${proto}://${location.host}/ws?meeting_id=${encodeURIComponent(this.meetingId)}&token=${encodeURIComponent(this.accessToken)}`;
    this.ws = new WebSocket(url);
    this.ws.binaryType = 'arraybuffer';

    this.ws.onopen = () => {
      this.status = 'Agent connected';
      this.ws!.send(JSON.stringify({
        type: 'init',
        user_email: this.userEmail,
        access_token: this.accessToken,
        meeting_id: this.meetingId,
      }));
    };
    this.ws.onmessage = (e) => {
      if (e.data instanceof ArrayBuffer) {
        // In diagramming mode suppress Gemini's voice — just listen/transcribe
        if (!this.diagramMode) this.playAudioChunk(e.data);
        return;
      }
      try {
        const msg = JSON.parse(e.data as string);
        if (msg.type === 'transcript') {
          const { turn_id, role, text } = msg;
          const roleLabel = role === 'agent' ? 'Gemini Architect' : 'User';
          
          let updated = false;
          const newTranscript = this.transcript.map(t => {
            if (t.id === turn_id) {
              updated = true;
              return { ...t, text: role === 'agent' ? (t.text + text) : text };
            }
            return t;
          });

          if (!updated) {
            // Simple de-dupe for new user turns against local recognition
            const existingText = this.transcript.map(t => t.text).join(' ').toLowerCase();
            if (role === 'agent' || !existingText.includes(text.toLowerCase().substring(0, 20))) {
              newTranscript.push({ id: turn_id, role: roleLabel, text: text });
            }
          }
          this.transcript = [...newTranscript];

          // Broadcast to Main Stage if in transcript mode
          if (this.transcriptMode && this.sidePanelClient) {
            this.sidePanelClient.notifyMainStage(JSON.stringify(msg)).catch(() => {});
          }

          // In diagramming mode: when user speaks, clear the text box and arm silence timer
          if (this.diagramMode && role === 'user' && text?.trim()) {
            this.diagramContext = '';
            this.lastTranscriptTime = Date.now();
            if (this.speechSilenceTimer) clearTimeout(this.speechSilenceTimer);
            this.speechSilenceTimer = setTimeout(() => {
              this.speechSilenceTimer = null;
              if (this.diagramMode && !this.diagramming) this.generateDiagram();
            }, 1000);
          }
        } else if (msg.type === 'status') {
          this.status = msg.text;
        } else if (msg.type === 'action_link') {
          this.actionLinks = [...this.actionLinks, {url: msg.url, label: msg.label || 'Open Document', content: msg.content}];
          this.openInMainStage(msg.url, msg.label || 'Open Document', msg.content || '');
        }
      } catch { }
    };
    this.ws.onerror = () => { this.error = 'WebSocket error'; };
    this.ws.onclose = () => {
      if (this.connected) this.status = 'Agent disconnected';
    };
  }

  private playAudioChunk(data: ArrayBuffer) {
    if (!this.playbackContext) return;
    const ctx = this.playbackContext;
    const int16 = new Int16Array(data);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
      float32[i] = int16[i] / 32768.0;
    }
    const buffer = ctx.createBuffer(1, float32.length, 24000);
    buffer.copyToChannel(float32, 0);
    const schedule = () => {
      const source = ctx.createBufferSource();
      source.buffer = buffer;
      source.connect(ctx.destination);
      const when = Math.max(ctx.currentTime, this.playbackNextTime);
      source.start(when);
      this.playbackNextTime = when + buffer.duration;
    };
    if (ctx.state === 'suspended') {
      ctx.resume().then(schedule);
    } else {
      schedule();
    }
  }

  private captureVideoFrame() {
    if (!this.videoEnabled || !this.videoEl || !this.videoCanvas) return;
    if (this.ws?.readyState !== WebSocket.OPEN) return;
    const ctx = this.videoCanvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(this.videoEl, 0, 0, 320, 180);
    const dataUrl = this.videoCanvas.toDataURL('image/jpeg', 0.7);
    const base64 = dataUrl.split(',')[1];
    this.ws.send(JSON.stringify({ type: 'video_frame', data: base64 }));
  }

  private toggleAudio() { this.audioEnabled = !this.audioEnabled; }
  private toggleVideo() { this.videoEnabled = !this.videoEnabled; }

  private async connect() {
    if (!this.initialized) return;
    this.connecting = true;
    this.error = '';

    try {
      // Create AudioContexts immediately inside the click gesture — before any await
      this.playbackContext = new AudioContext({ sampleRate: 24000 });
      this.playbackNextTime = 0;
      this.audioContext = new AudioContext({ sampleRate: 16000 });

      if (!this.accessToken) await this.requestOAuthToken();
      if (!this.userEmail) {
        try {
          const resp = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
            headers: { 'Authorization': `Bearer ${this.accessToken}` }
          });
          const info = await resp.json();
          this.userEmail = info.email || '';
          console.log('[concierge] user email:', this.userEmail);
        } catch (e) {
          console.warn('[concierge] userinfo fetch failed:', e);
        }
      }
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);

      await this.audioContext.audioWorklet.addModule('/pcm-recorder-processor.js');
      this.workletNode = new AudioWorkletNode(this.audioContext, 'pcm-recorder-processor');

      const silentGain = this.audioContext.createGain();
      silentGain.gain.value = 0;
      this.workletNode.connect(silentGain);
      silentGain.connect(this.audioContext.destination);

      this.connectWebSocket();

      this.workletNode.port.onmessage = (e) => {
        if (!this.audioEnabled || this.ws?.readyState !== WebSocket.OPEN) return;
        const chunk = this.floatTo16BitPCMArray(e.data as Float32Array);
        this.pcmBuffer.push(chunk);
        this.pcmBufferSamples += chunk.length;
        if (this.pcmBufferSamples >= GdmArchitectAgent.PCM_SEND_SAMPLES) {
          const merged = new Int16Array(this.pcmBufferSamples);
          let offset = 0;
          for (const c of this.pcmBuffer) { merged.set(c, offset); offset += c.length; }
          this.ws!.send(merged.buffer);
          this.pcmBuffer = [];
          this.pcmBufferSamples = 0;
        }
      };

      this.meetClient = new MeetMediaApiClientImpl({
        meetingSpaceId: this.meetingId,
        numberOfVideoStreams: 1,
        enableAudioStreams: true,
        accessToken: this.accessToken,
        logsCallback: (event) => console.log(`[Meet] ${event.sourceType}: ${event.logString}`),
      });

      this.meetClient.sessionStatus.subscribe((status) => {
        if (status.connectionState === MeetConnectionState.JOINED) {
          this.connected = true;
          this.connecting = false;
          this.status = 'Listening — Assistant is ready';
          this.startVolumeAnalysis();
        }
      });

      this.meetClient.meetStreamTracks.subscribe((tracks) => {
        tracks.forEach((meetTrack) => {
          const track = meetTrack.mediaStreamTrack;

          if (track.kind === 'audio' && !this.activeTrackIds.has(track.id)) {
            // Activate Chrome's Opus decoder — without a playing element the track delivers silence
            const audioEl = document.createElement('audio');
            audioEl.muted = true;
            audioEl.srcObject = new MediaStream([track]);
            audioEl.play().catch(() => {});
            this.audioContext!.resume();
            const source = this.audioContext!.createMediaStreamSource(new MediaStream([track]));
            source.connect(this.analyser!);
            source.connect(this.workletNode!);
            this.activeTrackIds.add(track.id);
            this.trackCount = this.activeTrackIds.size;
          }

          if (track.kind === 'video' && !this.activeVideoTrackIds.has(track.id)) {
            const videoEl = document.createElement('video');
            videoEl.autoplay = true;
            videoEl.playsInline = true;
            videoEl.muted = true;
            videoEl.srcObject = new MediaStream([track]);
            videoEl.play().catch(() => {});
            this.videoEl = videoEl;

            this.videoCanvas = document.createElement('canvas');
            this.videoCanvas.width = 320;
            this.videoCanvas.height = 180;

            if (this.videoFrameInterval) clearInterval(this.videoFrameInterval);
            this.videoFrameInterval = setInterval(() => this.captureVideoFrame(), 1000);
            this.activeVideoTrackIds.add(track.id);
          }
        });
      });

      await this.meetClient.joinMeeting();
    } catch (e: any) {
      this.error = `Connection failed: ${e.message || e}`;
      this.connecting = false;
    }
  }

  private startVolumeAnalysis() {
    const tick = () => {
      if (this.analyser && this.dataArray) {
        this.analyser.getByteFrequencyData(this.dataArray as any);
        let sum = 0;
        for (let i = 0; i < this.dataArray.length; i++) sum += this.dataArray[i];
        this.volume = sum / this.dataArray.length;
        this.animationFrameId = requestAnimationFrame(tick);
      }
    };
    tick();
  }

  private activateWakeWord() {
    this.wakeActive = true;
    this.status = 'Listening...';
    if (this.wakeTimeout) clearTimeout(this.wakeTimeout);
    this.wakeTimeout = setTimeout(() => this.deactivateWakeWord(), 15000);
  }

  private deactivateWakeWord() {
    this.wakeActive = false;
    this.status = "Standby — say 'Hey Gemini'";
    if (this.wakeTimeout) { clearTimeout(this.wakeTimeout); this.wakeTimeout = null; }
  }

  private async disconnect() {
    if (this.animationFrameId) { cancelAnimationFrame(this.animationFrameId); this.animationFrameId = null; }
    if (this.speechRecognition) { try { this.speechRecognition.stop(); } catch {} this.speechRecognition = null; }
    if (this.wakeTimeout) { clearTimeout(this.wakeTimeout); this.wakeTimeout = null; }
    if (this.videoFrameInterval) { clearInterval(this.videoFrameInterval); this.videoFrameInterval = null; }
    if (this.diagramInterval) { clearInterval(this.diagramInterval); this.diagramInterval = null; }
    if (this.speechSilenceTimer) { clearTimeout(this.speechSilenceTimer); this.speechSilenceTimer = null; }
    this.diagramMode = false;
    this.diagramSessionId = '';
    this.diagramActivityStarted = false;
    if (this.ws) { this.ws.close(); this.ws = null; }
    if (this.audioContext) { await this.audioContext.close(); this.audioContext = null; }
    if (this.playbackContext) { await this.playbackContext.close(); this.playbackContext = null; }
    if (this.meetClient) {
      try { await this.meetClient.leaveMeeting(); } catch {}
      this.meetClient = null;
    }
    this.activeTrackIds.clear();
    this.activeVideoTrackIds.clear();
    this.pcmBuffer = [];
    this.pcmBufferSamples = 0;
    this.videoEl = null;
    this.videoCanvas = null;
    this.connected = false;
    this.connecting = false;
    this.wakeActive = false;
    this.volume = 0;
    this.status = 'Disconnected';
  }

  private floatTo16BitPCMArray(float32: Float32Array): Int16Array {
    const out = new Int16Array(float32.length);
    for (let i = 0; i < float32.length; i++) {
      const s = Math.max(-1, Math.min(1, float32[i]));
      out[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return out;
  }

  private async toggleTranscriptMode() {
    if (this.transcriptMode) {
      this.transcriptMode = false;
    } else {
      this.transcriptMode = true;
      if (this.sidePanelClient && !this.isActivityStarted) {
        const stageUrl = `${location.origin}/main_stage.html?meeting=${encodeURIComponent(this.meetingId)}&token=${encodeURIComponent(this.accessToken)}`;
        try {
          await this.sidePanelClient.startActivity({ mainStageUrl: stageUrl });
          this.isActivityStarted = true;
        } catch (e: any) {
          console.warn('[concierge] startActivity (transcript):', e?.message || e);
          if (String(e).toLowerCase().includes('activity') || e?.name === 'ActivityIsOngoing') {
            this.error = 'Stage occupied: Close the active item (Doc/Sheet) to show captions.';
            this.transcriptMode = false;
          }
        }
      }
    }
  }

  private async toggleDiagramMode() {
    if (this.diagramMode) {
      this.diagramMode = false;
      this.diagramContext = '';
      this.diagramSessionId = '';
      this.diagramActivityStarted = false;
      if (this.speechSilenceTimer) { clearTimeout(this.speechSilenceTimer); this.speechSilenceTimer = null; }
      if (this.diagramInterval) { clearInterval(this.diagramInterval); this.diagramInterval = null; }
      
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'diagram_mode', active: false }));
        // Tell everyone to clear the stage
        this.ws.send(JSON.stringify({ type: 'view_change', mode: 'placeholder' }));
      }
      this.status = 'Assistant connected — listening';
    } else {
      this.diagramMode = true;
      this.transcriptMode = true; // Auto-activate captions when diagrams start
      this.actionLinks = [];
      this.transcriptStartIndex = this.transcript.map(t => `[${t.role}] ${t.text}`).join('\n').length;
      this.diagramSessionStartTime = new Date().toISOString();
      this.diagramSessionId = crypto.randomUUID();
      this.status = 'Gemini Agent Architect — speak your architecture description';
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'diagram_mode', active: true }));
      }
      // Register session server-side
      fetch(`/api/session/${encodeURIComponent(this.meetingId)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: this.diagramSessionId }),
      }).catch(() => {});

      if (this.sidePanelClient) {
        if (!this.isActivityStarted) {
          const stageUrl = `${location.origin}/main_stage.html?mode=diagram&diag_id=${encodeURIComponent(this.diagramSessionId)}&meeting=${encodeURIComponent(this.meetingId)}&token=${encodeURIComponent(this.accessToken)}`;
          try {
            await this.sidePanelClient.startActivity({ mainStageUrl: stageUrl });
            this.isActivityStarted = true;
          } catch (e: any) {
            console.warn('[concierge] startActivity (diagram):', e?.message || e);
            if (String(e).toLowerCase().includes('activity') || e?.name === 'ActivityIsOngoing') {
              this.error = 'Stage occupied: Close the active item (Doc/Sheet) to show diagram.';
              this.diagramMode = false;
            }
          }
        } else {
          // Tell everyone's stage to switch to diagram view (listening state)
          if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
              type: 'view_change',
              mode: 'diagram',
              diag_id: this.diagramSessionId
            }));
          }
        }
      }
      this.diagramInterval = setInterval(() => {
        if (this.diagramMode && !this.diagramming && this.lastTranscriptTime > this.lastGenerationTime) {
          this.generateDiagram();
        }
      }, 1000);
    }
  }

  private async openInMainStage(url: string, label: string, content: string = '') {
    if (this.sidePanelClient && url.includes('docs.google.com')) {
      if (!this.isActivityStarted) {
        const stageUrl = `${location.origin}/main_stage.html?doc=${encodeURIComponent(url)}&label=${encodeURIComponent(label)}&meeting=${encodeURIComponent(this.meetingId)}&token=${encodeURIComponent(this.accessToken)}${content ? `&content=${encodeURIComponent(content)}` : ''}`;
        try {
          await this.sidePanelClient.startActivity({ mainStageUrl: stageUrl });
          this.isActivityStarted = true;
        } catch (e) {
          console.error('[concierge] Failed to start activity:', e);
          window.open(url, '_blank');
        }
      } else {
        // Tell everyone's stage to switch to doc view
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({
            type: 'view_change',
            mode: 'doc',
            url,
            label,
            content
          }));
        }
      }
    } else {
      window.open(url, '_blank');
    }
  }


  private async fetchChatMessages(): Promise<string> {
    if (!this.accessToken || !this.meetingId) return '';
    try {
      // meetingId is in spaces/xxx format — same ID the Chat API uses
      const spaceId = this.meetingId.startsWith('spaces/') ? this.meetingId : `spaces/${this.meetingId}`;
      const resp = await fetch(
        `https://chat.googleapis.com/v1/${spaceId}/messages?pageSize=100&orderBy=createTime asc`,
        { headers: { 'Authorization': `Bearer ${this.accessToken}` } }
      );
      if (!resp.ok) {
        console.warn('[concierge] chat API', resp.status);
        return '';
      }
      const data = await resp.json();
      const messages: string[] = (data.messages || []).filter((m: any) => {
        if (!this.diagramSessionStartTime) return true;
        return m.createTime >= this.diagramSessionStartTime;
      }).map((m: any) => {
        const sender = m.sender?.displayName || m.sender?.name || 'Unknown';
        const text = m.text || m.formattedText || '';
        return text ? `${sender}: ${text}` : null;
      }).filter(Boolean);
      console.log(`[concierge] fetched ${messages.length} relevant chat messages`);
      return messages.join('\n');
    } catch (e) {
      console.warn('[concierge] fetchChatMessages error:', e);
      return '';
    }
  }

  private async generateDiagram() {
    if (this.diagramming) return;
    this.diagramming = true;
    const transcript = this.diagramContext.trim() || this.transcript.map(t => `[${t.role}] ${t.text}`).join('\n').substring(this.transcriptStartIndex).trim() || '';
    const chat = await this.fetchChatMessages();
    try {
      const resp = await fetch('/api/diagram', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transcript,
          chat,
          access_token: this.accessToken,
          space_id: this.meetingId,
          session_id: this.diagramSessionId,
          style: this.diagramStyle,
        }),
      });
      const data = await resp.json();
      if (data.error) throw new Error(data.error);
      this.lastGenerationTime = Date.now();
      if (data.drive_file_id) {
        this.lastDiagramFileId = data.drive_file_id;
      }
      if (this.diagramMode) this.status = 'Gemini Agent Architect — diagram updated';
    } catch (e: any) {
      console.error('[concierge] diagram error:', e);
      this.status = `Diagram failed: ${(e as any).message || e}`;
    } finally {
      this.lastGenerationTime = Date.now();
      this.diagramming = false;
    }
  }

  private async exportTranscript() {
    const fullTranscript = this.transcript.map(t => `[${t.role}] ${t.text}`).join('\n');
    if (!fullTranscript.trim()) {
      this.status = 'Nothing to export — speak first';
      return;
    }
    
    // Open window immediately to avoid popup blocker
    const driveWin = window.open('about:blank', '_blank');
    this.status = 'Exporting transcript to Doc…';

    try {
      const resp = await fetch('/api/transcript/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transcript: fullTranscript,
          access_token: this.accessToken,
          space_id: this.meetingId
        }),
      });
      const data = await resp.json();
      if (data.error) throw new Error(data.error);
      if (data.file_id) {
        this.lastTranscriptFileId = data.file_id;
        const driveUrl = `https://drive.google.com/file/d/${data.file_id}/view`;
        this.status = 'Transcript exported to Drive ✓';
        if (driveWin) {
          driveWin.location.href = driveUrl;
        } else {
          window.open(driveUrl, '_blank');
        }
      } else if (driveWin) {
        driveWin.close();
      }
    } catch (e: any) {
      this.status = `Export failed: ${e.message || e}`;
      if (driveWin) driveWin.close();
    }
  }

  private async saveDiagramToDrive(): Promise<boolean> {
    if (!this.diagramSessionId || !this.accessToken || !this.meetingId) {
      this.status = 'Cannot save — no active diagram session';
      return false;
    }

    // Open window immediately to avoid popup blocker
    const driveWin = window.open('about:blank', '_blank');
    this.status = 'Saving diagram to Drive…';
    
    try {
      const resp = await fetch(`/api/diagram/${this.diagramSessionId}/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ access_token: this.accessToken, space_id: this.meetingId }),
      });
      const data = await resp.json();
      if (data.error) throw new Error(data.error);
      if (data.file_id) {
        this.lastDiagramFileId = data.file_id;
        const driveUrl = `https://drive.google.com/file/d/${data.file_id}/view`;
        this.status = 'Diagram saved to Drive ✓';
        if (driveWin) {
          driveWin.location.href = driveUrl;
        } else {
          window.open(driveUrl, '_blank');
        }
        return true;
      }
      return false;
    } catch (e: any) {
      this.status = `Drive save failed: ${(e as any).message || e}`;
      return false;
    }
  }

  private async saveAndNewDiagram() {
    const success = await this.saveDiagramToDrive();
    if (!success) {
      // Don't wipe if save failed
      return;
    }
    
    console.log('[concierge] Saving and starting new diagram session...');
    this.diagramContext = '';
    this.actionLinks = [];
    this.transcriptStartIndex = this.transcript.map(t => `[${t.role}] ${t.text}`).join('\n').length;
    this.diagramSessionStartTime = new Date().toISOString();
    const oldSessionId = this.diagramSessionId;
    this.diagramSessionId = crypto.randomUUID();
    this.lastTranscriptTime = 0;
    this.lastGenerationTime = 0;
    this.lastTranscriptFileId = '';
    this.lastDiagramFileId = '';
    
    const broadcastMsg = {
      type: 'view_change',
      mode: 'diagram',
      diag_id: this.diagramSessionId,
      version: 0
    };

    // 1. Broadcast reset immediately
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(broadcastMsg));
    }

    // 2. Force local stage update via SDK
    if (this.sidePanelClient) {
      this.sidePanelClient.notifyMainStage(JSON.stringify(broadcastMsg)).catch(() => {});
    }

    // 3. Register session server-side & purge old cache
    try {
      await fetch(`/api/session/${encodeURIComponent(this.meetingId)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          session_id: this.diagramSessionId,
          purge_old: oldSessionId
        }),
      });
      this.status = 'New diagram session ready — speak to generate';
    } catch (e: any) {
      this.status = 'New session ready (registration failed)';
    }
  }

  private async resetDiagram() {
    console.log('[concierge] Resetting diagram session...');
    this.diagramContext = '';
    this.actionLinks = [];
    this.transcriptStartIndex = this.transcript.map(t => `[${t.role}] ${t.text}`).join('\n').length;
    this.diagramSessionStartTime = new Date().toISOString();
    const oldSessionId = this.diagramSessionId;
    this.diagramSessionId = crypto.randomUUID();
    this.lastTranscriptTime = 0;
    this.lastGenerationTime = 0;
    this.lastTranscriptFileId = '';
    this.lastDiagramFileId = '';
    
    const broadcastMsg = {
      type: 'view_change',
      mode: 'diagram',
      diag_id: this.diagramSessionId,
      version: 0
    };

    // 1. Broadcast via WebSocket to remote participants
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(broadcastMsg));
    }

    // 2. Force local stage update via SDK
    if (this.sidePanelClient) {
      this.sidePanelClient.notifyMainStage(JSON.stringify(broadcastMsg)).catch(() => {});
    }

    // 3. Register session server-side & purge old cache
    try {
      await fetch(`/api/session/${encodeURIComponent(this.meetingId)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          session_id: this.diagramSessionId,
          purge_old: oldSessionId 
        }),
      });
      this.status = 'Diagram reset — speak to generate';
    } catch (e: any) {
      this.status = 'Reset failed';
    }
  }

  render() {
    const transcriptLines = this.transcript;

    const docLinksSvg = html`<svg viewBox="0 0 24 24" fill="currentColor" style="width:14px;height:14px"><path d="M14 2H6a2 2 0 0 0-2 2v23a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm4 18H6V4h7v5h5v11zM8 15h8v2H8zm0-4h8v2H8z"/></svg>`;
    const imgLinksSvg = html`<svg viewBox="0 0 24 24" fill="currentColor" style="width:14px;height:14px"><path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 5H5l3.5-3.5z"/></svg>`;

    const actionCards = this.actionLinks.length > 0 ? html`
      <div class="section">
        <div class="section-head"><span class="section-title">Workspace Actions</span></div>
        <div class="action-list">
          ${this.actionLinks.map(link => {
            const isImg = link.url.includes('diagram');
            const isSheet = link.url.includes('/spreadsheets/');
            return html`
            <div class="action" @click=${() => this.openInMainStage(link.url, link.label, link.content)}>
              <div class="action-ico ${isImg ? 'img' : (isSheet ? 'sheet' : 'doc')}">${isImg ? imgLinksSvg : docLinksSvg}</div>
              <div class="action-body">
                <div class="action-title">${link.label}</div>
                <div class="action-sub">${link.url}</div>
              </div>
            </div>`;
          })}
        </div>
      </div>
    ` : html``;

    if (!this.initialized) {
      return html`
        <div class="topbar">
          <div class="brand">
            <div class="brand-mark">${GEMINI_LOGO}</div>
            <div class="brand-name">Gemini Live<span class="live"> · concierge</span></div>
          </div>
          <div style="font-size:9px;color:var(--fg-4)">v18.1</div>
        </div>
        <div class="body">
          <div class="hero" style="padding:40px 18px">
            <div class="orb-wrap">
              <div class="orb-ring r3"></div><div class="orb-ring r2"></div>
              <div class="orb-ring"></div><div class="orb"></div>
            </div>
            <div class="status-pill"><div class="status-dot"></div>Starting…</div>
            <div class="hero-title gem">Gemini Agent Architect</div>
            <div class="hero-sub">Initialising Google Meet Add-on SDK…</div>
          </div>
        </div>
      `;
    }

    if (!this.connected && !this.connecting) {
      this.setAttribute('data-state', 'disconnected');
      return html`
        <div class="topbar">
          <div class="brand">
            <div class="brand-mark">${GEMINI_LOGO}</div>
            <div class="brand-name">Gemini Live<span class="live"> · concierge</span></div>
          </div>
          <div style="font-size:9px;color:var(--fg-4)">v18.1</div>
        </div>
        <div class="body">
          <div class="hero" style="padding:40px 18px 24px">
            <div class="orb-wrap">
              <div class="orb-ring r3"></div><div class="orb-ring r2"></div>
              <div class="orb-ring"></div><div class="orb"></div>
            </div>
            <div class="status-pill disconnected"><div class="status-dot"></div>${this.accessToken ? 'Authenticated' : 'Offline'}</div>
            <div class="hero-title gem">Your AI Concierge</div>
            <div class="hero-sub">Voice-powered workspace assistant embedded in this meeting.</div>
          </div>

          ${this.error ? html`<div class="error-bar" style="margin-top:0">⚠ ${this.error}</div>` : ''}

          <div class="section" style="padding-top:0">
            ${!this.accessToken ? html`
              <button class="cta google" @click=${() => this.requestOAuthToken()}>
                <svg viewBox="0 0 24 24" style="width:18px;height:18px;margin-right:8px"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
                Sign in with Google
              </button>
            ` : html`
              <button class="cta" @click=${() => this.connect()}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="width:16px;height:16px"><path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/></svg>
                Connect to Meeting
              </button>
            `}
          </div>

          ${actionCards}

          <div class="section">
            <div class="section-head"><span class="section-title">How it works</span></div>
            <div class="tips">
              <div class="tip"><div class="tip-num">1</div><span>Say <kbd>Hey Gemini</kbd> to activate, then speak your request</span></div>
              <div class="tip"><div class="tip-num">2</div><span>Create docs, search the web live, or summarise the meeting</span></div>
              <div class="tip"><div class="tip-num">3</div><span>New documents appear here and launch on the main stage for everyone</span></div>
            </div>
          </div>
        </div>
      `;
    }

    if (this.connecting) {
      this.setAttribute('data-state', 'connecting');
      return html`
        <div class="topbar">
          <div class="brand">
            <div class="brand-mark">${GEMINI_LOGO}</div>
            <div class="brand-name">Gemini Live<span class="live"> · concierge</span></div>
          </div>
          <div style="font-size:9px;color:var(--fg-4)">v18.1</div>
        </div>
        <div class="body">
          <div class="hero">
            <div class="orb-wrap">
              <div class="orb-ring r3"></div><div class="orb-ring r2"></div>
              <div class="orb-ring"></div><div class="orb"></div>
            </div>
            <div class="status-pill live"><div class="status-dot"></div>Connecting</div>
            <div class="hero-title">Starting session…</div>
            <div class="hero-sub">${this.status}</div>
          </div>
          <div class="section">
            <div class="conn-progress"></div>
            <div class="checklist">
              <div class="check done"><div class="check-tick">✓</div>Add-on initialised</div>
              <div class="check active"><div class="check-tick"></div>Connecting to Gemini Live…</div>
              <div class="check"><div class="check-tick"></div>Joining meeting audio</div>
            </div>
          </div>
        </div>
      `;
    }

    this.setAttribute('data-state', this.wakeActive ? 'wake' : 'listening');
    return html`
      <div class="topbar">
        <div class="brand">
          <div class="brand-mark">${GEMINI_LOGO}</div>
          <div class="brand-name">Gemini Live<span class="live"> · concierge</span></div>
        </div>
        <div class="topbar-actions">
          ${this.lastDiagramFileId ? html`
            <button class="icon-btn" title="Open latest diagram"
              @click=${() => window.open(`https://drive.google.com/file/d/${this.lastDiagramFileId}/view`, '_blank')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
            </button>
          ` : ''}
          <div style="font-size:9px;color:var(--fg-4)">v18.1</div>
        </div>
      </div>
      <div class="body">
        <div class="hero" style="padding-bottom:12px">
          <div class="orb-wrap">
            <div class="orb-ring r3"></div><div class="orb-ring r2"></div>
            <div class="orb-ring"></div><div class="orb"></div>
          </div>
          <div class="status-pill live"><div class="status-dot"></div>${this.wakeActive ? 'Activated' : 'Live'}</div>
          <div class="hero-sub" style="margin-top:-4px">${this.status}</div>
        </div>

        ${actionCards}

        <div class="section">
          <div class="section-head"><span class="section-title">What can I say?</span></div>
          <div class="action-list" style="gap:8px">
            <div class="action-sub" style="font-size:11px;padding:0 4px;margin-bottom:4px">Ask Gemini to help with your workspace:</div>
            <div class="turn-text" style="font-size:11px;opacity:0.8;padding:4px;background:rgba(255,255,255,0.03);border-radius:6px">
              • "Create a document about our project plan"<br>
              • "Search for the latest architectural review"<br>
              • "Start diagramming a 3-tier web application"
            </div>
          </div>
        </div>

        <div class="section">
          <div class="controls-row" style="grid-template-columns:repeat(5, 1fr)">
            <div class="ctrl" data-active="${this.audioEnabled}" @click=${() => this.toggleAudio()}>
              <div class="ctrl-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:15px;height:15px"><path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/></svg>
              </div>
              <span class="ctrl-label">Mic</span>
              <span class="ctrl-state">${this.audioEnabled ? 'On' : 'Muted'}</span>
            </div>
            <div class="ctrl" data-active="${this.videoEnabled}" @click=${() => this.toggleVideo()}>
              <div class="ctrl-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:15px;height:15px"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>
              </div>
              <span class="ctrl-label">Cam</span>
              <span class="ctrl-state">${this.videoEnabled ? 'On' : 'Off'}</span>
            </div>
            <div class="ctrl" data-active="${this.wakeActive}" style="--gem-1:var(--gem-2)"
                 @click=${() => this.wakeActive ? this.deactivateWakeWord() : this.activateWakeWord()}>
              <div class="ctrl-icon">
                <svg viewBox="0 0 28 28" style="width:15px;height:15px"><path d="M14 1C14 8.2 8.2 14 1 14C8.2 14 14 19.8 14 27C14 19.8 19.8 14 27 14C19.8 14 14 8.2 14 1Z" fill="currentColor"/></svg>
              </div>
              <span class="ctrl-label">Wake</span>
              <span class="ctrl-state">${this.wakeActive ? 'Active' : 'Standby'}</span>
            </div>
            <div class="ctrl" data-active="${this.transcriptMode}"
                 @click=${() => this.toggleTranscriptMode()}>
              <div class="ctrl-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:15px;height:15px">
                  <rect x="1" y="4" width="22" height="16" rx="2" ry="2"/>
                  <path d="M7 15h2a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v4a2 2 0 0 0 2 2z"/>
                  <path d="M15 15h2a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-2a2 2 0 0 0-2 2v4a2 2 0 0 0 2 2z"/>
                </svg>
              </div>
              <span class="ctrl-label">Captions</span>
              <span class="ctrl-state">${this.transcriptMode ? 'On' : 'Off'}</span>
            </div>
            <div class="ctrl" data-active="${this.diagramMode}"
                 @click=${() => this.toggleDiagramMode()}>
              <div class="ctrl-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:15px;height:15px">
                  <rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>
                  <rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>
                  <line x1="6.5" y1="10" x2="6.5" y2="14"/><line x1="17.5" y1="10" x2="17.5" y2="14"/>
                  <line x1="10" y1="17.5" x2="14" y2="17.5"/>
                </svg>
              </div>
              <span class="ctrl-label">Diagrams</span>
              <span class="ctrl-state">${this.diagramMode ? (this.diagramming ? 'Updating' : 'Active') : 'Off'}</span>
            </div>
          </div>
        </div>

        ${this.diagramMode ? html`
        <div class="section">
          <div class="section-head">
            <span class="section-title">Diagram Visuals</span>
          </div>
          <div class="layout-switcher">
            <button class="style-btn" ?data-active=${this.diagramStyle === 'blueprint'} 
                    @click=${() => { this.diagramStyle = 'blueprint'; this.generateDiagram(); }}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px;margin-right:4px"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>
              Blueprint
            </button>
            <button class="style-btn" ?data-active=${this.diagramStyle === 'sketch'} 
                    @click=${() => { this.diagramStyle = 'sketch'; this.generateDiagram(); }}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px;margin-right:4px"><path d="M12 19l7-7 3 3-7 7-3-3z"/><path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z"/><path d="M2 2l5 5"/></svg>
              Sketch
            </button>
            <button class="style-btn" ?data-active=${this.diagramStyle === 'cyber'} 
                    @click=${() => { this.diagramStyle = 'cyber'; this.generateDiagram(); }}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px;margin-right:4px"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
              Dark Flow
            </button>
            <button class="style-btn" ?data-active=${this.diagramStyle === 'google'} 
                    @click=${() => { this.diagramStyle = 'google'; this.generateDiagram(); }}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="width:12px;height:12px;margin-right:4px"><circle cx="12" cy="12" r="10"/><path d="M12 8v8M8 12h8"/></svg>
              Corporate
            </button>
          </div>

          <div class="section-head" style="margin-top:16px">
            <span class="section-title">Diagram Context</span>
          </div>
          <div class="ctx-wrap">
            <textarea class="ctx-input" placeholder="Refine your architecture description here..."
              .value=${this.diagramContext}
              @input=${(e: any) => this.diagramContext = e.target.value}></textarea>
            <div class="ctx-actions" style="margin-top:12px; gap:8px">
              <button class="ctx-send" style="flex:1"
                ?disabled=${this.diagramming}
                @click=${() => this.generateDiagram()}>
                ${this.diagramming ? 'Generating…' : 'Generate'}
              </button>
              <button class="ctx-send" style="background:var(--bg-3);border:1px solid var(--line);color:var(--fg-3);flex:1"
                @click=${() => this.resetDiagram()}>
                New
              </button>
              <button class="ctx-send" style="background:var(--gem-1);flex:1.5"
                ?disabled=${!this.diagramSessionId || !this.lastGenerationTime}
                @click=${() => this.saveDiagramToDrive()}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="width:14px;height:14px;margin-right:6px"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                Export to Drive
              </button>
              ${this.lastDiagramFileId ? html`
                <button class="ctx-send" style="background:var(--gem-2);flex:1.2"
                  @click=${() => window.open(`https://drive.google.com/file/d/${this.lastDiagramFileId}/view`, '_blank')}>
                  Open PNG
                </button>
              ` : ''}
            </div>
          </div>
        </div>
        ` : html``}

        <div class="section">
          <div class="section-head">
            <span class="section-title">Transcript</span>
            <button class="mode-toggle" @click=${() => this.exportTranscript()}>Export</button>
          </div>
          ${transcriptLines.length > 0 ? html`
            <div class="transcript">
              ${transcriptLines.map(turn => {
                const isAgent = turn.role === 'Gemini Architect';
                return html`
                  <div class="turn">
                    <div class="avatar ${isAgent ? 'gem' : ''}">
                      ${isAgent
                        ? html`<svg viewBox="0 0 28 28" style="width:13px;height:13px;color:white"><path d="M14 1C14 8.2 8.2 14 1 14C8.2 14 14 19.8 14 27C14 19.8 19.8 14 27 14C19.8 14 14 8.2 14 1Z" fill="currentColor"/></svg>`
                        : html`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="width:11px;height:11px;color:var(--fg-3)"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`}
                    </div>
                    <div class="turn-body">
                      <div class="turn-role ${isAgent ? 'gem' : ''}">${turn.role}</div>
                      <div class="turn-text">${turn.text}</div>
                    </div>
                  </div>`;
              })}
            </div>
          ` : html`
            <div class="empty-state">
              <div class="empty-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></div>
              No conversation captured yet
            </div>
          `}
        </div>
      </div>
      <div class="footer">
        <div class="footer-meta">
          ${this.trackCount > 0 ? `${this.trackCount} audio track${this.trackCount > 1 ? 's' : ''}` : 'Meeting audio active'}
        </div>
        <button class="disc-btn" @click=${() => this.disconnect()}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          Disconnect
        </button>
      </div>
    `;
  }
}
