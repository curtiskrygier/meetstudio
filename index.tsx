import { LitElement, css, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { meet } from '@googleworkspace/meet-addons';
import { MeetMediaApiClientImpl } from './internal/meetmediaapiclient_impl';
import { MeetConnectionState } from './types/enums';

// Modular Services
import { AudioService } from './internal/services/audio_service';
import { WebSocketService, WebSocketMessage } from './internal/services/websocket_service';

// Modular Components
import './internal/components/gdm_transcript_view';
import './internal/components/gdm_actions_view';
import './internal/components/gdm_controls_view';
import './internal/components/gdm_status_view';

import { mainStyles } from './internal/styles';

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
  @state() private accessToken = '';
  private meetingId = '';
  private activeTrackIds = new Set<string>();
  private activeVideoTrackIds = new Set<string>();
  private speechRecognition: any = null;
  private wakeTimeout: ReturnType<typeof setTimeout> | null = null;
  private userEmail = '';

  // Modular Services
  private audioService = new AudioService();
  private wsService: WebSocketService | null = null;

  private animationFrameId: number | null = null;
  private videoEl: HTMLVideoElement | null = null;
  private videoCanvas: HTMLCanvasElement | null = null;
  private videoFrameInterval: ReturnType<typeof setInterval> | null = null;

  static styles = mainStyles;

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
          this.requestUpdate();
          resolve();
        },
        error_callback: (err: any) => {
          console.error('[concierge] OAuth error:', err);
          this.error = `Auth failed: ${err.message || err}`;
          reject(new Error(err.message || 'Authentication failed'));
        },
      });
      
      client.requestAccessToken({ prompt: 'consent' });
    });
  }

  private toggleAudio() { this.audioEnabled = !this.audioEnabled; }
  private toggleVideo() { this.videoEnabled = !this.videoEnabled; }

  private async authenticatedFetch(url: string, options: RequestInit = {}): Promise<Response> {
    console.log(`[concierge] auth fetch: ${url}`);
    const headers = new Headers(options.headers || {});
    if (this.accessToken) {
      headers.set('Authorization', `Bearer ${this.accessToken}`);
    }
    const resp = await fetch(url, { ...options, headers });
    if (!resp.ok) {
      console.warn(`[concierge] auth fetch failed (${resp.status}): ${url}`);
    }
    return resp;
  }

  private async getAuthTicket(): Promise<string> {
    try {
      console.log('[concierge] requesting auth ticket...');
      const resp = await this.authenticatedFetch('/api/auth/ticket');
      if (!resp.ok) {
        const txt = await resp.text();
        console.error('[concierge] ticket request failed:', resp.status, txt);
        this.error = `Server auth failed: ${resp.status}`;
        return '';
      }
      const data = await resp.json();
      console.log('[concierge] ticket acquired');
      return data.ticket || '';
    } catch (e: any) {
      console.error('[concierge] ticket error:', e);
      this.error = `Ticket error: ${e.message || e}`;
      return '';
    }
  }

  private async connect() {
    if (!this.initialized) return;
    this.connecting = true;
    this.error = '';

    try {
      // Must initialize audio context in this click handler to satisfy browser policy
      await this.audioService.initialize();

      if (!this.accessToken) {
        await this.requestOAuthToken();
        this.connecting = false;
        return; // Wait for user to click "Connect" again after auth
      }
      
      if (!this.userEmail) {
        try {
          const resp = await this.authenticatedFetch('https://www.googleapis.com/oauth2/v3/userinfo');
          const info = await resp.json();
          this.userEmail = info.email || '';
          console.log('[concierge] user email:', this.userEmail);
        } catch (e) {
          console.warn('[concierge] userinfo fetch failed:', e);
        }
      }

      await this.connectWebSocket();

      this.audioService.getWorkletNode()!.port.onmessage = (e) => {
        if (!this.audioEnabled) return;
        const float32 = e.data as Float32Array;
        const int16 = this.floatTo16BitPCMArray(float32);
        this.wsService?.sendAudio(int16);
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
          this.status = 'Assistant is ready';
          this.startVolumeAnalysis();
        }
      });

      this.meetClient.meetStreamTracks.subscribe((tracks) => {
        tracks.forEach((meetTrack) => {
          const track = meetTrack.mediaStreamTrack;

          if (track.kind === 'audio' && !this.activeTrackIds.has(track.id)) {
            const audioEl = document.createElement('audio');
            audioEl.muted = true;
            audioEl.srcObject = new MediaStream([track]);
            audioEl.play().catch(() => {});
            this.audioService.resume();
            const source = this.audioService.getRecordingContext()!.createMediaStreamSource(new MediaStream([track]));
            source.connect(this.audioService.getAnalyser()!);
            source.connect(this.audioService.getWorkletNode()!);
            this.activeTrackIds.add(track.id);
            this.trackCount = this.activeTrackIds.size;
          }
        });
      });

      await this.meetClient.joinMeeting();
    } catch (e: any) {
      this.error = `Connection failed: ${e.message || e}`;
      this.connecting = false;
    }
  }

  private async connectWebSocket() {
    const ticket = await this.getAuthTicket();
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${proto}://${location.host}/ws?meeting_id=${encodeURIComponent(this.meetingId)}&token=${encodeURIComponent(ticket)}`;
    
    this.wsService = new WebSocketService(
      (msg) => this.handleWebSocketMessage(msg),
      () => { this.error = 'WebSocket error'; }
    );

    this.wsService.connect(url, {
      user_email: this.userEmail,
      access_token: this.accessToken,
      meeting_id: this.meetingId,
    });
  }

  private handleWebSocketMessage(msg: WebSocketMessage | ArrayBuffer) {
    if (msg instanceof ArrayBuffer) {
      if (!this.diagramMode) this.audioService.playChunk(msg);
      return;
    }

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
        const existingText = this.transcript.map(t => t.text).join(' ').toLowerCase();
        if (role === 'agent' || !existingText.includes(text.toLowerCase().substring(0, 20))) {
          newTranscript.push({ id: turn_id, role: roleLabel, text: text });
        }
      }
      this.transcript = [...newTranscript];

      if (this.transcriptMode && this.sidePanelClient) {
        this.sidePanelClient.notifyMainStage(JSON.stringify(msg)).catch(() => {});
      }

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
  }

  private startVolumeAnalysis() {
    const tick = () => {
      const analyser = this.audioService.getAnalyser();
      if (analyser) {
        const data = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteFrequencyData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i++) sum += data[i];
        this.volume = sum / data.length;
        this.animationFrameId = requestAnimationFrame(tick);
      }
    };
    tick();
  }

  private async disconnect() {
    if (this.animationFrameId) cancelAnimationFrame(this.animationFrameId);
    if (this.speechSilenceTimer) clearTimeout(this.speechSilenceTimer);
    if (this.diagramInterval) clearInterval(this.diagramInterval);
    
    this.diagramMode = false;
    this.wsService?.disconnect();
    this.audioService.disconnect();
    
    if (this.meetClient) {
      try { await this.meetClient.leaveMeeting(); } catch {}
      this.meetClient = null;
    }
    this.activeTrackIds.clear();
    this.activeVideoTrackIds.clear();
    this.connected = false;
    this.connecting = false;
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
        const ticket = await this.getAuthTicket();
        const stageUrl = `${location.origin}/main_stage.html?meeting=${encodeURIComponent(this.meetingId)}&ticket=${encodeURIComponent(ticket)}`;
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
      
      if (this.wsService?.readyState === WebSocket.OPEN) {
        this.wsService?.sendJson({ type: 'diagram_mode', active: false });
        this.wsService?.sendJson({ type: 'view_change', mode: 'placeholder' });
      }
      this.status = 'Assistant connected — listening';
    } else {
      this.diagramMode = true;
      this.transcriptMode = true;
      this.actionLinks = [];
      this.transcriptStartIndex = this.transcript.map(t => `[${t.role}] ${t.text}`).join('\n').length;
      this.diagramSessionStartTime = new Date().toISOString();
      this.diagramSessionId = crypto.randomUUID();
      this.status = 'Gemini Agent Architect — speak your architecture description';
      
      if (this.wsService?.readyState === WebSocket.OPEN) {
        this.wsService?.sendJson({ type: 'diagram_mode', active: true });
      }

      this.authenticatedFetch(`/api/session/${encodeURIComponent(this.meetingId)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: this.diagramSessionId }),
      }).catch(() => {});

      if (this.sidePanelClient) {
        if (!this.isActivityStarted) {
          const ticket = await this.getAuthTicket();
          const stageUrl = `${location.origin}/main_stage.html?mode=diagram&diag_id=${encodeURIComponent(this.diagramSessionId)}&meeting=${encodeURIComponent(this.meetingId)}&ticket=${encodeURIComponent(ticket)}`;
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
          if (this.wsService?.readyState === WebSocket.OPEN) {
            this.wsService?.sendJson({
              type: 'view_change',
              mode: 'diagram',
              diag_id: this.diagramSessionId
            });
          }
        }
      }
      this.diagramInterval = setInterval(() => {
        if (this.diagramMode && !this.diagramming && this.lastTranscriptTime > this.lastGenerationTime) {
          // Skip auto-gen if user is actively refining context manually
          if (!this.diagramContext.trim()) {
            this.generateDiagram();
          }
        }
      }, 1000);
    }
  }

  private async openInMainStage(url: string, label: string, content: string = '') {
    if (this.sidePanelClient && url.includes('docs.google.com')) {
      if (!this.isActivityStarted) {
        const ticket = await this.getAuthTicket();
        const stageUrl = `${location.origin}/main_stage.html?doc=${encodeURIComponent(url)}&label=${encodeURIComponent(label)}&meeting=${encodeURIComponent(this.meetingId)}&ticket=${encodeURIComponent(ticket)}${content ? `&content=${encodeURIComponent(content)}` : ''}`;
        try {
          await this.sidePanelClient.startActivity({ mainStageUrl: stageUrl });
          this.isActivityStarted = true;
        } catch (e) {
          console.error('[concierge] Failed to start activity:', e);
          window.open(url, '_blank');
        }
      } else {
        if (this.wsService?.readyState === WebSocket.OPEN) {
          this.wsService?.sendJson({
            type: 'view_change',
            mode: 'doc',
            url,
            label,
            content
          });
        }
      }
    } else {
      window.open(url, '_blank');
    }
  }

  private async fetchChatMessages(): Promise<string> {
    if (!this.accessToken || !this.meetingId) return '';
    try {
      const spaceId = this.meetingId.startsWith('spaces/') ? this.meetingId : `spaces/${this.meetingId}`;
      const resp = await this.authenticatedFetch(
        `https://chat.googleapis.com/v1/${spaceId}/messages?pageSize=100&orderBy=createTime asc`
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
      const resp = await this.authenticatedFetch('/api/diagram', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transcript,
          chat,
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
    const driveWin = window.open('about:blank', '_blank');
    this.status = 'Exporting transcript to Doc…';

    try {
      const resp = await this.authenticatedFetch('/api/transcript/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transcript: fullTranscript,
          space_id: this.meetingId
        }),
      });
      const data = await resp.json();
      if (data.error) throw new Error(data.error);
      if (data.file_id) {
        this.lastTranscriptFileId = data.file_id;
        const driveUrl = `https://drive.google.com/file/d/${data.file_id}/view`;
        this.status = 'Transcript exported to Drive ✓';
        if (driveWin) driveWin.location.href = driveUrl;
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
    const driveWin = window.open('about:blank', '_blank');
    this.status = 'Saving diagram to Drive…';
    
    try {
      const resp = await this.authenticatedFetch(`/api/diagram/${this.diagramSessionId}/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ space_id: this.meetingId }),
      });
      const data = await resp.json();
      if (data.error) throw new Error(data.error);
      if (data.file_id) {
        this.lastDiagramFileId = data.file_id;
        const driveUrl = `https://drive.google.com/file/d/${data.file_id}/view`;
        this.status = 'Diagram saved to Drive ✓';
        if (driveWin) driveWin.location.href = driveUrl;
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
    if (!success) return;
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

    if (this.wsService?.readyState === WebSocket.OPEN) {
      this.wsService?.sendJson(broadcastMsg);
    }

    if (this.sidePanelClient) {
      this.sidePanelClient.notifyMainStage(JSON.stringify(broadcastMsg)).catch(() => {});
    }

    try {
      await this.authenticatedFetch(`/api/session/${encodeURIComponent(this.meetingId)}`, {
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

    if (this.wsService?.readyState === WebSocket.OPEN) {
      this.wsService?.sendJson(broadcastMsg);
    }

    if (this.sidePanelClient) {
      this.sidePanelClient.notifyMainStage(JSON.stringify(broadcastMsg)).catch(() => {});
    }

    try {
      await this.authenticatedFetch(`/api/session/${encodeURIComponent(this.meetingId)}`, {
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
    const state = this.connecting ? 'connecting' : (this.connected ? (this.wakeActive ? 'wake' : 'listening') : 'disconnected');

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
        <gdm-status-view 
          .state=${state} 
          .status=${this.status} 
          .error=${this.error}
          .authenticated=${!!this.accessToken}>
        </gdm-status-view>

        ${!this.connected && !this.connecting ? html`
          <div class="section" style="padding-top:0">
            ${!this.accessToken ? html`
              <button class="cta google" @click=${() => this.requestOAuthToken().catch(e => console.error('[concierge] click-auth error:', e))}>
                <svg viewBox="0 0 24 24" style="width:18px;height:18px;margin-right:8px"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
                Sign in with Google
              </button>
            ` : html`
              <button class="cta" @click=${() => this.connect()}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="width:16px;height:16px"><path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/></svg>
                Join & Start Audio
              </button>
            `}
          </div>
        ` : ''}

        ${this.connecting ? html`
          <div class="section">
            <div class="conn-progress"></div>
            <div class="checklist">
              <div class="check done"><div class="check-tick">✓</div>Add-on initialised</div>
              <div class="check active"><div class="check-tick"></div>Connecting to Gemini Live…</div>
              <div class="check"><div class="check-tick"></div>Joining meeting audio</div>
            </div>
          </div>
        ` : ''}

        ${this.connected ? html`
          <div class="section">
            <gdm-controls-view
              .audioEnabled=${this.audioEnabled}
              .videoEnabled=${this.videoEnabled}
              .diagramMode=${this.diagramMode}
              .transcriptMode=${this.transcriptMode}
              @toggle-audio=${() => this.toggleAudio()}
              @toggle-video=${() => this.toggleVideo()}
              @toggle-diagram=${() => this.toggleDiagramMode()}
              @toggle-transcript=${() => this.toggleTranscriptMode()}>
            </gdm-controls-view>
          </div>

          ${this.actionLinks.length > 0 ? html`
            <div class="section">
              <div class="section-head"><span class="section-title">Workspace Actions</span></div>
              <gdm-actions-view 
                .actions=${this.actionLinks}
                @action-click=${(e: any) => this.openInMainStage(e.detail.url, e.detail.label, e.detail.content)}>
              </gdm-actions-view>
            </div>
          ` : ''}

          ${this.diagramMode ? html`
            <div class="section">
              <div class="section-head"><span class="section-title">Diagram Visuals</span></div>
              <div class="layout-switcher">
                ${['blueprint', 'sketch', 'cyber', 'google'].map(s => html`
                  <button class="style-btn" ?data-active=${this.diagramStyle === s} 
                          @click=${() => { this.diagramStyle = s as any; this.generateDiagram(); }}>
                    ${s.toUpperCase()}
                  </button>
                `)}
              </div>
              <textarea class="ctx-input" placeholder="Refine your architecture description here..."
                .value=${this.diagramContext}
                @input=${(e: any) => this.diagramContext = e.target.value}></textarea>
              <div style="display:flex; gap:8px; margin-top:12px">
                <button class="ctx-send" style="flex:1" ?disabled=${this.diagramming} @click=${() => this.generateDiagram()}>
                  ${this.diagramming ? 'Generating…' : 'Update'}
                </button>
                <button class="ctx-send" style="background:var(--bg-3); border:1px solid var(--line); color:var(--fg-3); flex:1" @click=${() => this.resetDiagram()}>
                  New
                </button>
                <button class="ctx-send" style="background:var(--gem-1); flex:1.5"
                  ?disabled=${!this.diagramSessionId || !this.lastGenerationTime}
                  @click=${() => this.saveDiagramToDrive()}>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="width:14px;height:14px;margin-right:6px"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                  Save PNG
                </button>
              </div>
            </div>
          ` : ''}

          <div class="section">
            <div class="section-head">
              <span class="section-title">Transcript</span>
              ${this.lastDiagramFileId ? html`
                <button class="mode-toggle-lg" @click=${() => window.open(`https://drive.google.com/file/d/${this.lastDiagramFileId}/view`, '_blank')}>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="width:12px;height:12px;margin-right:6px"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                  Open Image
                </button>
              ` : html`
                <button class="mode-toggle" @click=${() => this.exportTranscript()}>Export</button>
              `}
            </div>
            <gdm-transcript-view .transcript=${this.transcript}></gdm-transcript-view>
          </div>
        ` : ''}

        ${!this.connected && !this.connecting ? html`
          <div class="section">
            <div class="section-head"><span class="section-title">How it works</span></div>
            <div class="tips">
              <div class="tip"><div class="tip-num">1</div><span>Say <kbd>Hey Gemini</kbd> to activate, then speak your request</span></div>
              <div class="tip"><div class="tip-num">2</div><span>Create docs, search the web live, or summarise the meeting</span></div>
              <div class="tip"><div class="tip-num">3</div><span>New documents appear here and launch on the main stage for everyone</span></div>
            </div>
          </div>
        ` : ''}
      </div>

      ${this.connected ? html`
        <div class="footer">
          <div class="footer-meta">
            ${this.trackCount > 0 ? `${this.trackCount} audio track${this.trackCount > 1 ? 's' : ''}` : 'Meeting audio active'}
          </div>
          <button class="disc-btn" @click=${() => this.disconnect()}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            Disconnect
          </button>
        </div>
      ` : ''}
    `;
  }
}
