# Handover — 3D Catalogue (for Gemini)

Picking up "point 2": make the 3D engine genuinely advanced **and** A2UI-friendly.
Prior session landed the composable primitives layer + a safe committed checkpoint
(rev `00079-8dr`). Read `A2UI_PRIMITIVES_PLAN.md` first — it defines the conventions
you must follow (atoms vs molecules, CSP-safe styling, the CATALOG descriptor as
single source of truth, the headless dev loop). This doc is the 3D-specific brief.

## Goal

Two intertwined objectives:
1. **Make it look advanced.** `gdm-3d-airspace` is currently an *orthographic* hand-rolled
   projection on a 2D canvas — reads like a schematic, not a 3D scene.
2. **Make it A2UI-friendly / reusable.** It's airspace-specific. Generalise the engine into
   a reusable **`gdm-3d-scene`** the agent drives with data (points / links / camera), so 3D
   stops being a bespoke set-piece and becomes a catalogue capability.

## Where the code is

`internal/components/gdm_stage_3d_airspace.ts`:
- `getFlight3DPosition()` — maps a flight to a 3D point.
- `_project()` (~line 660) — the projection. Currently **orthographic**:
  `f = min(_canvasW,_canvasH)*0.95; u = _canvasW/2 + x2*scale; v = _canvasH/2 - z2*scale`
  (no perspective divide). `cameraPitch`/`cameraYaw` rotate the scene.
- Draw passes: `_drawGrid`, `_drawGlideSlope`, `_drawFlightsAndTrails`, `_drawHUDHorizon`,
  `_drawScene` (the rAF loop). Logical dims are `_canvasW`/`_canvasH` (CSS px); buffer is
  scaled by `devicePixelRatio`.
- **Already fixed last session:** the "renders only in the top half" bug — `_handleResize`
  now measures `.viewport-wrapper`, the `ResizeObserver` watches the host + wrapper, with a
  rAF re-measure and a zero-size guard. Don't regress this; keep the draw loop using
  `_canvasW/_canvasH` (CSS px), never the raw buffer dims.

Descriptor entry: `gdm-3d-airspace` in `app/a2ui_catalog.py` (`in_prompt=False`, strict).

## Two paths (recommend A first)

**Path A — push the 2.5D canvas engine (no new deps, high ROI):**
- True **perspective**: divide projected size by depth (camera-space z) so near objects loom.
- **Depth fog**: fade size/opacity with distance (atmospheric perspective).
- **Painter's-algorithm sort**: draw back-to-front so overlaps are correct.
- **Shaded terrain heightfield** instead of the flat grid; lit by height/normal.
- Aircraft as **heading-oriented glyphs** + velocity-faded motion trails + bloom.
- Depth-anchored labels with leader lines.

**Path B — WebGL/Three.js:** real meshes, lighting, terrain, post bloom. Far more impressive
but a large rewrite + heavy bundle (~Three.js). Only if Path A isn't enough.

## The A2UI-friendly move: `gdm-3d-scene`

Generalise rather than hard-code airspace. Proposed props (drive from data, agent-composable):
- `points`: `[{id,x,y,z,color,label,glyph,size}]`
- `links`: `[{from,to,color}]` (optional edges/paths)
- `camera`: `{pitch,yaw,zoom,fov}` (+ `autoOrbit`, `lockTo` id)
- `terrain`/`grid`/`fog` toggles
Then `gdm-3d-airspace` becomes a thin **molecule** that feeds flight data into `gdm-3d-scene`
(same way the clock is a molecule over atoms). Other domains (org charts, network maps,
point clouds) reuse the same 3D atom — that's the catalogue win.

## Conventions to follow (from the primitives plan)

- Register any new component in `CATALOG` (`app/a2ui_catalog.py`) + import in `main_stage.ts`.
- Fixed styling → static shadow CSS; dynamic agent-set styling → inline (CSP now allows
  `style-src 'unsafe-inline'`; `script-src` stays strict).
- Validation is warn-don't-block; unknown component *name* is the only hard error.
- Realtime data must NOT flow through the LLM. Agent sets the scene/structure occasionally;
  a server loop (or eventually `dataModelUpdate` binding) pushes per-frame data.

## How to verify (no Meet session, no cloud deploy needed)

Headless stage capture via the stage-ticket flow:
- `uvicorn main:app --port 8085` (serves `dist/` + API + `/ws/stage`); `npm run build` to refresh.
- Adapt `capture_atoms.py` / `capture_composable.py` (Playwright opens
  `GET /api/stage-ticket/{space}` → `stage_url`, becomes a stage listener, renders, screenshots).
- `tsc --noEmit` + `python -m pytest tests/test_a2ui_stage.py` before deploy.
- Deploy: `gcloud run deploy meet-live-concierge --source . --region us-central1 --timeout=3600
  --session-affinity --allow-unauthenticated --project=centered-planet-497209-r5`
  (build-time env from committed `.env.production`; do NOT pass `--set-env-vars` — it replaces
  the whole runtime env set).

## Definition of done

A `gdm-3d-scene` (or a clearly-upgraded `gdm-3d-airspace`) that: renders with perspective +
depth cues, fills the stage, is driven by data props, is registered in the catalogue, verified
headlessly, and the Toulouse airspace demo still works through it.
