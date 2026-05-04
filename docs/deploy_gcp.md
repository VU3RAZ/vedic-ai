# Deploying Vedic AI on Google Cloud Run

Cloud Run is serverless — you pay only when requests are served, scales to zero when idle.
Free tier: 2 million requests/month and 360,000 GB-seconds/month.

---

## Prerequisites

| Tool | Install |
|---|---|
| Google Cloud SDK (`gcloud`) | https://cloud.google.com/sdk/docs/install |
| Docker | https://docs.docker.com/get-docker/ |
| A GCP project | https://console.cloud.google.com/projectcreate |

---

## First-time setup (do once)

### 1. Authenticate

```bash
gcloud auth login
gcloud auth configure-docker   # lets Docker push to gcr.io
```

### 2. Enable required APIs

```bash
export GCP_PROJECT=your-project-id   # e.g. vedic-ai-prod

make gcp-setup GCP_PROJECT=$GCP_PROJECT
```

This enables Cloud Run, Cloud Build, Container Registry, and Secret Manager.

### 3. Grant Cloud Build access to Secret Manager

Cloud Build needs to read the Gemini API key from Secret Manager:

```bash
PROJECT_NUMBER=$(gcloud projects describe $GCP_PROJECT --format='value(projectNumber)')

gcloud projects add-iam-policy-binding $GCP_PROJECT \
  --member=serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
```

### 4. Build the FAISS index locally (if not already done)

The Docker image bundles the pre-built index — build it once before deploying:

```bash
make build-index
```

---

## Deploy

```bash
export GCP_PROJECT=your-project-id
export GEMINI_API_KEY=AIzaSy...your-key...

make deploy GCP_PROJECT=$GCP_PROJECT
```

This does four things automatically:
1. Stores `GEMINI_API_KEY` in Secret Manager (never baked into the image)
2. Submits the source to Cloud Build
3. Builds the Docker image (bundles code + FAISS index + embedding model)
4. Deploys the image to Cloud Run and prints the live URL

**First deploy takes ~5–7 minutes** (downloading Python packages and the 88 MB embedding model into the image). Subsequent deploys take ~2 minutes.

---

## Test locally before deploying

```bash
export GEMINI_API_KEY=AIzaSy...

make docker-build              # build image locally
make docker-run                # runs on http://localhost:8080
```

Open http://localhost:8080 — it should behave identically to the cloud deployment.

---

## Deployment architecture

```
Browser  →  Cloud Run (vedic-ai)
                │
                ├── FastAPI + uvicorn (PORT from env)
                ├── FAISS index  (bundled in image, 8 MB)
                ├── Corpus texts + rules  (bundled in image)
                ├── all-MiniLM-L6-v2  (baked into image layer, 88 MB)
                │     HF_HUB_OFFLINE=1 → no outbound HF calls
                │
                └── Gemini API  (GEMINI_API_KEY from Secret Manager)
```

**Image size:** ~1.5 GB (Python base + deps + model)  
**Memory:** 2 Gi (configured in `cloudbuild.yaml`)  
**Concurrency:** 4 requests per instance  
**Timeout:** 300 s per request (generous for multi-scope predictions)

---

## Update an existing deployment

Just run `make deploy` again — Cloud Build builds a new image tagged with the
git short SHA and rolls it out with zero downtime.

---

## Useful commands

```bash
# View live logs
gcloud run services logs read vedic-ai --region=asia-south1 --project=$GCP_PROJECT

# Tail logs in real time
gcloud beta run services logs tail vedic-ai --region=asia-south1 --project=$GCP_PROJECT

# List deployed revisions
gcloud run revisions list --service=vedic-ai --region=asia-south1 --project=$GCP_PROJECT

# Roll back to previous revision
gcloud run services update-traffic vedic-ai \
  --to-revisions=vedic-ai-00001-abc=100 \
  --region=asia-south1 --project=$GCP_PROJECT

# Get the live URL
gcloud run services describe vedic-ai \
  --region=asia-south1 --project=$GCP_PROJECT \
  --format="value(status.url)"
```

---

## Update the Gemini API key

```bash
echo -n "NEW_KEY_HERE" | gcloud secrets versions add GEMINI_API_KEY \
  --data-file=- --project=$GCP_PROJECT

# Then redeploy so Cloud Run picks up the new version:
make deploy GCP_PROJECT=$GCP_PROJECT
```

---

## Cost estimate (Mumbai / asia-south1)

| Usage | Monthly cost |
|---|---|
| 1,000 predictions (Gemini ~2 s each) | **$0** — within free tier |
| 10,000 predictions | ~$0.10 Cloud Run compute |
| 50,000 predictions | ~$0.50 Cloud Run compute |
| Gemini API (free tier: 1,500 req/day) | **$0** for personal use |

Dominant cost at scale is Gemini API, not Cloud Run.

---

## Switching region

Default is `asia-south1` (Mumbai — lowest latency from India).
To use a different region:

```bash
make deploy GCP_PROJECT=$GCP_PROJECT GCP_REGION=us-central1
```

---

## CI/CD (optional — auto-deploy on git push)

Connect the repository to Cloud Build triggers:

1. Go to **Cloud Build → Triggers → Create Trigger**
2. Connect your GitHub / Cloud Source Repository
3. Set trigger: push to `main`
4. Build config: `cloudbuild.yaml`
5. Add substitution: `_REGION` = `asia-south1`

Every `git push` to `main` will automatically build and deploy.
