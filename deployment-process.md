# Meet Live Concierge — Deployment Process

All secrets are referenced as shell variables. Set them before running any command.

---

## Variables

```bash
export GCP_PROJECT=agent-archi
export GCP_PROJECT_NUMBER=649226456677
export REGION=us-central1
export SERVICE_NAME=meet-live-concierge
export CLIENT_ID=649226456677-kg2d06f201h6narlrddgass1qs2ka3e1.apps.googleusercontent.com
export GEMINI_PROJECT=agent-archi
export KORE_VOICE=Charon
# Optional: export SYSTEM_PROMPT="..."
```

---

## Step 1 — Enable APIs

```bash
gcloud services enable run.googleapis.com aiplatform.googleapis.com cloudbuild.googleapis.com \
  --project=$GCP_PROJECT
```

---

## Step 2 — IAM grants

```bash
# Vertex AI access for Cloud Run SA
gcloud projects add-iam-policy-binding $GCP_PROJECT \
  --member="serviceAccount:${GCP_PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# Cloud Build SA needs storage + run access (required for --source deploys)
gcloud projects add-iam-policy-binding $GCP_PROJECT \
  --member="serviceAccount:${GCP_PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding $GCP_PROJECT \
  --member="serviceAccount:${GCP_PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"
```

---

## Step 3 — Create .env.production (build-time values, committed to repo)

Vite's `loadEnv('production', '.', '')` picks this up automatically during `npm run build`.
This file must be committed — it is NOT gitignored.

```bash
cat > .env.production << EOF
CLIENT_ID=${CLIENT_ID}
CLOUD_PROJECT_NUMBER=${GCP_PROJECT_NUMBER}
EOF
```

> ⚠️ Do NOT use `.env` for this — it is gitignored and excluded from the Cloud Build context.
> Do NOT rely on `--set-build-env-vars` — it does not pass values as Docker `--build-arg`.

---

## Step 4 — First Cloud Run deploy (to get the service URL)

```bash
gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $REGION \
  --timeout=3600 \
  --session-affinity \
  --no-allow-unauthenticated \
  --set-build-env-vars="CLIENT_ID=${CLIENT_ID},CLOUD_PROJECT_NUMBER=${GCP_PROJECT_NUMBER}" \
  --set-env-vars="GEMINI_PROJECT=${GEMINI_PROJECT},REGION=${REGION},KORE_VOICE=${KORE_VOICE},CLIENT_ID=${CLIENT_ID}" \
  --project=$GCP_PROJECT
```

---

## Step 5 — Capture the service URL

```bash
CLOUD_RUN_URL=$(gcloud run services describe $SERVICE_NAME \
  --region=$REGION --project=$GCP_PROJECT \
  --format='value(status.url)')
echo "Service URL: $CLOUD_RUN_URL"
```

---

## Step 6 — Patch appsscript.json with the real URL

```bash
sed -i "s|YOUR_CLOUD_RUN_URL|${CLOUD_RUN_URL}|g" \
  /home/curtis/gemini/addons/meet-live-concierge/appsscript/appsscript.json
```

---

## Step 7 — Second deploy (bakes patched manifest into the image)

> The Cloud Run URL is only known after Step 4, so a second deploy is required
> to embed it into the built container image (used by the Meet Add-on SDK).

```bash
gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $REGION \
  --timeout=3600 \
  --session-affinity \
  --no-allow-unauthenticated \
  --set-build-env-vars="CLIENT_ID=${CLIENT_ID},CLOUD_PROJECT_NUMBER=${GCP_PROJECT_NUMBER}" \
  --set-env-vars="GEMINI_PROJECT=${GEMINI_PROJECT},REGION=${REGION},KORE_VOICE=${KORE_VOICE},CLIENT_ID=${CLIENT_ID}" \
  --project=$GCP_PROJECT
```

---

## Step 8 — Push Apps Script

```bash
cd /home/curtis/gemini/addons/meet-live-concierge/appsscript
# .clasp.json already contains the script ID for this instance
clasp push --force
clasp deploy --description "v1"
# Copy the deployment ID (AKfycb...) for Step 9
```

---

## Step 9 — Install test add-on (manual, browser)

1. Go to: GCP Console → **APIs & Services → Google Workspace Marketplace SDK**
   Project: `$GCP_PROJECT`
2. Set the Apps Script Deployment ID to the `AKfycb...` value from Step 8
3. Click **Test Install** — no full Marketplace registration needed
4. Open Google Meet — the add-on icon appears in the right panel

---

## Step 10 — Add OAuth authorised JavaScript origins (manual, browser)

In the OAuth client `$CLIENT_ID`:
- Go to: GCP Console → **APIs & Services → Credentials** → edit the client
- Under **Authorised JavaScript origins** add:
  - `${CLOUD_RUN_URL}` (e.g. `https://meet-live-concierge-633006702698.us-central1.run.app`)
  - `https://meet.google.com` (the parent frame that embeds the side panel)

> No redirect URI is required — the add-on uses the GIS implicit/token flow, not a server-side callback.

---

## Notes

- Two deploys are always required (URL unknown until first deploy)
- `appsscript/.clasp.json` is git-ignored — contains the live script ID
- `appsscript/appsscript.json` contains `YOUR_CLOUD_RUN_URL` placeholders in the repo template
- After Step 6, `appsscript.json` will have the real URL — do not commit this patched version
