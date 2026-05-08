# Problem: Vite build-time env vars not baking into Cloud Run container

## Context

This is a Google Meet Web Add-on. The frontend is a Lit/TypeScript app built with Vite.
At build time, Vite must inline two values into the JS bundle:

- `CLOUD_PROJECT_NUMBER` — the GCP project number (`633006702698`)
- `CLIENT_ID` — the OAuth client ID (`633006702698-lf3vsget4m8c7cati2k0eki33n0l19lt.apps.googleusercontent.com`)

These values are used in `index.tsx`:
```typescript
const CLOUD_PROJECT_NUMBER = process.env.CLOUD_PROJECT_NUMBER;
const CLIENT_ID = process.env.CLIENT_ID;
```

And in `vite.config.ts`:
```js
const env = loadEnv(mode, '.', '');
// ...
define: {
  'process.env.CLIENT_ID': JSON.stringify(env.CLIENT_ID || process.env.CLIENT_ID || ''),
  'process.env.CLOUD_PROJECT_NUMBER': JSON.stringify(env.CLOUD_PROJECT_NUMBER || process.env.CLOUD_PROJECT_NUMBER || ''),
}
```

The `cloudProjectNumber` is passed to the Meet Add-ons SDK:
```typescript
await meet.addon.createAddonSession({ cloudProjectNumber: CLOUD_PROJECT_NUMBER });
```
If it is empty or wrong, Meet refuses to load the add-on with "add-on could not load".

---

## Deployment method

```bash
gcloud run deploy meet-live-concierge \
  --source . \
  --region us-central1 \
  --project=master-engine-495207-j8
```

This uses Cloud Run source deploy, which uploads the source to GCS and runs a Cloud Build job using the `Dockerfile`.

---

## What the Dockerfile does

```dockerfile
FROM node:22-slim AS frontend
WORKDIR /app
COPY package.json ./
RUN npm install
COPY index.html index.tsx index.css vite.config.ts tsconfig.json ./
COPY internal ./internal
COPY types ./types
COPY public ./public
ARG CLIENT_ID
ARG CLOUD_PROJECT_NUMBER
ENV CLIENT_ID=$CLIENT_ID
ENV CLOUD_PROJECT_NUMBER=$CLOUD_PROJECT_NUMBER
RUN echo "CLIENT_ID=633006702698-lf3vsget4m8c7cati2k0eki33n0l19lt.apps.googleusercontent.com" > .env && \
    echo "CLOUD_PROJECT_NUMBER=633006702698" >> .env
RUN npm run build
...
```

---

## The problem

Despite multiple attempts, the built JS bundle being served from Cloud Run does NOT contain `633006702698`. The bundle always contains an empty string for the project number:

```js
// In the minified bundle, nc is the cloudProjectNumber variable
const nc = ""   // <-- should be "633006702698"
```

Confirmed by:
```bash
curl -s https://meet-live-concierge-633006702698.us-central1.run.app/assets/index-Bfzv048q.js \
  | python3 -c "import sys; print('633006702698' in sys.stdin.read())"
# Output: False
```

The bundle filename `index-Bfzv048q.js` has NOT changed across 5 deploys despite Dockerfile changes, which suggests Cloud Build is serving a cached Docker layer for the `npm run build` step.

---

## What has been tried

1. `--set-build-env-vars="CLIENT_ID=...,CLOUD_PROJECT_NUMBER=633006702698"` on the gcloud deploy command — values do not reach Vite
2. Writing `.env` file before deploy and deleting after — `.env` is in `.gitignore` so Cloud Build excludes it from the build context
3. `COPY .env* ./` in Dockerfile — fails with "no source files were specified" when `.env` is absent (gitignored)
4. `RUN echo "CLIENT_ID=..." > .env && echo "CLOUD_PROJECT_NUMBER=633006702698" >> .env` in Dockerfile — layer appears to be cached by Cloud Build, bundle unchanged
5. `ARG` + `ENV` in Dockerfile — `ARG` values are empty because `--set-build-env-vars` does not pass them as Docker `--build-arg`

---

## What is needed

One of the following solutions:

**Option A** — Force Cloud Build to pass Docker build args correctly:
```bash
gcloud run deploy meet-live-concierge \
  --source . \
  --build-arg CLIENT_ID=633006702698-... \
  --build-arg CLOUD_PROJECT_NUMBER=633006702698 \
  ...
```
(If `gcloud run deploy --source` supports a `--build-arg` flag — needs verification)

**Option B** — Add a `cloudbuild.yaml` that disables layer caching and passes explicit build args:
```yaml
steps:
- name: 'gcr.io/cloud-builders/docker'
  args:
    - build
    - --no-cache
    - --build-arg
    - CLIENT_ID=633006702698-lf3vsget4m8c7cati2k0eki33n0l19lt.apps.googleusercontent.com
    - --build-arg
    - CLOUD_PROJECT_NUMBER=633006702698
    - -t
    - '$_AR_HOSTNAME/$PROJECT_ID/cloud-run-source-deploy/$_SERVICE_NAME:$COMMIT_SHA'
    - .
```

**Option C** — Move the build out of Docker entirely. Pre-build locally:
```bash
CLIENT_ID=633006702698-... CLOUD_PROJECT_NUMBER=633006702698 npm run build
```
Then commit the `dist/` folder (or use a separate build step before `gcloud run deploy`).

**Option D** — Use a `.env.production` file (NOT gitignored) committed to the repo with the values hardcoded for this deployment. Vite's `loadEnv('production', '.', '')` will pick it up automatically.

---

## Project details

| Item | Value |
|---|---|
| GCP Project | `master-engine-495207-j8` |
| Project Number | `633006702698` |
| Cloud Run service | `meet-live-concierge` |
| Region | `us-central1` |
| Service URL | `https://meet-live-concierge-633006702698.us-central1.run.app` |
| Client ID | `633006702698-lf3vsget4m8c7cati2k0eki33n0l19lt.apps.googleusercontent.com` |
| Source directory | `/home/curtis/gemini/addons/meet-live-concierge` |
| vite.config.ts | Uses `loadEnv(mode, '.', '')` + `process.env` fallback |
