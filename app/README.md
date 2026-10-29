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
make eval-personas PAPER=<paper_id> [PERSONAS=lazy,injector] [FLOWS=evidence,commit_first]
```

Without Docker the backend falls back to PyMuPDF parsing (regex sentences, pattern-detected section headings).

## Architecture

```
backend/copilot/
  main.py               FastAPI routes: profile, papers, map, sessions/turn (SSE), agenda rail, facts, remember,
                        units (+ rephrase), draft (+ register), scores, export
  config.py             env loading (.env in app/ or repo root), data paths
  db.py                 SQLite via SQLModel: Paper, Block, PaperMap, ReviewerProfile, ReviewSession, Event (append-only trace)
  ingest.py             upload / arXiv → parse → hidden-text flags → blocks → paper map (background)
  parsing/
    grobid.py           GROBID client; TEI → sentence/heading/caption/table blocks with page-% boxes
    fallback.py         PyMuPDF fallback (column-aware order, regex sentences, heading detection, word boxes)
    hidden_text.py      invisible / white / tiny / off-page text detection
  agents/paper_map.py   objective extraction (9 categories) with validated block ids → facets
  llm.py                Bedrock Messages-API (Claude: Citations, structured output, caching)
                        + Bedrock Converse (non-Claude, e.g. GLM-5); client-side fallback; timeouts
  dialogue/
    criteria.py         reviewer criteria + default "where to look", levels L0–L3, per-paper options, ARR field help
    agenda.py           agenda planner: profile + paper → evidence cards (validated ids, ranked, level-capped),
                        orientation / background / positioning cards, glossary; runs in the background
    monitor.py          coverage monitor: extraction call (act, opinion units, claims, preferences) + deterministic
                        coverage of the ARR fields (reports fields, never content)
    engine.py           run_turn(): monitor → statement checks → allowed_actions() (code boundaries) →
                        conversation agent (cited, chooses one allowed step) → Guard; prefetch; rail, facts, remember
    prompts.py          casual firewall rules, action guide, level rules, Guard (R1–R8), statement check, fallbacks
    dimensions.py       the 8 ARR fields (background structure for coverage and the draft)
    review.py           synthesis in three registers (words / polished / formal) with drift checks, confirmed paper
                        facts, scores, ARR export + disclosure + JSON trace, per-session locking
    legacy.py           the previous commit-first engine (+ legacy_prompts.py), kept for the A/B comparison
backend/evals/          persona suite: personas.py, run.py (both flows, judges, fidelity, friction, self-BLEU), rejudge.py
backend/tests/          unit tests: TEI parsing, code boundaries, coverage, agenda helpers, legacy policy, export preflight
frontend/src/
  onboarding/           Onboarding: level first, then level-specific questions; study-mode toggle
  pdf/PdfPane.tsx       Lector viewer + CustomLayer overlay (facet / active / hidden highlights, jump)
  workspace/            Workspace (tabs, selection toolbar, focus navigator), PaperSetup (per-paper questions),
                        AgendaRail, ChatPanel (SSE, chips, capture pills, facts checklist, remember prompt),
                        CitedText (citation chips + glossary), BriefPanel, SentenceIndex, LedgerPanel (register slider)
  review/               DraftPanel (register slider, provenance, accept/edit/reject, scores), ExportModal
  lib/api.ts            typed API client + SSE turn stream
config/models.yaml      role → model mapping (swap models here)
```

**Turn pipeline.** See [`../docs/conversation_redesign.md`](../docs/conversation_redesign.md) §5.4. The monitor and the
Guard run on every typed turn; statement checks only when the reviewer states facts about the paper; chip clicks skip
the monitor. The agent's first output line is `ACTION: <step> [| CARD: Cn] [| FIELD: f]`, validated against the
allowed steps before the Guard sees the message.

**Grounding.** The paper is sent to Claude as a *custom-content document*, one content block per sentence block. Citations come back as block indices, which map 1:1 to block ids (`s-0042`) and their PDF boxes. Citations and structured outputs cannot be combined in one request, so cited calls (agent, statement check) are separate from structured calls (monitor, Guard, agenda planner, paper map, synthesis).

**Trace.** Every user message, monitor analysis, statement check, agent decision (allowed steps, chosen step, candidates, focus), guard verdict, copilot message, agenda plan, rail edit, unit edit, confirmed fact, register change, sentence edit, and score is an `Event` row. `GET /api/sessions/{id}/export?format=json` returns the full trace.

## iCloud Drive hygiene (if the repo lives in iCloud)

Heavy directories are kept out of iCloud sync:

| Directory | How it is excluded |
|---|---|
| `backend/.venv.nosync` | `UV_PROJECT_ENVIRONMENT` is set in the Makefile |
| `data.nosync/` | the `.nosync` suffix |
| `frontend/node_modules` | a real directory with the xattr `com.apple.fileprovider.ignore#P`, set by `make setup`; pnpm rejects a symlinked `node_modules` |

Some macOS sandboxed tools cannot start processes inside `~/Library/Mobile Documents`. In that case, start the servers from a normal terminal.
