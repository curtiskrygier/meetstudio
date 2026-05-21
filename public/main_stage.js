(function() {
    const params = new URLSearchParams(location.search);
    let currentMode = params.get('mode') || 'placeholder';
    let diagramId = params.get('diag_id') || '';
    const meetingId = params.get('meeting') || '';
    const ticket = params.get('ticket') || '';
    let knownVersion = 0;
    let turns = [];

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
            <div style="font-weight:600; color:rgba(255,255,255,0.8); margin-bottom:4px">Waiting for Architecture Description</div>
            <div style="font-size:12px">Describe your architecture to generate a new diagram</div>
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

    function playVideo(url) {
      const videoEl = document.getElementById('stage-video');
      const iframeEl = document.getElementById('stage-iframe');
      if (!videoEl || !iframeEl) return;

      const ytId = youtubeId(url);
      if (ytId) {
        videoEl.classList.add('hidden');
        videoEl.pause();
        videoEl.src = '';
        iframeEl.src = `https://www.youtube.com/embed/${ytId}?autoplay=1&enablejsapi=1`;
        iframeEl.classList.remove('hidden');
      } else {
        iframeEl.classList.add('hidden');
        iframeEl.src = '';
        videoEl.classList.remove('hidden');
        videoEl.src = url;
        videoEl.play().catch(() => {});
      }
    }

    function renderStageImage(base64) {
      const imgEl = document.getElementById('stage-image');
      if (!imgEl) return;
      imgEl.classList.remove('loaded');
      imgEl.onload = () => imgEl.classList.add('loaded');
      imgEl.src = 'data:image/jpeg;base64,' + base64;
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

    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

    // Activate button — unlocks AudioContext and hides itself on first click
    const activateBtn = document.getElementById('audio-activate');
    if (activateBtn) {
      activateBtn.addEventListener('click', () => {
        audioCtx.resume();
        activateBtn.style.display = 'none';
      }, { once: true });
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

    let stageWS = null;

    function connectStageWS() {
      if (!meetingId) return;
      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      const ws = new WebSocket(`${proto}://${location.host}/ws/stage?meeting_id=${encodeURIComponent(meetingId)}&ticket=${encodeURIComponent(ticket)}`);
      stageWS = ws;
      
      ws.onopen = () => console.log('[stage] Caption broadcast connected');
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === 'transcript') {
            updateTranscript(msg);
          } else if (msg.type === 'emoji_reaction') {
            launchEmoji(msg.emoji || '👏');
          } else if (msg.type === 'theme_change') {
            console.log('[stage] Applying theme change...');
            Object.entries(msg.tokens).forEach(([k, v]) => {
              document.documentElement.style.setProperty(k, v);
            });
          } else if (msg.type === 'audio') {
            if (msg.data) playAudioChunk(msg.data);
          } else if (msg.type === 'browser_frame') {
            const frameImg = document.getElementById('browser-frame');
            if (frameImg) frameImg.src = msg.data;
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
              renderStageImage(msg.imageData);
            }
            if (msg.mode === 'video' && msg.url) {
              playVideo(msg.url);
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
            if (msg.type === 'transcript') {
              updateTranscript(msg);
            } else if (msg.type === 'view_change') {
              if (msg.mode === 'diagram') {
                if (diagramId !== msg.diag_id) {
                  diagramId = msg.diag_id;
                  knownVersion = 0;
                  if (!msg.svg) showDiagramPlaceholder();
                }
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
              } else if (msg.mode === 'diagram') {
                if (msg.svg) {
                  renderInlineSVG(msg.svg);
                  knownVersion = msg.version;
                }
              }
            }
          } catch (e) {}
        });
      } catch (e) { console.warn('Meet SDK init failed:', e); }
    })();
})();
