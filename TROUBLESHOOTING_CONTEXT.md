# Troubleshooting Context: Meet Live Concierge Diagram Failures

## 1. Architecture Overview
**Flow**: `Google Meet > Chrome (SDK) > WebSockets > FastAPI (Cloud Run) > Gemini Multimodal Live (Native Audio) > D2 Rendering Engine > Google Meet Main Stage (Broadcast Hub) > Google Drive`

- **Live Agent**: Gemini 2.5 Flash handles the audio stream and provides transcriptions.
- **Architect Agent**: A separate Gemini 2.5 Flash call takes the transcript and generates D2 code.
- **D2 Engine**: The `d2` CLI runs inside the Docker container to convert D2 code -> SVG.
- **Main Stage**: A unified `main_stage.html` serves as a persistent overlay for Captions, Diagrams, and Documents.

---

## 2. Current Issues
1.  **Compiler Errors**: D2 is frequently failing with `double quoted strings must be terminated with "`.
2.  **Unknown Keywords**: Occasional errors like `unknown shape "web"`.
3.  **Icon Inconsistency**: Google brand icons are not rendering reliably.
4.  **Reset Logic**: The "Save & New" and "New" buttons sometimes fail to clear the stage for all participants.

---

## 3. Representative Error Logs (Cloud Run)
```text
[d2] error detail: err: failed to compile ../tmp/tmp4o8j9s4p/diagram.d2: /tmp/tmp4o8j9s4p/diagram.d2:3:21: double quoted strings must be terminated with "
[d2] error detail: err: failed to compile ../tmp/tmpnind3u8p/diagram.d2: /tmp/tmpnind3u8p/diagram.d2:4:18: unknown shape "web"
[diagram] render failed: err: failed to compile ../tmp/tmpy3kv2qic/diagram.d2: /tmp/tmpy3kv2qic/diagram.d2:4:21: double quoted strings must be terminated with "
```

---

## 4. Backend Logic (`main.py`)

### D2 Prompt and Icons
```python
D2_PROMPT = """You are an expert systems architect. Analyse the meeting context below and generate a D2 diagram using DOT SYNTAX.

Rules:
- Output ONLY valid D2 code. No markdown, no backticks, no explanation.
- CRITICAL: EVERY node name MUST be wrapped in double quotes, even in attributes.
- Use DOT SYNTAX for attributes: "Node Name".shape: cloud
- For icons, use: "Node Name".icon: "URL"
- Icons available:
  - Google Meet: https://www.gstatic.com/images/branding/product/2x/meet_2020q4_48dp.png
  - Google Docs: https://www.gstatic.com/images/branding/product/1x/docs_48dp.png
  - Google Sheets: https://www.gstatic.com/images/branding/product/1x/sheets_48dp.png
  - Gemini: https://www.gstatic.com/lamda/images/gemini_sparkle_v2_60b73b22b163d0434.svg
- Start with:
  direction: right
  title: "Meeting Architecture"
- Keep it under 10 nodes.

Example Output:
direction: right
title: "Sample Arch"
"User" -> "Gemini": "Prompts"
"Gemini".shape: cloud
"Gemini".icon: "https://www.gstatic.com/lamda/images/gemini_sparkle_v2_60b73b22b163d0434.svg"
"""
```

### Generation & Cleaning Function
```python
async def generate_diagram(...):
    # ... GenAI call ...
    d2_code = response.text.strip()
    
    # Strip markdown fences
    d2_code = re.sub(r'^```[a-z]*\n?', '', d2_code, flags=re.MULTILINE)
    d2_code = re.sub(r'```$', '', d2_code, flags=re.MULTILINE).strip()
    
    # Cleaning logic
    lines = d2_code.splitlines()
    clean_lines = []
    for line in lines:
        l = line.strip()
        if not l or l.endswith(':'): continue
        l = re.sub(r'//.*$', '', l).strip()
        if l: clean_lines.append(l)
    
    d2_code = "\n".join(clean_lines)
    # ... render call ...
```

---

## 5. Side Panel Logic (`index.tsx`)

### Reset and Save Logic
```typescript
  private async resetDiagram() {
    this.diagramContext = '';
    this.diagramSessionId = crypto.randomUUID();
    // Tells everyone to clear the stage and show "listening"
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'broadcast_view',
        mode: 'diagram',
        diag_id: this.diagramSessionId
      }));
    }
  }

  private async saveAndNewDiagram() {
    await this.saveDiagramToDrive();
    await this.resetDiagram();
  }
```

---

## 6. Main Stage UI (`public/main_stage.html`)

### Sizing and SVG Reset
```html
<style>
    #diagram-container svg {
      width: 100%;
      height: 100%;
      display: block;
      background: #fff;
      border-radius: 12px;
      padding: 16px;
    }
</style>

<script>
    function updateTranscript(msg) {
        // ... Bumping logic (limited to 2 lines) ...
        // turn.prev-2, turn.old { display: none !important; }
    }

    async function pollDiagram() {
      // ... fetches SVG and injects into #diagram-container ...
      const svgEl = container.querySelector('svg');
      if (svgEl) {
        svgEl.removeAttribute('width');
        svgEl.removeAttribute('height');
        svgEl.style.width = '100%';
        svgEl.style.height = '100%';
      }
    }
</script>
```
