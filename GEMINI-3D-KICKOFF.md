# Gemini / agy kickoff prompt — 3D catalogue + asset updates

Paste the block below to Gemini (agy). It assumes the repo
`/home/curtis/gemini/addons/meet-live-concierge` at the committed checkpoint
(rev `00079-8dr`).

---

You are continuing the meet-live-concierge A2UI work — **point 2: the 3D catalogue**, plus
**asset/skill updates**. Before doing anything, READ in full:
`A2UI_PRIMITIVES_PLAN.md`, `HANDOVER-3D-CATALOGUE.md`, and
`/home/curtis/gemini/skills/meet-live-concierge/SKILL.md`. They define the conventions you
MUST follow (atoms vs molecules; catalogue descriptor = single source of truth in
`app/a2ui_catalog.py`; warn-don't-block validation; CSP-safe styling; realtime data must NOT
flow through the LLM; the headless stage dev workflow).

Run the work as **three parallel sub-agents** (the file sets are disjoint, so they won't
collide). You are the integrator: review each, then build/verify/deploy once at the end.

**Sub-agent A — 3D scene engine (Path A, no new deps).**
Build `internal/components/gdm_stage_3d_scene.ts`: a reusable, data-driven 3D atom with props
`points:[{id,x,y,z,color,label,glyph,size}]`, `links:[{from,to,color}]`,
`camera:{pitch,yaw,zoom,fov,autoOrbit,lockTo}`, and `terrain`/`grid`/`fog` toggles. Upgrade the
projection from the current orthographic math in `gdm_stage_3d_airspace.ts` (`_project`, ~line
660) to **true perspective** (divide by camera-space depth), add **depth fog**, **painter's-
algorithm back-to-front sorting**, a **shaded terrain heightfield**, **heading-oriented glyphs**,
velocity-faded trails, and bloom. Preserve the existing resize fix (observe host/`.viewport-
wrapper`, rAF re-measure, zero-size guard; draw in CSS-px `_canvasW/_canvasH`). Keep styling
CSP-safe.

**Sub-agent B — generalize airspace + catalogue + demo + verify.**
Refactor `gdm-3d-airspace` into a thin molecule that feeds flight data into `gdm-3d-scene`
(like `gdm-clock` over atoms). Register `gdm-3d-scene` in `CATALOG` (`app/a2ui_catalog.py`) and
import it in `main_stage.ts`. Update `demo_a2ui_toulouse_airspace.py` to drive it. Verify
headlessly (adapt `capture_composable.py`/`capture_atoms.py` via `/api/stage-ticket`), and run
`npx tsc --noEmit` + `python -m pytest tests/test_a2ui_stage.py`.

**Sub-agent C — asset / skill updates.**
Using the `d2-architect-standard` skill, generate/update `diagram.d2` + render `diagram.svg` for
`skills/meet-live-concierge/` (and `skills/a2ui-spec/` if the catalogue changed):
`d2 -t 0 skills/<skill>/diagram.d2 skills/<skill>/diagram.svg`. Bump the SKILL.md "Last verified"
line. Then sync to Drive: `export BW_SESSION=$(bw unlock --raw)` then `sync-skills`
(per /home/curtis/gemini/CLAUDE.md). Do NOT touch component or backend files.

**Guardrails (all sub-agents):**
- Fixed styling → static shadow CSS; dynamic agent-set styling → inline (CSP allows
  `style-src 'unsafe-inline'`; `script-src` stays strict).
- Unknown component *name* is the only hard validation error; prop issues are warnings.
- Don't re-send the full surface through the LLM per frame — agent sets structure, a server
  loop pushes data; prefer `dataModelUpdate` binding where you can.
- **Confirm with the user before deploying or writing outside the repo.**
- Deploy (only at the end, after verification, with user OK):
  `gcloud run deploy meet-live-concierge --source . --region us-central1 --timeout=3600
  --session-affinity --allow-unauthenticated --project=centered-planet-497209-r5`
  (build env from committed `.env.production`; do NOT pass `--set-build-env-vars` or
  `--set-env-vars` — the latter replaces the whole runtime env set).

**Done when:** `gdm-3d-scene` renders with perspective + depth cues, fills the stage, is
data-driven, registered in the catalogue, headlessly verified, the Toulouse demo works through
it, tests + tsc pass, the skill diagram + SKILL.md are updated and synced, and it's deployed.
