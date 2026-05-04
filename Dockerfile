FROM python:3.11-slim

# libgomp1  — required by faiss-cpu (OpenMP)
# build-essential — needed by pyswisseph native extension
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python dependencies (cached layer — only rebuilds when requirements change) ──
COPY requirements.txt pyproject.toml ./
COPY src/ src/
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -e ".[engine,retrieval,llm,api]" \
 && pip install --no-cache-dir google-genai

# ── Pre-download sentence-transformers model at build time ──────────────────────
# Sets HF_HUB_OFFLINE=1 at runtime — no outbound calls needed after this.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# ── Application data (corpus texts, rules, pre-built FAISS index) ───────────────
# Run  make build-index  locally BEFORE  docker build  so the index is present.
COPY configs/ configs/
COPY data/corpus/   data/corpus/
COPY data/processed/ data/processed/

# Strip API key from configs — injected at runtime via GEMINI_API_KEY env var.
RUN python - <<'EOF'
import yaml, pathlib
p = pathlib.Path("configs/models.yaml")
if p.exists():
    cfg = yaml.safe_load(p.read_text()) or {}
    llm = cfg.setdefault("llm", {})
    llm["backend"] = "gemini"
    llm.setdefault("gemini", {})["api_key"] = ""
    p.write_text(yaml.dump(cfg, default_flow_style=False))
EOF

# ── Runtime environment ─────────────────────────────────────────────────────────
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

EXPOSE 8080

# Cloud Run injects PORT; exec form ensures signals propagate correctly.
CMD exec uvicorn vedic_ai.api.app:create_api_app \
        --factory \
        --host 0.0.0.0 \
        --port ${PORT} \
        --workers 1
