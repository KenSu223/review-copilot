SHELL := /bin/bash
# Keep the Python venv out of iCloud sync (.nosync suffix is ignored by iCloud Drive).
export UV_PROJECT_ENVIRONMENT := .venv.nosync

.PHONY: dev setup grobid backend frontend stop test typecheck eval-personas

setup:            ## install backend + frontend dependencies
	cd backend && uv sync
	mkdir -p frontend/node_modules && xattr -w 'com.apple.fileprovider.ignore#P' 1 frontend/node_modules 2>/dev/null || true
	cd frontend && pnpm install

grobid:           ## start the GROBID PDF parser (Docker)
	docker compose up -d grobid

backend:          ## API on :8000
	cd backend && uv run uvicorn copilot.main:app --reload --port 8000

frontend:         ## web UI on :5173 (proxies /api to :8000)
	cd frontend && pnpm dev

dev: grobid       ## everything: GROBID + API + web UI
	@trap 'kill 0' INT TERM; $(MAKE) backend & $(MAKE) frontend & wait

stop:
	docker compose stop grobid

test:
	cd backend && uv run pytest -q

typecheck:
	cd frontend && pnpm typecheck

eval-personas:    ## persona test suite on a paper: make eval-personas PAPER=<paper_id> [PERSONAS=a,b]
	cd backend && uv run python -m evals.run --paper "$(PAPER)" $(if $(PERSONAS),--personas $(PERSONAS),)
