# Status Report — Meet Live Concierge

## Current State
I have implemented the **Diagramming Feature** (D2 architecture generation from meeting transcripts).
- **Backend:** `main.py` has the logic to use Gemini 2.5 Flash to generate D2 code, render it to SVG via the `d2` binary, and serve it via `/api/diagram`.
- **Frontend:** `index.tsx` has a "Diagram" button that captures the current transcript and launches `diagram_stage.html` in the Meet main stage.
- **Infrastructure:** `Dockerfile` is updated to install the `d2` binary.
- **Deployment:** The service is live on Cloud Run.

## The Blocker: Missing Transcription
The diagramming feature requires a text transcript. Currently, no transcript is being captured, which makes the button unusable.

### 1. Backend Failure (`google-genai` SDK)
I attempted to enable real-time transcription in the `LiveConnectConfig` inside `main.py`, but it causes a **ValidationError** that crashes the WebSocket session.

**Failing Code:**
```python
config = types.LiveConnectConfig(
    response_modalities=["AUDIO", "TEXT"],
    generation_config={
        "speech_config": {
            "speech_recognition_config": {"enabled": True}
        }
    },
    # ...
)
```

**Error Log:**
```
[ws] ValidationError: 1 validation error for LiveConnectConfig
generation_config.speech_config.speech_recognition_config
Extra inputs are not permitted [type=extra_forbidden, input_value={'enabled': True}, input_type=dict]
```

### 2. Frontend Failure (Web Speech API)
I tried a client-side fallback using the browser's `SpeechRecognition` API. This failed with:
`speech error:not allowed`
This is expected because the Meet Add-on runs in a cross-origin iframe where microphone access for the Web Speech API (as opposed to the Meet Media API) is likely restricted by Permissions Policy.

## Where Help is Needed
I need the **correct schema/syntax** to enable real-time input transcription (STT) for the user's audio stream in the `google-genai` (Python) SDK for the Multimodal Live API.

Specifically:
- How do I configure `LiveConnectConfig` or `generation_config` to ensure `server_content.input_transcription` events are emitted by the model?
- If the `google-genai` SDK doesn't support this specific field yet via `types.LiveConnectConfig`, is there a raw dictionary bypass or an alternative configuration (e.g., system instruction or tool) to get text back for user speech?

**Current build version: v16** (Backend transcription attempt active but crashing).