const DEFAULT_URL = 'https://meetstudio-602445641262.us-central1.run.app';

async function getBaseUrl() {
  return new Promise((resolve) => {
    chrome.storage.local.get('meetstudio_url', (res) => {
      resolve(res.meetstudio_url || DEFAULT_URL);
    });
  });
}

async function getContext() {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ type: 'GET_CONTEXT' }, (res) => {
      resolve(res?.context ?? null);
    });
  });
}

function buildMeetStudioUrl(baseUrl, ctx) {
  if (!ctx) return `${baseUrl}/?platform=livekit`;
  const params = new URLSearchParams({ platform: ctx.platform, room: ctx.room });
  if (ctx.identity) params.set('identity', ctx.identity);
  return `${baseUrl}/?${params}`;
}

// Stage ticket cache: keyed by `${baseUrl}::${room}`, value { url, expires }
const STAGE_CACHE_TTL_MS = 3 * 60 * 60 * 1000; // 3h (tickets last 4h)

async function getStageUrl(baseUrl, room) {
  const cacheKey = `ms_stage_${baseUrl}::${room}`;
  return new Promise((resolve) => {
    chrome.storage.local.get(cacheKey, async (res) => {
      const cached = res[cacheKey];
      if (cached && cached.expires > Date.now()) {
        resolve(cached.url);
        return;
      }
      try {
        const resp = await fetch(`${baseUrl}/api/join/${encodeURIComponent(room)}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        chrome.storage.local.set({ [cacheKey]: { url: data.stage_url, expires: Date.now() + STAGE_CACHE_TTL_MS } });
        resolve(data.stage_url);
      } catch (e) {
        console.error('[MeetStudio] stage join failed:', e);
        resolve(null);
      }
    });
  });
}

async function init() {
  const [baseUrl, ctx] = await Promise.all([getBaseUrl(), getContext()]);

  const loading = document.getElementById('loading');
  const loadingStatus = document.getElementById('loading-status');
  const roomTag = document.getElementById('room-tag');
  const frameContainer = document.getElementById('frame-container');
  const frame = document.getElementById('ms-frame');
  const toolbarLabel = document.getElementById('toolbar-label');
  const toolbar = document.getElementById('toolbar');
  const stageToggle = document.getElementById('stage-toggle');

  const panelUrl = buildMeetStudioUrl(baseUrl, ctx);
  let stageMode = false;

  if (ctx) {
    loadingStatus.textContent = 'connecting…';
    roomTag.textContent = `${ctx.platform} · ${ctx.room}`;
    roomTag.style.display = 'block';
    toolbarLabel.textContent = `${ctx.platform} · ${ctx.room}`;
  } else {
    loadingStatus.textContent = 'no meeting detected — opening MeetStudio';
    toolbarLabel.textContent = 'meetstudio';
    // No room context — hide the stage toggle
    stageToggle.style.display = 'none';
  }

  frame.src = panelUrl;

  frame.addEventListener('load', () => {
    loading.style.display = 'none';
    frameContainer.style.display = 'block';
  });

  // Fallback: show frame after 3s even if load event doesn't fire (cross-origin)
  setTimeout(() => {
    if (loading.style.display !== 'none') {
      loading.style.display = 'none';
      frameContainer.style.display = 'block';
    }
  }, 3000);

  stageToggle.addEventListener('click', async () => {
    if (!ctx) return;
    if (stageMode) {
      // Back to panel
      stageMode = false;
      stageToggle.classList.remove('active');
      stageToggle.textContent = '▶ STAGE';
      stageToggle.title = 'Switch to Stage view';
      toolbar.classList.remove('stage-mode');
      frame.src = panelUrl;
    } else {
      // Switch to stage
      stageToggle.classList.add('loading');
      stageToggle.textContent = '…';
      const stageUrl = await getStageUrl(baseUrl, ctx.room);
      stageToggle.classList.remove('loading');
      if (!stageUrl) {
        stageToggle.textContent = '▶ STAGE';
        return;
      }
      stageMode = true;
      stageToggle.classList.add('active');
      stageToggle.textContent = '◁ PANEL';
      stageToggle.title = 'Switch back to Panel';
      toolbar.classList.add('stage-mode');
      frame.src = stageUrl;
    }
  });
}

// Settings panel wiring
const settingsBtn = document.getElementById('settings-btn');
const settingsPanel = document.getElementById('settings-panel');
const urlInput = document.getElementById('url-input');
const saveBtn = document.getElementById('save-btn');
const cancelBtn = document.getElementById('cancel-btn');

settingsBtn.addEventListener('click', async () => {
  const stored = await getBaseUrl();
  urlInput.value = stored;
  settingsPanel.classList.add('visible');
});

cancelBtn.addEventListener('click', () => {
  settingsPanel.classList.remove('visible');
});

saveBtn.addEventListener('click', async () => {
  const newUrl = urlInput.value.trim().replace(/\/$/, '');
  if (!newUrl) return;
  chrome.storage.local.set({ meetstudio_url: newUrl }, async () => {
    settingsPanel.classList.remove('visible');
    // Reload frame with new URL
    const ctx = await getContext();
    const frame = document.getElementById('ms-frame');
    frame.src = buildMeetStudioUrl(newUrl, ctx);
    document.getElementById('loading').style.display = 'flex';
    document.getElementById('frame-container').style.display = 'none';
  });
});

init();
