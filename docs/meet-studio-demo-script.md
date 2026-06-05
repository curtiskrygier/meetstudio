# Google Meet Studio — Demo Script
### *Persona: Google Meet Developer Product Lead*

---

> "What you're about to see isn't a prototype. It's a production add-on running live inside Google Meet — and everything it does is possible today, for any developer, using the public Meet Add-on SDK."

---

## The Setup

Two accounts. Same meeting. One presenter, one participant.

Open the side panel on both. This is where the story begins — because the side panel is where your add-on lives, and from there, you can reach every screen in the room.

---

## Act 1: The Presenter Experience

> "The presenter doesn't need to leave Meet. They don't need a second screen. Everything they need is here — in a 360px panel."

**What to show:**
- Sign in as Presenter → Google OAuth popup → token acquired
- MeetingID auto-detected from the SDK: `spaces/XXXXXXXX`
- Playbook selector populates with pre-built content libraries
- Slide selector shows labelled chapters within each playbook

**What to say:**
> "The SDK gives us `getMeetingInfo()`. One call. We know exactly which meeting we're in, with no user input. The presenter doesn't type a room code — the room finds them."

---

## Act 2: Launch — One Button to Rule the Room

> "This is the moment I always enjoy showing."

**What to show:**
- Click **▶ Launch Session**
- On the participant's screen: "Join the activity" prompt appears
- Participant clicks it — their main stage transforms
- The presenter's slide fires to the shared stage simultaneously

**What to say:**
> "One `startActivity()` call. The SDK delivers a URL to every participant's main stage simultaneously. Not a screen share. Not a link in chat. The content appears — rendered natively, in the meeting, on every screen in the room. That's the power of the main stage."

**SDK moment to highlight:**
```
startActivity({
  mainStageUrl:   '…/main_stage.html?join_session=spaces/XXX',
  sidePanelUrl:   '…/',
  additionalData: '{ "session": "spaces/XXX" }'
})
```
> "Three parameters. Main stage URL, side panel URL for joiners, and a data payload. The participant's side panel auto-configures from `additionalData` — no manual state passing."

---

## Act 3: The Stage is a Canvas

> "Here's where we go beyond slides."

The MeetStudio main stage runs A2UI — a composable component system that renders directly in the meeting window. Show what's possible:

**Data Visualisation**
- Fire `dataviz_demo` → live charts, sankey flows, cohort retention grids render in the stage
- > "This isn't an iframe embed of a dashboard. These are native components — rendered at 16:9, GPU-accelerated, inside Meet."

**Media Panels**
- Cast a YouTube feed to Panel 1 of a grid layout
- Switch to split → grid → single with layout controls
- > "The grid layout API lets you compose up to four content areas simultaneously. Video, data, documents — all in one stage."

**Live Overlays**
- Toggle the chyron lower-third with presenter name
- Fire a scrolling ticker tape
- Trigger emoji rain
- > "These aren't just gimmicks. For broadcast-style events, this is the production layer. Chyrons, tickers, reactions — all driven from the side panel, all appearing on every participant's stage."

**Standby Slate with Countdown**
- Activate the intermission slate → countdown timer animates live
- > "The stage is always yours. Between segments, between speakers — you control what participants see."

---

## Act 4: Individual Experience — The Hidden Capability

> "This is the part most developers don't know is possible."

**What to show:**
- Participant opens side panel → "Waiting for presenter..."
- Presenter launches → participant panel flips to name entry
- Participant types their name → registered
- Presenter sees them by name in the participant list
- Hit **Send** next to their name → only that participant's stage updates

**What to say:**
> "Every participant gets their own private stage space — created silently when they join. The presenter sees them by name. They can broadcast to all, or target one person. Same infrastructure, two routing paths."

> "Think about what this enables: personalised content, adaptive presentations, branching demos, assessment flows. All inside a standard Google Meet call."

---

## Act 5: The Playbook Pattern

> "Now let me show you how this scales."

**What to show:**
- Select `read_the_room` playbook
- Fire `cover` → `problem` → `approach` → `proof` slides in sequence
- > "Each slide is a function. It builds an A2UI surface and pushes it to stage_listeners. No page reload. No transition delay. Instant."

**What to say:**
> "A playbook is just a collection of slide builders — Python functions that produce component trees. The presenter fires them from the control panel; they fan out to every connected stage in the session. Want to build a 20-slide presentation that works live in Meet? Write 20 functions."

---

## Act 6: The Control Room

> "For power users — and for demos — the presenter dashboard is the view from the director's chair."

**What to show:**
- Open `/presenter/{space_id}?ticket={api_key}` in browser
- WebSocket connects → engine goes online
- Select playbook and slide → fire → content appears on stage in Meet

**What to say:**
> "This isn't part of the add-on. It's a standalone web app — also running on Cloud Run, also connecting to the same WebSocket infrastructure. Any authorised client can drive the stage. The meeting is just one output channel."

---

## The SDK Capabilities — Summarised Live

| What we just did | SDK / API behind it |
|---|---|
| Auto-detected meeting | `getMeetingInfo().meetingId` |
| Pushed stage to all | `startActivity({ mainStageUrl })` |
| Auto-joined participant | `getFrameOpenReason() === 'JOIN_ACTIVITY'` |
| Passed state to participant | `ActivityStartingState.additionalData` |
| Individual slide targeting | Server fan-out via private participant spaces |
| Live component rendering | A2UI + WebSocket broadcast to `stage_listeners` |
| Inter-frame data | `frameToFrameMessage` / `notifyMainStage` |

---

## Closing Line

> "Everything you saw tonight — the stage, the playbooks, the individual targeting, the overlays — is built on three public APIs: the Meet Add-on SDK, Cloud Run, and a WebSocket. The meeting becomes the interface. Your content becomes the experience. And none of your participants ever left Google Meet."

---

## What's Coming / What's Possible Next

- **Meet Media API** — real-time audio/video stream access (requires GCP allowlist; separate programme)
- **Participant roster** — currently not exposed in SDK; watch for future releases
- **Multi-activity coordination** — SDK today supports one activity at a time; architectural patterns exist to work within this
- **Adaptive content** — use `additionalData` + participant registration to serve personalised stage content based on role, cohort, or response

---

*Deploy command: always run from `meetstudio/` root, not from `appsscript/`.*
*Control room: `/presenter/{space_id}?ticket={STAGE_API_KEY}`*
