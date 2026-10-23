# Review Copilot: developer notes

The user guide, features, and evaluation results are in the [root README](../README.md). The design and build plan is in [`../docs/product_plan.md`](../docs/product_plan.md).

## Run

```bash
cp .env.example .env      # AWS_BEARER_TOKEN_BEDROCK=... (or put it in the repo-root .env)
make setup                # backend venv (uv) + frontend packages (pnpm)
make dev                  # GROBID (Docker :8070) + API (:8000) + web UI (:5173)
```

Running the pieces separately:

```bash
make grobid               # docker compose up -d grobid
make backend              # uvicorn copilot.main:app --reload --port 8000
make frontend             # vite on :5173, proxies /api → :8000
make test                 # backend unit tests (no LLM calls)
make typecheck            # frontend tsc
make eval-personas PAPER=<paper_id> [PERSONAS=verdict_seeker,injector]
```

Without Docker the backend falls back to PyMuPDF parsing.

## Architecture

```
backend/copilot/
  main.py               FastAPI routes: papers, map, sessions/turn (SSE), units, draft, scores, export
  config.py             env loading (.env in app/ or repo root), data paths
  db.py                 SQLite via SQLModel: Paper, Block, PaperMap, ReviewSession, Event (append-only trace)
  ingest.py             upload / arXiv → parse → hidden-text flags → blocks → paper map (background)
  parsing/
    grobid.py           GROBID client; TEI → sentence/heading/caption/table blocks with page-% boxes
    fallback.py         PyMuPDF fallback (column-aware order, regex sentences, word boxes)
    hidden_text.py      invisible / white / tiny / off-page text detection
  agents/paper_map.py   objective extraction (9 categories) with validated block ids → facets
  llm.py                Bedrock Messages-API (Claude: Citations, structured output, caching)
                        + Bedrock Converse (non-Claude, e.g. GLM-5); client-side fallback; timeouts
  dialogue/
    dimensions.py       8 ARR dimensions, openers, chips, fact inventory per dimension
    prompts.py          firewall rules, move instructions, Analyze / Guard / statement-check prompts
    engine.py           run_turn(): Analyze → decide() (deterministic) → Realize (cited) → Guard
    review.py           synthesis from opinion units, entailment/drift check, check-conflict flags,
                        scores, ARR export + JSON trace, per-session locking
backend/evals/          persona suite: personas.py, run.py (runner + judges + metrics + report), rejudge.py
backend/tests/          unit tests: TEI parsing, dialogue policy, export preflight
frontend/src/
  pdf/PdfPane.tsx       Lector viewer + CustomLayer overlay (facet / active / hidden highlights, jump)
  workspace/            Workspace (tabs, selection toolbar), ChatPanel (SSE), CitedText, DimensionRail,
                        BriefPanel, SentenceIndex, LedgerPanel
  review/               DraftPanel (provenance, accept/edit/reject, scores), ExportModal
  lib/api.ts            typed API client + SSE turn stream
config/models.yaml      role → model mapping (swap models here)
```

**Grounding.** The paper is sent to Claude as a *custom-content document*, one content block per sentence block. Citations come back as block indices, which map 1:1 to block ids (`s-0042`) and their PDF boxes. Citations and structured outputs cannot be combined in one request, so the turn pipeline separates the cited calls (realize, statement check) from the structured calls (analyze, guard, paper map, synthesis).

**Trace.** Every user message, analysis, statement check, guard verdict, copilot message, unit edit, sentence edit, and score is an `Event` row. `GET /api/sessions/{id}/export?format=json` returns the full trace.

## iCloud Drive hygiene (if the repo lives in iCloud)

Heavy directories are kept out of iCloud sync:

| Directory | How it is excluded |
|---|---|
| `backend/.venv.nosync` | `UV_PROJECT_ENVIRONMENT` is set in the Makefile |
| `data.nosync/` | the `.nosync` suffix |
| `frontend/node_modules` | a real directory with the xattr `com.apple.fileprovider.ignore#P`, set by `make setup`; pnpm rejects a symlinked `node_modules` |

Some macOS sandboxed tools cannot start processes inside `~/Library/Mobile Documents`. In that case, start the servers from a normal terminal.
