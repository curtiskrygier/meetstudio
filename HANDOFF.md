# LLM Handoff - Meet Live Concierge

## Summary of Recent Changes

### 1. Branding Updates (Completed)
- Renamed all instances of **"Agent Archi"** to **"Gemini Agent Architect"**.
- Updated: `public/main_stage.html`, `public/diagram_stage.html`, and status messages in `index.tsx`.

### 2. "New" Feature Logic (Clean Slate)
- **Voice Transcript Isolation**: Implemented `transcriptStartIndex` in `index.tsx`. Only transcript data since starting a session is sent to Gemini.
- **Chat Message Filtering**: Implemented `diagramSessionStartTime`. Chat history from earlier in the meeting is now ignored.
- **UI State Reset**: `actionLinks` (Workspace Actions) are now cleared when starting a new session.

### 3. SVG Rendering Fixes (Critical)
- **Safe Context Insertion**: Switched from `.format()` to `.replace("{context}", context)` in `main.py`. This prevents `KeyError` crashes when meeting discussions contain curly braces (e.g., code snippets or transcription artifacts).
- **Improved Extraction**: Implemented robust D2 code block extraction. It now correctly identifies and strips conversational text before or after the triple backticks in Gemini's response.
- **Bundled Assets**: Added the `--bundle` flag to the `d2` command to ensure all icons and assets are embedded as data URIs in the SVG, preventing 404s on the frontend.
- **Idiomatic D2 Config**: Moved `d2-config` to the top-level (out of `vars`) to ensure it is correctly parsed by the renderer.

### 4. Brainstorming Mode (Backlog)
- **Status**: Feature **rolled back** and moved to the backlog (`STATUS.md`).
- **Reason**: Hallucinations with empty context and UI sync complexity.

## Current Status

### 1. Deployment (Fully Restored & Robust)
- **Status**: **Success**. The latest revision (`meet-live-concierge-00097-frw`) is live and has been verified with clean logs.
- **Stability**: The `KeyError` has been eliminated, and diagram generation is now much more robust.

## Technical Context
- **Backend**: FastAPI / Cloud Run (`main.py`)
- **Frontend**: Lit / TypeScript (`index.tsx`)
- **Reasoning Engine**: Vertex AI (GE04)
