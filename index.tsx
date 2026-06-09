import { LitElement, css, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { unsafeHTML } from 'lit/directives/unsafe-html.js';
import { meet } from '@googleworkspace/meet-addons';
import { MeetMediaApiClientImpl } from './internal/meetmediaapiclient_impl';
import { MeetConnectionState } from './types/enums';

// Modular Services
import { AudioService } from './internal/services/audio_service';
import { WebSocketService, WebSocketMessage } from './internal/services/websocket_service';
import { A2UIEngine } from './internal/a2ui/engine';

// Modular Components
import './internal/components/gdm_transcript_view';
import './internal/components/gdm_actions_view';
import './internal/components/gdm_controls_view';
import './internal/components/gdm_status_view';
import './internal/components/gdm_doc_view';
import './internal/components/gdm_diagram_refiner';
import './internal/components/gdm_poll_view';

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
  @state() components: Array<{id: string; element: string; props: any}> = [];
  @state() lastTranscriptFileId = '';
  @state() lastDiagramFileId = '';
  @state() diagramStyle: 'cyber' | 'blueprint' | 'sketch' | 'google' = 'sketch';
  @state() diagramContext = '';
  @state() diagramming = false;
  @state() status = 'Initialising...';
  @state() authenticated = false;
  @state() geminiLiveEnabled: boolean | null = null;  // explicitly null until /api/capabilities checks
  @state() demoJoinCode = '';  // MEET-ABC123 displayed to presenter
  @state() demoParticipantCount = 0;
  @state() demoLaunchError = '';
  @state() layout = 'default';
  @state() uiPromptText = '';
  @state() uiPromptSending = false;
  @state() imageGenerating = false;

  private audioEnabled = true;
  private videoEnabled = false;
  private diagramMode = false;
  private transcriptMode = false;
  private actionLinks: Array<{url: string; label: string; content?: string}> = [];
  private trackCount = 0;
  private wakeActive = false;

  private diagramInterval: ReturnType<typeof setInterval> | null = null;

  private diagramSessionId = '';
  private diagramActivityStarted = false;
  private lastTranscriptTime = 0;
  private lastGenerationTime = 0;
  private transcriptStartIndex = 0;
  private diagramSessionStartTime: string | null = null;
  private speechSilenceTimer: ReturnType<typeof setTimeout> | null = null;
  private diagramContextTimer: ReturnType<typeof setTimeout> | null = null;

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

  // A2UI v0.8 engine — shared with the main stage (internal/a2ui/engine.ts)
  private a2uiEngine = new A2UIEngine(components => { this.components = components; });

  @state() private activeTab: 'concierge' | 'widgets' = 'concierge';
  @state() private ytUrl = '';
  @state() private ytPanel = 1;
  @state() private ytAutoplay = true;
  @state() private camPanel = 1;
  @state() private camEnabled = false;
  @state() private chyronTitle = '';
  @state() private chyronSub = '';
  @state() private chyronActive = false;
  @state() private tickerText = '';
  @state() private tickerActive = false;
  @state() private standbyTime = 5;
  @state() private standbySecs = 0;
  @state() private standbyBadge = 'STANDBY / INTERMISSION';
  @state() private standbyTitle = 'Session Will Resume Shortly';
  @state() private standbyDesc = 'We are taking a brief break. Streaming live from Meet Broadcast Studio.';
  @state() private standbyActive = false;
  @state() private activeLayout: 'single' | 'split' | 'grid' = 'single';
  @state() private studioActive = false;
  @state() private simulatedSender = 'Audience Member';
  @state() private simulatedText = 'wow I had no idea Google Meet was so versatile!';
  @state() private gdocUrl = 'https://drive.google.com/file/d/1--WyD9_iSA45xSQ2Sbflu74z3WJejd24/view?usp=drive_link';
  @state() private gdocDrafting = false;
  @state() private gdocStatus = '';
  @state() private chatSpaceIdInput = '';
  @state() private chatSpaceId = '';
  private lastSeenChatMsgName = '';
  private lastSeenChatMsgTime = '';
  private chatPollInterval: ReturnType<typeof setInterval> | null = null;
  private standbyInterval: ReturnType<typeof setInterval> | null = null;
  @state() private standbyRemainingSecs = 0;

  // Presenter / participant mode
  @state() private sessionRole: 'presenter' | 'participant' | null = null;
  @state() private participantRegistered = false;
  @state() private participantName = '';
  @state() private participantNumber = 0;
  @state() private participantDisplayName = '';
  @state() private sessionActive = false;
  @state() private playbookList: string[] = [];
  @state() private selectedPlaybook = '';
  @state() private slideList: Array<{slide_id: string; label: string}> = [];
  @state() private selectedSlide = '';
  @state() private participantList: Array<{space: string; connected: boolean; number: number; name: string}> = [];
  @state() private sendingSlide = false;
  @state() private sessionLaunched = false;
  private sessionCheckInterval: ReturnType<typeof setInterval> | null = null;

  private parseChatSpaceId(input: string): string {
    const trimmed = input.trim();
    if (!trimmed) return '';
    
    let parsed = trimmed;
    try {
      if (trimmed.includes('//')) {
        const url = new URL(trimmed);
        const pathParts = url.pathname.split('/').filter(Boolean);
        const hashParts = url.hash.split('/').filter(Boolean);
        
        if (pathParts.includes('chat') || pathParts.includes('room') || pathParts.includes('space')) {
          const index = Math.max(pathParts.indexOf('chat'), pathParts.indexOf('room'), pathParts.indexOf('space'));
          if (index !== -1 && pathParts[index + 1]) {
            parsed = pathParts[index + 1];
          }
        } else if (hashParts.includes('chat') || hashParts.includes('space') || hashParts.includes('room')) {
          const index = Math.max(hashParts.indexOf('chat'), hashParts.indexOf('space'), hashParts.indexOf('room'));
          if (index !== -1 && hashParts[index + 1]) {
            parsed = hashParts[index + 1];
          }
        } else {
          parsed = pathParts[pathParts.length - 1] || trimmed;
        }
      }
    } catch (e) {}
    
    parsed = parsed.split('?')[0].split('#')[0];
    if (parsed.startsWith('spaces/')) {
      return parsed;
    }
    return `spaces/${parsed}`;
  }

  private handleChatSpaceIdInput(val: string) {
    this.chatSpaceIdInput = val;
    this.chatSpaceId = this.parseChatSpaceId(val);
    console.log('[concierge] Parsed Chat Space ID:', this.chatSpaceId);
    if (this.chatPollInterval) {
      this.startChatPolling();
    }
  }


  private getBaseStageComponents(): any[] {
    return [
      {
        id: 'stage_captions',
        element: 'gdm-captions',
        props: { active: false, speaker: 'Gemini', text: '' }
      },
      {
        id: 'stage_emojis',
        element: 'gdm-emoji-burst',
        props: { active: false, emoji: '👏', count: 12 }
      },
      {
        id: 'stage_ticker',
        element: 'gdm-ticker',
        props: { 
          active: this.tickerActive, 
          text: this.tickerText || 'LIVE FEED: CAPGEMINI SE (CAP.PA) €194.20 (+1.45%) • AIRBUS A321XLR FLIGHT TEST AIB201 • VÉLÔTOULOUSE: 420 STATIONS ACTIVE • METRO LINE B: NORMAL SERVICE',
          fontSize: 48,
          height: 100
        }
      }
    ];
  }

  private extractYoutubeId(url: string): string {
    const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
    const match = url.match(regExp);
    return (match && match[2].length === 11) ? match[2] : url;
  }

  private changeLayout(layout: 'single' | 'split' | 'grid') {
    this.activeLayout = layout;
    const payload = {
      type: 'surfaceUpdate',
      surfaceUpdate: {
        components: [
          ...this.getBaseStageComponents(),
          {
            id: 'root',
            component: {
              'gdm-stage-grid': {
                layout: layout,
                focusedPanel: 0
              }
            }
          }
        ]
      }
    };
    this.wsService?.sendJson(payload);
    this.wsService?.sendJson({ type: 'beginRendering', beginRendering: { root: 'root' } });
  }

  private clearMainStage() {
    if (this.wsService?.readyState === WebSocket.OPEN) {
      this.wsService?.sendJson({ type: 'deleteSurface' });
      // Reset layout to grid-3 for future additions
      this.activeLayout = 'grid';
    }
  }

  private triggerDirectView(mode: 'notepad' | 'diagram' | 'dashboard') {
    let component = {};
    let id = '';
    if (mode === 'dashboard') {
      id = 'telemetry_panel';
      component = { 'gdm-telemetry-dashboard': { active: true } };
    } else if (mode === 'diagram') {
      id = 'diagram_panel';
      component = { 'gdm-diagram-view': { active: true, diag_id: this.diagramSessionId } };
    } else {
      id = 'notepad_panel';
      component = { 'gdm-notepad': { active: true } };
    }

    const payload = {
      type: 'surfaceUpdate',
      surfaceUpdate: {
        components: [
          ...this.getBaseStageComponents(),
          {
            id: 'root',
            component: {
              'gdm-stage-grid': {
                layout: 'single',
                children: [id]
              }
            }
          },
          { id, component }
        ]
      }
    };

    if (this.wsService?.readyState === WebSocket.OPEN) {
      this.wsService?.sendJson(payload);
      this.wsService?.sendJson({ type: 'beginRendering', beginRendering: { root: 'root' } });
    }
  }

  private castYoutube() {
    const raw = this.ytUrl.trim();
    if (!raw) return;
    const videoId = this.extractYoutubeId(raw);
    
    const panelId = `panel_${this.ytPanel}`;
    const payload = {
      type: 'surfaceUpdate',
      surfaceUpdate: {
        components: [
          ...this.getBaseStageComponents(),
          {
            id: 'root',
            component: {
              'gdm-stage-grid': {
                layout: this.activeLayout
              }
            }
          },
          {
            id: panelId,
            component: {
              'gdm-video-panel': {
                src: `https://www.youtube.com/embed/${videoId}?autoplay=1`,
                label: 'YouTube Feed'
              }
            }
          }
        ]
      }
    };

    if (this.wsService?.readyState === WebSocket.OPEN) {
      this.wsService?.sendJson(payload);
      this.wsService?.sendJson({ type: 'beginRendering', beginRendering: { root: 'root' } });
    }
  }

  private async draftPlaybookFromGdoc() {
    const input = this.gdocUrl.trim();
    if (!input || !this.meetingId) return;
    this.gdocDrafting = true;
    this.gdocStatus = 'Processing request...';
    
    // Auto-detect if input is a URL or a text prompt topic
    const isUrl = input.startsWith('http://') || input.startsWith('https://');
    const isGdoc = isUrl && (input.includes('docs.google.com') || input.includes('drive.google.com'));
    
    const payload = isUrl 
      ? { source: 'drive', doc_url: input } 
      : { source: 'prompt', prompt: input };

    if (isUrl) {
      this.gdocStatus = isGdoc 
        ? 'Fetching Google Doc content & drafting via Gemini...' 
        : 'Fetching website page & drafting via Gemini...';
    } else {
      this.gdocStatus = 'Generating custom Google Doc and presentation via Gemini...';
    }

    try {
      const resp = await this.authenticatedFetch(`/api/playbook/draft-from-doc/${this.meetingId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!resp.ok) {
        this.gdocStatus = `Draft failed: ${data.detail || data.error || 'Server error'}`;
        return;
      }
      if (data.error === 'scope_missing') {
        this.gdocStatus = `⚠️ Consent required: ${data.detail}. Required Scope: ${data.required_scope}. Fallback: ${data.fallback}`;
        return;
      }
      
      // Update status beautifully and include a link if a Doc was generated or fetched!
      if (data.doc_url) {
        const isUrlGdoc = data.doc_url.includes('docs.google.com') || data.doc_url.includes('drive.google.com');
        const linkLabel = isUrlGdoc ? 'Open Doc on Drive ↗' : 'Open Website Page ↗';
        this.gdocStatus = html`
          ✔ Playbook drafted as "${data.playbook_name}"!<br/>
          📝 Source Link: <a href="${data.doc_url}" target="_blank" style="color:var(--accent); font-weight:bold; text-decoration:underline;">${linkLabel}</a><br/>
          Firing kickoff slide...
        ` as any;
      } else {
        this.gdocStatus = `✔ Playbook drafted successfully as "${data.playbook_name}"! Firing kickoff slide...`;
      }
      
      // Fire the first slide automatically!
      if (data.fire_url) {
        if (this.sidePanelClient && !this.isActivityStarted) {
          const ticket = await this.getAuthTicket();
          const stageUrl = `${location.origin}/main_stage.html?meeting=${encodeURIComponent(this.meetingId)}&ticket=${encodeURIComponent(ticket)}`;
          try {
            await this.sidePanelClient.startActivity({ mainStageUrl: stageUrl });
            this.isActivityStarted = true;
          } catch (e: any) {
            console.error('[concierge] Failed to start main stage activity during draft:', e?.message || e);
          }
        }
        const fireResp = await this.authenticatedFetch(data.fire_url, { method: 'POST' });
        if (fireResp.ok) {
          if (data.doc_url) {
            const isUrlGdoc = data.doc_url.includes('docs.google.com') || data.doc_url.includes('drive.google.com');
            const linkLabel = isUrlGdoc ? 'Open Doc on Drive ↗' : 'Open Website Page ↗';
            this.gdocStatus = html`
              ✔ Playbook "${data.playbook_name}" drafted & kickoff slide fired successfully!<br/>
              📝 Source Link: <a href="${data.doc_url}" target="_blank" style="color:var(--accent); font-weight:bold; text-decoration:underline;">${linkLabel}</a>
            ` as any;
          } else {
            this.gdocStatus = `✔ Playbook "${data.playbook_name}" drafted and kickoff slide fired successfully!`;
          }
        } else {
          this.gdocStatus = `✔ Drafted, but failed to fire kickoff slide automatically (${fireResp.status})`;
        }
      }
    } catch (e: any) {
      console.warn('[concierge] draft error:', e);
      this.gdocStatus = `Error: ${e.message || e}`;
    } finally {
      this.gdocDrafting = false;
    }
  }

  private togglePresenterCam(enabled: boolean) {
    this.camEnabled = enabled;
    const panelId = `panel_${this.camPanel}`;
    
    if (enabled) {
      const payload = {
        type: 'surfaceUpdate',
        surfaceUpdate: {
          components: [
            {
              id: 'root',
              component: {
                'gdm-stage-grid': { layout: this.activeLayout }
              }
            },
            {
              id: panelId,
              component: {
                'gdm-camera-panel': {
                  label: 'Presenter Live Feed',
                  mirrored: true
                }
              }
            }
          ]
        }
      };
      this.wsService?.sendJson(payload);
      this.wsService?.sendJson({ type: 'beginRendering', beginRendering: { root: 'root' } });
    } else {
      // In A2UI, to "clear" a panel, we can either delete its surface or update the grid children
      this.wsService?.sendJson({
        type: 'surfaceUpdate',
        surfaceUpdate: {
          components: [{
            id: panelId,
            component: {} // Emptying the component
          }]
        }
      });
      this.wsService?.sendJson({ type: 'beginRendering', beginRendering: { root: 'root' } });
    }
  }

  private changeCamPanel(panel: number) {
    this.wsService?.sendJson({
      type: 'view_change',
      mode: 'image',
      imageData: 'clear_camera',
      panel: this.camPanel,
      imageLayout: this.activeLayout
    });
    
    this.camPanel = panel;
    if (this.camEnabled) {
      if (panel > 2 && this.activeLayout !== 'grid') {
        this.activeLayout = 'grid';
      } else if (panel === 2 && this.activeLayout === 'single') {
        this.activeLayout = 'split';
      }
      this.wsService?.sendJson({
        type: 'view_change',
        mode: 'image',
        imageData: 'camera',
        panel: panel,
        imageLayout: this.activeLayout,
        label: 'Presenter Live Feed'
      });
    }
  }

  private async toggleStudioMode(forceActive?: boolean) {
    this.studioActive = forceActive !== undefined ? forceActive : !this.studioActive;
    this.wsService?.sendJson({
      type: 'studio_mode_event',
      active: this.studioActive
    });
    
    if (this.studioActive && this.sidePanelClient && !this.isActivityStarted) {
      const ticket = await this.getAuthTicket();
      // join_session: each participant auto-joins to get their own private space
      // meeting: used for shared/presenter stage (Gemini Live mode)
      const param = this.geminiLiveEnabled ? 'meeting' : 'join_session';
      const stageUrl = `${location.origin}/main_stage.html?${param}=${encodeURIComponent(this.meetingId)}&ticket=${encodeURIComponent(ticket)}`;
      try {
        await this.sidePanelClient.startActivity({ mainStageUrl: stageUrl });
        this.isActivityStarted = true;
      } catch (e: any) {
        console.error('[concierge] Failed to start main stage activity:', e?.message || e);
      }
    }
  }

  private switchTab(tab: 'concierge' | 'widgets') {
    this.activeTab = tab;
    if (tab === 'widgets') {
      if (this.audioEnabled) {
        this.toggleAudio();
      }
      if (!this.studioActive) {
        this.toggleStudioMode(true);
      }
    } else {
      if (this.studioActive) {
        this.toggleStudioMode(false);
      }
    }
  }

  private toggleChyron() {
    this.chyronActive = !this.chyronActive;
    const payload = {
      type: 'surfaceUpdate',
      surfaceUpdate: {
        components: [{
          id: 'chyron_overlay',
          component: {
            'gdm-chyron': {
              active: this.chyronActive,
              title: this.chyronTitle.trim() || 'Presenter',
              subtitle: this.chyronSub.trim() || 'Workspace Live Stream'
            }
          }
        }]
      }
    };
    this.wsService?.sendJson(payload);
    this.wsService?.sendJson({ type: 'beginRendering', beginRendering: { root: 'root' } });
  }

  private toggleTicker() {
    this.tickerActive = !this.tickerActive;
    const payload = {
      type: 'surfaceUpdate',
      surfaceUpdate: {
        components: [{
          id: 'ticker_overlay',
          component: {
            'gdm-ticker': {
              active: this.tickerActive,
              text: this.tickerText.trim() || 'Broadcasting Live'
            }
          }
        }]
      }
    };
    this.wsService?.sendJson(payload);
    this.wsService?.sendJson({ type: 'beginRendering', beginRendering: { root: 'root' } });
  }

  private sendSimulatedComment() {
    const sender = this.simulatedSender.trim() || 'Producer';
    const text = this.simulatedText.trim();
    if (!text) return;

    const chat_id = `chat_${Date.now()}`;
    const payload = {
      type: 'surfaceUpdate',
      surfaceUpdate: {
        components: [{
          id: chat_id,
          component: {
            'gdm-chat-card': {
              sender,
              text,
              avatar: ''
            }
          }
        }]
      }
    };

    if (this.wsService?.readyState === WebSocket.OPEN) {
      this.wsService?.sendJson(payload);
      this.wsService?.sendJson({ type: 'beginRendering', beginRendering: { root: 'root' } });
    }

    // Also send the comment to the actual Google Chat space if we are authenticated
    const targetSpace = this.chatSpaceId ? this.chatSpaceId : (this.meetingId ? (this.meetingId.startsWith('spaces/') ? this.meetingId : `spaces/${this.meetingId}`) : '');
    if (this.accessToken && targetSpace) {
      console.log('[concierge] Access token and target space resolved. Posting comment to real Google Chat space...');
      this.authenticatedFetch(`https://chat.googleapis.com/v1/${targetSpace}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text })
      }).then(resp => {
        if (resp.ok) {
          console.log('[concierge] Successfully posted comment to real Google Chat space');
        } else {
          console.warn('[concierge] Failed to post comment to real Google Chat space:', resp.status);
        }
      }).catch(err => {
        console.error('[concierge] Error posting comment to Google Chat space:', err);
      });
    }

    this.simulatedText = ''; // Clear text input after broadcast
  }

  private async pollGoogleChat() {
    if (!this.accessToken) return;
    const targetSpace = this.chatSpaceId ? this.chatSpaceId : (this.meetingId ? (this.meetingId.startsWith('spaces/') ? this.meetingId : `spaces/${this.meetingId}`) : '');
    if (!targetSpace) return;
    try {
      // Order DESC so page 1 is always the most-recent messages. With ASC ordering
      // a continuous-chat space with >100 messages of history would only ever return
      // the oldest 100 on page 1, and new arrivals (at the tail) would never be seen.
      const resp = await this.authenticatedFetch(
        `https://chat.googleapis.com/v1/${targetSpace}/messages?pageSize=50&orderBy=${encodeURIComponent('createTime desc')}`
      );
      if (!resp.ok) {
        console.warn('[concierge] pollGoogleChat API status:', resp.status);
        return;
      }
      const data = await resp.json();
      const rawMessages = data.messages || []; // newest-first (createTime desc)

      if (rawMessages.length === 0) return;

      // First run: just initialize last seen message to the latest in the space
      if (!this.lastSeenChatMsgName) {
        const latest = rawMessages[0];
        this.lastSeenChatMsgName = latest.name || '';
        this.lastSeenChatMsgTime = latest.createTime || '';
        console.log('[concierge] Chat poller initialized with latest msg:', this.lastSeenChatMsgName);
        return;
      }

      // Find any new messages since last check, then reverse to chronological order
      // (oldest first) so cards render on the stage in the order they were typed.
      const newMessages = rawMessages.filter((m: any) => {
        // Must be strictly after our last seen message time or have a different unique resource name
        if (m.name === this.lastSeenChatMsgName) return false;
        if (this.lastSeenChatMsgTime && m.createTime <= this.lastSeenChatMsgTime) return false;
        return true;
      }).reverse();

      if (newMessages.length > 0) {
        console.log(`[concierge] Polled ${newMessages.length} new Google Chat messages`);
        for (const m of newMessages) {
          const sender = m.sender?.displayName || m.sender?.name || 'Unknown';
          const text = m.text || m.formattedText || '';
          const avatar = m.sender?.avatarUrl || m.sender?.avatarUri || '';

          if (text) {
            const trimmedText = text.trim();
            const lowerText = trimmedText.toLowerCase();

            // Support the hardcoded demo messages
            const isHardcodedExample =
              lowerText === 'wow i had no idea google meet was so versatile!' ||
              lowerText === 'welcome everyone to the meet broadcast studio live event!' ||
              lowerText === 'airspace radar telemetry is running at 10.0x zoom!';

            const hasPrefix = lowerText.startsWith('/mainstage');

            if (isHardcodedExample || hasPrefix) {
              let cleanText = trimmedText;
              if (hasPrefix) {
                // Strip "/mainstage" (case-insensitive)
                cleanText = trimmedText.substring('/mainstage'.length).trim();
              }

              const chat_id = `chat_${m.name ? m.name.split('/').pop() : Date.now()}`;
              const payload = {
                type: 'surfaceUpdate',
                surfaceUpdate: {
                  components: [{
                    id: chat_id,
                    component: {
                      'gdm-chat-card': {
                        sender,
                        text: cleanText,
                        avatar
                      }
                    }
                  }]
                }
              };

              console.log('[concierge] Promoting chat message to main stage via A2UI:', payload);

              if (this.wsService?.readyState === WebSocket.OPEN) {
                this.wsService?.sendJson(payload);
                this.wsService?.sendJson({ type: 'beginRendering', beginRendering: { root: 'root' } });
              }
            } else {
              console.log('[concierge] Ignored regular chat message (no /mainstage prefix or demo preset matches):', text);
            }
          }
        }

        // Update last seen to the absolute latest message
        const absoluteLatest = newMessages[newMessages.length - 1];
        this.lastSeenChatMsgName = absoluteLatest.name || '';
        this.lastSeenChatMsgTime = absoluteLatest.createTime || '';
      }
    } catch (e) {
      console.warn('[concierge] pollGoogleChat error:', e);
    }
  }

  private startChatPolling() {
    if (this.chatPollInterval) {
      clearInterval(this.chatPollInterval);
    }
    // Initial fetch to mark last seen and avoid flooding old messages
    this.pollGoogleChat();
    // Poll every 4 seconds
    this.chatPollInterval = setInterval(() => {
      this.pollGoogleChat();
    }, 4000);
    console.log('[concierge] Google Chat periodic poller started (4s interval)');
  }

  private pushStandbyComponents(badge: string, title: string, description: string, remainingSeconds: number) {
    const components: any[] = [];

    // 1. Root Grid
    components.push({
      id: 'root',
      component: {
        'gdm-stage-grid': {
          layout: 'single',
          children: ['welcome_outer_container']
        }
      }
    });

    // 2. Outer Full-Stage Container
    components.push({
      id: 'welcome_outer_container',
      component: {
        'gdm-container': {
          direction: 'column',
          justify: 'center',
          align: 'center',
          width: '100%',
          height: '100%',
          background: 'rgba(10, 15, 30, 0.45)',
          children: ['welcome_card']
        }
      }
    });

    // 3. Glassmorphic Welcome Card
    const cardChildren = [
      'welcome_header_row',
      'welcome_divider',
      'welcome_title'
    ];
    if (description) {
      cardChildren.push('welcome_description');
    }
    if (remainingSeconds > 0) {
      cardChildren.push('welcome_countdown');
      cardChildren.push('welcome_countdown_line');
    }
    cardChildren.push('welcome_progress');
    cardChildren.push('welcome_status_row');

    components.push({
      id: 'welcome_card',
      component: {
        'gdm-container': {
          direction: 'column',
          justify: 'center',
          align: 'center',
          padding: '32px',
          gap: '20px',
          width: '500px',
          glass: true,
          borderRadius: '16px',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          children: cardChildren
        }
      }
    });

    // 4. Header Row
    components.push({
      id: 'welcome_header_row',
      component: {
        'gdm-container': {
          direction: 'row',
          justify: 'space-between',
          align: 'center',
          width: '100%',
          children: ['welcome_icon', 'welcome_badge']
        }
      }
    });

    components.push({
      id: 'welcome_icon',
      component: {
        'gdm-icon': {
          name: 'sonar',
          color: 'cyan',
          size: '32px'
        }
      }
    });

    components.push({
      id: 'welcome_badge',
      component: {
        'gdm-badge': {
          text: badge.toUpperCase(),
          type: 'cyan',
          pulse: true
        }
      }
    });

    // 5. Divider
    components.push({
      id: 'welcome_divider',
      component: {
        'gdm-divider': {
          vertical: false,
          color: 'rgba(255, 255, 255, 0.15)',
          thickness: '1px',
          margin: '4px 0'
        }
      }
    });

    // 6. Title
    components.push({
      id: 'welcome_title',
      component: {
        'gdm-text': {
          content: title,
          size: 'h2',
          color: 'accent',
          pulse: true,
          uppercase: true,
          font: 'sans',
          align: 'center'
        }
      }
    });

    // 7. Description
    if (description) {
      components.push({
        id: 'welcome_description',
        component: {
          'gdm-text': {
            content: description,
            size: 'body',
            color: 'white',
            align: 'center'
          }
        }
      });
    }

    // 8. Countdown Timer
    if (remainingSeconds > 0) {
      const minutes = Math.floor(remainingSeconds / 60);
      const seconds = remainingSeconds % 60;
      const timeStr = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
      components.push({
        id: 'welcome_countdown',
        component: {
          'gdm-text': {
            content: timeStr,
            size: '64px',
            weight: '800',
            color: 'accent',
            pulse: true,
            font: 'mono',
            align: 'center'
          }
        }
      });
      components.push({
        id: 'welcome_countdown_line',
        component: {
          'gdm-divider': {
            vertical: false,
            color: 'rgba(0, 242, 255, 0.4)',
            thickness: '2px',
            margin: '0 auto'
          }
        }
      });
    }

    // 9. Progress Bar
    components.push({
      id: 'welcome_progress',
      component: {
        'gdm-progress': {
          value: 100.0,
          color: 'cyan',
          height: '8px',
          animated: true,
          glow: true
        }
      }
    });

    // 10. Status Row
    components.push({
      id: 'welcome_status_row',
      component: {
        'gdm-container': {
          direction: 'row',
          justify: 'space-between',
          align: 'center',
          width: '100%',
          children: ['welcome_status_lbl', 'welcome_clock']
        }
      }
    });

    components.push({
      id: 'welcome_status_lbl',
      component: {
        'gdm-text': {
          content: remainingSeconds > 0 ? '📡 Aligning WebSocket feeds...' : '🟢 Broadcast stage calibrated',
          size: 'caption',
          color: 'mute'
        }
      }
    });

    components.push({
      id: 'welcome_clock',
      component: {
        'gdm-clock': {
          showClock: true,
          showDate: false,
          format: '24h',
          accentColor: 'cyan'
        }
      }
    });

    const payload = {
      type: 'surfaceUpdate',
      surfaceUpdate: {
        components: components
      }
    };
    this.wsService?.sendJson(payload);
    this.wsService?.sendJson({ type: 'beginRendering', beginRendering: { root: 'root' } });
  }

  private toggleStandby() {
    this.standbyActive = !this.standbyActive;
    if (this.standbyActive) {
      this.standbyRemainingSecs = (this.standbyTime * 60) + this.standbySecs;
      if (this.standbyInterval) {
        clearInterval(this.standbyInterval);
      }
      this.pushStandbyComponents(this.standbyBadge, this.standbyTitle, this.standbyDesc, this.standbyRemainingSecs);
      this.standbyInterval = setInterval(() => {
        if (this.standbyRemainingSecs > 0) {
          this.standbyRemainingSecs--;
          this.pushStandbyComponents(this.standbyBadge, this.standbyTitle, this.standbyDesc, this.standbyRemainingSecs);
        } else {
          this.toggleStandby();
        }
      }, 1000);
    } else {
      if (this.standbyInterval) {
        clearInterval(this.standbyInterval);
        this.standbyInterval = null;
      }
      this.wsService?.sendJson({ type: 'deleteSurface' });
      const restorePayload = {
        type: 'surfaceUpdate',
        surfaceUpdate: {
          components: [
            ...this.getBaseStageComponents(),
            {
              id: 'root',
              component: {
                'gdm-stage-grid': {
                  layout: this.activeLayout,
                  focusedPanel: 0
                }
              }
            }
          ]
        }
      };
      this.wsService?.sendJson(restorePayload);
      this.wsService?.sendJson({ type: 'beginRendering', beginRendering: { root: 'root' } });
    }
  }

  private triggerSound(sound: string) {
    this.wsService?.sendJson({
      type: 'sound_event',
      sound: sound
    });
  }

  private triggerEmoji(emoji: string) {
    this.wsService?.sendJson({
      type: 'emoji_event',
      emoji: emoji
    });
  }

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

  updated(changed: Map<string, unknown>) {
    // Auto-load playbooks when connected in playbook mode and list is empty
    if (changed.has('connected') && this.connected && this.geminiLiveEnabled === false && this.accessToken && this.playbookList.length === 0) {
      this.loadPlaybooks();
    }
  }

  firstUpdated() {
    console.log('[concierge] build v18.1 — modular backend, 16:9 optimized, cinematic UX');
    fetch('/api/version').then(r => r.json()).then(d => {
      const el = this.shadowRoot?.querySelector('#build-badge') as HTMLElement;
      if (el) el.textContent = `v${d.version} · ${d.built}`;
    }).catch(() => {});
    this.checkCapabilities().then(() => this.initializeAddon());
  }

  private async checkCapabilities() {
    try {
      const resp = await fetch('/api/capabilities');
      if (resp.ok) {
        const caps = await resp.json();
        this.geminiLiveEnabled = caps.gemini_live === true;
        if (!this.geminiLiveEnabled) {
          console.log('[concierge] Gemini Live disabled — playbook mode only');
          this.status = 'Ready';
        }
      } else {
        console.warn('[concierge] capabilities check returned non-ok status, assuming full mode');
        this.geminiLiveEnabled = true;
      }
    } catch (e) {
      console.warn('[concierge] capabilities check failed, assuming full mode:', e);
      this.geminiLiveEnabled = true;
    }
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

      // Detect if this side panel opened because the user joined an activity
      const openReason = await this.sidePanelClient.getFrameOpenReason();
      if (openReason === 'JOIN_ACTIVITY') {
        this.sessionRole = 'participant';
        this.sessionActive = true;
        console.log('[concierge] Joined activity — switching to participant view');
      }

      this.sidePanelClient.on('frameToFrameMessage', (arg: any) => {
        try {
          const msg = JSON.parse(arg.payload);
          if (msg.type === 'view_change' && msg.mode === 'doc') {
            this.openInMainStage(msg.url, msg.label, msg.content);
          }
          if (msg.type === 'diagram_override' && msg.text) {
            console.log('[concierge] Main Stage override received:', msg.text);
            this.diagramContext = msg.text;
            this.generateDiagram();
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

      client.requestAccessToken({ prompt: '' });
    });
  }

  private toggleAudio() {
    if (this.wsService?.readyState === WebSocket.OPEN) {
      this.wsService?.sendJson({ type: 'toggle_audio' });
    }
  }

  private toggleVideo() {
    if (this.wsService?.readyState === WebSocket.OPEN) {
      this.wsService?.sendJson({ type: 'toggle_video' });
    }
  }

  private async generateImage() {
    const prompt = this.uiPromptText.trim();
    if (!prompt || !this.meetingId) {
      this.status = 'Type an image description in the field below, then click Image';
      return;
    }
    this.imageGenerating = true;
    this.status = 'Generating image…';
    try {
      await this.authenticatedFetch('/api/image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, space_id: this.meetingId }),
      });
      this.uiPromptText = '';
      this.status = 'Image generating — will appear on stage';
    } catch (e: any) {
      this.status = `Image failed: ${(e as any).message || e}`;
    } finally {
      this.imageGenerating = false;
    }
  }

  private async sendUiPrompt() {
    const text = this.uiPromptText.trim();
    if (!text || !this.meetingId) return;
    this.uiPromptSending = true;
    try {
      await this.authenticatedFetch('/api/ui-prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: text, space_id: this.meetingId }),
      });
      this.uiPromptText = '';
    } catch (e) {
      console.warn('[concierge] ui-prompt error:', e);
    } finally {
      this.uiPromptSending = false;
    }
  }

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

  private async startPlaybookDemo() {
    if (!this.sidePanelClient || !this.connected) {
      await this.connect();
      return;
    }
    this.demoLaunchError = '';
    this.status = 'Launching Read the Room...';
    try {
      // Step 1: Create join code for participants
      const codeResp = await this.authenticatedFetch(
        `/api/join-code/${encodeURIComponent(this.meetingId)}`,
        { method: 'POST' }
      );
      const { join_code } = await codeResp.json();
      this.demoJoinCode = join_code;
      console.log('[concierge] Join code created:', join_code);

      // Step 2: Push stage to participants
      const ticket = await this.getAuthTicket();
      const stageUrl = `${location.origin}/main_stage.html?join_session=${encodeURIComponent(this.meetingId)}&ticket=${encodeURIComponent(ticket)}`;
      await this.sidePanelClient.startActivity({ mainStageUrl: stageUrl });
      this.isActivityStarted = true;
      this.status = `Broadcast sent — show code: ${join_code}`;

      // Step 3: Fire read_the_room cover to the session
      const fireResp = await this.authenticatedFetch(
        `/api/playbook/fire/read_the_room/cover/${encodeURIComponent(this.meetingId)}`,
        { method: 'POST' }
      );
      if (!fireResp.ok) throw new Error(`Fire failed: ${fireResp.status}`);

      console.log('[concierge] Read the Room started — code:', join_code);

      // Step 4: Poll participant count
      this.startParticipantCountPoll();
    } catch (e: any) {
      const msg = e?.message || String(e);
      console.error('[concierge] startPlaybookDemo failed:', msg);
      this.demoLaunchError = `Failed to launch: ${msg}. Check connection and retry.`;
      this.status = 'Ready — playbook mode';
    }
  }

  private pollParticipantInterval: ReturnType<typeof setInterval> | null = null;

  private _pollTick = 0;
  private startParticipantCountPoll() {
    if (this.pollParticipantInterval) clearInterval(this.pollParticipantInterval);
    this._pollTick = 0;
    this.pollParticipantInterval = setInterval(async () => {
      this._pollTick++;
      try {
        const resp = await this.authenticatedFetch(
          `/api/session/${encodeURIComponent(this.meetingId)}/status`
        );
        const { participant_count } = await resp.json();
        this.demoParticipantCount = participant_count;
      } catch (e) {
        // Silent fail on poll
      }
      // Refresh detailed participant list every 5 ticks (5s)
      if (this._pollTick % 5 === 0) {
        this.refreshParticipantList();
      }
    }, 1000);
  }

  private async connect() {
    if (!this.initialized) return;
    this.connecting = true;
    this.error = '';

    // Playbook-only mode — no Gemini Live, no audio/video
    if (this.geminiLiveEnabled === false) {
      if (!this.accessToken) {
        await this.requestOAuthToken();
        this.connecting = false;
        return;
      }
      await this.connectWebSocket();
      this.connected = true;
      this.connecting = false;
      this.status = 'Ready — playbook mode';
      this.startChatPolling();
      return;
    }

    // Not yet determined or Gemini Live mode
    if (this.geminiLiveEnabled !== true) {
      console.warn('[concierge] capabilities not yet checked; waiting...');
      this.connecting = false;
      return;
    }

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
          this.startChatPolling();
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
    const url = `wss://${location.host}/ws?meeting_id=${encodeURIComponent(this.meetingId)}&ticket=${encodeURIComponent(ticket)}`;

    
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

  private applyTheme(tokens: Record<string, string>) {
    const host = this.shadowRoot?.host as HTMLElement;
    if (!host) return;
    Object.entries(tokens).forEach(([k, v]) => host.style.setProperty(k, v));
  }

  private handleWebSocketMessage(msg: WebSocketMessage | ArrayBuffer) {
    if (msg instanceof ArrayBuffer) {
      const diagramMode = this.components.find(c => c.id === 'control_bar')?.props.diagramMode;
      if (!diagramMode) this.audioService.playChunk(msg);
      return;
    }

    if (this.a2uiEngine.handleMessage(msg)) return;

    if (msg.type === 'A2UI_STATE') {
      const a2ui = msg as any;
      this.components = a2ui.components;
      this.layout = a2ui.layout || 'default';
      
      // Apply theme if provided by server
      if (a2ui.theme) {
        this.applyTheme(a2ui.theme);
      }

      // Extract status text for local status property (fallback)
      const hero = this.components.find(c => c.id === 'hero_status');
      if (hero) {
        this.status = hero.props.status;
        this.authenticated = hero.props.authenticated;
      }
      
      const ctrl = this.components.find(c => c.id === 'control_bar');
      if (ctrl) {
        this.audioEnabled = ctrl.props.audioEnabled;
        this.videoEnabled = ctrl.props.videoEnabled;
        this.diagramMode = ctrl.props.diagramMode;
        this.transcriptMode = ctrl.props.transcriptMode;
      }

      const links = this.components.find(c => c.id === 'workspace_links');
      if (links) {
        this.actionLinks = links.props.actions;
      }

      return;
    }

    if (msg.type === 'transcript') {
      const { turn_id, role, text, label } = msg;
      const roleLabel = label || (role === 'agent' ? 'Gemini Architect' : 'User');
      
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
    if (this.standbyInterval) {
      clearInterval(this.standbyInterval);
      this.standbyInterval = null;
    }
    if (this.chatPollInterval) {
      clearInterval(this.chatPollInterval);
      this.chatPollInterval = null;
    }
    
    this.components = [];
    this.a2uiEngine.clear();
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
        const payload = {
          type: 'surfaceUpdate',
          surfaceUpdate: {
            components: [
              {
                id: 'root',
                component: { 'gdm-stage-grid': { layout: 'single', children: ['doc_panel'] } }
              },
              {
                id: 'doc_panel',
                component: {
                  'gdm-doc-panel': {
                    url,
                    label,
                    content
                  }
                }
              }
            ]
          }
        };
        if (this.wsService?.readyState === WebSocket.OPEN) {
          this.wsService?.sendJson(payload);
          this.wsService?.sendJson({ type: 'beginRendering', beginRendering: { root: 'root' } });
        }
      }
    } else {
      window.open(url, '_blank');
    }
  }

  private async fetchChatMessages(): Promise<string> {
    if (!this.accessToken) return '';
    const targetSpace = this.chatSpaceId ? this.chatSpaceId : (this.meetingId ? (this.meetingId.startsWith('spaces/') ? this.meetingId : `spaces/${this.meetingId}`) : '');
    if (!targetSpace) return '';
    try {
      const resp = await this.authenticatedFetch(
        `https://chat.googleapis.com/v1/${targetSpace}/messages?pageSize=100&orderBy=${encodeURIComponent('createTime asc')}`
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

    // Reset the auto-gen guard timer if user just edited context
    if (this.diagramContextTimer) {
      clearTimeout(this.diagramContextTimer);
    }
    this.diagramContextTimer = setTimeout(() => {
      if (this.diagramContext) {
        console.log('[concierge] Auto-clearing diagram context due to inactivity');
        this.diagramContext = '';
      }
    }, 30000); // 30s timeout

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

  private async loadPlaybooks() {
    try {
      const resp = await this.authenticatedFetch('/api/playbook/list');
      if (!resp.ok) return;
      const data = await resp.json();
      this.playbookList = data.playbooks || [];
      if (this.playbookList.length > 0 && !this.selectedPlaybook) {
        await this.loadSlides(this.playbookList[0]);
      } else if (this.selectedPlaybook) {
        await this.loadSlides(this.selectedPlaybook);
      }
    } catch (e) {
      console.warn('[concierge] loadPlaybooks error:', e);
    }
  }

  private async loadSlides(playbook: string) {
    if (!playbook) return;
    this.selectedPlaybook = playbook;
    this.selectedSlide = '';
    this.slideList = [];
    try {
      const resp = await this.authenticatedFetch(`/api/playbook/list/${encodeURIComponent(playbook)}`);
      if (!resp.ok) return;
      const data = await resp.json();
      this.slideList = data.slides || [];
      if (this.slideList.length > 0) {
        this.selectedSlide = this.slideList[0].slide_id;
      }
    } catch (e) {
      console.warn('[concierge] loadSlides error:', e);
    }
  }

  private async registerAsParticipant() {
    if (!this.meetingId || !this.participantName.trim()) return;
    try {
      const resp = await fetch(
        `/api/join/${encodeURIComponent(this.meetingId)}?name=${encodeURIComponent(this.participantName.trim())}`
      );
      if (!resp.ok) throw new Error(`Join failed: ${resp.status}`);
      const data = await resp.json();
      this.participantNumber = data.participant_number;
      this.participantDisplayName = data.display_name;
      this.participantRegistered = true;
    } catch (e: any) {
      this.error = `Join failed: ${e.message || e}`;
    }
  }

  private startSessionCheck() {
    if (this.sessionCheckInterval) clearInterval(this.sessionCheckInterval);
    this.sessionCheckInterval = setInterval(async () => {
      if (!this.meetingId) return;
      try {
        const resp = await fetch(`/api/session/${encodeURIComponent(this.meetingId)}/active`);
        if (resp.ok) {
          const { active } = await resp.json();
          if (active && !this.sessionActive) {
            this.sessionActive = true;
            clearInterval(this.sessionCheckInterval!);
            this.sessionCheckInterval = null;
            // Try to auto-join the activity so participant doesn't need to click
            await this.participantAutoJoinActivity();
          }
        }
      } catch (e) { /* silent */ }
    }, 3000);
  }

  private async participantAutoJoinActivity() {
    if (!this.sidePanelClient || !this.meetingId) return;
    try {
      // Get a stage ticket for this participant
      const joinResp = await fetch(`/api/join/${encodeURIComponent(this.meetingId)}`);
      if (!joinResp.ok) return;
      const { ticket, stage_url } = await joinResp.json();
      // Attempt startActivity — Meet may auto-join rather than error if activity matches
      await this.sidePanelClient.startActivity({ mainStageUrl: stage_url });
    } catch (e: any) {
      // ActivityIsOngoing means host already has it running — participant sees "Join the activity" button
      // Nothing further needed; the prompt guides them
      console.log('[concierge] participant auto-join:', e?.name || e?.message);
    }
  }

  private async launchPresenterSession() {
    if (!this.sidePanelClient || !this.accessToken) return;
    this.demoLaunchError = '';
    if (!this.connected) {
      await this.connect();
      if (!this.connected) return;
    }
    try {
      this.status = 'Launching session...';
      const codeResp = await this.authenticatedFetch(
        `/api/join-code/${encodeURIComponent(this.meetingId)}`,
        { method: 'POST' }
      );
      const { join_code } = await codeResp.json();
      this.demoJoinCode = join_code;

      const ticket = await this.getAuthTicket();
      const stageUrl = `${location.origin}/main_stage.html?join_session=${encodeURIComponent(this.meetingId)}&ticket=${encodeURIComponent(ticket)}`;
      await this.sidePanelClient.startActivity({
        mainStageUrl: stageUrl,
        sidePanelUrl: location.origin + '/',
        additionalData: JSON.stringify({ session: this.meetingId }),
      });
      this.isActivityStarted = true;
      this.sessionLaunched = true;

      if (this.selectedPlaybook && this.selectedSlide) {
        await this.authenticatedFetch(
          `/api/playbook/fire/${encodeURIComponent(this.selectedPlaybook)}/${encodeURIComponent(this.selectedSlide)}/${encodeURIComponent(this.meetingId)}`,
          { method: 'POST' }
        );
      }
      this.status = `Live — code: ${join_code}`;
      this.startParticipantCountPoll();
    } catch (e: any) {
      this.demoLaunchError = `Launch failed: ${e?.message || e}`;
      this.status = 'Ready';
    }
  }

  private async sendSlideToAll() {
    if (!this.selectedPlaybook || !this.selectedSlide || !this.meetingId) return;
    this.sendingSlide = true;
    try {
      await this.authenticatedFetch(
        `/api/playbook/fire/${encodeURIComponent(this.selectedPlaybook)}/${encodeURIComponent(this.selectedSlide)}/${encodeURIComponent(this.meetingId)}`,
        { method: 'POST' }
      );
    } catch (e) {
      console.warn('[concierge] sendSlideToAll error:', e);
    } finally {
      this.sendingSlide = false;
    }
  }

  private async sendSlideToParticipant(space: string) {
    if (!this.selectedPlaybook || !this.selectedSlide || !space) return;
    try {
      await this.authenticatedFetch(
        `/api/playbook/fire/${encodeURIComponent(this.selectedPlaybook)}/${encodeURIComponent(this.selectedSlide)}/${encodeURIComponent(space)}`,
        { method: 'POST' }
      );
    } catch (e) {
      console.warn('[concierge] sendSlideToParticipant error:', e);
    }
  }

  private async refreshParticipantList() {
    if (!this.meetingId || !this.accessToken) return;
    try {
      const resp = await this.authenticatedFetch(`/api/session/participants/${encodeURIComponent(this.meetingId)}`);
      if (!resp.ok) return;
      const data = await resp.json();
      const parts: Record<string, any> = data.participants || {};
      this.participantList = Object.entries(parts).map(([space, p]) => ({
        space,
        connected: p.connected || false,
        number: p.number || 0,
        name: p.name || `Participant #${p.number}`
      }));
      this.demoParticipantCount = data.total || 0;
    } catch (e) {
      // silent
    }
  }

  private get componentRegistry() {
    return new Map<string, (props: any) => any>([
      ['gdm-status-view', (p) => html`<gdm-status-view .state=${p.state} .status=${p.status} .authenticated=${p.authenticated}></gdm-status-view>`],
      ['gdm-controls-view', (p) => this.geminiLiveEnabled ? html`<gdm-controls-view .audioEnabled=${p.audioEnabled} .videoEnabled=${p.videoEnabled} .diagramMode=${p.diagramMode} .transcriptMode=${p.transcriptMode} @toggle-audio=${()=>this.toggleAudio()} @toggle-video=${()=>this.toggleVideo()} @toggle-diagram=${()=>this.toggleDiagramMode()} @toggle-transcript=${()=>this.toggleTranscriptMode()} @generate-image=${()=>this.generateImage()}></gdm-controls-view>` : html``],
      ['gdm-actions-view', (p) => html`<gdm-actions-view .actions=${p.actions} @action-click=${(e: any)=>this.openInMainStage(e.detail.url, e.detail.label, e.detail.content)}></gdm-actions-view>`],
      ['gdm-doc-view', (p) => html`<gdm-doc-view .title=${p.title} .htmlContent=${p.htmlContent}></gdm-doc-view>`],
      ['gdm-diagram-refiner', (p) => html`<gdm-diagram-refiner .diagramStyle=${this.diagramStyle} .context=${this.diagramContext} .generating=${this.diagramming} .canSave=${!!(this.diagramSessionId && this.lastGenerationTime)} @change-style=${(e: any) => { this.diagramStyle = e.detail; this.generateDiagram(); }} @update-context=${(e: any) => this.diagramContext = e.detail} @generate=${() => this.generateDiagram()} @new=${() => this.resetDiagram()} @save=${() => this.saveDiagramToDrive()}></gdm-diagram-refiner>`],
      ['gdm-poll-view', (p) => html`<gdm-poll-view .question=${p.question} .options=${p.options} @poll-select=${(e: any) => {
        this.uiPromptText = `User selected ${e.detail.option} in the poll. Update theme and diagram accordingly.`;
        this.sendUiPrompt();
      }}></gdm-poll-view>`],
      ['gdm-transcript-view', (p) => html`
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
      `],
    ]);
  }

  private renderComponent(comp: any) {
    const factory = this.componentRegistry.get(comp.element);
    return factory ? factory(comp.props) : html``;
  }

  render() {
    const state = this.connecting ? 'connecting' : (this.connected ? (this.wakeActive ? 'wake' : 'listening') : 'disconnected');

    return html`
      <div class="topbar">
        <div class="brand">
          <div class="brand-mark">${GEMINI_LOGO}</div>
          <div class="brand-name">Google Meet Studio</div>
        </div>
        <div class="topbar-actions">
          ${this.lastDiagramFileId ? html`
            <button class="icon-btn" title="Open latest diagram"
              @click=${() => window.open(`https://drive.google.com/file/d/${this.lastDiagramFileId}/view`, '_blank')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
            </button>
          ` : ''}
          <div id="build-badge" style="font-size:9px;color:#00f2ff;background:rgba(0,242,255,0.1);border:1px solid rgba(0,242,255,0.3);border-radius:4px;padding:2px 6px;font-family:monospace;">v18.1</div>
        </div>
      </div>

      <div class="body layout-${this.layout}">
        ${!this.connected && !this.connecting ? html`
          <gdm-status-view 
            .state=${state} 
            .status=${this.status} 
            .error=${this.error}
            .authenticated=${!!this.accessToken}>
          </gdm-status-view>
          
          <div class="section" style="padding-top:0">
            ${this.geminiLiveEnabled === false ? html`
              ${this.sessionRole === null ? html`
                <!-- Role picker -->
                <p style="font-size:12px;color:#94a3b8;margin:0 0 14px;line-height:1.5;text-align:center;">Who are you in this session?</p>
                <div style="display:flex;gap:8px;">
                  <button class="cta" style="flex:1;" @click=${() => { this.sessionRole = 'presenter'; if (this.accessToken) this.loadPlaybooks(); }}>
                    🎙️ Presenting
                  </button>
                  <button class="cta" style="flex:1;background:rgba(0,242,255,0.08);border:1px solid rgba(0,242,255,0.4);color:#00f2ff;"
                    @click=${() => { this.sessionRole = 'participant'; this.startSessionCheck(); }}>
                    👤 Participant
                  </button>
                </div>
              ` : this.sessionRole === 'presenter' ? html`
                <!-- Presenter flow -->
                <div style="display:flex;align-items:center;margin-bottom:12px;">
                  <span style="font-size:11px;color:#6ee7b7;font-weight:600;">🎙️ Presenting</span>
                  <button style="margin-left:auto;font-size:10px;color:#64748b;background:none;border:none;cursor:pointer;"
                    @click=${() => { this.sessionRole = null; }}>← Change</button>
                </div>
                ${!this.accessToken ? html`
                  <button class="cta google" @click=${() => this.requestOAuthToken().then(() => this.loadPlaybooks()).catch(e => console.error('[concierge] auth error:', e))}>
                    <svg viewBox="0 0 24 24" style="width:18px;height:18px;margin-right:8px"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
                    Sign in as Presenter
                  </button>
                ` : html`
                  <div style="font-size:10px;color:#64748b;margin-bottom:3px;text-transform:uppercase;letter-spacing:0.05em;">Meeting ID</div>
                  <div style="font-size:11px;color:#00f2ff;font-family:monospace;background:rgba(0,242,255,0.06);border:1px solid rgba(0,242,255,0.2);border-radius:6px;padding:5px 10px;margin-bottom:14px;word-break:break-all;">
                    ${this.meetingId || 'Initialising...'}
                  </div>
                  ${this.playbookList.length === 0 ? html`
                    <button class="btn-action" style="width:100%;margin-bottom:12px;" @click=${() => this.loadPlaybooks()}>
                      Load Playbooks
                    </button>
                  ` : html`
                    <div style="display:flex;gap:8px;margin-bottom:10px;">
                      <div style="flex:1;min-width:0;">
                        <div style="font-size:10px;color:#64748b;margin-bottom:3px;">Playbook</div>
                        <select class="select-control" @change=${(e: any) => this.loadSlides(e.target.value)}>
                          ${this.playbookList.map(p => html`<option value=${p} ?selected=${p === this.selectedPlaybook}>${p}</option>`)}
                        </select>
                      </div>
                      <div style="flex:1;min-width:0;">
                        <div style="font-size:10px;color:#64748b;margin-bottom:3px;">Slide</div>
                        <select class="select-control" @change=${(e: any) => this.selectedSlide = e.target.value}>
                          ${this.slideList.map(s => html`<option value=${s.slide_id} ?selected=${s.slide_id === this.selectedSlide}>${s.label || s.slide_id}</option>`)}
                        </select>
                      </div>
                    </div>
                  `}
                  ${!this.sessionLaunched ? html`
                    <button class="cta" style="background:linear-gradient(135deg,#00f2ff,#9b6dff);color:#000;font-weight:900;"
                      @click=${() => this.launchPresenterSession()}
                      ?disabled=${!this.selectedPlaybook || !this.selectedSlide}>
                      ▶ Launch Session
                    </button>
                  ` : html`
                    <button class="cta" @click=${() => this.sendSlideToAll()} ?disabled=${this.sendingSlide || !this.selectedSlide}>
                      ${this.sendingSlide ? 'Sending...' : '⬆ Send to All'}
                    </button>
                    <div style="background:rgba(0,242,255,0.08);border:1px solid rgba(0,242,255,0.25);border-radius:8px;padding:10px 12px;margin-top:10px;">
                      <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;">Join Code</div>
                      <div style="font-size:20px;font-weight:900;color:#00f2ff;font-family:monospace;letter-spacing:0.15em;margin:3px 0;">${this.demoJoinCode}</div>
                      <div style="font-size:11px;color:${this.demoParticipantCount > 0 ? '#6ee7b7' : '#64748b'};">
                        ${this.demoParticipantCount > 0 ? `✓ ${this.demoParticipantCount} joined` : '⏳ Waiting for participants...'}
                      </div>
                    </div>
                  `}
                  ${this.demoLaunchError ? html`
                    <div style="font-size:11px;color:#ff5252;background:rgba(244,67,54,0.1);border-left:2px solid #ff5252;padding:8px;margin-top:10px;border-radius:4px;">
                      ⚠ ${this.demoLaunchError}
                    </div>
                  ` : ''}
                `}
              ` : html`
                <!-- Participant flow -->
                <div style="display:flex;align-items:center;margin-bottom:12px;">
                  <span style="font-size:11px;color:#00f2ff;font-weight:600;">👤 Participant</span>
                  <button style="margin-left:auto;font-size:10px;color:#64748b;background:none;border:none;cursor:pointer;"
                    @click=${() => { this.sessionRole = null; this.participantRegistered = false; this.sessionActive = false; if (this.sessionCheckInterval) { clearInterval(this.sessionCheckInterval); this.sessionCheckInterval = null; } }}>← Change</button>
                </div>

                ${!this.sessionActive ? html`
                  <div style="text-align:center;padding:20px 0;">
                    <div style="font-size:28px;margin-bottom:10px;">⏳</div>
                    <div style="font-size:13px;color:#94a3b8;margin-bottom:6px;">Waiting for presenter...</div>
                    <div style="font-size:10px;color:#475569;">The stage will appear in Meet automatically when the session starts</div>
                  </div>
                ` : !this.participantRegistered ? html`
                  <div style="background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.3);border-radius:8px;padding:10px 12px;margin-bottom:14px;">
                    <div style="font-size:12px;font-weight:600;color:#6ee7b7;">✓ Session is live</div>
                    <div style="font-size:11px;color:#94a3b8;margin-top:2px;">Enter your name so the presenter can see you</div>
                  </div>
                  <input
                    class="ctx-input"
                    type="text"
                    placeholder="Your name..."
                    .value=${this.participantName}
                    @input=${(e: any) => this.participantName = e.target.value}
                    @keydown=${(e: KeyboardEvent) => e.key === 'Enter' && this.registerAsParticipant()}
                    style="margin-bottom:8px;"
                  />
                  <button class="cta" style="background:rgba(0,242,255,0.1);border:1px solid rgba(0,242,255,0.4);color:#00f2ff;"
                    @click=${() => this.registerAsParticipant()}
                    ?disabled=${!this.participantName.trim()}>
                    ✓ Join Session
                  </button>
                ` : html`
                  <div style="background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.35);border-radius:8px;padding:16px;text-align:center;">
                    <div style="font-size:16px;font-weight:700;color:#6ee7b7;">${this.participantDisplayName}</div>
                    <div style="font-size:11px;color:#94a3b8;margin-top:4px;">Participant #${this.participantNumber}</div>
                    <div style="font-size:10px;color:#475569;margin-top:8px;">Content is appearing on your Meet stage</div>
                  </div>
                `}
              `}
            ` : (this.geminiLiveEnabled === true ? html`
              <!-- Gemini Live mode — original sign in / connect flow -->
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
            ` : html`
              <p style="font-size:12px;color:#94a3b8;">Loading capabilities...</p>
            `)}
          </div>

          ${this.geminiLiveEnabled === true ? html`
          <div class="section">
            <div class="section-head"><span class="section-title">How it works</span></div>
            <div class="tips">
              <div class="tip"><div class="tip-num">1</div><span>Say <kbd>Hey Gemini</kbd> to activate, then speak your request</span></div>
              <div class="tip"><div class="tip-num">2</div><span>Create docs, search the web live, or summarise the meeting</span></div>
              <div class="tip"><div class="tip-num">3</div><span>New documents appear here and launch on the main stage for everyone</span></div>
            </div>
          </div>
          ` : html``}
        ` : ''}

        ${this.connecting ? html`
          <gdm-status-view 
            .state=${state} 
            .status=${this.status} 
            .error=${this.error}
            .authenticated=${!!this.accessToken}>
          </gdm-status-view>
          <div class="section">
            <div class="conn-progress"></div>
            <div class="checklist">
              <div class="check done"><div class="check-tick">✓</div>Add-on initialised</div>
              ${this.geminiLiveEnabled ? html`
                <div class="check active"><div class="check-tick"></div>Connecting to Gemini Live…</div>
                <div class="check"><div class="check-tick"></div>Joining meeting audio</div>
              ` : html`
                <div class="check active"><div class="check-tick"></div>Connecting to stage…</div>
              `}
            </div>
          </div>
        ` : ''}

        ${this.connected ? html`
          <div class="tabs-container">
            <button class="tab-btn ${this.activeTab === 'concierge' ? 'active' : ''}" @click=${() => this.switchTab('concierge')}>
              ⬡ Studio
            </button>
            <button class="tab-btn ${this.activeTab === 'widgets' ? 'active' : ''}" @click=${() => this.switchTab('widgets')}>
              🎛️ Studio Mode
            </button>
          </div>

          ${this.activeTab === 'concierge' ? html`
            ${this.geminiLiveEnabled === false ? html`
              <!-- Playbook presenter controls (connected) -->
              <div class="section">
                <div style="font-size:10px;color:#64748b;margin-bottom:3px;text-transform:uppercase;letter-spacing:0.05em;">Meeting ID</div>
                <div style="font-size:11px;color:#00f2ff;font-family:monospace;background:rgba(0,242,255,0.06);border:1px solid rgba(0,242,255,0.2);border-radius:6px;padding:5px 10px;margin-bottom:14px;word-break:break-all;">
                  ${this.meetingId}
                </div>

                <div style="display:flex;gap:8px;margin-bottom:10px;">
                  <div style="flex:1;min-width:0;">
                    <div style="font-size:10px;color:#64748b;margin-bottom:3px;">Playbook</div>
                    <select class="select-control" .value=${this.selectedPlaybook}
                      @change=${(e: any) => this.loadSlides(e.target.value)}>
                      ${this.playbookList.length === 0
                        ? html`<option value="">— tap Load —</option>`
                        : this.playbookList.map(p => html`<option value=${p}>${p}</option>`)}
                    </select>
                  </div>
                  <div style="flex:1;min-width:0;">
                    <div style="font-size:10px;color:#64748b;margin-bottom:3px;">Slide</div>
                    <select class="select-control" .value=${this.selectedSlide}
                      @change=${(e: any) => this.selectedSlide = e.target.value}>
                      ${this.slideList.map(s => html`<option value=${s.slide_id}>${s.label || s.slide_id}</option>`)}
                    </select>
                  </div>
                </div>

                ${this.playbookList.length === 0 ? html`
                  <button class="btn-action" style="width:100%;margin-bottom:10px;" @click=${() => this.loadPlaybooks()}>Load Playbooks</button>
                ` : ''}

                <button class="cta" @click=${() => this.sendSlideToAll()} ?disabled=${this.sendingSlide || !this.selectedSlide}>
                  ${this.sendingSlide ? 'Sending...' : '⬆ Send to All'}
                </button>

                ${this.demoJoinCode ? html`
                  <div style="display:flex;align-items:baseline;gap:10px;margin-top:12px;padding:8px 10px;background:rgba(0,242,255,0.06);border:1px solid rgba(0,242,255,0.2);border-radius:6px;">
                    <span style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;white-space:nowrap;">Code</span>
                    <span style="font-size:15px;font-weight:900;color:#00f2ff;font-family:monospace;letter-spacing:0.12em;">${this.demoJoinCode}</span>
                    <span style="margin-left:auto;font-size:11px;color:${this.demoParticipantCount > 0 ? '#6ee7b7' : '#64748b'};">
                      ${this.demoParticipantCount > 0 ? `${this.demoParticipantCount} joined` : 'none yet'}
                    </span>
                  </div>

                  ${this.participantList.length > 0 ? html`
                    <div style="margin-top:10px;">
                      <div style="font-size:10px;color:#64748b;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.05em;">Participants</div>
                      ${this.participantList.map((p) => html`
                        <div style="display:flex;align-items:center;gap:8px;padding:5px 8px;background:rgba(255,255,255,0.03);border-radius:6px;margin-bottom:3px;">
                          <div style="width:6px;height:6px;border-radius:50%;flex-shrink:0;background:${p.connected ? '#10b981' : '#475569'};"></div>
                          <span style="font-size:11px;color:#e2e8f0;flex:1;">${p.name}</span>
                          <button class="btn-action" style="height:22px;padding:0 8px;font-size:10px;margin:0;"
                            @click=${() => this.sendSlideToParticipant(p.space)}>Send</button>
                        </div>
                      `)}
                    </div>
                  ` : ''}
                ` : ''}
              </div>
            ` : html`
              ${this.components.map(comp => html`<div class="section">${this.renderComponent(comp)}</div>`)}
              <div class="section ui-prompt-bar">
                <div class="ui-prompt-row">
                  <input
                    class="ctx-input ui-prompt-input"
                    type="text"
                    placeholder="Change UI or describe an image… e.g. neon robot at a meeting"
                    .value=${this.uiPromptText}
                    ?disabled=${this.uiPromptSending}
                    @input=${(e: any) => this.uiPromptText = e.target.value}
                    @keydown=${(e: KeyboardEvent) => e.key === 'Enter' && this.sendUiPrompt()}
                  />
                  <button
                    class="ctx-send"
                    ?disabled=${this.uiPromptSending || !this.uiPromptText.trim()}
                    @click=${() => this.sendUiPrompt()}>
                    ${this.uiPromptSending ? '…' : 'Apply'}
                  </button>
                </div>
              </div>
            `}
          ` : html`
            <div class="widget-container">
              <!-- Studio Activation & Controls -->
              <div class="widget-card" style="border: 1px solid var(--accent-glow); box-shadow: 0 0 15px rgba(255, 0, 85, 0.15);">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <span style="font-weight:bold; color:var(--accent);">🔴 Studio Broadcast Mode</span>
                  <button class="btn-action ${this.studioActive ? 'active' : 'danger'}" @click=${() => this.toggleStudioMode()} style="width:auto; padding:6px 12px; margin:0;">
                    ${this.studioActive ? 'Deactivate' : 'Activate Stage'}
                  </button>
                </div>
                <div class="widget-subtitle" style="margin-top: 6px;">
                  Triggers explicit audio permission prompt & camera preparation overlay on the main stage.
                </div>
              </div>

              <!-- Google Doc Playbook Drafter -->
              <div class="widget-card">
                <div class="widget-title">📖 Live Web & Doc Playbook Drafter</div>
                <div class="widget-subtitle">Paste a Google Doc/PDF/Website link, OR type a topic prompt (e.g., "History of Roman Siege Engines") to auto-generate content, compile slides, and project them live on stage!</div>
                <div class="form-group">
                  <span class="form-label">Google Doc, PDF, Website URL or Custom Topic</span>
                  <input class="ctx-input" type="text" placeholder="Paste link (Doc, PDF, or Web page) or enter a topic (e.g., History of Roman Siege Engines)..." .value=${this.gdocUrl} @input=${(e: any) => this.gdocUrl = e.target.value} />
                </div>
                <div style="font-size: 11px; margin-top: -10px; margin-bottom: 12px; color: rgba(255, 255, 255, 0.6); display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                  <span>Try:</span>
                  <a href="#" style="color: var(--accent); text-decoration: none; border-bottom: 1px dashed var(--accent); padding-bottom: 2px; font-weight: 500;" @click=${(e: Event) => { e.preventDefault(); this.gdocUrl = 'https://drive.google.com/file/d/1--WyD9_iSA45xSQ2Sbflu74z3WJejd24/view?usp=drive_link'; }}>A2UI 0.9 Spec (PDF) ⚡</a>
                  <span>•</span>
                  <a href="#" style="color: var(--accent); text-decoration: none; border-bottom: 1px dashed var(--accent); padding-bottom: 2px; font-weight: 500;" @click=${(e: Event) => { e.preventDefault(); this.gdocUrl = 'https://en.wikipedia.org/wiki/Antigravity'; }}>Antigravity (Wiki Web) 🌐</a>
                  <span>•</span>
                  <a href="#" style="color: var(--accent); text-decoration: none; border-bottom: 1px dashed var(--accent); padding-bottom: 2px; font-weight: 500;" @click=${(e: Event) => { e.preventDefault(); this.gdocUrl = '15 dad jokes'; }}>15 Dad Jokes 🎭</a>
                </div>
                ${this.gdocStatus ? html`<div style="font-size:11px; color:var(--accent); margin-bottom:8px; word-break:break-all;">${this.gdocStatus}</div>` : ''}
                <button class="cta" @click=${() => this.draftPlaybookFromGdoc()} ?disabled=${this.gdocDrafting || !this.gdocUrl.trim()}>
                  ${this.gdocDrafting ? 'Drafting & Compiling...' : '📖 Draft & Fire Playbook'}
                </button>
              </div>

              <!-- Grid Layout & Views -->
              <div class="widget-card">
                <div class="widget-title">🖥️ Grid Layout & Views</div>
                <div class="widget-subtitle">Select the stage grid layout</div>
                <div class="btn-grid">
                  <button class="btn-action ${this.activeLayout === 'single' ? 'active' : ''}" @click=${() => this.changeLayout('single')}>Single</button>
                  <button class="btn-action ${this.activeLayout === 'split' ? 'active' : ''}" @click=${() => this.changeLayout('split')}>Split (2)</button>
                  <button class="btn-action ${this.activeLayout === 'grid' ? 'active' : ''}" @click=${() => this.changeLayout('grid')}>Grid (4)</button>
                </div>
                <div class="widget-subtitle" style="margin-top: 6px; margin-bottom: 2px;">Direct Activators</div>
                <div class="btn-grid">
                  <button class="btn-action" @click=${() => this.triggerDirectView('notepad')}>📝 Notepad</button>
                  <button class="btn-action" @click=${() => this.triggerDirectView('diagram')}>📊 Diagram</button>
                  <button class="btn-action" @click=${() => this.triggerDirectView('dashboard')}>📈 Telemetry</button>
                </div>
                <div style="margin-top: 8px;">
                  <button class="btn-action" @click=${() => this.clearMainStage()} style="width: 100%; border-color: rgba(255, 0, 85, 0.4); color: #ff3b30; font-weight: bold; background: rgba(255, 0, 85, 0.05); cursor: pointer; transition: all 0.2s;">🧹 Clear Main Stage</button>
                </div>
              </div>

              <!-- Cast YouTube Feed -->
              <div class="widget-card">
                <div class="widget-title">📺 Cast YouTube Feed</div>
                <div class="form-group">
                  <span class="form-label">Video Link or ID</span>
                  <input class="ctx-input" type="text" placeholder="https://www.youtube.com/watch?v=..." .value=${this.ytUrl} @input=${(e: any) => this.ytUrl = e.target.value} />
                </div>
                <div class="form-row">
                  <div class="form-group">
                    <span class="form-label">Target Grid Panel</span>
                    <select class="select-control" .value=${this.ytPanel} @change=${(e: any) => this.ytPanel = parseInt(e.target.value)}>
                      <option value="1">Panel 1 (Top Left)</option>
                      <option value="2">Panel 2 (Top Right)</option>
                      <option value="3">Panel 3 (Bottom Left)</option>
                      <option value="4">Panel 4 (Bottom Right)</option>
                    </select>
                  </div>
                </div>
                <div class="switch-row">
                  <div class="switch-label-wrap">
                    <span class="switch-lbl">Autoplay Video</span>
                    <span class="switch-desc">Start playback automatically (muted)</span>
                  </div>
                  <label class="switch-container">
                    <input type="checkbox" ?checked=${this.ytAutoplay} @change=${(e: any) => this.ytAutoplay = e.target.checked} />
                    <span class="slider"></span>
                  </label>
                </div>
                <button class="cta" @click=${() => this.castYoutube()}>Cast to Stage Grid</button>
              </div>

              <!-- Presenter Camera Feed -->
              <div class="widget-card">
                <div class="widget-title">🎥 Presenter Camera Feed</div>
                <div class="switch-row">
                  <div class="switch-label-wrap">
                    <span class="switch-lbl">Enable Camera Grid Stream</span>
                    <span class="switch-desc">Acquire webcam and stream to chosen panel</span>
                  </div>
                  <label class="switch-container">
                    <input type="checkbox" ?checked=${this.camEnabled} @change=${(e: any) => this.togglePresenterCam(e.target.checked)} />
                    <span class="slider"></span>
                  </label>
                </div>
                <div class="form-group" ?disabled=${!this.camEnabled}>
                  <span class="form-label">Webcam Grid Slot</span>
                  <select class="select-control" ?disabled=${!this.camEnabled} .value=${this.camPanel} @change=${(e: any) => this.changeCamPanel(parseInt(e.target.value))}>
                    <option value="1">Panel 1 (Top Left)</option>
                    <option value="2">Panel 2 (Top Right)</option>
                    <option value="3">Panel 3 (Bottom Left)</option>
                    <option value="4">Panel 4 (Bottom Right)</option>
                  </select>
                </div>
              </div>

              <!-- Live Chyron Lower-Third -->
              <div class="widget-card">
                <div class="widget-title">🏷️ Speaker Lower-Third (Chyron)</div>
                <div class="form-group">
                  <span class="form-label">Presenter Name / Title</span>
                  <input class="ctx-input" type="text" placeholder="e.g. Curtis Krygier" .value=${this.chyronTitle} @input=${(e: any) => this.chyronTitle = e.target.value} />
                </div>
                <div class="form-group">
                  <span class="form-label">Subtitle / Affiliation</span>
                  <input class="ctx-input" type="text" placeholder="e.g. Lead Cloud Architect" .value=${this.chyronSub} @input=${(e: any) => this.chyronSub = e.target.value} />
                </div>
                <button class="btn-action ${this.chyronActive ? 'active' : ''}" @click=${() => this.toggleChyron()}>
                  ${this.chyronActive ? '📴 Hide Lower-Third' : '🏷️ Show Lower-Third'}
                </button>
              </div>

              <!-- Scrolling Ticker Tape -->
              <div class="widget-card">
                <div class="widget-title">💬 Scrolling News Ticker Tape</div>
                <div class="form-group">
                  <span class="form-label">Rolling Announcement Text</span>
                  <input class="ctx-input" type="text" placeholder="e.g. Next session starts in 10 minutes..." .value=${this.tickerText} @input=${(e: any) => this.tickerText = e.target.value} />
                </div>
                <button class="btn-action ${this.tickerActive ? 'active' : ''}" @click=${() => this.toggleTicker()}>
                  ${this.tickerActive ? '📴 Turn Off Ticker' : '💬 Start Scrolling Ticker'}
                </button>
              </div>

              <!-- Live Chat Broadcaster -->
              <div class="widget-card">
                <div class="widget-title">💬 Live Chat Broadcaster</div>
                <div class="widget-subtitle">Post a custom, glassmorphic comment card on the main stage</div>
                <div class="form-group">
                  <span class="form-label" style="display: flex; justify-content: space-between;">
                    Google Chat Space URL / ID
                    <span style="opacity: 0.7; font-weight: normal; font-size: 10px; color: ${this.chatSpaceId ? '#4caf50' : '#e0a030'};">
                      ${this.chatSpaceId ? '🔗 Polling this Chat space' : '⚠️ Paste the meeting\'s Chat space URL'}
                    </span>
                  </span>
                  <input class="ctx-input" type="text" placeholder="Paste the linked Chat space URL (chat.google.com/room/...)" .value=${this.chatSpaceIdInput} @input=${(e: any) => this.handleChatSpaceIdInput(e.target.value)} />
                  <span class="form-label" style="font-size: 10px; opacity: 0.6; margin-top: 4px; display: block; font-weight: normal;">
                    Requires continuous meeting chat ON. Open the meeting's Chat space and paste its URL here — Meet's in-call chat is not readable by ID alone.
                  </span>
                </div>
                <div class="form-group">
                  <span class="form-label">Sender Display Name</span>
                  <input class="ctx-input" type="text" placeholder="e.g. Curtis Krygier" .value=${this.simulatedSender} @input=${(e: any) => this.simulatedSender = e.target.value} />
                </div>
                <div class="form-group">
                  <span class="form-label">Comment Message</span>
                  <input class="ctx-input" type="text" placeholder="Type message to broadcast..." .value=${this.simulatedText} @input=${(e: any) => this.simulatedText = e.target.value} @keydown=${(e: KeyboardEvent) => e.key === 'Enter' && this.sendSimulatedComment()} />
                </div>
                <div style="margin-top: -6px; margin-bottom: 12px;">
                  <span class="form-label" style="font-size: 10px; margin-bottom: 4px; display: block; opacity: 0.7;">Suggested Presets</span>
                  <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                    <button class="btn-action" style="height: 24px; padding: 0 8px; font-size: 10px; flex: 1; min-width: 120px;" @click=${() => { this.simulatedSender = 'Audience Member'; this.simulatedText = 'wow I had no idea Google Meet was so versatile!'; }}>
                      💡 "wow I had no idea..."
                    </button>
                    <button class="btn-action" style="height: 24px; padding: 0 8px; font-size: 10px; flex: 1; min-width: 120px;" @click=${() => { this.simulatedSender = 'Producer'; this.simulatedText = 'Welcome everyone to the Meet Broadcast Studio live event!'; }}>
                      🎙️ "Welcome everyone..."
                    </button>
                    <button class="btn-action" style="height: 24px; padding: 0 8px; font-size: 10px; flex: 1; min-width: 120px;" @click=${() => { this.simulatedSender = 'Flight Analyst'; this.simulatedText = 'Airspace radar telemetry is running at 10.0x zoom!'; }}>
                      ✈️ "Airspace radar telemetry..."
                    </button>
                  </div>
                </div>
                <button class="cta" @click=${() => this.sendSimulatedComment()} ?disabled=${!this.simulatedText.trim()}>
                  💬 Broadcast Comment
                </button>
              </div>

              <!-- Intermission Slate -->
              <div class="widget-card">
                <div class="widget-title">⏳ Broadcast Intermission Slate</div>
                
                <div class="form-group">
                  <span class="form-label">Slate Badge</span>
                  <input class="ctx-input" type="text" placeholder="STANDBY / INTERMISSION" .value=${this.standbyBadge} @input=${(e: any) => this.standbyBadge = e.target.value} />
                </div>

                <div class="form-group">
                  <span class="form-label">Slate Title</span>
                  <input class="ctx-input" type="text" placeholder="Session Will Resume Shortly" .value=${this.standbyTitle} @input=${(e: any) => this.standbyTitle = e.target.value} />
                </div>

                <div class="form-group">
                  <span class="form-label">Slate Subtitle / Description</span>
                  <textarea class="ctx-input" style="height: 60px; resize: vertical; padding: 6px 10px;" placeholder="We are taking a brief break..." .value=${this.standbyDesc} @input=${(e: any) => this.standbyDesc = e.target.value}></textarea>
                </div>

                <div class="form-row" style="display: flex; gap: 10px;">
                  <div class="form-group" style="flex: 1;">
                    <span class="form-label">Minutes</span>
                    <input class="ctx-input" type="number" min="0" max="60" .value=${this.standbyTime} @input=${(e: any) => this.standbyTime = parseInt(e.target.value) || 0} />
                  </div>
                  <div class="form-group" style="flex: 1;">
                    <span class="form-label">Seconds</span>
                    <input class="ctx-input" type="number" min="0" max="59" .value=${this.standbySecs} @input=${(e: any) => this.standbySecs = parseInt(e.target.value) || 0} />
                  </div>
                </div>

                <button class="btn-action ${this.standbyActive ? 'active' : 'danger'}" @click=${() => this.toggleStandby()} style="margin-top: 10px;">
                  ${this.standbyActive ? '📴 Deactivate Slate' : '⏳ Activate Countdown Slate'}
                </button>
              </div>

              <!-- Soundboard & Emoji Reaction Rain -->
              <div class="widget-card">
                <div class="widget-title">🔊 Soundboard & Crowd FX</div>
                <div class="btn-grid-2">
                  <button class="btn-action" @click=${() => this.triggerSound('applause')}>👏 Applause</button>
                  <button class="btn-action" @click=${() => this.triggerSound('drumroll')}>🥁 Drumroll</button>
                  <button class="btn-action" @click=${() => this.triggerSound('buzzer')}>🚨 Buzzer</button>
                  <button class="btn-action" @click=${() => this.triggerSound('chimes')}>🔔 Chimes</button>
                </div>
                <div class="widget-title" style="margin-top: 10px; margin-bottom: 2px;">💬 Emoji Reaction Rain</div>
                <div class="reaction-grid">
                  <button class="reaction-btn" @click=${() => this.triggerEmoji('👏')}><span style="font-size:18px">👏</span><span class="reaction-name">Clap</span></button>
                  <button class="reaction-btn" @click=${() => this.triggerEmoji('🎉')}><span style="font-size:18px">🎉</span><span class="reaction-name">Party</span></button>
                  <button class="reaction-btn" @click=${() => this.triggerEmoji('🔥')}><span style="font-size:18px">🔥</span><span class="reaction-name">Hot</span></button>
                  <button class="reaction-btn" @click=${() => this.triggerEmoji('💡')}><span style="font-size:18px">💡</span><span class="reaction-name">Idea</span></button>
                </div>
              </div>
            </div>
          `}
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
