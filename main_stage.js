(function() {
  const params = new URLSearchParams(location.search);
  const meetingId = params.get('meeting') || '';
  const ticket = params.get('ticket') || '';
  let stageWS = null;
  let audioCtx = null;

  function init() {
    setupWebSocket();
    window.addEventListener('unload', () => stageWS?.close());
  }

  function setupWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/ws/stage?meeting_id=${encodeURIComponent(meetingId)}&ticket=${encodeURIComponent(ticket)}`;
    console.log('[stage] Connecting to WebSocket...', wsUrl);
    
    stageWS = new WebSocket(wsUrl);
    window.__stageWS = stageWS; 

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
        if (window.__a2uiEngine && window.__a2uiEngine.handleMessage(msg)) {
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

  function handleLegacyMessage(msg) {
    if (msg.type === 'audio') {
      if (msg.data) playAudioChunk(msg.data);
    } else if (msg.type === 'sound_event') {
      if (msg.sound) triggerSoundEffect(msg.sound);
    } else if (msg.type === 'theme_change') {
      if (msg.tokens) {
        Object.entries(msg.tokens).forEach(([k, v]) => {
          document.documentElement.style.setProperty(k, v);
        });
      }
    }
  }

  async function playAudioChunk(base64) {
    try {
      if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
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

  function triggerSoundEffect(sound) {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
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

  document.addEventListener('DOMContentLoaded', () => {
    init();
  });
})();
