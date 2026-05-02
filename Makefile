.PHONY: install build-index serve test clean

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
