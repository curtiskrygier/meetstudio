import { css } from 'lit';

export const mainStyles = css`
    :host {
      display: flex; flex-direction: column; width: 100%; height: 100%; overflow: hidden;
      
      /* Default Theme Tokens */
      --bg-0: #0c0d10; 
      --bg-1: #131418; 
      --bg-2: #191b20; 
      --bg-3: #20232a;
      --line: #262932; 
      --line-soft: #1d2027;
      --fg: #f2f3f5; 
      --fg-2: #b8bcc4; 
      --fg-3: #7e828c; 
      --fg-4: #565a64;
      --gem-1: #4285F4; 
      --gem-2: #9B6DFF; 
      --gem-3: #EE82A8;
      --live: #34d27a; 
      --live-soft: #1c2c23;
      --warn: #f0a04b; 
      --radius: 14px; 
      --radius-sm: 10px;
      --font: "Plus Jakarta Sans", system-ui, sans-serif;

      background: var(--bg-0); 
      color: var(--fg);
      font-family: var(--font);
      -webkit-font-smoothing: antialiased;
      color-scheme: dark;
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
    
    /* Layout Sections */
    .section { padding: 0 16px 14px; transition: all 300ms ease; }
    .section + .section { padding-top: 4px; }
    
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

    /* UI Primitives */
    .mode-toggle {
      font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
      padding: 3px 7px; border-radius: 5px;
      background: var(--bg-3); border: 1px solid var(--line);
      color: var(--gem-2); cursor: pointer; transition: all 120ms;
    }
    .mode-toggle:hover { background: var(--bg-2); border-color: var(--fg-4); }

    .mode-toggle-lg {
      font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.02em;
      padding: 6px 12px; border-radius: 8px;
      background: var(--bg-3); border: 1px solid var(--line);
      color: var(--gem-2); cursor: pointer; transition: all 120ms;
      display: flex; align-items: center; gap: 4px;
    }
    .mode-toggle-lg:hover { background: var(--bg-2); border-color: var(--fg-4); transform: translateY(-1px); }
    .mode-toggle-lg:active { transform: translateY(0); }
    .section-title { font-size: 11px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--fg-4); }
    
    /* Checklist */
    .conn-progress { width: 100%; height: 3px; background: var(--bg-2); border-radius: 2px; overflow: hidden; margin-bottom: 10px; }
    .conn-progress::after { content: ""; display: block; height: 100%; width: 30%; background: linear-gradient(90deg, transparent, var(--gem-2), transparent); animation: conn-slide 1.4s linear infinite; }
    @keyframes conn-slide { from { transform: translateX(-100%); } to { transform: translateX(400%); } }
    .checklist { display: flex; flex-direction: column; gap: 6px; }
    .check { display: flex; align-items: center; gap: 8px; padding: 7px 10px; font-size: 12px; color: var(--fg-3); background: var(--bg-1); border: 1px solid var(--line-soft); border-radius: 9px; }
    .check.done { color: var(--fg-2); }
    .check.active { color: var(--fg); border-color: rgba(155,109,255,0.32); background: rgba(155,109,255,0.06); }
    .check-tick { width: 14px; height: 14px; border-radius: 50%; border: 1.5px solid var(--fg-4); display: grid; place-items: center; flex-shrink: 0; }
    .check.done .check-tick { background: var(--live); border-color: var(--live); }

    /* Layout Footer */
    .footer { padding: 10px 16px 14px; border-top: 1px solid var(--line-soft); background: linear-gradient(0deg, rgba(0,0,0,0.25), transparent); display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
    .footer-meta { flex: 1; font-size: 11px; color: var(--fg-4); }
    .disc-btn { height: 32px; padding: 0 12px; border-radius: 8px; background: rgba(244,67,54,0.10); color: #f3a59f; border: 1px solid rgba(244,67,54,0.28); font-size: 12px; font-weight: 500; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
    .disc-btn:hover { background: rgba(244,67,54,0.16); }
    .disc-btn svg { width: 12px; height: 12px; }

    /* Tips */
    .tip { display: flex; gap: 10px; padding: 10px 12px; border-radius: var(--radius-sm); background: var(--bg-1); border: 1px solid var(--line-soft); font-size: 12px; color: var(--fg-2); line-height: 1.4; }
    .tip + .tip { margin-top: 8px; }
    .tip-num { width: 18px; height: 18px; border-radius: 50%; background: var(--bg-3); border: 1px solid var(--line); display: grid; place-items: center; font-size: 10.5px; font-weight: 600; color: var(--fg-3); flex-shrink: 0; margin-top: 1px; }
    kbd { display: inline-block; padding: 1px 6px; margin: 0 1px; font: 500 11px sans-serif; color: var(--fg-2); background: var(--bg-3); border: 1px solid var(--line); border-bottom-width: 2px; border-radius: 5px; }

    .empty-state { padding: 32px 16px; text-align: center; color: var(--fg-4); }
    .empty-icon { margin-bottom: 12px; opacity: 0.2; }
    .empty-icon svg { width: 48px; height: 48px; }

    /* Layout Modes */
    /* Focus: Only status and transcript */
    .body.layout-focus gdm-controls-view,
    .body.layout-focus gdm-actions-view,
    .body.layout-focus gdm-diagram-refiner { display: none; }
    
    /* Minimal: Only status orb, compact padding */
    .body.layout-minimal .section { padding: 8px; }
    .body.layout-minimal gdm-controls-view,
    .body.layout-minimal gdm-actions-view,
    .body.layout-minimal gdm-diagram-refiner,
    .body.layout-minimal gdm-transcript-view { display: none; }

    /* Presentation: Enlarged status, no controls/transcript */
    .body.layout-presentation gdm-status-view { transform: scale(1.1); margin: 20px 0; }
    .body.layout-presentation gdm-controls-view,
    .body.layout-presentation gdm-transcript-view { display: none; }

    /* Split: Two-column layout (simulated with grid) */
    .body.layout-split { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; }
    .body.layout-split .section { padding: 8px; }

    /* UI Prompt Bar */
    .ui-prompt-bar { padding-top: 0; padding-bottom: 10px; }
    .ui-prompt-row { display: flex; gap: 8px; align-items: flex-start; }
    .ui-prompt-input { min-height: unset; height: 36px; resize: none; padding: 8px 12px; flex: 1; }

    /* Broadcast Media Studio Sub-menu Styles */
    .tabs-container {
      display: flex; gap: 4px; padding: 10px 16px; border-bottom: 1px solid var(--line-soft);
      background: rgba(0,0,0,0.15); backdrop-filter: blur(10px); flex-shrink: 0;
    }
    .tab-btn {
      flex: 1; height: 34px; border-radius: 8px; border: 1px solid transparent;
      background: transparent; color: var(--fg-3); font-size: 12.5px; font-weight: 600;
      cursor: pointer; transition: all 150ms ease; display: flex; align-items: center; justify-content: center; gap: 6px;
    }
    .tab-btn:hover { color: var(--fg-2); background: rgba(255,255,255,0.02); }
    .tab-btn.active {
      color: var(--fg); background: var(--bg-2); border-color: var(--line);
      box-shadow: 0 2px 8px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.05);
    }
    
    .widget-container {
      display: flex; flex-direction: column; gap: 16px; padding: 16px;
    }
    .widget-card {
      background: var(--bg-1); border: 1px solid var(--line-soft); border-radius: var(--radius);
      padding: 14px; display: flex; flex-direction: column; gap: 12px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.15); transition: border-color 150ms;
    }
    .widget-card:hover { border-color: var(--line); }
    .widget-title {
      font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;
      color: var(--fg-2); display: flex; align-items: center; gap: 6px; margin-bottom: 2px;
    }
    .widget-subtitle {
      font-size: 11px; color: var(--fg-4); margin-top: -8px; margin-bottom: 4px;
    }
    
    .btn-grid {
      display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px;
    }
    .btn-grid-2 {
      display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px;
    }
    .btn-action {
      height: 34px; border-radius: 8px; border: 1px solid var(--line);
      background: var(--bg-2); color: var(--fg-2); font-size: 11.5px; font-weight: 600;
      cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px;
      transition: all 120ms ease;
    }
    .btn-action:hover {
      background: var(--bg-3); border-color: var(--fg-4); color: var(--fg);
      transform: translateY(-1px);
    }
    .btn-action:active { transform: translateY(0); }
    .btn-action.active {
      background: rgba(155,109,255,0.12); border-color: rgba(155,109,255,0.4); color: #c4a1ff;
      box-shadow: 0 0 12px rgba(155,109,255,0.1);
    }
    .btn-action.active:hover {
      background: rgba(155,109,255,0.18); border-color: rgba(155,109,255,0.6);
    }
    .btn-action.danger {
      background: rgba(244,67,54,0.06); border-color: rgba(244,67,54,0.2); color: #fba49e;
    }
    .btn-action.danger:hover {
      background: rgba(244,67,54,0.12); border-color: rgba(244,67,54,0.4);
    }
    
    .form-row {
      display: flex; gap: 8px; align-items: center;
    }
    .form-group {
      display: flex; flex-direction: column; gap: 5px; flex: 1;
    }
    .form-label {
      font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; color: var(--fg-3);
    }
    .ctx-input {
      height: 34px; background: var(--bg-2); border: 1px solid var(--line-soft);
      border-radius: 8px; padding: 0 10px; color: var(--fg); font-size: 12px;
      transition: all 120ms; width: 100%; box-sizing: border-box;
    }
    .ctx-input:focus {
      outline: none; border-color: var(--gem-1); background: var(--bg-3);
      box-shadow: 0 0 8px rgba(66,133,244,0.15);
    }
    .select-control {
      height: 34px; background: var(--bg-2); border: 1px solid var(--line-soft);
      border-radius: 8px; padding: 0 8px; color: var(--fg-2); font-size: 12px;
      cursor: pointer; transition: all 120ms; width: 100%; box-sizing: border-box;
    }
    .select-control:focus {
      outline: none; border-color: var(--gem-1);
    }
    
    /* Toggle switch */
    .switch-row {
      display: flex; justify-content: space-between; align-items: center; padding: 4px 0;
    }
    .switch-label-wrap {
      display: flex; flex-direction: column; gap: 2px;
    }
    .switch-lbl { font-size: 12px; font-weight: 600; color: var(--fg-2); }
    .switch-desc { font-size: 10px; color: var(--fg-4); }
    
    .switch-container {
      position: relative; display: inline-block; width: 36px; height: 20px;
    }
    .switch-container input { opacity: 0; width: 0; height: 0; }
    .slider {
      position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
      background-color: var(--bg-3); border: 1px solid var(--line);
      transition: .2s; border-radius: 20px;
    }
    .slider:before {
      position: absolute; content: ""; height: 12px; width: 12px; left: 3px; bottom: 3px;
      background-color: var(--fg-3); transition: .2s; border-radius: 50%;
    }
    input:checked + .slider {
      background-color: rgba(52,210,122,0.15); border-color: rgba(52,210,122,0.4);
    }
    input:checked + .slider:before {
      transform: translateX(16px); background-color: var(--live);
    }
    
    .reaction-grid {
      display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px;
    }
    .reaction-btn {
      height: 42px; border-radius: 10px; border: 1px solid var(--line-soft);
      background: var(--bg-2); font-size: 16px; cursor: pointer;
      display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px;
      transition: all 120ms ease;
    }
    .reaction-btn:hover {
      background: var(--bg-3); border-color: var(--line); transform: scale(1.05);
    }
    .reaction-btn:active { transform: scale(0.95); }
    .reaction-name { font-size: 8px; font-weight: 700; text-transform: uppercase; color: var(--fg-4); letter-spacing: 0.02em; }
    .reaction-btn:hover .reaction-name { color: var(--fg-3); }
`;
