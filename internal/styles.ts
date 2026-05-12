import { css } from 'lit';

export const mainStyles = css`
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

    /* Layout switcher */
    .layout-switcher { display: flex; gap: 6px; margin: 8px 0 12px; }
    .style-btn { 
      flex: 1; height: 28px; border-radius: 6px; border: 1px solid var(--line); 
      background: var(--bg-1); color: var(--fg-3); font-size: 10px; font-weight: 600; 
      cursor: pointer; transition: all 120ms;
    }
    .style-btn[data-active] { background: var(--gem-1); border-color: var(--gem-1); color: white; }
    .style-btn:hover:not([data-active]) { background: var(--bg-2); border-color: var(--line-soft); }

    /* Context Input */
    .ctx-input { width: 100%; min-height: 88px; background: var(--bg-2) !important; border: 1px solid var(--line); border-radius: var(--radius-sm); color: var(--fg) !important; font-family: inherit; font-size: 12px; line-height: 1.5; padding: 10px 12px; resize: vertical; box-sizing: border-box; transition: border-color 150ms; }
    .ctx-input:focus { outline: none; border-color: var(--gem-2); }
    .ctx-send { flex-shrink: 0; height: 36px; padding: 0 14px; background: var(--gem-2); border: none; border-radius: var(--radius-sm); color: #fff; font-family: inherit; font-size: 12px; font-weight: 600; cursor: pointer; align-self: flex-end; white-space: nowrap; }
    .ctx-send:hover { opacity: 0.85; }
    .ctx-send:disabled { opacity: 0.4; cursor: default; }

    /* Footer */
    .footer { padding: 10px 16px 14px; border-top: 1px solid var(--line-soft); background: linear-gradient(0deg, rgba(0,0,0,0.25), transparent); display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
    .footer-meta { flex: 1; font-size: 11px; color: var(--fg-4); }
    .disc-btn { height: 32px; padding: 0 12px; border-radius: 8px; background: rgba(244,67,54,0.10); color: #f3a59f; border: 1px solid rgba(244,67,54,0.28); font-size: 12px; font-weight: 500; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
    .disc-btn:hover { background: rgba(244,67,54,0.16); }
    .disc-btn svg { width: 12px; height: 12px; }

    /* Tips */
    .tip { display: flex; gap: 10px; padding: 10px 12px; border-radius: 10px; background: var(--bg-1); border: 1px solid var(--line-soft); font-size: 12px; color: var(--fg-2); line-height: 1.4; }
    .tip + .tip { margin-top: 8px; }
    .tip-num { width: 18px; height: 18px; border-radius: 50%; background: var(--bg-3); border: 1px solid var(--line); display: grid; place-items: center; font-size: 10.5px; font-weight: 600; color: var(--fg-3); flex-shrink: 0; margin-top: 1px; }
    kbd { display: inline-block; padding: 1px 6px; margin: 0 1px; font: 500 11px sans-serif; color: var(--fg-2); background: var(--bg-3); border: 1px solid var(--line); border-bottom-width: 2px; border-radius: 5px; }

    .empty-state { padding: 32px 16px; text-align: center; color: var(--fg-4); }
    .empty-icon { margin-bottom: 12px; opacity: 0.2; }
    .empty-icon svg { width: 48px; height: 48px; }
`;
