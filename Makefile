.PHONY: install build-index serve test clean \
        docker-build docker-run docker-stop deploy gcp-setup

# ── Setup ──────────────────────────────────────────────────────────────────────

install:
	python -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[dev,engine,retrieval,llm,api]"
	@echo ""
	@echo "✓ Install complete.  Next step:  make build-index"

# ── One-time index build (downloads ~90 MB embedding model on first run) ───────

build-index:
	.venv/bin/vedic-ai build-index
	@echo ""
	@echo "✓ Index built.  Start the server with:  make serve"

# ── Run ────────────────────────────────────────────────────────────────────────

serve:
	.venv/bin/vedic-ai serve

serve-lan:
	.venv/bin/vedic-ai serve --host 0.0.0.0 --port 8000

# ── Tests ──────────────────────────────────────────────────────────────────────

test:
	.venv/bin/pytest tests/unit -q

test-all:
	.venv/bin/pytest tests/ -q

# ── Cleanup ────────────────────────────────────────────────────────────────────

clean:
	rm -rf .venv data/processed __pycache__ .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# ── Docker / GCP deployment ────────────────────────────────────────────────────
# Prerequisites: Docker installed; gcloud CLI authenticated; FAISS index built.
# Set GCP_PROJECT to your GCP project ID, e.g.:  make deploy GCP_PROJECT=my-proj

GCP_PROJECT ?= $(shell gcloud config get-value project 2>/dev/null)
GCP_REGION  ?= asia-south1
SERVICE     ?= vedic-ai
IMAGE       ?= gcr.io/$(GCP_PROJECT)/$(SERVICE)

# Build Docker image locally (useful to test before pushing)
docker-build:
	@echo "Building image: $(IMAGE)"
	@test -f data/processed/faiss.index || (echo "ERROR: Run 'make build-index' first — FAISS index not found." && exit 1)
	docker build -t $(IMAGE):latest .

# Run the image locally (mirrors the Cloud Run environment)
docker-run:
	docker run --rm -p 8080:8080 \
		-e GEMINI_API_KEY=$(GEMINI_API_KEY) \
		$(IMAGE):latest

docker-stop:
	docker ps -q --filter ancestor=$(IMAGE):latest | xargs -r docker stop

# One-command deploy to Cloud Run via Cloud Build
# Stores GEMINI_API_KEY in Secret Manager the first time; updates on subsequent runs.
deploy:
	@test -n "$(GCP_PROJECT)" || (echo "ERROR: set GCP_PROJECT=<your-project-id>" && exit 1)
	@test -n "$(GEMINI_API_KEY)" || (echo "ERROR: export GEMINI_API_KEY=<your-key>" && exit 1)
	@test -f data/processed/faiss.index || (echo "ERROR: Run 'make build-index' first." && exit 1)
	@echo "→ Storing GEMINI_API_KEY in Secret Manager..."
	@echo -n "$(GEMINI_API_KEY)" | gcloud secrets create GEMINI_API_KEY \
		--data-file=- --project=$(GCP_PROJECT) 2>/dev/null || \
	echo -n "$(GEMINI_API_KEY)" | gcloud secrets versions add GEMINI_API_KEY \
		--data-file=- --project=$(GCP_PROJECT)
	@echo "→ Submitting Cloud Build..."
	gcloud builds submit \
		--config cloudbuild.yaml \
		--project=$(GCP_PROJECT) \
		--substitutions _REGION=$(GCP_REGION),_SERVICE=$(SERVICE) \
		.
	@echo ""
	@echo "✓ Deployed. URL:"
	@gcloud run services describe $(SERVICE) \
		--region=$(GCP_REGION) --project=$(GCP_PROJECT) \
		--format="value(status.url)"

# One-time GCP project setup — run once before first deploy
gcp-setup:
	@test -n "$(GCP_PROJECT)" || (echo "ERROR: set GCP_PROJECT=<your-project-id>" && exit 1)
	gcloud config set project $(GCP_PROJECT)
	gcloud services enable \
		run.googleapis.com \
		cloudbuild.googleapis.com \
		containerregistry.googleapis.com \
		secretmanager.googleapis.com \
		--project=$(GCP_PROJECT)
	@echo "✓ APIs enabled. Grant Cloud Build the Secret Manager accessor role:"
	@echo "  gcloud projects add-iam-policy-binding $(GCP_PROJECT) \\"
	@echo "    --member=serviceAccount:\$$(gcloud projects describe $(GCP_PROJECT) \\"
	@echo "      --format='value(projectNumber)')@cloudbuild.gserviceaccount.com \\"
	@echo "    --role=roles/secretmanager.secretAccessor"
