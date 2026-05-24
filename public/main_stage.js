(function() {
    const params = new URLSearchParams(location.search);
    let currentMode = params.get('mode') || 'placeholder';
    let diagramId = params.get('diag_id') || '';
    const meetingId = params.get('meeting') || '';
    const ticket = params.get('ticket') || '';
    let knownVersion = 0;
    let turns = [];
    const panelAutoplay = { video: true, 1: true, 2: true, 3: true, 4: true };
    const panelSources = { video: null, 1: null, 2: null, 3: null, 4: null };
    let userVotedOption = null;
    let lastVal1 = 0;
    let lastVal2 = 0;
    let lastVal3 = 0;
    let lastVal4 = 0;
    let hasOpt3 = false;
    let hasOpt4 = false;
    const activeCameraStreams = {};
    let standbyInterval = null;
    let audioCtx = null;

    let lockedFlightCallsign = null;
    let lockedFlightAltitude = 0;
    let lockedFlightSpeed = 0;
    let radarZoomLevel = 10.0;
    let renderDashboardGlobal = () => {};

    window.changeRadarZoom = function(amount) {
      const prevZoom = radarZoomLevel;
      radarZoomLevel = Math.max(0.5, Math.min(10.0, radarZoomLevel + amount));
      if (radarZoomLevel !== prevZoom) {
        try {
          if (audioCtx) {
            if (audioCtx.state === 'suspended') audioCtx.resume();
            const now = audioCtx.currentTime;
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            const startFreq = amount > 0 ? 600 : 800;
            const endFreq = amount > 0 ? 900 : 500;
            osc.frequency.setValueAtTime(startFreq, now);
            osc.frequency.exponentialRampToValueAtTime(endFreq, now + 0.1);
            gain.gain.setValueAtTime(0.04, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.1);
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            osc.start(now);
            osc.stop(now + 0.1);
          }
        } catch (e) {
          console.error("Audio beep error:", e);
        }
        renderDashboardGlobal();
      }
    };

    window.selectFlightTarget = function(callsign, altitude, speed) {
      lockedFlightCallsign = callsign;
      lockedFlightAltitude = altitude;
      lockedFlightSpeed = speed;
      try {
        if (audioCtx) {
          if (audioCtx.state === 'suspended') audioCtx.resume();
          const now = audioCtx.currentTime;
          const osc1 = audioCtx.createOscillator();
          const gain1 = audioCtx.createGain();
          osc1.frequency.setValueAtTime(880, now);
          gain1.gain.setValueAtTime(0.08, now);
          gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.12);
          osc1.connect(gain1);
          gain1.connect(audioCtx.destination);
          osc1.start(now);
          osc1.stop(now + 0.12);

          const osc2 = audioCtx.createOscillator();
          const gain2 = audioCtx.createGain();
          osc2.frequency.setValueAtTime(1320, now + 0.05);
          gain2.gain.setValueAtTime(0.06, now + 0.05);
          gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.2);
          osc2.connect(gain2);
          gain2.connect(audioCtx.destination);
          osc2.start(now + 0.05);
          osc2.stop(now + 0.2);
        }
      } catch (e) {}
      renderDashboardGlobal();
    };

    // Smooth scrolling auto-ticker engine
    let lastScrollTick = Date.now();
    function startAutoTickerEngine() {
      function tick() {
        const now = Date.now();
        const delta = (now - lastScrollTick) / 1000;
        lastScrollTick = now;

        const tickers = document.querySelectorAll('.stocks-ticker-container');
        tickers.forEach(container => {
          if (container.matches(':hover')) return;

          container.scrollTop += 20 * delta;

          const halfway = container.scrollHeight / 2;
          if (container.scrollTop >= halfway) {
            container.scrollTop -= halfway;
          }
        });

        requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    }
    startAutoTickerEngine();


    // Drawing Canvas initialization
    const canvas = document.getElementById('drawing-canvas');
    let ctx = null;
    if (canvas) {
      ctx = canvas.getContext('2d');
      const resizeCanvas = () => {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
      };
      window.addEventListener('resize', resizeCanvas);
      resizeCanvas();
    }

    function showDiagramPlaceholder() {
      const container = document.getElementById('diagram-container');
      if (!container) return;
      container.innerHTML = `
        <div class="inner-placeholder">
          <div class="ear-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:28px;height:28px">
              <path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
            </svg>
          </div>
          <div>
            <div style="font-weight:600; color:rgba(255,255,255,0.9); margin-bottom:4px">Awaiting Design Description</div>
            <div style="font-size:12px; color:rgba(255,255,255,0.5)">Say or type something to dynamically build the stage system architecture</div>
          </div>
        </div>`;
    }

    function setView(mode) {
      document.querySelectorAll('#content-layer > div').forEach(div => div.classList.add('hidden'));
      const active = document.getElementById(`view-${mode}`);
      if (active) active.classList.remove('hidden');
      
      // Reset preview if moving away from doc
      if (mode !== 'doc') {
        const previewEl = document.getElementById('doc-preview');
        if (previewEl) {
          previewEl.textContent = '';
          previewEl.classList.add('hidden');
        }
      }
      currentMode = mode;
    }

    let visualizerTimeout = null;
    function triggerVoiceVisualizer(durationMs = 4000) {
      const vis = document.getElementById('voice-visualizer');
      if (vis) {
        vis.classList.remove('hidden');
        if (visualizerTimeout) clearTimeout(visualizerTimeout);
        visualizerTimeout = setTimeout(() => {
          vis.classList.add('hidden');
        }, durationMs);
      }
    }

    function updateTranscript(msg) {
      const { turn_id, role, text, label } = msg;
      const container = document.getElementById('transcript-container');
      if (!container) return;
      let existing = turns.find(t => t.turn_id === turn_id);

      if (!existing) {
        const el = document.createElement('div');
        el.className = `turn active ${role}`;
        el.innerHTML = `<span class="role-label">${label || (role === 'agent' ? 'Gemini Architect' : 'You')}</span><span class="content"></span>`;
        
        turns.forEach(t => {
          if (t.element.classList.contains('active')) { t.element.classList.replace('active', 'prev-1'); }
          else if (t.element.classList.contains('prev-1')) { t.element.classList.replace('prev-1', 'prev-2'); }
          else if (t.element.classList.contains('prev-2')) { t.element.classList.replace('prev-2', 'old'); }
        });

        container.appendChild(el);
        existing = { turn_id, role, element: el };
        turns.push(existing);
        if (turns.length > 5) {
            const removed = turns.shift();
            if (removed && removed.element) removed.element.remove();
        }
      }
      const contentEl = existing.element.querySelector('.content');
      if (contentEl) contentEl.textContent = text;

      // Trigger gorgeous active voice bouncing bars overlay!
      triggerVoiceVisualizer(4000);
    }

    function renderInlineSVG(base64) {
      try {
        console.log('[stage] Rendering inline SVG...');
        const binString = atob(base64);
        const bytes = new Uint8Array(binString.length);
        for (let i = 0; i < binString.length; i++) bytes[i] = binString.charCodeAt(i);
        const svg = new TextDecoder().decode(bytes);
        
        const container = document.getElementById('diagram-container');
        if (!container) return;
        container.innerHTML = DOMPurify.sanitize(svg);
        
        const svgEl = container.querySelector('svg');
        if (svgEl) {
          svgEl.removeAttribute('width');
          svgEl.removeAttribute('height');
          svgEl.setAttribute('preserveAspectRatio', 'xMidYMid meet');
          svgEl.style.opacity = '0';
          svgEl.style.transition = 'opacity 400ms ease-out';
          requestAnimationFrame(() => svgEl.style.opacity = '1');
        }
      } catch (e) {
        console.error('[stage] SVG render failed:', e);
      }
    }

    function youtubeId(url) {
      try {
        const u = new URL(url);
        if (u.hostname.includes('youtube.com')) return u.searchParams.get('v');
        if (u.hostname === 'youtu.be') return u.pathname.slice(1);
      } catch (e) {}
      return null;
    }

    function updateAutoplayBadge(pIdx) {
      let parent = null;
      if (pIdx === 'video') {
        parent = document.getElementById('view-video');
      } else {
        parent = document.getElementById(`image-panel-${pIdx}`);
      }
      if (!parent) return;

      let badge = parent.querySelector('.autoplay-badge');
      if (!badge) {
        badge = document.createElement('div');
        badge.className = 'autoplay-badge';
        parent.appendChild(badge);
        badge.addEventListener('click', (e) => {
          e.stopPropagation();
          panelAutoplay[pIdx] = !panelAutoplay[pIdx];
          if (pIdx === 'video') {
            const url = panelSources['video'];
            if (url) playVideo(url);
          } else {
            const srcInfo = panelSources[pIdx];
            if (srcInfo) {
              renderStageImage(srcInfo.base64, pIdx, srcInfo.layout, srcInfo.label);
            }
          }
        });
      }

      const isAutoplay = panelAutoplay[pIdx];
      if (isAutoplay) {
        badge.className = 'autoplay-badge mode-autoplay';
        badge.innerHTML = '⚡ Autoplay';
      } else {
        badge.className = 'autoplay-badge mode-manual';
        badge.innerHTML = '🖱️ Manual Play';
      }
    }

    function setupYoutubeAutoplay(iframeEl) {
      if (!iframeEl) return;
      let attempts = 0;
      const interval = setInterval(() => {
        attempts++;
        if (attempts > 12) {
          clearInterval(interval);
          return;
        }
        try {
          if (iframeEl && iframeEl.contentWindow) {
            iframeEl.contentWindow.postMessage('{"event":"command","func":"playVideo","args":""}', '*');
          }
        } catch (e) {
          console.warn("[stage] postMessage attempt error", e);
        }
      }, 250);
    }

    function playVideo(url) {
      const videoEl = document.getElementById('stage-video');
      const iframeEl = document.getElementById('stage-iframe');
      if (!videoEl || !iframeEl) return;

      panelSources['video'] = url;

      const ytId = youtubeId(url);
      if (ytId) {
        videoEl.classList.add('hidden');
        videoEl.pause();
        videoEl.src = '';
        const isAutoplay = panelAutoplay['video'];
        if (isAutoplay) {
          iframeEl.src = `https://www.youtube.com/embed/${ytId}?autoplay=1&mute=1&enablejsapi=1`;
          setupYoutubeAutoplay(iframeEl);
        } else {
          iframeEl.src = `https://www.youtube.com/embed/${ytId}?autoplay=0&mute=0&controls=1&enablejsapi=1`;
          iframeEl.onload = null;
        }
        iframeEl.classList.remove('hidden');
        updateAutoplayBadge('video');
      } else {
        const existingBadge = document.getElementById('view-video')?.querySelector('.autoplay-badge');
        if (existingBadge) existingBadge.remove();
        iframeEl.classList.add('hidden');
        iframeEl.src = '';
        videoEl.classList.remove('hidden');
        videoEl.src = url;
        videoEl.play().catch(() => {});
     }
    }

    let dashboardInterval = null;
    let chartData = Array(15).fill(15);
    let telemetryMode = 'stk'; // 'stk', 'ord', 'id'
    let customDashboardState = null;
    let autoRotationInterval = null;
    let activeTabs = [
      { id: 'stk', label: 'STK' },
      { id: 're', label: 'PROP' },
      { id: 'flt', label: 'FLT' }
    ];

    // AI-oriented Megatech stocks (Top 20)
    const aiStocks = [
      { symbol: 'NVDA', name: 'NVIDIA Corp.', price: 914.85, change: 1.45, prevPrice: 914.85 },
      { symbol: 'MSFT', name: 'Microsoft Corp.', price: 421.90, change: 0.82, prevPrice: 421.90 },
      { symbol: 'GOOGL', name: 'Alphabet Inc.', price: 173.50, change: 1.15, prevPrice: 173.50 },
      { symbol: 'META', name: 'Meta Platforms', price: 475.20, change: -0.42, prevPrice: 475.20 },
      { symbol: 'AMZN', name: 'Amazon.com Inc.', price: 185.30, change: 0.65, prevPrice: 185.30 },
      { symbol: 'AAPL', name: 'Apple Inc.', price: 189.85, change: -0.21, prevPrice: 189.85 },
      { symbol: 'PLTR', name: 'Palantir Tech', price: 21.45, change: 3.82, prevPrice: 21.45 },
      { symbol: 'TSLA', name: 'Tesla Inc.', price: 174.60, change: -1.75, prevPrice: 174.60 },
      { symbol: 'AVGO', name: 'Broadcom Inc.', price: 1395.00, change: 0.95, prevPrice: 1395.00 },
      { symbol: 'AMD', name: 'Advanced Micro', price: 160.20, change: -0.85, prevPrice: 160.20 },
      { symbol: 'ARM', name: 'ARM Holdings', price: 112.40, change: 2.10, prevPrice: 112.40 },
      { symbol: 'QCOM', name: 'Qualcomm Inc.', price: 188.50, change: 0.45, prevPrice: 188.50 },
      { symbol: 'ASML', name: 'ASML Holding', price: 920.00, change: -0.30, prevPrice: 920.00 },
      { symbol: 'SMCI', name: 'Super Micro', price: 815.50, change: 4.50, prevPrice: 815.50 },
      { symbol: 'SNOW', name: 'Snowflake Inc.', price: 145.20, change: -1.20, prevPrice: 145.20 },
      { symbol: 'CRWD', name: 'CrowdStrike', price: 320.10, change: 1.80, prevPrice: 320.10 },
      { symbol: 'MDB', name: 'MongoDB Inc.', price: 340.50, change: -0.90, prevPrice: 340.50 },
      { symbol: 'DDOG', name: 'Datadog Inc.', price: 115.80, change: 0.75, prevPrice: 115.80 },
      { symbol: 'ADBE', name: 'Adobe Inc.', price: 485.40, change: -0.55, prevPrice: 485.40 },
      { symbol: 'ORCL', name: 'Oracle Corp.', price: 122.30, change: 1.25, prevPrice: 122.30 }
    ];

    let stockCycleIndex = 0;
    let cycleTickCount = 0;

    let globalOrderCounter = 1452180;
    let orderVelocity = 512;
    let slaRate = 99.98;

    let idTrustIndex = 99.98;
    let idLatency = 32;

    function activateDashboardTelemetry() {
      if (dashboardInterval) return;

      const fillPath = document.getElementById('chart-path-fill');
      const linePath = document.getElementById('chart-path-line');
      const val1 = document.getElementById('dash-val-latency');
      const val2 = document.getElementById('dash-val-speed');
      const val3 = document.getElementById('dash-val-efficiency');

      const titleText = document.getElementById('dashboard-title-text');
      const tabsContainer = document.getElementById('dashboard-tabs-container');

      // Schema-driven telemetry modules (Server-Driven A2UI design)
      const dataModel = {
        stk: {
          getMetrics() {
            // Drift stocks
            aiStocks.forEach(s => {
              s.prevPrice = s.price;
              const driftPercent = (Math.random() * 0.003 - 0.0013);
              s.price += s.price * driftPercent;
              s.change += driftPercent * 100;
            });

            cycleTickCount++;
            if (cycleTickCount >= 4) {
              cycleTickCount = 0;
              stockCycleIndex = (stockCycleIndex + 1) % aiStocks.length;
            }

            const s1 = aiStocks[stockCycleIndex];
            const s2 = aiStocks[(stockCycleIndex + 1) % aiStocks.length];
            const s3 = aiStocks[(stockCycleIndex + 2) % aiStocks.length];

            const getColor = (s) => s.price >= s.prevPrice ? '#00ff88' : '#ff3b30';
            const getArrow = (s) => s.price >= s.prevPrice ? '▲' : '▼';

            return {
              title: '⚡ Realtime AI Stocks Ticker (Top 20)',
              metrics: [
                { label: `${s1.symbol} (${s1.change >= 0 ? '+' : ''}${s1.change.toFixed(2)}%)`, value: `$${s1.price.toFixed(2)} ${getArrow(s1)}`, color: getColor(s1) },
                { label: `${s2.symbol} (${s2.change >= 0 ? '+' : ''}${s2.change.toFixed(2)}%)`, value: `$${s2.price.toFixed(2)} ${getArrow(s2)}`, color: getColor(s2) },
                { label: `${s3.symbol} (${s3.change >= 0 ? '+' : ''}${s3.change.toFixed(2)}%)`, value: `$${s3.price.toFixed(2)} ${getArrow(s3)}`, color: getColor(s3) }
              ],
              chartValue: Math.max(0, Math.min(100, 50 + (s1.change * 15)))
            };
          }
        },
        ord: {
          getMetrics() {
            globalOrderCounter += Math.floor(Math.random() * 14 + 12);
            orderVelocity += Math.floor(Math.random() * 9 - 4);
            if (orderVelocity < 480) orderVelocity = 480;
            if (orderVelocity > 545) orderVelocity = 545;

            slaRate += (Math.random() * 0.02 - 0.01);
            if (slaRate > 99.99) slaRate = 99.99;
            if (slaRate < 99.91) slaRate = 99.91;

            return {
              title: '📦 Global Realtime AI Inference Orders',
              metrics: [
                { label: 'Cumulative Orders', value: globalOrderCounter.toLocaleString(), color: '#00f2ff' },
                { label: 'Inference Velocity', value: `${orderVelocity} req/s`, color: '#00ff88' },
                { label: 'SLA Compliance', value: `${slaRate.toFixed(3)}%`, color: '#00ff88' }
              ],
              chartValue: ((orderVelocity - 480) / 65) * 100
            };
          }
        },
        id: {
          getMetrics() {
            idTrustIndex += (Math.random() * 0.01 - 0.005);
            if (idTrustIndex > 100.0) idTrustIndex = 100.0;
            if (idTrustIndex < 99.92) idTrustIndex = 99.92;

            idLatency += Math.floor(Math.random() * 5 - 2);
            if (idLatency < 26) idLatency = 26;
            if (idLatency > 38) idLatency = 38;

            const sigHex = Math.floor(Math.random() * 16).toString(16).toUpperCase();
            const sessionSig = `AG-${Math.floor(Math.random() * 899 + 100)}X-${sigHex}E`;

            return {
              title: '🛡️ Identity, Session & Trust Integrity',
              metrics: [
                { label: 'Session Signature', value: sessionSig, color: '#00f2ff' },
                { label: 'Trust Score Index', value: `${idTrustIndex.toFixed(3)}%`, color: '#00ff88' },
                { label: 'Handshake Latency', value: `${idLatency} ms`, color: '#00f2ff' }
              ],
              chartValue: 100 - ((idLatency - 26) / 12) * 80
            };
          }
        }
      };



      function renderDashboard() {
        // Resolve active visible dashboard element dynamically (works on panel 1 or panel 3!)
        const dashboardEl = document.querySelector('.panel-dashboard:not(.hidden)');
        if (!dashboardEl) return;

        const titleText = dashboardEl.querySelector('[id*="title-text"]') || document.getElementById('dashboard-title-text');
        const tabsContainer = dashboardEl.querySelector('[id*="tabs-container"]') || document.getElementById('dashboard-tabs-container');
        const dynamicContentEl = dashboardEl.querySelector('[id*="dynamic-content"]') || document.getElementById('dashboard-dynamic-content');
        
        const fillPath = dashboardEl.querySelector('[id*="chart-path-fill"]') || document.getElementById('chart-path-fill');
        const linePath = dashboardEl.querySelector('[id*="chart-path-line"]') || document.getElementById('chart-path-line');
        const val1 = dashboardEl.querySelector('[id*="val-latency"]') || document.getElementById('dash-val-latency');
        const val2 = dashboardEl.querySelector('[id*="val-speed"]') || document.getElementById('dash-val-speed');
        const val3 = dashboardEl.querySelector('[id*="val-efficiency"]') || document.getElementById('dash-val-efficiency');

        // Publish to global scope so target locks can trigger re-renders
        renderDashboardGlobal = renderDashboard;

        // Render tabs container dynamically (Zero hardcoded HTML tabs)
        if (tabsContainer) {
          tabsContainer.innerHTML = '';
          activeTabs.forEach(t => {
            const span = document.createElement('span');
            span.className = 'dash-tab';
            span.id = `tab-${t.id}`;
            span.textContent = t.label;
            span.style.cursor = 'pointer';
            span.style.fontSize = '9px';
            span.style.padding = '2px 6px';
            span.style.borderRadius = '4px';
            span.style.transition = 'all 0.2s';

            if (t.id === telemetryMode) {
              span.style.border = '1px solid rgba(0, 242, 255, 0.4)';
              span.style.background = 'rgba(0, 242, 255, 0.1)';
              span.style.color = '#00f2ff';
            } else {
              span.style.border = '1px solid rgba(255, 255, 255, 0.1)';
              span.style.background = 'transparent';
              span.style.color = 'rgba(255, 255, 255, 0.4)';
            }

            span.onclick = () => {
              telemetryMode = t.id;
              chartData = Array(15).fill(t.id === 'stk' ? 40 : t.id === 'ord' ? 60 : 20);
              renderDashboard();
              resetAutoRotation();
            };
            tabsContainer.appendChild(span);
          });
        }

        // Fetch dynamic schema metrics
        let viewData;
        if (customDashboardState && (customDashboardState.activeTabId === telemetryMode || customDashboardState.mode === telemetryMode)) {
          const msg = customDashboardState;
          viewData = {
            title: msg.title || 'Custom Telemetry',
            metrics: (msg.metrics || []).map(m => ({ label: m.label, value: m.value, color: m.color, data: m.data })),
            chartValue: msg.chartValue !== undefined ? msg.chartValue : 50
          };
          if (msg.chart && Array.isArray(msg.chart)) {
            chartData = [...msg.chart];
            while (chartData.length < 15) chartData.unshift(0);
            if (chartData.length > 15) chartData = chartData.slice(-15);
            viewData.chartValue = chartData[chartData.length - 1];
          }
        } else if (dataModel[telemetryMode]) {
          viewData = dataModel[telemetryMode].getMetrics();
        } else {
          viewData = { title: 'Unknown Mode', metrics: [], chartValue: 20 };
        }

        // Apply metadata to UI targets
        if (titleText && viewData.title) titleText.innerHTML = viewData.title;

        if (dynamicContentEl) {
          const activeTabId = telemetryMode || 'stk';

          // Cache scroll position of ticker list before replacing HTML
          const oldTicker = dynamicContentEl.querySelector('.stocks-ticker-container');
          const savedScrollPos = oldTicker ? oldTicker.scrollTop : 0;

          // Resolve rendering capability dynamically (Fully Server-Driven A2UI design)
          let viewType = 'ticker';
          if (customDashboardState && customDashboardState.viewType) {
            viewType = customDashboardState.viewType;
          } else if (activeTabId === 're') {
            viewType = 'cards';
          } else if (activeTabId === 'flt') {
            viewType = 'radar';
          }

          if (viewType === 'cards') {
            // Dense Card Grid Capability
            let html = `<div class="dense-cards-grid">`;
            const items = (customDashboardState && customDashboardState.metrics) ? customDashboardState.metrics : [
              {label: "Station CAPITOLE", value: "12 bikes / 8 stands"},
              {label: "Station JEANNE D'ARC", value: "7 bikes / 15 stands"},
              {label: "Station GARE MATABIAU", value: "19 bikes / 3 stands"}
            ];
            items.forEach(s => {
              const name = s.label.replace(/^(Station|Location|Task|Item)\s+/i, '');
              const parts = s.value.match(/(\d+)\s*([a-zA-Z]*)\s*(?:\/|➔)\s*(\d+)\s*([a-zA-Z]*)/i);
              let val1 = 5, val2 = 10, pct = 50;
              let u1 = "units", u2 = "slots";
              if (parts) {
                val1 = parseInt(parts[1]);
                u1 = parts[2] || "units";
                val2 = parseInt(parts[3]);
                u2 = parts[4] || "slots";
                const total = val1 + val2;
                pct = total > 0 ? (val1 / total) * 100 : 0;
              } else {
                const singleNum = s.value.match(/(\d+)/);
                if (singleNum) {
                  val1 = parseInt(singleNum[1]);
                  pct = Math.min(100, val1);
                }
              }
              const color = s.color || (val1 > 3 ? '#00ff88' : '#ff3b30');
              html += `
                <div class="dense-card">
                  <div>
                    <div class="dense-card-title">● ${name}</div>
                    <div class="dense-card-value" style="color: ${color};">${val1} <span style="font-size: 11px; color: rgba(255,255,255,0.4);">${parts ? '/ ' + (val2 + val1) : ''}</span></div>
                  </div>
                  <div class="progress-bar-bg">
                    <div class="progress-bar-fill" style="width: ${pct}%; background-color: ${color};"></div>
                  </div>
                </div>
              `;
            });
            html += `</div>`;
            dynamicContentEl.innerHTML = html;

          } else if (viewType === 'radar') {
            // Check if panel layout is stretched (grid-3 or fullscreen single)
            const layoutAttr = document.getElementById('view-image')?.getAttribute('data-image-layout');
            const isStretched = ['grid-3', 'single', 'presentation'].includes(layoutAttr);
            
            // Plot dynamic aircraft / radar target plots
            const flights = (customDashboardState && customDashboardState.metrics) ? customDashboardState.metrics : [
              {label: "Flight AFR6129 (NCE ➔ TLS)", value: "Alt: 1450m / Spd: 420km/h", color: "#00f2ff"},
              {label: "Flight BAW373 (LHR ➔ TLS)", value: "Alt: 3200m / Spd: 510km/h", color: "#00f2ff"}
            ];

            // A2UI paradigm: prefer the structured `data` object; fall back to scraping
            // the display strings only for legacy/preset payloads that omit it.
            const flightFields = (f) => {
              const d = f.data || {};
              const altMatch = f.value ? f.value.match(/Alt:\s*(\d+)m/i) : null;
              const spdMatch = f.value ? f.value.match(/Spd:\s*(\d+)km\/h/i) : null;
              const callsign = d.callsign || (f.label || '').replace(/^Flight\s+/i, '').split(' ')[0];
              return {
                callsign,
                altitude: d.altitude != null ? d.altitude : (altMatch ? parseInt(altMatch[1]) : 1500),
                speed: d.speed != null ? d.speed : (spdMatch ? parseInt(spdMatch[1]) : 400),
                vrate: d.vrate != null ? d.vrate : 0,
              };
            };
            // Blip colour by vertical rate: green descending, amber climbing, cyan level.
            const blipColor = (vrate) => vrate < -250 ? '#00ff88' : (vrate > 250 ? '#ffd60a' : '#00f2ff');

            let radarSvg = "";
            if (isStretched) {
              // High-fidelity widescreen cockpit layout: side-by-side layout
              radarSvg += `<div style="display: flex; flex-direction: row; gap: 24px; align-items: stretch; justify-content: stretch; height: 100%; width: 100%; min-height: 0; flex: 1;">`;
              
              // Left Column: Large circular radar scope
              radarSvg += `
                <div class="radar-column" style="width: 42%; display: flex; flex-direction: column; align-items: stretch; min-height: 0;">
                  <div class="radar-container" style="flex: 1; height: 165px; min-height: 165px; margin-bottom: 4px;">
                    <svg viewBox="0 0 200 200" style="width: 100%; height: 100%; display: block;">
                      <!-- Concentric radar distance rings -->
                      <circle cx="100" cy="100" r="20" fill="none" stroke="rgba(0, 242, 255, 0.1)" stroke-width="0.5"/>
                      <circle cx="100" cy="100" r="45" fill="none" stroke="rgba(0, 242, 255, 0.15)" stroke-width="0.5"/>
                      <circle cx="100" cy="100" r="70" fill="none" stroke="rgba(0, 242, 255, 0.1)" stroke-width="0.5" stroke-dasharray="2 2"/>
                      <circle cx="100" cy="100" r="95" fill="none" stroke="rgba(0, 242, 255, 0.05)" stroke-width="0.5"/>
                      
                      <!-- Radar crosshairs -->
                      <line x1="100" y1="5" x2="100" y2="195" stroke="rgba(0, 242, 255, 0.1)" stroke-width="0.5"/>
                      <line x1="5" y1="100" x2="195" y2="100" stroke="rgba(0, 242, 255, 0.1)" stroke-width="0.5"/>
                      
                      <!-- LFBO Runway vectors oriented at 320 degrees -->
                      <line x1="${100 - 15 * (radarZoomLevel / 10.0)}" y1="${100 + 20 * (radarZoomLevel / 10.0)}" x2="${100 + 15 * (radarZoomLevel / 10.0)}" y2="${100 - 20 * (radarZoomLevel / 10.0)}" stroke="rgba(0, 242, 255, 0.3)" stroke-width="1.5" stroke-dasharray="3 2"/>
                      <line x1="${100 - 10 * (radarZoomLevel / 10.0)}" y1="${100 + 22 * (radarZoomLevel / 10.0)}" x2="${100 + 20 * (radarZoomLevel / 10.0)}" y2="${100 - 18 * (radarZoomLevel / 10.0)}" stroke="rgba(0, 242, 255, 0.15)" stroke-width="1" stroke-dasharray="3 2"/>
                      <text x="${100 + 22 * (radarZoomLevel / 10.0)}" y="${100 - 16 * (radarZoomLevel / 10.0)}" fill="rgba(0, 242, 255, 0.4)" font-size="5px" font-family="monospace">LFBO 32L/R</text>

                      <!-- Sweeping radar line animation -->
                      <line x1="100" y1="100" x2="100" y2="5" class="radar-sweep-line" style="transform-origin: 100px 100px;" stroke="rgba(0, 242, 255, 0.35)" stroke-width="1"/>
                      <polygon points="100,100 90,5 100,5" fill="url(#sweep-grad)" class="radar-sweep-line" style="transform-origin: 100px 100px;"/>
                      <defs>
                        <linearGradient id="sweep-grad" x1="0" y1="0" x2="1" y2="0">
                          <stop offset="0%" stop-color="rgba(0, 242, 255, 0.15)"/>
                          <stop offset="100%" stop-color="rgba(0, 242, 255, 0)"/>
                        </linearGradient>
                      </defs>
              `;
            } else {
              // Cramped vertical layout: stacked style for standard grid cells
              radarSvg += `
                <div class="radar-container" style="flex: 1; height: 95px; min-height: 95px; margin-bottom: 4px;">
                  <svg viewBox="0 0 300 120" style="width: 100%; height: 100%; display: block;">
                    <!-- Concentric radar distance rings -->
                    <circle cx="150" cy="60" r="15" fill="none" stroke="rgba(0, 242, 255, 0.1)" stroke-width="0.5"/>
                    <circle cx="150" cy="60" r="35" fill="none" stroke="rgba(0, 242, 255, 0.15)" stroke-width="0.5"/>
                    <circle cx="150" cy="60" r="55" fill="none" stroke="rgba(0, 242, 255, 0.1)" stroke-width="0.5" stroke-dasharray="2 2"/>
                    <circle cx="150" cy="60" r="75" fill="none" stroke="rgba(0, 242, 255, 0.05)" stroke-width="0.5"/>
                    
                    <!-- Radar crosshairs -->
                    <line x1="150" y1="5" x2="150" y2="115" stroke="rgba(0, 242, 255, 0.1)" stroke-width="0.5"/>
                    <line x1="75" y1="60" x2="225" y2="60" stroke="rgba(0, 242, 255, 0.1)" stroke-width="0.5"/>
                    
                    <!-- LFBO Runway vectors oriented at 320 degrees -->
                    <line x1="${150 - 15 * (radarZoomLevel / 10.0)}" y1="${60 + 20 * (radarZoomLevel / 10.0)}" x2="${150 + 15 * (radarZoomLevel / 10.0)}" y2="${60 - 20 * (radarZoomLevel / 10.0)}" stroke="rgba(0, 242, 255, 0.3)" stroke-width="1.5" stroke-dasharray="3 2"/>
                    <line x1="${150 - 10 * (radarZoomLevel / 10.0)}" y1="${60 + 22 * (radarZoomLevel / 10.0)}" x2="${150 + 20 * (radarZoomLevel / 10.0)}" y2="${60 - 18 * (radarZoomLevel / 10.0)}" stroke="rgba(0, 242, 255, 0.15)" stroke-width="1" stroke-dasharray="3 2"/>
                    <text x="${150 + 22 * (radarZoomLevel / 10.0)}" y="${60 - 16 * (radarZoomLevel / 10.0)}" fill="rgba(0, 242, 255, 0.4)" font-size="5px" font-family="monospace">LFBO 32L/R</text>

                    <!-- Sweeping radar line animation -->
                    <line x1="150" y1="60" x2="150" y2="5" class="radar-sweep-line" style="transform-origin: 150px 60px;" stroke="rgba(0, 242, 255, 0.35)" stroke-width="1"/>
                    <polygon points="150,60 140,5 150,5" fill="url(#sweep-grad)" class="radar-sweep-line" style="transform-origin: 150px 60px;"/>
                    <defs>
                      <linearGradient id="sweep-grad" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stop-color="rgba(0, 242, 255, 0.15)"/>
                        <stop offset="100%" stop-color="rgba(0, 242, 255, 0)"/>
                      </linearGradient>
                    </defs>
              `;
            }

            flights.forEach((f, idx) => {
              if (!f.label || f.label.includes("Monitoring")) return;
              // Structured-first extraction (A2UI), regex fallback for legacy payloads
              const ff = flightFields(f);
              const callsign = ff.callsign;
              const altitude = ff.altitude;
              const speed = ff.speed;
              const targetColor = blipColor(ff.vrate);

              // Coordinates centered at (100, 100) for stretched or (150, 60) for regular
              const cx = isStretched ? 100 : 150;
              const cy = isStretched ? 100 : 60;
              const maxDist = isStretched ? 90 : 50;
              const maxAlt = isStretched ? 5000 : 6000;
              
              // Calculate radar positioning (Lower altitude = closer to airport center, zoomed in)
              const dist = Math.max(5, (altitude / maxAlt) * maxDist * (radarZoomLevel / 10.0));
              // Deterministic angle based on callsign letters
              let angleCode = 0;
              for (let i = 0; i < callsign.length; i++) angleCode += callsign.charCodeAt(i);
              const angle = (angleCode * 25) % 360;
              const rad = (angle * Math.PI) / 180;
              const x = cx + dist * Math.cos(rad);
              const y = cy + dist * Math.sin(rad);
              
              const isLocked = lockedFlightCallsign === callsign;
              const brackets = isLocked ? `
                <g stroke="#00ff88" stroke-width="1" fill="none" class="hud-bracket" style="transform-origin: ${x}px ${y}px; animation: target-pulse 0.8s ease-in-out infinite alternate;">
                  <path d="M ${x - 5} ${y - 2} L ${x - 5} ${y - 5} L ${x - 2} ${y - 5}" />
                  <path d="M ${x + 5} ${y - 2} L ${x + 5} ${y - 5} L ${x + 2} ${y - 5}" />
                  <path d="M ${x - 5} ${y + 2} L ${x - 5} ${y + 5} L ${x - 2} ${y + 5}" />
                  <path d="M ${x + 5} ${y + 2} L ${x + 5} ${y + 5} L ${x + 2} ${y + 5}" />
                </g>
              ` : '';
              
              radarSvg += `
                <g class="radar-target" style="animation-delay: ${idx * 0.4}s; cursor: pointer;" data-callsign="${callsign}" data-altitude="${altitude}" data-speed="${speed}">
                  ${brackets}
                  <circle cx="${x}" cy="${y}" r="2.5" fill="${isLocked ? '#00f2ff' : targetColor}"/>
                  <circle cx="${x}" cy="${y}" r="5" fill="none" stroke="${isLocked ? '#00f2ff' : targetColor}" stroke-width="0.5" opacity="0.4"/>
                  <line x1="${x}" y1="${y}" x2="${x - (speed/120) * Math.cos(rad)}" y2="${y - (speed/120) * Math.sin(rad)}" stroke="${isLocked ? '#00f2ff' : targetColor}" stroke-width="0.75" stroke-dasharray="1 1" opacity="0.7"/>
                  <text x="${x + 6}" y="${y - 1}" fill="${isLocked ? '#00f2ff' : targetColor}" font-size="5.5px" font-family="'Roboto Mono', monospace" font-weight="700">${callsign}</text>
                  <text x="${x + 6}" y="${y + 4}" fill="${isLocked ? 'rgba(0, 242, 255, 0.7)' : 'rgba(0, 255, 136, 0.7)'}" font-size="4.5px" font-family="'Roboto Mono', monospace">FL${Math.round(altitude * 3.28084 / 100)} / ${speed}kmh</text>
                </g>
              `;
            });

            // Holographic HUD Lock Card inside the radar circle on widescreen
            if (isStretched) {
              if (lockedFlightCallsign) {
                radarSvg += `
                  <g transform="translate(10, 142)" opacity="0.95" style="animation: radar-blink 3s infinite;">
                    <rect x="0" y="0" width="85" height="35" rx="4" fill="rgba(0, 255, 136, 0.08)" stroke="#00ff88" stroke-width="0.75" />
                    <line x1="0" y1="8" x2="85" y2="8" stroke="rgba(0, 255, 136, 0.2)" stroke-width="0.5" />
                    <text x="5" y="6" fill="#00ff88" font-size="4.5px" font-family="'Roboto Mono', monospace" font-weight="700">TARGET ACQUIRED</text>
                    <text x="5" y="14" fill="rgba(255,255,255,0.9)" font-size="5px" font-family="'Roboto Mono', monospace">CALLSIGN: ${lockedFlightCallsign}</text>
                    <text x="5" y="21" fill="rgba(255,255,255,0.7)" font-size="4.5px" font-family="'Roboto Mono', monospace">ALTITUDE: FL${Math.round(lockedFlightAltitude * 3.28084 / 100)}</text>
                    <text x="5" y="28" fill="rgba(255,255,255,0.7)" font-size="4.5px" font-family="'Roboto Mono', monospace">AIRSPEED: ${lockedFlightSpeed} KMH</text>
                    <text x="55" y="28" fill="#00ff88" font-size="5px" font-family="'Roboto Mono', monospace" font-weight="700">LOCK ON</text>
                  </g>
                `;
              } else {
                radarSvg += `
                  <g transform="translate(10, 168)" opacity="0.6">
                    <text x="5" y="6" fill="rgba(255, 255, 255, 0.35)" font-size="5px" font-family="'Roboto Mono', monospace">HUD INTERACTIVE LOCK [CLICK TARGETS]</text>
                  </g>
                `;
              }
            }

            if (isStretched) {
              radarSvg += `
                    </svg>
                    <!-- Floating Glassmorphic HUD Zoom Controls -->
                    <div class="radar-zoom-controls" style="position: absolute; bottom: 8px; right: 8px; display: flex; gap: 4px; z-index: 10; align-items: center; background: rgba(5, 15, 25, 0.65); border: 1px solid rgba(0, 242, 255, 0.25); border-radius: 6px; padding: 2px 4px; backdrop-filter: blur(4px);">
                      <button class="radar-zoom-btn radar-zoom-out">−</button>
                      <span style="color: #00f2ff; font-family: 'Roboto Mono', monospace; font-size: 8px; font-weight: bold; min-width: 32px; text-align: center; user-select: none; border-left: 1px solid rgba(0, 242, 255, 0.15); border-right: 1px solid rgba(0, 242, 255, 0.15); padding: 0 4px;">${radarZoomLevel.toFixed(2)}x</span>
                      <button class="radar-zoom-btn radar-zoom-in">+</button>
                    </div>
                  </div>
                  <div style="display:flex; justify-content:space-between; margin-top:2px; font-size:8px; font-family:'Roboto Mono', monospace; border-top:1px solid rgba(255,255,255,0.05); padding-top:4px; color:rgba(255,255,255,0.55); margin-bottom: 2px;">
                    <span>LFBO RADAR CONSOLE</span>
                    <span style="color:#00ff88; text-shadow: 0 0 5px rgba(0,255,136,0.4);">● LIVE ACTIVE</span>
                  </div>
                </div>
                
                <!-- Right Column: Wide table/ticker list of flights -->
                <div class="logs-column" style="width: 55%; display: flex; flex-direction: column; align-items: stretch; min-height: 0;">
                  <div style="display:flex; justify-content:space-between; font-size:9px; font-family:'Roboto Mono', monospace; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:6px; color:#00f2ff; margin-bottom: 6px; font-weight:700; text-transform:uppercase; letter-spacing:1px;">
                    <span>Airspace Inventory logs</span>
                    <span>ACTIVE TARGETS: ${flights.filter(f => f.label && !f.label.includes("Monitoring")).length}</span>
                  </div>
                  <div class="stocks-ticker-container" style="flex: 1; max-height: none; overflow-y: auto;">
              `;
            } else {
              radarSvg += `
                    </svg>
                    <!-- Floating Glassmorphic HUD Zoom Controls -->
                    <div class="radar-zoom-controls" style="position: absolute; bottom: 8px; right: 8px; display: flex; gap: 4px; z-index: 10; align-items: center; background: rgba(5, 15, 25, 0.65); border: 1px solid rgba(0, 242, 255, 0.25); border-radius: 6px; padding: 2px 4px; backdrop-filter: blur(4px);">
                      <button class="radar-zoom-btn radar-zoom-out">−</button>
                      <span style="color: #00f2ff; font-family: 'Roboto Mono', monospace; font-size: 8px; font-weight: bold; min-width: 32px; text-align: center; user-select: none; border-left: 1px solid rgba(0, 242, 255, 0.15); border-right: 1px solid rgba(0, 242, 255, 0.15); padding: 0 4px;">${radarZoomLevel.toFixed(2)}x</span>
                      <button class="radar-zoom-btn radar-zoom-in">+</button>
                    </div>
                  </div>
                  <div style="display:flex; justify-content:space-between; margin-top:2px; font-size:8px; font-family:'Roboto Mono', monospace; border-top:1px solid rgba(255,255,255,0.05); padding-top:4px; color:rgba(255,255,255,0.55); margin-bottom: 6px;">
                    <span>LFBO RADAR CONSOLE // APP STAGES</span>
                    <span style="color:#00ff88; text-shadow: 0 0 5px rgba(0,255,136,0.4);">● LIVE ACTIVE RADAR SWEEP</span>
                  </div>
                  <div class="stocks-ticker-container" style="flex: 1; max-height: none; overflow-y: auto;">
              `;
            }

            // List the flights below/beside the radar sweep
            flights.forEach(f => {
              if (!f.label) return;
              const isMonitoring = f.label.includes("Monitoring") || f.label.includes("Scanning");
              const labelText = f.label;
              const valText = f.value;
              const colorText = f.color || "#00f2ff";
              
              const ff = flightFields(f);
              const callsign = ff.callsign;
              const altitude = ff.altitude;
              const speed = ff.speed;

              const isLocked = lockedFlightCallsign === callsign;

              radarSvg += `
                <div class="stocks-ticker-row radar-flight-row" style="padding: 6px 10px; font-size: 11px; cursor: pointer; ${isLocked ? 'border-color: #00ff88; background: rgba(0, 255, 136, 0.06);' : ''}" data-callsign="${callsign}" data-altitude="${altitude}" data-speed="${speed}">
                  <span style="font-weight:700; color:${isMonitoring ? 'rgba(255,255,255,0.35)' : (isLocked ? '#00ff88' : 'rgba(255,255,255,0.85)')};">${labelText}</span>
                  <span style="color:${isMonitoring ? 'rgba(255,255,255,0.3)' : (isLocked ? '#00ff88' : colorText)}; font-weight:700;">${isLocked ? '🔒 LOCKED ON' : valText}</span>
                </div>
              `;
            });

            if (isStretched) {
              radarSvg += `
                  </div>
                </div>
              </div>
              `;
            } else {
              radarSvg += `
                </div>
              `;
            }
            
            dynamicContentEl.innerHTML = radarSvg;

            // Bind programmatic CSP-compliant event listeners to dynamic elements
            const outBtn = dynamicContentEl.querySelector('.radar-zoom-out');
            if (outBtn) {
              outBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                window.changeRadarZoom(-0.25);
              });
            }
            const inBtn = dynamicContentEl.querySelector('.radar-zoom-in');
            if (inBtn) {
              inBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                window.changeRadarZoom(0.25);
              });
            }
            const targets = dynamicContentEl.querySelectorAll('.radar-target');
            targets.forEach(tgt => {
              tgt.addEventListener('click', (e) => {
                e.stopPropagation();
                const callsign = tgt.getAttribute('data-callsign');
                const altitude = parseInt(tgt.getAttribute('data-altitude'), 10);
                const speed = parseInt(tgt.getAttribute('data-speed'), 10);
                window.selectFlightTarget(callsign, altitude, speed);
              });
            });
            const rows = dynamicContentEl.querySelectorAll('.radar-flight-row');
            rows.forEach(row => {
              row.addEventListener('click', (e) => {
                e.stopPropagation();
                const callsign = row.getAttribute('data-callsign');
                const altitude = parseInt(row.getAttribute('data-altitude'), 10);
                const speed = parseInt(row.getAttribute('data-speed'), 10);
                window.selectFlightTarget(callsign, altitude, speed);
              });
            });

          } else {
            // Megatech Stocks / Fallback: 3 Main Cards + Trade Flow List
            let html = `<div class="dashboard-grid" style="margin-bottom: 12px;">`;
            const topThree = viewData.metrics.slice(0, 3);
            for (let i = 0; i < 3; i++) {
              const metric = topThree[i];
              html += `
                <div class="dashboard-card">
                  <div class="card-label">${metric ? metric.label : '--'}</div>
                  <div class="card-value" style="color: ${metric && metric.color ? metric.color : '#fff'};">${metric ? metric.value : '--'}</div>
                </div>
              `;
            }
            html += `</div><div class="stocks-ticker-container">`;

            const allMetrics = (customDashboardState && (customDashboardState.activeTabId === 'stk' || customDashboardState.mode === 'stk' || !customDashboardState.activeTabId) && customDashboardState.metrics) ? customDashboardState.metrics : [];
            const extraStocks = allMetrics.length > 0 ? allMetrics : [
              {label: "NVDA (NVIDIA)", value: "$914.85 ▲", color: "#00ff88"},
              {label: "MSFT (Microsoft)", value: "$421.90 ▲", color: "#00f2ff"},
              {label: "GOOG (Alphabet)", value: "$173.50 ▲", color: "#00ff88"},
              {label: "AAPL (Apple)", value: "$189.50 ▲", color: "#00ff88"},
              {label: "AMZN (Amazon)", value: "$180.20 ▼", color: "#ff3b30"},
              {label: "META (Meta)", value: "$475.10 ▲", color: "#00ff88"},
              {label: "TSM (TSMC)", value: "$145.30 ▲", color: "#00ff88"},
              {label: "ANTH (Anthropic)", value: "$32.40 ▲", color: "#00ff88"},
              {label: "MIST (Mistral AI)", value: "$12.80 ▼", color: "#ff3b30"}
            ];

            // Double the list so we have infinite seamless scrolling loop
            const doubleStocks = [...extraStocks, ...extraStocks];
            doubleStocks.forEach(s => {
              html += `
                <div class="stocks-ticker-row">
                  <span style="font-weight:700; color:rgba(255,255,255,0.8);">${s.label}</span>
                  <span style="color:${s.color || '#00f2ff'}; font-weight:700;">${s.value}</span>
                </div>
              `;
            });
            html += `</div>`;
            dynamicContentEl.innerHTML = html;
          }

          // Restore scroll position after HTML replacement
          const newTicker = dynamicContentEl.querySelector('.stocks-ticker-container');
          if (newTicker && savedScrollPos) {
            newTicker.scrollTop = savedScrollPos;
          }
        }
      }

      function resetAutoRotation() {
        if (autoRotationInterval) clearInterval(autoRotationInterval);
        autoRotationInterval = setInterval(() => {
          const modeCycle = activeTabs.map(t => t.id);
          const nextIdx = (modeCycle.indexOf(telemetryMode) + 1) % modeCycle.length;
          telemetryMode = modeCycle[nextIdx];
          chartData = Array(15).fill(telemetryMode === 'stk' ? 40 : telemetryMode === 'ord' ? 60 : 20);
          renderDashboard();
        }, 10000); // cycle every 10 seconds
      }

      resetAutoRotation();
      renderDashboard(); // First paint

      dashboardInterval = setInterval(() => {
        renderDashboard();
      }, 1000);
    }

    function deactivateDashboardTelemetry() {
      if (dashboardInterval) {
        clearInterval(dashboardInterval);
        dashboardInterval = null;
      }
      if (autoRotationInterval) {
        clearInterval(autoRotationInterval);
        autoRotationInterval = null;
      }
    }

    function renderStageImage(base64, panelIdx, layout, label) {
      const pIdx = panelIdx || 1;
      panelSources[pIdx] = { base64, layout, label };

      const wrap = document.getElementById('view-image');
      if (wrap) {
        const currentLayout = layout || 'single';
        wrap.setAttribute('data-image-layout', currentLayout);
        
        // Hide/show panels according to layout
        for (let i = 1; i <= 4; i++) {
          const p = document.getElementById(`image-panel-${i}`);
          if (p) {
            if (currentLayout === 'single' && i === 1) p.classList.remove('hidden');
            else if (currentLayout === 'split' && i <= 2) p.classList.remove('hidden');
            else if (currentLayout === 'grid') p.classList.remove('hidden');
            else if (currentLayout === 'grid-3' && i <= 3) p.classList.remove('hidden');
            else if (currentLayout === 'presentation') p.classList.remove('hidden');
            else p.classList.add('hidden');
          }
        }
      }

      const imgEl = document.getElementById(`stage-image-${pIdx}`);
      const iframeEl = document.getElementById(`stage-panel-iframe-${pIdx}`);
      const dashboardEl = document.getElementById(`stage-dashboard-${pIdx}`);
      const videoEl = document.getElementById(`stage-panel-video-${pIdx}`);

      // Clean up any old error overlays first
      document.getElementById(`image-panel-${pIdx}`)?.querySelectorAll('.camera-error-overlay').forEach(el => el.remove());

      const ytId = youtubeId(base64) || (base64.startsWith('youtube:') ? base64.split(':')[1] : null);

      // Hide all by default for this panel, then selectively display
      if (imgEl) imgEl.classList.add('hidden');
      if (iframeEl) {
        iframeEl.classList.add('hidden');
        const currentSrc = iframeEl.getAttribute('src') || '';
        if (!ytId || !currentSrc.includes(`/embed/${ytId}`)) {
          iframeEl.src = '';
        }
      }
      if (dashboardEl) { dashboardEl.classList.add('hidden'); deactivateDashboardTelemetry(); }
      if (videoEl) {
        videoEl.classList.add('hidden');
        videoEl.src = '';
        if (activeCameraStreams[pIdx]) {
          try {
            if (activeCameraStreams[pIdx]._streamInterval) {
              clearInterval(activeCameraStreams[pIdx]._streamInterval);
            }
            activeCameraStreams[pIdx].getTracks().forEach(track => track.stop());
          } catch(e) {}
          delete activeCameraStreams[pIdx];
          videoEl.srcObject = null;
        }
      }

      if (ytId && iframeEl) {
        const currentSrc = iframeEl.getAttribute('src') || '';
        if (!currentSrc.includes(`/embed/${ytId}`)) {
          const isAutoplay = panelAutoplay[pIdx];
          if (isAutoplay) {
            iframeEl.src = `https://www.youtube.com/embed/${ytId}?autoplay=1&mute=1&controls=0&loop=1&playlist=${ytId}&modestbranding=1&enablejsapi=1`;
            setupYoutubeAutoplay(iframeEl);
          } else {
            iframeEl.src = `https://www.youtube.com/embed/${ytId}?autoplay=0&mute=0&controls=1&loop=1&playlist=${ytId}&modestbranding=1&enablejsapi=1`;
            iframeEl.onload = null;
          }
        }
        iframeEl.classList.remove('hidden');
        updateAutoplayBadge(pIdx);
      } else {
        const existingBadge = document.getElementById(`image-panel-${pIdx}`)?.querySelector('.autoplay-badge');
        if (existingBadge) existingBadge.remove();

        const isDirectVideo = (base64.startsWith('http://') || base64.startsWith('https://') || base64.startsWith('/')) && 
                              (base64.includes('.mp4') || base64.includes('.webm') || base64.includes('.ogg') || base64.includes('.mov'));

        if (base64 === 'camera' && videoEl) {
          videoEl.classList.remove('hidden');
          navigator.mediaDevices.getUserMedia({ video: true, audio: false })
            .then(stream => {
              activeCameraStreams[pIdx] = stream;
              videoEl.srcObject = stream;
              videoEl.play().catch(e => console.warn('[stage] video play failed:', e));

              // Start streaming frames over the WebSocket
              const canvas = document.createElement('canvas');
              const ctx = canvas.getContext('2d');
              const intervalId = setInterval(() => {
                if (!activeCameraStreams[pIdx] || videoEl.paused || videoEl.ended) {
                  clearInterval(intervalId);
                  return;
                }
                // Only capture if stageWS is open
                if (stageWS && stageWS.readyState === WebSocket.OPEN) {
                  canvas.width = videoEl.videoWidth || 640;
                  canvas.height = videoEl.videoHeight || 480;
                  ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);
                  const dataUrl = canvas.toDataURL('image/jpeg', 0.4);
                  stageWS.send(JSON.stringify({
                    type: 'stage_camera_frame',
                    panel: pIdx,
                    data: dataUrl
                  }));
                }
              }, 100); // 10 FPS
              activeCameraStreams[pIdx]._streamInterval = intervalId;
            })
            .catch(err => {
              console.error('[stage] camera stream failed:', err);
              // Render gorgeous production fallback alert overlay
              const errorOverlay = document.createElement('div');
              errorOverlay.className = 'camera-error-overlay';
              errorOverlay.innerHTML = `
                <div style="text-align:center; padding: 24px; color:#ff0055; background: rgba(15, 15, 20, 0.85); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border: 1px solid rgba(255, 0, 85, 0.2); border-radius: 12px; max-width: 80%; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);">
                  <span style="font-size:32px; display:block; margin-bottom:10px; filter: drop-shadow(0 0 8px rgba(255, 0, 85, 0.5));">🎥</span>
                  <div style="font-weight:700; font-size:13px; text-transform:uppercase; letter-spacing:1px; margin-bottom:6px; color:#fff; text-shadow: 0 0 10px rgba(255,0,85,0.4);">Feed Blocked</div>
                  <div style="font-size:11px; color:rgba(255,255,255,0.65); line-height:1.5;">Webcam already active in Google Meet<br/>or system permission was denied.</div>
                </div>
              `;
              errorOverlay.style.position = 'absolute';
              errorOverlay.style.top = '0';
              errorOverlay.style.left = '0';
              errorOverlay.style.width = '100%';
              errorOverlay.style.height = '100%';
              errorOverlay.style.display = 'flex';
              errorOverlay.style.alignItems = 'center';
              errorOverlay.style.justifyContent = 'center';
              errorOverlay.style.zIndex = '10';
              document.getElementById(`image-panel-${pIdx}`).appendChild(errorOverlay);
            });
        } else if (isDirectVideo && videoEl) {
          videoEl.classList.remove('hidden');
          videoEl.src = base64;
          videoEl.loop = true;
          videoEl.muted = true;
          videoEl.play().catch(e => console.warn('[stage] direct video play failed:', e));
        } else if (base64 === 'clear_camera') {
          if (imgEl) {
            imgEl.classList.remove('hidden');
            imgEl.src = '';
          }
        } else if (base64 === 'dashboard' && dashboardEl) {
          dashboardEl.classList.remove('hidden');
          activateDashboardTelemetry();
        } else if (imgEl) {
          imgEl.classList.remove('hidden');
          imgEl.classList.remove('loaded');
          imgEl.onload = () => imgEl.classList.add('loaded');
          if (base64.startsWith('http://') || base64.startsWith('https://') || base64.startsWith('/') || base64.startsWith('data:')) {
            imgEl.src = base64;
          } else if (base64 && base64.trim().length > 0) {
            imgEl.src = 'data:image/jpeg;base64,' + base64;
          }
        }
      }

      const labelEl = document.getElementById(`image-label-${pIdx}`);
      if (labelEl) {
        if (label) {
          labelEl.textContent = label;
          labelEl.classList.remove('hidden');
        } else {
          labelEl.classList.add('hidden');
        }
      }
    }

    function setFocusedPanel(panelIdx, preventBroadcast = false) {
      for (let i = 1; i <= 4; i++) {
        const p = document.getElementById(`image-panel-${i}`);
        if (p) {
          if (panelIdx && i === parseInt(panelIdx)) {
            p.classList.add('focused');
          } else {
            p.classList.remove('focused');
          }
        }
      }
      // Sync back to sidepanel/server if needed, unless preventBroadcast is true
      if (!preventBroadcast && stageWS && stageWS.readyState === WebSocket.OPEN) {
        stageWS.send(JSON.stringify({
          type: 'focus_panel',
          panel: panelIdx
        }));
      }
    }

    function launchEmoji(emoji) {
      const layer = document.getElementById('emoji-layer');
      if (!layer) return;
      const count = Math.floor(Math.random() * 3) + 2;
      for (let i = 0; i < count; i++) {
        setTimeout(() => {
          const el = document.createElement('div');
          el.className = 'emoji-float';
          el.textContent = emoji;
          el.style.left = (10 + Math.random() * 80) + '%';
          el.style.animationDelay = (Math.random() * 0.4) + 's';
          layer.appendChild(el);
          el.addEventListener('animationend', () => el.remove());
        }, i * 120);
      }
    }

    function displayChatComment(sender, text, avatar) {
      const overlay = document.getElementById('stage-chat-overlay');
      if (!overlay) return;

      const card = document.createElement('div');
      card.className = 'stage-chat-card';

      const avatarEl = document.createElement('div');
      avatarEl.className = 'stage-chat-card-avatar';
      if (avatar && (avatar.startsWith('http') || avatar.startsWith('/'))) {
        const img = document.createElement('img');
        img.src = avatar;
        img.alt = sender;
        avatarEl.appendChild(img);
      } else {
        avatarEl.textContent = (sender || 'U').charAt(0).toUpperCase();
      }

      const contentEl = document.createElement('div');
      contentEl.className = 'stage-chat-card-content';

      const senderEl = document.createElement('div');
      senderEl.className = 'stage-chat-card-sender';
      senderEl.textContent = sender || 'Anonymous';

      const textEl = document.createElement('div');
      textEl.className = 'stage-chat-card-text';
      textEl.textContent = text || '';

      contentEl.appendChild(senderEl);
      contentEl.appendChild(textEl);

      card.appendChild(avatarEl);
      card.appendChild(contentEl);

      overlay.appendChild(card);

      // Keep only last 4 visible comments
      while (overlay.children.length > 4) {
        overlay.children[0].remove();
      }

      // Cleanup lifecycle after 6 seconds
      setTimeout(() => {
        card.classList.add('fade-out');
        const handleRemoval = () => {
          card.removeEventListener('animationend', handleRemoval);
          card.remove();
        };
        card.addEventListener('animationend', handleRemoval);
        // Safety fallback in case transition/animation doesn't fire
        setTimeout(() => card.remove(), 1000);
      }, 6000);
    }

    audioCtx = new (window.AudioContext || window.webkitAudioContext)();

    // Activate button — unlocks AudioContext and hides itself on first click
    const activateBtn = document.getElementById('audio-activate');
    if (activateBtn) {
      activateBtn.addEventListener('click', () => {
        audioCtx.resume();
        activateBtn.style.display = 'none';
      }, { once: true });
    }

    // Studio Activation Modal button bindings
    const studioModal = document.getElementById('stage-activation-modal');
    const modalUnlockAudio = document.getElementById('modal-unlock-audio');
    const modalUnlockCamera = document.getElementById('modal-unlock-camera');
    const modalClose = document.getElementById('modal-close');

    if (modalUnlockAudio) {
      modalUnlockAudio.addEventListener('click', () => {
        audioCtx.resume().then(() => {
          modalUnlockAudio.textContent = '🔊 Audio Engine Active ✓';
          modalUnlockAudio.style.background = 'rgba(76, 175, 80, 0.15)';
          modalUnlockAudio.style.borderColor = '#4caf50';
          modalUnlockAudio.style.color = '#4caf50';
          // Also hide standard audio-activate button if visible
          const actBtn = document.getElementById('audio-activate');
          if (actBtn) actBtn.style.display = 'none';
        });
      });
    }

    if (modalUnlockCamera) {
      modalUnlockCamera.addEventListener('click', () => {
        navigator.mediaDevices.getUserMedia({ video: true, audio: false })
          .then(stream => {
            modalUnlockCamera.textContent = '📷 Camera Access Granted ✓';
            modalUnlockCamera.style.background = 'rgba(76, 175, 80, 0.15)';
            modalUnlockCamera.style.borderColor = '#4caf50';
            modalUnlockCamera.style.color = '#4caf50';
            // Stop the temporary stream tracks immediately
            stream.getTracks().forEach(track => track.stop());
          })
          .catch(err => {
            console.error('[stage] modal camera permission failed:', err);
            modalUnlockCamera.textContent = '❌ Access Denied / Blocked';
            modalUnlockCamera.style.background = 'rgba(244, 67, 54, 0.15)';
            modalUnlockCamera.style.borderColor = '#f44336';
            modalUnlockCamera.style.color = '#f44336';
          });
      });
    }

    if (modalClose) {
      modalClose.addEventListener('click', () => {
        if (studioModal) studioModal.classList.add('hidden');
      });
    }

    function resumeAudio() {
      if (audioCtx.state === 'suspended') audioCtx.resume();
    }
    document.addEventListener('click', resumeAudio);
    document.addEventListener('keydown', resumeAudio);

    async function playAudioChunk(base64wav) {
      try {
        if (audioCtx.state === 'suspended') await audioCtx.resume();
        const bytes = Uint8Array.from(atob(base64wav), c => c.charCodeAt(0));
        const buffer = await audioCtx.decodeAudioData(bytes.buffer);
        const src = audioCtx.createBufferSource();
        src.buffer = buffer;
        src.connect(audioCtx.destination);
        src.start();
      } catch (e) { console.warn('[stage] audio play error', e); }
    }

    function updateTerminal(data, append) {
      const term = document.getElementById('terminal-body');
      if (!term) return;
      if (append) {
        term.textContent += data;
      } else {
        term.textContent = data;
      }
      term.scrollTop = term.scrollHeight;
    }

    function triggerSoundEffect(sound) {
      if (audioCtx.state === 'suspended') audioCtx.resume();
      const now = audioCtx.currentTime;
      
      function getNoiseBuffer() {
        const bufferSize = audioCtx.sampleRate * 2;
        const buffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
        const data = buffer.getChannelData(0);
        for (let i = 0; i < bufferSize; i++) {
          data[i] = Math.random() * 2 - 1;
        }
        return buffer;
      }

      if (sound === 'applause') {
        const noise = audioCtx.createBufferSource();
        noise.buffer = getNoiseBuffer();
        const filter = audioCtx.createBiquadFilter();
        filter.type = 'bandpass';
        filter.frequency.value = 1000;
        filter.Q.value = 1.0;
        
        const tremolo = audioCtx.createGain();
        tremolo.gain.value = 0.8;
        const osc = audioCtx.createOscillator();
        osc.frequency.value = 15;
        const oscGain = audioCtx.createGain();
        oscGain.gain.value = 0.3;
        
        const mainGain = audioCtx.createGain();
        mainGain.gain.setValueAtTime(0, now);
        mainGain.gain.linearRampToValueAtTime(0.8, now + 0.5);
        mainGain.gain.exponentialRampToValueAtTime(0.001, now + 4.0);
        
        osc.connect(oscGain);
        oscGain.connect(tremolo.gain);
        noise.connect(filter);
        filter.connect(tremolo);
        tremolo.connect(mainGain);
        mainGain.connect(audioCtx.destination);
        
        osc.start(now);
        noise.start(now);
        osc.stop(now + 4.0);
        noise.stop(now + 4.0);
        
      } else if (sound === 'drumroll') {
        const noise = audioCtx.createBufferSource();
        noise.buffer = getNoiseBuffer();
        const filter = audioCtx.createBiquadFilter();
        filter.type = 'bandpass';
        filter.frequency.value = 180;
        
        const tremolo = audioCtx.createGain();
        const osc = audioCtx.createOscillator();
        osc.frequency.value = 18;
        const oscGain = audioCtx.createGain();
        oscGain.gain.value = 0.6;
        
        const mainGain = audioCtx.createGain();
        mainGain.gain.setValueAtTime(0, now);
        mainGain.gain.linearRampToValueAtTime(0.5, now + 0.1);
        mainGain.gain.setValueAtTime(0.5, now + 2.0);
        mainGain.gain.exponentialRampToValueAtTime(0.001, now + 2.1);
        
        osc.connect(oscGain);
        oscGain.connect(tremolo.gain);
        noise.connect(filter);
        filter.connect(tremolo);
        tremolo.connect(mainGain);
        mainGain.connect(audioCtx.destination);
        
        osc.start(now);
        noise.start(now);
        osc.stop(now + 2.1);
        noise.stop(now + 2.1);
        
        setTimeout(() => {
          const crashNow = audioCtx.currentTime;
          const cymbal = audioCtx.createBufferSource();
          cymbal.buffer = getNoiseBuffer();
          const cymbalFilter = audioCtx.createBiquadFilter();
          cymbalFilter.type = 'highpass';
          cymbalFilter.frequency.value = 8000;
          
          const cymbalGain = audioCtx.createGain();
          cymbalGain.gain.setValueAtTime(1.0, crashNow);
          cymbalGain.gain.exponentialRampToValueAtTime(0.001, crashNow + 1.5);
          
          cymbal.connect(cymbalFilter);
          cymbalFilter.connect(cymbalGain);
          cymbalGain.connect(audioCtx.destination);
          cymbal.start(crashNow);
          cymbal.stop(crashNow + 1.5);
        }, 2000);
        
      } else if (sound === 'buzzer') {
        const osc1 = audioCtx.createOscillator();
        const osc2 = audioCtx.createOscillator();
        osc1.type = 'sawtooth';
        osc2.type = 'sawtooth';
        osc1.frequency.value = 110;
        osc2.frequency.value = 111.5;
        
        const filter = audioCtx.createBiquadFilter();
        filter.type = 'lowpass';
        filter.frequency.value = 800;
        
        const mainGain = audioCtx.createGain();
        mainGain.gain.setValueAtTime(0.6, now);
        mainGain.gain.setValueAtTime(0.6, now + 0.8);
        mainGain.gain.exponentialRampToValueAtTime(0.001, now + 1.0);
        
        osc1.connect(filter);
        osc2.connect(filter);
        filter.connect(mainGain);
        mainGain.connect(audioCtx.destination);
        
        osc1.start(now);
        osc2.start(now);
        osc1.stop(now + 1.0);
        osc2.stop(now + 1.0);
        
      } else if (sound === 'chimes' || sound === 'ding') {
        const freqs = [523.25, 659.25, 783.99, 1046.50];
        freqs.forEach((freq, idx) => {
          const t = now + idx * 0.15;
          const osc = audioCtx.createOscillator();
          osc.type = 'sine';
          osc.frequency.value = freq;
          
          const gain = audioCtx.createGain();
          gain.gain.setValueAtTime(0, t);
          gain.gain.linearRampToValueAtTime(0.4, t + 0.02);
          gain.gain.exponentialRampToValueAtTime(0.001, t + 1.0);
          
          osc.connect(gain);
          gain.connect(audioCtx.destination);
          osc.start(t);
          osc.stop(t + 1.0);
        });
      }
    }

    let pointerHistory = [];
    let isDrawingTrail = false;

    function drawPointerTrail() {
      if (!ctx || !canvas) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      pointerHistory = pointerHistory.filter(pt => {
        pt.age += 16;
        return pt.age < 1500;
      });

      if (pointerHistory.length > 1) {
        ctx.shadowBlur = 15;
        ctx.shadowColor = '#ff003c';
        ctx.lineWidth = 4;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        for (let i = 1; i < pointerHistory.length; i++) {
          const pt1 = pointerHistory[i - 1];
          const pt2 = pointerHistory[i];
          const alpha = Math.max(0, 1 - (pt2.age / 1500));
          ctx.strokeStyle = `rgba(255, 0, 60, ${alpha * 0.8})`;

          ctx.beginPath();
          ctx.moveTo((pt1.x / 100) * canvas.width, (pt1.y / 100) * canvas.height);
          ctx.lineTo((pt2.x / 100) * canvas.width, (pt2.y / 100) * canvas.height);
          ctx.stroke();
        }
        ctx.shadowBlur = 0;
      }

      if (pointerHistory.length > 0) {
        requestAnimationFrame(drawPointerTrail);
      } else {
        isDrawingTrail = false;
      }
    }

    function redrawPollUI() {
      let currentVal1 = lastVal1;
      let currentVal2 = lastVal2;
      let currentVal3 = lastVal3;
      let currentVal4 = lastVal4;
      
      // Apply local user vote offset (gives a huge premium boost to their selected option!)
      if (userVotedOption === 1) currentVal1 += 25;
      else if (userVotedOption === 2) currentVal2 += 25;
      else if (userVotedOption === 3) currentVal3 += 25;
      else if (userVotedOption === 4) currentVal4 += 25;
      
      // Recalculate percentages
      let total = currentVal1 + currentVal2;
      if (hasOpt3) total += currentVal3;
      if (hasOpt4) total += currentVal4;
      if (total === 0) total = 100;
      
      let pct1 = Math.round((currentVal1 / total) * 100);
      let pct2 = Math.round((currentVal2 / total) * 100);
      let pct3 = hasOpt3 ? Math.round((currentVal3 / total) * 100) : 0;
      let pct4 = hasOpt4 ? Math.round((currentVal4 / total) * 100) : 0;
      
      // Normalize to sum up to 100%
      let sum = pct1 + pct2 + pct3 + pct4;
      if (sum !== 100 && sum > 0) {
        let maxVal = Math.max(pct1, pct2, pct3, pct4);
        let diff = 100 - sum;
        if (maxVal === pct1) pct1 += diff;
        else if (maxVal === pct2) pct2 += diff;
        else if (maxVal === pct3) pct3 += diff;
        else if (maxVal === pct4) pct4 += diff;
      }

      const b1 = document.getElementById('poll-bar-1');
      const b2 = document.getElementById('poll-bar-2');
      const b3 = document.getElementById('poll-bar-3');
      const b4 = document.getElementById('poll-bar-4');
      const p1 = document.getElementById('poll-percent-1');
      const p2 = document.getElementById('poll-percent-2');
      const p3 = document.getElementById('poll-percent-3');
      const p4 = document.getElementById('poll-percent-4');
      
      if (b1) b1.style.width = `${pct1}%`;
      if (b2) b2.style.width = `${pct2}%`;
      if (b3) b3.style.width = `${pct3}%`;
      if (b4) b4.style.width = `${pct4}%`;
      
      if (p1) p1.textContent = `${pct1}%`;
      if (p2) p2.textContent = `${pct2}%`;
      if (p3) p3.textContent = `${pct3}%`;
      if (p4) p4.textContent = `${pct4}%`;
      
      // Highlight the voted option row
      const r1 = document.getElementById('poll-opt-row-1');
      const r2 = document.getElementById('poll-opt-row-2');
      const r3 = document.getElementById('poll-opt-row-3');
      const r4 = document.getElementById('poll-opt-row-4');
      if (r1) r1.classList.remove('voted');
      if (r2) r2.classList.remove('voted');
      if (r3) r3.classList.remove('voted');
      if (r4) r4.classList.remove('voted');
      
      if (userVotedOption === 1 && r1) r1.classList.add('voted');
      if (userVotedOption === 2 && r2) r2.classList.add('voted');
      if (userVotedOption === 3 && r3) r3.classList.add('voted');
      if (userVotedOption === 4 && r4) r4.classList.add('voted');
    }

    function castVote(optionIdx) {
      if (userVotedOption !== null) return; // Only allow one vote
      userVotedOption = optionIdx;
      
      // Play a delightful synth sound for voting feedback
      try {
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.frequency.setValueAtTime(523.25, audioCtx.currentTime); // C5
        osc.frequency.exponentialRampToValueAtTime(783.99, audioCtx.currentTime + 0.15); // G5
        gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.2);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.2);
      } catch (e) {}
      
      redrawPollUI();
    }

    // Attach click handlers on initial document ready/DOMContentLoaded
    document.addEventListener('DOMContentLoaded', () => {
      const r1 = document.getElementById('poll-opt-row-1');
      const r2 = document.getElementById('poll-opt-row-2');
      const r3 = document.getElementById('poll-opt-row-3');
      const r4 = document.getElementById('poll-opt-row-4');
      if (r1) r1.addEventListener('click', () => castVote(1));
      if (r2) r2.addEventListener('click', () => castVote(2));
      if (r3) r3.addEventListener('click', () => castVote(3));
      if (r4) r4.addEventListener('click', () => castVote(4));

      // Click listeners for direct main stage focusing:
      for (let i = 1; i <= 4; i++) {
        const p = document.getElementById(`image-panel-${i}`);
        if (p) {
          if (!p._clickBound) {
            p._clickBound = true;
            p.addEventListener('click', () => {
              setFocusedPanel(i);
            });
          }
        }
      }
    });
    // Just in case DOMContentLoaded has already fired, bind immediately too
    const r1 = document.getElementById('poll-opt-row-1');
    const r2 = document.getElementById('poll-opt-row-2');
    const r3 = document.getElementById('poll-opt-row-3');
    const r4 = document.getElementById('poll-opt-row-4');
    if (r1) r1.addEventListener('click', () => castVote(1));
    if (r2) r2.addEventListener('click', () => castVote(2));
    if (r3) r3.addEventListener('click', () => castVote(3));
    if (r4) r4.addEventListener('click', () => castVote(4));

    for (let i = 1; i <= 4; i++) {
      const p = document.getElementById(`image-panel-${i}`);
      if (p) {
        if (!p._clickBound) {
          p._clickBound = true;
          p.addEventListener('click', () => {
            setFocusedPanel(i);
          });
        }
      }
    }

    let stageWS = null;

    function handleStageMessage(msg) {
      if (!msg) return;
      try {
        if (msg.type === 'transcript') {
          updateTranscript(msg);
        } else if (msg.type === 'chat_comment') {
          displayChatComment(msg.sender, msg.text, msg.avatar);
        } else if (msg.type === 'emoji_reaction' || msg.type === 'emoji_event') {
          launchEmoji(msg.emoji || '👏');
        } else if (msg.type === 'layout_event') {
          const layer = document.getElementById('content-layer');
          if (layer) {
            layer.setAttribute('data-layout', msg.layout || 'single');
          }
          const wrap = document.getElementById('view-image');
          if (wrap) {
            const targetLayout = msg.layout || 'single';
            wrap.setAttribute('data-image-layout', targetLayout);
            for (let i = 1; i <= 4; i++) {
              const p = document.getElementById(`image-panel-${i}`);
              if (p) {
                if (targetLayout === 'single' && i === 1) p.classList.remove('hidden');
                else if (targetLayout === 'split' && i <= 2) p.classList.remove('hidden');
                else if (targetLayout === 'grid') p.classList.remove('hidden');
                else if (targetLayout === 'grid-3' && i <= 3) p.classList.remove('hidden');
                else if (targetLayout === 'presentation') p.classList.remove('hidden');
                else p.classList.add('hidden');
              }
            }
          }
        } else if (msg.type === 'poll_event') {
          const widget = document.getElementById('stage-poll-widget');
          if (widget) {
            if (msg.active) {
              if (msg.question) document.getElementById('poll-question-text').textContent = msg.question;
              
              const opt1 = msg.opt1 || (msg.options && msg.options[0]) || '';
              const opt2 = msg.opt2 || (msg.options && msg.options[1]) || '';
              const opt3 = msg.opt3 || (msg.options && msg.options[2]) || '';
              const opt4 = msg.opt4 || (msg.options && msg.options[3]) || '';

              if (opt1) document.getElementById('poll-opt-label-1').textContent = opt1;
              if (opt2) document.getElementById('poll-opt-label-2').textContent = opt2;
              
              const r3 = document.getElementById('poll-opt-row-3');
              if (opt3) {
                document.getElementById('poll-opt-label-3').textContent = opt3;
                if (r3) r3.classList.remove('hidden');
                hasOpt3 = true;
              } else {
                if (r3) r3.classList.add('hidden');
                hasOpt3 = false;
              }
              
              const r4 = document.getElementById('poll-opt-row-4');
              if (opt4) {
                document.getElementById('poll-opt-label-4').textContent = opt4;
                if (r4) r4.classList.remove('hidden');
                hasOpt4 = true;
              } else {
                if (r4) r4.classList.add('hidden');
                hasOpt4 = false;
              }

              lastVal1 = msg.val1 !== undefined ? msg.val1 : (msg.values && msg.values[0] !== undefined ? msg.values[0] : 0);
              lastVal2 = msg.val2 !== undefined ? msg.val2 : (msg.values && msg.values[1] !== undefined ? msg.values[1] : 0);
              lastVal3 = msg.val3 !== undefined ? msg.val3 : (msg.values && msg.values[2] !== undefined ? msg.values[2] : 0);
              lastVal4 = msg.val4 !== undefined ? msg.val4 : (msg.values && msg.values[3] !== undefined ? msg.values[3] : 0);
              
              redrawPollUI();
              
              widget.classList.remove('hidden');
            } else {
              widget.classList.add('hidden');
              userVotedOption = null; // Reset user vote when poll closes/resets
            }
          }
        } else if (msg.type === 'studio_mode_event') {
          const modal = document.getElementById('stage-activation-modal');
          if (modal) {
            if (msg.active) {
              modal.classList.remove('hidden');
            } else {
              modal.classList.add('hidden');
            }
          }
        } else if (msg.type === 'stage_camera_frame') {
          const imgEl = document.getElementById(`stage-image-${msg.panel}`);
          if (imgEl) {
            imgEl.src = msg.data;
            imgEl.classList.remove('hidden');
            // Hide the local webcam video on this slot if there is one to allow the frame stream to be visible
            const localVideoEl = document.getElementById(`stage-panel-video-${msg.panel}`);
            if (localVideoEl) localVideoEl.classList.add('hidden');
          }
        } else if (msg.type === 'theme_event') {
          document.documentElement.className = `theme-${msg.theme || 'darkflow'}`;
        } else if (msg.type === 'dashboard_event') {
          customDashboardState = msg;
          telemetryMode = msg.activeTabId || msg.mode || 'stk';
          if (msg.tabs && Array.isArray(msg.tabs)) {
            activeTabs = msg.tabs;
          }
          if (autoRotationInterval) {
            clearInterval(autoRotationInterval);
            autoRotationInterval = null;
          }
          renderDashboard();
        } else if (msg.type === 'pointer_event') {
          const dot = document.getElementById('laser-pointer-dot');
          if (dot) {
            if (msg.active !== false) {
              const xVal = parseFloat(msg.x);
              const yVal = parseFloat(msg.y);
              dot.style.left = `${xVal}%`;
              dot.style.top = `${yVal}%`;
              dot.classList.add('active');

              // Add to laser tracing trail
              pointerHistory.push({ x: xVal, y: yVal, age: 0 });
              if (!isDrawingTrail) {
                isDrawingTrail = true;
                requestAnimationFrame(drawPointerTrail);
              }

              if (dot.laserTimeout) clearTimeout(dot.laserTimeout);
              dot.laserTimeout = setTimeout(() => dot.classList.remove('active'), 2000);
            } else {
              dot.classList.remove('active');
            }
          }
        } else if (msg.type === 'draw_event') {
          if (ctx && canvas) {
            if (msg.action === 'clear') {
              ctx.clearRect(0, 0, canvas.width, canvas.height);
            } else if (msg.action === 'line') {
              ctx.beginPath();
              ctx.strokeStyle = msg.color || '#ff003c';
              ctx.lineWidth = msg.lineWidth || 3;
              ctx.lineCap = 'round';
              const x1 = (msg.x1 / 100) * canvas.width;
              const y1 = (msg.y1 / 100) * canvas.height;
              const x2 = (msg.x2 / 100) * canvas.width;
              const y2 = (msg.y2 / 100) * canvas.height;
              ctx.moveTo(x1, y1);
              ctx.lineTo(x2, y2);
              ctx.stroke();
            } else if (msg.action === 'rect') {
              ctx.beginPath();
              ctx.strokeStyle = msg.color || '#ff003c';
              ctx.lineWidth = msg.lineWidth || 3;
              const x = (msg.x / 100) * canvas.width;
              const y = (msg.y / 100) * canvas.height;
              const w = (msg.w / 100) * canvas.width;
              const h = (msg.h / 100) * canvas.height;
              ctx.strokeRect(x, y, w, h);
            } else if (msg.action === 'text') {
              ctx.font = msg.font || '20px "Courier New"';
              ctx.fillStyle = msg.color || '#ff003c';
              const x = (msg.x / 100) * canvas.width;
              const y = (msg.y / 100) * canvas.height;
              ctx.fillText(msg.text || '', x, y);
            }
          }
        } else if (msg.type === 'notepad_event') {
          const bodyEl = document.getElementById('notepad-body');
          if (bodyEl) {
            const isFocused = document.activeElement === bodyEl;
            let start = 0, end = 0;
            if (isFocused) {
              start = bodyEl.selectionStart;
              end = bodyEl.selectionEnd;
            }
            
            const newText = msg.text || '';
            if (msg.action === 'overwrite') {
              bodyEl.value = newText;
            } else if (msg.action === 'append') {
              bodyEl.value += newText;
            }
            
            if (isFocused) {
              bodyEl.setSelectionRange(start, end);
            }
          }
        } else if (msg.type === 'theme_change') {
          console.log('[stage] Applying theme change...');
          Object.entries(msg.tokens).forEach(([k, v]) => {
            document.documentElement.style.setProperty(k, v);
          });
        } else if (msg.type === 'audio') {
          if (msg.data) playAudioChunk(msg.data);
        } else if (msg.type === 'sound_event') {
          if (msg.sound) triggerSoundEffect(msg.sound);
        } else if (msg.type === 'chyron_event') {
          const chyron = document.getElementById('stage-chyron');
          if (chyron) {
            if (msg.active) {
              document.getElementById('chyron-title').textContent = msg.title || '';
              document.getElementById('chyron-sub').textContent = msg.subtitle || '';
              chyron.classList.remove('hidden');
            } else {
              chyron.classList.add('hidden');
            }
          }
        } else if (msg.type === 'ticker_event') {
          const ticker = document.getElementById('stage-ticker');
          if (ticker) {
            if (msg.active) {
              document.getElementById('ticker-content').textContent = msg.text || '';
              ticker.classList.remove('hidden');
            } else {
              ticker.classList.add('hidden');
            }
          }
        } else if (msg.type === 'standby_event') {
          const standby = document.getElementById('stage-standby');
          if (standby) {
            if (msg.active) {
              // Update customizable texts
              const badgeEl = document.getElementById('standby-badge');
              const titleEl = document.getElementById('standby-title');
              const subtitleEl = document.getElementById('standby-subtitle');
              
              if (badgeEl && msg.badge !== undefined) badgeEl.textContent = msg.badge;
              if (titleEl && msg.title !== undefined) titleEl.textContent = msg.title;
              if (subtitleEl && msg.description !== undefined) subtitleEl.textContent = msg.description;

              standby.classList.remove('hidden');
              
              // Clear any running interval first
              if (standbyInterval) clearInterval(standbyInterval);
              
              let secondsLeft = (parseInt(msg.duration) || 0) * 60 + (parseInt(msg.seconds) || 0);
              if (secondsLeft <= 0) secondsLeft = 300; // fallback to 5 minutes
              
              const displayEl = document.getElementById('standby-timer-display');
              
              const updateDisplay = () => {
                const mm = String(Math.floor(secondsLeft / 60)).padStart(2, '0');
                const ss = String(secondsLeft % 60).padStart(2, '0');
                if (displayEl) displayEl.textContent = `${mm}:${ss}`;
              };
              
              updateDisplay();
              standbyInterval = setInterval(() => {
                if (secondsLeft > 0) {
                  secondsLeft--;
                  updateDisplay();
                } else {
                  clearInterval(standbyInterval);
                  standbyInterval = null;
                }
              }, 1000);
              } else {
                standby.classList.add('hidden');
                if (standbyInterval) {
                  clearInterval(standbyInterval);
                  standbyInterval = null;
                }
              }
            }
          } else if (msg.type === 'browser_frame') {
            const frameImg = document.getElementById('browser-frame');
            if (frameImg) frameImg.src = msg.data;
          } else if (msg.type === 'focus_panel') {
            // Optional layout switch (e.g. stretch a panel to 'presentation' then revert
            // to 'grid') WITHOUT clearing panel content — keeps the live dashboard intact.
            if (msg.layout) {
              const wrap = document.getElementById('view-image');
              if (wrap) {
                const targetLayout = msg.layout;
                wrap.setAttribute('data-image-layout', targetLayout);
                for (let i = 1; i <= 4; i++) {
                  const p = document.getElementById(`image-panel-${i}`);
                  if (!p) continue;
                  if (targetLayout === 'single' && i === 1) p.classList.remove('hidden');
                  else if (targetLayout === 'split' && i <= 2) p.classList.remove('hidden');
                  else if (targetLayout === 'grid') p.classList.remove('hidden');
                  else if (targetLayout === 'grid-3' && i <= 3) p.classList.remove('hidden');
                  else if (targetLayout === 'presentation') p.classList.remove('hidden');
                  else p.classList.add('hidden');
                }
              }
            }
            setFocusedPanel(msg.panel);
          } else if (msg.type === 'clear_mainstage') {
            // Revert stage to black background with one focused panel
            for (let i = 1; i <= 4; i++) {
              panelSources[i] = null;
              const imgEl = document.getElementById(`stage-image-${i}`);
              if (imgEl) {
                imgEl.removeAttribute('src');
                imgEl.classList.add('hidden');
              }
              const iframeEl = document.getElementById(`stage-panel-iframe-${i}`);
              if (iframeEl) {
                iframeEl.removeAttribute('src');
                iframeEl.classList.add('hidden');
              }
              const videoEl = document.getElementById(`stage-panel-video-${i}`);
              if (videoEl) {
                videoEl.classList.add('hidden');
                videoEl.src = '';
                if (activeCameraStreams[i]) {
                  try {
                    activeCameraStreams[i].getTracks().forEach(track => track.stop());
                  } catch(e){}
                  delete activeCameraStreams[i];
                }
                videoEl.srcObject = null;
              }
              const dashboardEl = document.getElementById(`stage-dashboard-${i}`);
              if (dashboardEl) {
                dashboardEl.classList.add('hidden');
              }
            }
            deactivateDashboardTelemetry();
            const wrap = document.getElementById('view-image');
            if (wrap) {
              const targetLayout = msg.layout || 'grid-3';
              wrap.setAttribute('data-image-layout', targetLayout);
              for (let i = 1; i <= 4; i++) {
                const p = document.getElementById(`image-panel-${i}`);
                if (p) {
                  if (targetLayout === 'single' && i === 1) p.classList.remove('hidden');
                  else if (targetLayout === 'split' && i <= 2) p.classList.remove('hidden');
                  else if (targetLayout === 'grid') p.classList.remove('hidden');
                  else if (targetLayout === 'grid-3' && i <= 3) p.classList.remove('hidden');
                  else if (targetLayout === 'presentation') p.classList.remove('hidden');
                  else p.classList.add('hidden');
                }
              }
            }
            setView('image');
            setFocusedPanel(msg.focus_panel || 1, true);
          } else if (msg.type === 'view_change') {
            if (msg.mode === 'diagram') {
              if (diagramId !== msg.diag_id) {
                diagramId = msg.diag_id;
                knownVersion = 0;
                if (!msg.svg) showDiagramPlaceholder();
              }
              if (msg.svg) {
                renderInlineSVG(msg.svg);
                knownVersion = msg.version;
              }
            }
            if (msg.mode === 'image' && msg.imageData) {
              if (msg.autoplay !== undefined) {
                panelAutoplay[msg.panel || 1] = !!msg.autoplay;
              }
              renderStageImage(msg.imageData, msg.panel, msg.imageLayout, msg.label);
            }
            if (msg.mode === 'video' && msg.url) {
              if (msg.autoplay !== undefined) {
                panelAutoplay['video'] = !!msg.autoplay;
              }
              playVideo(msg.url);
            }
            if (msg.mode === 'terminal' && msg.terminal_data !== undefined) {
              setView('terminal');
              updateTerminal(msg.terminal_data, msg.append);
            }
            setView(msg.mode);
            if (msg.mode === 'doc') {
              document.getElementById('doc-link').href = msg.url || '#';
              document.getElementById('doc-title').textContent = msg.label || 'Document Ready';
              const previewEl = document.getElementById('doc-preview');
              if (previewEl) {
                if (msg.htmlContent) {
                  previewEl.innerHTML = DOMPurify.sanitize(msg.htmlContent);
                  previewEl.classList.remove('hidden');
                } else if (msg.content) {
                  previewEl.textContent = msg.content;
                  previewEl.classList.remove('hidden');
                }
              }
            }
          }
      } catch (err) {
        console.error('[stage-dispatcher] Error processing event:', err);
      }
    }

    function connectStageWS() {
      if (!meetingId) return;
      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      const ws = new WebSocket(`${proto}://${location.host}/ws/stage?meeting_id=${encodeURIComponent(meetingId)}&ticket=${encodeURIComponent(ticket)}`);
      stageWS = ws;
      
      ws.onopen = () => console.log('[stage] Caption broadcast connected');
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          handleStageMessage(msg);
        } catch (err) {}
      };
      ws.onclose = () => setTimeout(connectStageWS, 3000);
      ws.onerror = () => ws.close();
    }

    // Initialize
    if (params.get('doc')) {
      setView('doc');
      document.getElementById('doc-link').href = params.get('doc');
      document.getElementById('doc-title').textContent = params.get('label') || 'Document Ready';
      const previewEl = document.getElementById('doc-preview');
      if (previewEl) {
        const htmlContent = params.get('htmlContent');
        const content = params.get('content');
        if (htmlContent) {
          previewEl.innerHTML = DOMPurify.sanitize(decodeURIComponent(htmlContent));
          previewEl.classList.remove('hidden');
        } else if (content) {
          previewEl.textContent = decodeURIComponent(content);
          previewEl.classList.remove('hidden');
        }
      }
    } else if (diagramId || params.get('mode') === 'diagram') {
      showDiagramPlaceholder();
      setView('diagram');
    }

    // Signal server when a direct video finishes so the queue can advance
    const stageVideo = document.getElementById('stage-video');
    if (stageVideo) {
      stageVideo.addEventListener('ended', () => {
        if (stageWS && stageWS.readyState === WebSocket.OPEN) {
          stageWS.send(JSON.stringify({ type: 'video_ended' }));
        }
      });
    }

    connectStageWS();

    // Collaborative typing pad listener
    const notepadBody = document.getElementById('notepad-body');
    const notepadStatus = document.getElementById('notepad-status');
    if (notepadBody) {
      notepadBody.addEventListener('input', (e) => {
        if (notepadStatus) {
          notepadStatus.textContent = 'Typing...';
          notepadStatus.style.color = '#ffb300';
        }
        
        // Broadcast input update over stage WS
        if (stageWS && stageWS.readyState === WebSocket.OPEN) {
          stageWS.send(JSON.stringify({
            type: 'notepad_update',
            text: e.target.value
          }));
        }
        
        clearTimeout(notepadBody.saveTimeout);
        notepadBody.saveTimeout = setTimeout(() => {
          if (notepadStatus) {
            notepadStatus.textContent = 'Synced ✓';
            notepadStatus.style.color = '#4caf50';
          }
        }, 800);
      });
    }

    (async () => {
      try {
        const session = await meet.addon.createAddonSession({ cloudProjectNumber: '649226456677' });
        // Attempt AudioContext unlock on Meet SDK init (user join gesture context)
        if (audioCtx.state === 'suspended') {
          audioCtx.resume().then(() => {
            if (audioCtx.state === 'running') {
              const btn = document.getElementById('audio-activate');
              if (btn) btn.style.display = 'none';
            }
          }).catch(() => {});
        }
        const client = await session.createMainStageClient();
        
        client.on('frameToFrameMessage', (arg) => {
          try {
            const msg = JSON.parse(arg.payload);
            handleStageMessage(msg);
          } catch (e) {
            console.error('[stage-dispatcher] Error processing frameToFrameMessage:', e);
          }
        });
      } catch (e) { console.warn('Meet SDK init failed:', e); }
    })();
})();
