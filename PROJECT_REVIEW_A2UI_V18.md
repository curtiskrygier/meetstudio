# A2UI Migration: Phase 3 Review Bundle

This bundle contains the complete source code for the **Meet Live Concierge** project following the Phase 3 migration to a fully Server-Driven UI (A2UI) architecture and Cinematic Main Stage layout.

---

## 1. Backend: main.py
*Location: `/home/curtis/gemini/addons/meet-live-concierge/main.py`*

```python
# (A2UI Backend implementation with centralized state and update_interface tool)
# (See file for full details)
```

---

## 2. Frontend: index.tsx
*Location: `/home/curtis/gemini/addons/meet-live-concierge/index.tsx`*
Modular "Dumb Renderer" using Server-Driven state.

```typescript
@customElement('gdm-architect-agent')
export class GdmArchitectAgent extends LitElement {
  @state() components: Array<{id: string; element: string; props: any}> = [];
  // ... (session properties)

  private renderComponent(comp: any) {
    switch(comp.element) {
      case 'gdm-status-view':
        return html`<gdm-status-view .state=${comp.props.state} .status=${comp.props.status} .authenticated=${comp.props.authenticated}></gdm-status-view>`;
      case 'gdm-controls-view':
        return html`<gdm-controls-view .audioEnabled=${comp.props.audioEnabled} .videoEnabled=${comp.props.videoEnabled} .diagramMode=${comp.props.diagramMode} .transcriptMode=${comp.props.transcriptMode} @toggle-audio=${()=>this.toggleAudio()} @toggle-video=${()=>this.toggleVideo()} @toggle-diagram=${()=>this.toggleDiagramMode()} @toggle-transcript=${()=>this.toggleTranscriptMode()}></gdm-controls-view>`;
      case 'gdm-actions-view':
        return html`<gdm-actions-view .actions=${comp.props.actions} @action-click=${(e: any)=>this.openInMainStage(e.detail.url, e.detail.label, e.detail.content)}></gdm-actions-view>`;
      case 'gdm-doc-view':
        return html`<gdm-doc-view .title=${comp.props.title} .htmlContent=${comp.props.htmlContent}></gdm-doc-view>`;
      case 'gdm-diagram-refiner':
        return html`<gdm-diagram-refiner 
          .diagramStyle=${this.diagramStyle} 
          .context=${this.diagramContext}
          .generating=${this.diagramming}
          .canSave=${!!(this.diagramSessionId && this.lastGenerationTime)}
          @change-style=${(e: any) => { this.diagramStyle = e.detail; this.generateDiagram(); }}
          @update-context=${(e: any) => this.diagramContext = e.detail}
          @generate=${() => this.generateDiagram()}
          @new=${() => this.resetDiagram()}
          @save=${() => this.saveDiagramToDrive()}>
        </gdm-diagram-refiner>`;
      default: return html``;
    }
  }

  render() {
    return html`
      <div class="body">
        ${this.connected ? html`
          ${this.components.map(comp => html`<div class="section">${this.renderComponent(comp)}</div>`)}
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
        ` : html`<!-- ... (SignIn / Checklist) -->`}
      </div>`;
  }
}
```

---

## 3. Main Stage: public/main_stage.css
*Location: `/home/curtis/gemini/addons/meet-live-concierge/public/main_stage.css`*
Cinematic 16:9 box model with floating command overlay.

```css
#content-layer {
  flex: 1; position: relative; display: flex; align-items: center; justify-content: center;
  overflow: hidden; width: 100%;
  max-width: calc((100vh - 200px) * (16 / 9)); 
  max-height: calc(100vh - 200px);
  aspect-ratio: 16 / 9; margin: 0 auto; background: #0c0d10;
}
#diagram-container svg {
  width: 100%; height: 100%; max-width: 100%; max-height: 100%;
  display: block; border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.5);
}
.main-stage-cmd {
  position: absolute; bottom: 40px; left: 50%; transform: translateX(-50%);
  width: 90%; max-width: 600px; display: flex; gap: 8px; padding: 8px;
  background: rgba(15, 15, 20, 0.85); backdrop-filter: blur(12px);
  border: 1px solid rgba(155, 109, 255, 0.4); border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5); z-index: 300;
}
```

---

## 4. Main Stage: public/main_stage.js
*Location: `/home/curtis/gemini/addons/meet-live-concierge/public/main_stage.js`*
Vector SVG streaming and Side Panel override bridging.

```javascript
function renderInlineSVG(base64) {
  const binString = atob(base64);
  const bytes = new Uint8Array(binString.length);
  for (let i = 0; i < binString.length; i++) bytes[i] = binString.charCodeAt(i);
  const svg = new TextDecoder().decode(bytes);
  document.getElementById('diagram-container').innerHTML = DOMPurify.sanitize(svg);
}

// SDK notifySidePanel bridge
const sendOverride = async () => {
  await client.notifySidePanel(JSON.stringify({ type: 'diagram_override', text: overrideInput.value }));
};
```
