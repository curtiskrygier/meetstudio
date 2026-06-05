# MeetStudio — Deployment Reference

Production service for the Google Meet Studio add-on. Cloud Run backend + Vite/TypeScript frontend.

---

## Active Configuration

| Key | Value |
|---|---|
| GCP Project | `meet-studio-498405` (number: `738395425892`) |
| Gemini/Vertex AI Project | `weighty-arcadia-196219` |
| Cloud Run Service | `meetstudio` |
| Region | `europe-west1` |
| Service URL | `https://meetstudio-738395425892.europe-west1.run.app` |
| Artifact Registry | `europe-west1-docker.pkg.dev/meet-studio-498405/cloud-run-source-deploy/meetstudio` |
| Secret Manager | `stage-api-key` → `STAGE_API_KEY` env var |

---

## Canonical Deploy Command

**Always run from the project root — `meetstudio/`, never from `appsscript/`.**

Running from a subdirectory uploads the wrong directory and silently deploys stale code. This has caused multiple wasted deploy cycles.

```bash
cd /home/curtis/gemini/addons/meetstudio
gcloud builds submit \
  --config cloudbuild.yaml \
  --project meet-studio-498405 \
  --timeout=1200 \
  .
```

The `cloudbuild.yaml` does everything: `docker build --no-cache` → push to Artifact Registry → `gcloud run deploy`.

`--no-cache` is mandatory. Without it, Docker layer caching preserves old JS bundles across deploys even though the source changed.

---

## Verifying a Deploy Landed

### Version badge (fastest)
The topbar shows a cyan badge: `v18.1 · MM-DD HH:MM`

The timestamp comes from `GET /api/version` at runtime (server start time). It changes on every deploy. If the timestamp matches when you deployed, the new code is live.

```bash
curl -s https://meetstudio-738395425892.europe-west1.run.app/api/version
# → {"version": "18.1", "built": "06-05 22:14"}
```

### Bundle check
```bash
curl -s https://meetstudio-738395425892.europe-west1.run.app/ | grep -o 'assets/index-[^"]*\.js'
```

### Active connections
```bash
KEY=$(gcloud secrets versions access latest --secret=stage-api-key --project=meet-studio-498405)
curl -s -H "Authorization: Bearer $KEY" \
  https://meetstudio-738395425892.europe-west1.run.app/api/telemetry
```

### Active space IDs (from logs)
```bash
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="meetstudio" AND textPayload=~"init"' \
  --project=meet-studio-498405 --limit=5 --format="value(textPayload)"
```

---

## Env-var-only Update (no rebuild)

```bash
gcloud run services update meetstudio \
  --region europe-west1 \
  --project meet-studio-498405 \
  --update-env-vars="KEY=value"
```

---

## Key Env Vars

| Var | Where set | Purpose |
|---|---|---|
| `GEMINI_PROJECT` | `cloudbuild.yaml` runtime | Vertex AI project for Gemini calls |
| `REGION` | `cloudbuild.yaml` runtime | Cloud Run region |
| `CLIENT_ID` | `cloudbuild.yaml` build + runtime | OAuth client ID (must match `.env.production`) |
| `STAGE_API_KEY` | Secret Manager | Auth for producer API endpoints and `/ws/stage` |
| `CLIENT_ID` / `CLOUD_PROJECT_NUMBER` | `.env.production` | Injected at Vite build time for the SDK init |

> If `CLIENT_ID` or `CLOUD_PROJECT_NUMBER` changes, update **both** `.env.production` (Vite build-time) and `cloudbuild.yaml` (runtime).

---

## Apps Script / Clasp

The `appsscript/` folder contains the Apps Script manifest (`appsscript.json`) that configures the Meet add-on entry point. Changes here require:

```bash
cd appsscript
clasp push --force
clasp deploy --description "description of change"
```

The deployment ID from `clasp deployments` (format `AKfycb...`) must be set in:
- GCP Console → APIs & Services → Google Workspace Marketplace SDK → App Configuration → Deployment ID

After updating the Marketplace SDK config, the Store Listing must be **re-published** for the change to reach all users.

**Common gotcha:** `clasp deployments` are immutable snapshots. You can't update `@2` — you create `@5`. Update the Marketplace SDK to point to the new ID and republish.

---

## Presenter Control Room

```
https://meetstudio-738395425892.europe-west1.run.app/presenter/{space_id}?ticket={STAGE_API_KEY}
```

`space_id` is the full `spaces/XXXXXXXX` from `getMeetingInfo().meetingId` (not the `vpp-xxxx-xxx` room code).

The WebSocket for the control room connects to `/ws/stage` using the API key directly as the ticket.

---

## Vertex AI API

The draft-and-fire playbook feature uses Gemini via Vertex AI in project `weighty-arcadia-196219`. Required API:

```bash
gcloud services enable aiplatform.googleapis.com --project=weighty-arcadia-196219
```

This was disabled and caused 500 errors on the `/api/playbook/draft-from-doc/` endpoint.

---

## YAML Playbook Templates

Playbooks live in `playbooks/*.yaml`. Each slide has an `id`, a `template`, and template-specific fields.

### Available templates

| Template | Use case |
|---|---|
| `title` | Opening slide — headline, sub, badge |
| `list_5` | Bullet point list with up to 5 items |
| `hero_stat` | Single large metric with delta indicator |
| `split_with_action` | Two-column layout with action buttons |
| `table_view` | Data table |
| `market_ticker` | Live market/data ticker display |
| `signoff` | Closing slide — lines, brands, chef line |
| `airspace_command_deck` | Specialised radar/aerospace display |
| `landing_queue_display` | Airport/ATC queue display |

### Minimal playbook structure

```yaml
name: my_playbook
slides:
  - id: cover
    template: title
    badge: { text: "LIVE DEMO", type: primary }
    title: "HEADLINE HERE"
    subtitle: "Supporting line"
    next_action:
      text: "Next"
      fires: detail

  - id: detail
    template: list_5
    badge: { text: "KEY POINTS", type: cyan }
    title: "WHAT WE COVER"
    points:
      - "First point"
      - "Second point"
      - "Third point"
    next_action:
      text: "Sign Off"
      fires: close

  - id: close
    template: signoff
    lines:
      - { text: "LINE ONE.",   color: white }
      - { text: "LINE TWO.",   color: phosphor }
      - { text: "LINE THREE.", color: cyan }
    brands:
      left:  "YOUR BRAND"
      right: "MEETSTUDIO"
    badge_text: "SHORT · PUNCHY · TAGLINE"
    chef_line:  "ONE SENTENCE SUMMARY."
    chef_sub:   "supporting detail."
    tagline:    "closing thought."
```

### Playbook reload

After adding or editing a YAML file, the server hot-reloads playbooks automatically via `register_yaml_playbooks_in_dir()`. No restart needed.

### Draft-from-URL

The "Draft & Fire" widget in Studio Mode can generate a YAML playbook from a URL, Google Doc, or free-text topic via Gemini. The generated YAML is saved to `playbooks/` and fired immediately.
