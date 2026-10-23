<!-- Research agent report, generated 2026-10-21 for the Academic Review Copilot product plan. Verify items before citing. -->

# Academic Review Copilot: technical stack research (as of 2026-10-21)

I checked everything below against GitHub (via `gh api`), PyPI/npm JSON, vendor docs, or a live HEAD/GET request. Star counts and push dates are from 2026-10-21/22. Where I couldn't confirm something, I say so. I installed nothing.

## Summary

- **Recommended stack:** a FastAPI (Python) backend and a React + Vite + TypeScript frontend.
- **PDF parsing:** GROBID 0.9.1 (`-crf` Docker image) is the primary parser. PyMuPDF 2.0 is the fallback, and also the tool for turning words into coordinates.
- **PDF viewer:** Lector (`@anaralabs/lector`).
- **Chat:** the Vercel AI SDK `useChat` hook, reading an SSE stream from FastAPI.
- **LLM calls:** the Anthropic Python SDK, plus the OpenAI SDK with a `base_url` for open models.
- **Storage:** SQLite with SQLModel.
- **Biggest finding:** Claude's Citations API with **custom content documents** can return the exact index of the sentence it cited. That makes "LLM claim → PDF highlight" an exact lookup for Claude, so fuzzy matching is only needed as a fallback.
- **Two blockers to plan for:**
  - OpenReview now effectively requires a login.
  - ACL Rolling Review (ARR) policy restricts uploading confidential submissions to generative tools.

---

## 1. Comparison tables

### Task 1: PDF → structured text with coordinates

| Tool | Latest release / last push | License | Stars | Structure for ML papers | Coordinates | macOS install | Speed | Verdict |
|---|---|---|---|---|---|---|---|---|
| **GROBID** (grobidOrg/grobid) | 0.9.1 (2026-08-04) / 2026-10-21 | Apache-2.0 | 5.2k | Built for scholarly papers. TEI output with header, sections (`head`), paragraphs, sentences, references, citation markers, figures/tables, formulas, footnotes | `@coords` on `s`, `p`, `head`, `figure`, `formula`, `ref`, `biblStruct`, `note`, `title`, `persName`, `affiliation`. Format is page,x,y,w,h in PDF units with a top-left origin, one box per line. Sentences need `segmentSentences` | Docker. `grobid/grobid:0.9.1-crf` (~500MB) has a **native arm64** build. `-full` (~8GB) is amd64-only and runs slowly under emulation on a Mac. Needs ~4GB RAM | README: ~10.6 PDF/s on a 16-CPU machine (older benchmark) | **Primary** |
| **PyMuPDF** | 2.0 (2026-10-19) / 2026-10-21 | AGPL-3.0 or commercial | 11.0k | Raw blocks, lines and spans. Version 2.x now bundles the former pymupdf4llm code ("layout analysis *without* any GPU"), with Markdown/JSON output | Bounding boxes per character, span and word. `search_for()` returns rects/quads and handles words hyphenated across lines | `pip` wheel only, no ML | Very fast (no models) | **Fallback** and coordinate tool |
| pdfplumber | 0.11.10 (2026-06-15) / 2026-10-15 | MIT | 10.8k | No semantic structure | Character and word boxes. `.search(regex)` returns boxes. `expand_ligatures=True` by default | Pure Python | Slower | MIT alternative to PyMuPDF |
| Docling | 2.141.0 (2026-10-20) / 2026-10-21 | MIT | 69.3k | Layout, reading order, tables, formulas, code, OCR, and a VLM pipeline (GraniteDocling) | `ProvenanceItem(page_no, bbox, charspan)` per item, i.e. paragraph level. Character/word/line cells via `generate_parsed_pages=True`. Coordinate origin can be `BOTTOMLEFT` | `pip`, Python ≥3.10, arm64 supported | 1.27 s/page on an M3 Max CPU with OCR and tables on (v2.5.2, arXiv 2501.17887). About 60% faster with OCR off | Strong alternative if tables/equations matter |
| Marker (datalab-to) | 2.0.0 (2026-07-20) / 2026-10-19 | Code Apache-2.0. **Weights use a modified OpenRAIL-M** (free for research and orgs under $5M) | 40.6k | Markdown/JSON/HTML/chunks | Block-level boxes | Needs a llama.cpp server on CPU/Apple Silicon | 4.2 s/page on M3 Max (v0.3.10, same paper) | Not recommended |
| MinerU | 4.0.12 (2026-10-11) / 2026-10-19 | "MinerU Open Source License" (Apache-2.0 plus usage thresholds and an **attribution obligation**) | 82.2k | Strong on formulas and tables | Block/span boxes | Apple Silicon "standard" setup needs 16GB RAM and MPS | Old v0.9.3 "did not finish" on M3 Max in the Docling paper | Too heavy for this demo |
| papermage (AllenAI) | 0.20.0 (2024-04) / 2024-11 | Apache-2.0 | 815 | Tokens, rows, sentences and sections linked to each other (e.g. `sent.rows`) | Boxes on every span | conda, Python 3.11, heavy predictor models | – | Stale. Borrow the data-model idea only |
| Nougat | 0.1.17 (2023-10) / 2025-02 | Code MIT, **weights CC-BY-NC** | 10.1k | Markdown/LaTeX output | **No coordinates** | GPU recommended | – | Unsuitable |
| s2orc-doc2json | – / 2024-04 | Apache-2.0 | 478 | TEI→JSON converter around GROBID (pinned to GROBID 0.7.3) | – | Java + GROBID | – | Use GROBID directly |
| science-parse | – / 2024-05 | Apache-2.0 | 707 | Title, authors, abstract, sections, bibliography, mentions (per README) | – | JVM | – | Superseded |

**Why GROBID is primary.** It is the only option that natively returns sentence-level boxes for a scientific-paper structure. That gives you stable sentence IDs that the LLM can cite and the UI can highlight.

**Why PyMuPDF is the fallback.** It needs no Docker, so it still works if GROBID is down. It also supplies word-level rectangles for quotes that don't line up with sentence boundaries. If AGPL is a problem, swap in pdfplumber (MIT).

### Task 3: PDF viewer with highlights

| Library | Latest / last push | License | Stars | pdf.js | Programmatic highlights | Scroll to highlight | Click on highlight | Select text → "ask" | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **Lector** (`@anaralabs/lector`) | 3.16.2 (2026-10-19) | MIT | 402 | peer `^5.5.207`, React ≥19 | `HighlightLayer` takes page/left/top/width/height in scale-1 px **or percent**. Also `ColoredHighlightLayer` and `AnnotationHighlightLayer` | `usePdfJump().jumpToHighlightRects` / `scrollToHighlightRects` | `AnnotationTooltip` (note: plain `HighlightLayer` has `pointer-events:none`) | `usePdfSelection` + `SelectionTooltip` return text and rects. Also exports `useSearch` (fuzzy `threshold`) and `calculateHighlightRects` | **Recommended** |
| react-pdf (wojtekmaj) | 11.0.0 (2026-09-10) | MIT | 11.2k | 6.3.289 | None built in (`customTextRenderer` only). You build the overlay | DIY | DIY | DIY | Fallback |
| react-pdf-highlighter | 8.0.0-rc.0 (2024-09) / 2024-11 | MIT | 1.4k | 4.4.168 | Yes (scaled positions) | `scrollRef` | Yes | `onSelectionFinished` | Stale |
| react-pdf-highlighter-extended | 8.1.0 (2024-07) / 2024-11 | MIT | 111 | ^4.4.168 | Yes, including area highlights | `utilsRef.scrollToHighlight` | Yes | `selectionTip` | Stale (Open Paper still uses it) |
| @react-pdf-viewer/core | 3.12.0 (2023-03) | Custom license | 2.6k | 2.x/3.x | – | – | – | – | **Repo archived. Avoid** |
| pdfjs-dist / PDF.js viewer | 6.4.299 (2026-10-03) | Apache-2.0 | 54k | – | Low-level, or the prebuilt viewer in an iframe (kotaemon's approach) | DIY | DIY | DIY | Too much glue |
| EmbedPDF | 2.15.1 (2026-09) | Apache-2.0 (repo has mixed licenses) | 4.6k | PDFium/WASM, not pdf.js | Annotation plugins | – | – | – | v3 marked "not yet recommended for production" |
| PDFSlick | 4.0.3 (2026-10-09) | MIT | 1.1k | pdf.js + Zustand | Viewer-focused | – | – | – | Alternative |

### Task 4: Chat UI, streaming, and overall stack

| Option | Glue code | Pros | Cons | Verdict |
|---|---|---|---|---|
| **A. FastAPI + React/Vite + AI SDK `useChat`** (`ai` 7.0.148, `@ai-sdk/react` 4.0.152, Apache-2.0) | FastAPI emits the "UI message stream" protocol: SSE JSON events with header `x-vercel-ai-ui-message-stream: v1` | `useChat` manages message state, abort and status. Custom `data-*` parts can carry citations and highlight commands. Official FastAPI examples exist: `vercel/ai/examples/next-fastapi` and `vercel-labs/ai-sdk-preview-python-streaming` | Tied to the AI SDK protocol version, so pin it | **Recommended** |
| B. FastAPI + custom SSE (fetch + ReadableStream) | ~100 lines of TypeScript | No extra dependency | You own state, abort and reconnect | Good if A feels heavy |
| C. A + assistant-ui (`@assistant-ui/react` 0.15.30, MIT, 12.7k★) | `useChatRuntime` / `useDataStreamRuntime` | Polished, composable chat components | Another layer of abstraction | Optional UI layer |
| D. Next.js full stack + Python sidecar | Two runtimes anyway | `streamText` + `@ai-sdk/anthropic` | Data model duplicated in TS and Python. pdf.js needs `dynamic(..., {ssr:false})` | Not worth it |
| E. CopilotKit (38k★, MIT) | Heavy | Agent framework | Overkill | No |

**Backend detail.** FastAPI ≥0.135 has native SSE (`from fastapi.sse import EventSourceResponse, ServerSentEvent`), with 15 s keep-alive pings and `X-Accel-Buffering: no`. Current version is 0.159.1. `sse-starlette` 3.5.0 is an alternative.

**Why Python on the backend.** The parsing tools (GROBID client, PyMuPDF, Docling), rapidfuzz, openreview-py and arxiv are all Python. A Next.js backend would still need a Python service next to it.

### Task 5: LLM provider layer

| Option | Version | Notes |
|---|---|---|
| **Anthropic Python SDK** | `anthropic` 2.1.0 (2026-10-21), Apache-2.0 | See the Claude capabilities list below. |
| **OpenAI SDK with `base_url`** | `openai` 3.36.0 | For open models via vLLM or Ollama (`http://localhost:11434/v1/`). **Don't** use Anthropic's own OpenAI-compatibility endpoint for Claude: it ignores `strict` and `response_format`, has no PDFs, citations or prompt caching, and Anthropic says it is "not considered a long-term or production-ready solution". |
| LiteLLM | 1.106.2, MIT (outside `enterprise/`), 61.8k★ | Unified OpenAI-style interface. Anthropic citations supported since PR #8382 (Feb 2025). **The PyPI package was compromised on 2026-03-24** (versions 1.82.7 and 1.82.8). If you use it, pin with hashes. |
| instructor / pydantic-ai | 1.17.0 / 2.59.0, both MIT | Structured output across providers |

**Claude capabilities that matter here:**
- **Citations (GA):** each citation carries `cited_text` plus a location:
  - plain text → `char_location`
  - PDF → `page_location` (page numbers only, so not enough for rectangles)
  - **custom content → `content_block_location`** with `start_block_index` / `end_block_index` (0-indexed, end exclusive)
- Docs: citations are "guaranteed to contain valid pointers", and `cited_text` doesn't count as output tokens.
- Streaming delivers citations as `citations_delta` events.
- **Citations and structured outputs can't be combined in one request (HTTP 400).**
- Structured outputs are GA (`output_config.format`, or `client.messages.parse()` with Pydantic), as is `strict: true` on tools.
- Model IDs: `claude-opus-5-5` (default), `claude-sonnet-5-5`, `claude-haiku-5-5` (cheap per-turn classification).

**Recommendation:** write your own thin `LLMProvider` interface (~200 lines) with two implementations instead of using LiteLLM. Give each provider capability flags, e.g. `native_citations` and `strict_json`.

---

## 2. Recommended architecture

**Main design choice: ground everything on sentence IDs, not on matching strings.**

1. **Ingest.** Accept an upload, an arXiv ID, or an OpenReview forum URL. Store the PDF as `data/pdfs/<sha256>.pdf`.
2. **Parse.** Call GROBID `processFulltextDocument` with `segmentSentences=1` and `teiCoordinates` = `s, p, head, figure, formula, ref, biblStruct`. Convert the TEI into a `block` table: sections, paragraphs and sentences with stable IDs (`s-0042`), each with boxes stored as **page percentages** using the page sizes in `<facsimile><surface lrx lry>`. If GROBID fails, use PyMuPDF words plus a sentence splitter (syntok 1.4.4, MIT).
3. **System highlights.** Send the sentence list with IDs to Claude using structured outputs, and get back `[{category: claim|evidence|experiment|limitation, sentence_ids, rationale}]`. Check that every returned ID exists.
4. **Socratic chat.**
   - **Claude:** send the paper as a **custom content document** with one content block per sentence, `citations: {enabled: true}`, and `cache_control` on the document. Each `content_block_location` maps block index → sentence ID → rectangles, with no fuzzy matching. Stream text deltas plus `data-citation` parts to `useChat`.
   - **Open models:** tag sentences in the prompt (`[s-0042] ...`), have the model cite the tags, and check them afterwards. Also fuzzy-check any quotes it returns.
5. **Capture opinions.** After each reviewer turn, a cheap structured-output call (Haiku, low effort) labels the dialogue act and pulls out opinion units (aspect, polarity, text, evidence sentence IDs). The reviewer confirms or edits them.
6. **Synthesize the review.** Use structured outputs to produce review sentences, each with provenance `{opinion_unit_ids, paper_sentence_ids, event_ids}`.
7. **Export.** `GET /sessions/{id}/export.json`.

**Quote → rectangles (for open models, pasted quotes, or the fallback parser):**
1. Normalize both texts: NFKC (turns the ﬁ ligature into "fi"), remove line-end hyphens, collapse whitespace, unify quotes and dashes. Keep an offset map back to word indices.
2. Try an exact match first.
3. If that fails, try `rapidfuzz.fuzz.partial_ratio_alignment` (returns `ScoreAlignment(score, src_start, src_end, dest_start, dest_end)`) or `fuzzysearch.find_near_matches(max_l_dist=…)`, searching within the page or section hint.
4. Convert the matched character span to word boxes (PyMuPDF `get_text("words")`, or GROBID sentence boxes), merge them per line, and convert to percent.
5. Below a score threshold, mark the citation "unverified" and don't highlight it.
6. For exact quotes, PyMuPDF `search_for()` already returns rectangles and handles hyphenation. On the client, Lector's `useSearch` + `calculateHighlightRects` does the same job.

**Proposed layout:**
```
review-copilot/
  Makefile                # make dev | make test | make export SESSION=…
  docker-compose.yml      # grobid (grobid/grobid:0.9.1-crf); profile "full" adds api+web
  .env.example            # ANTHROPIC_API_KEY, OPENAI_BASE_URL/KEY, OPENREVIEW_USERNAME/PASSWORD
  backend/  (uv, pyproject.toml, uv.lock)
    app/main.py
    app/api/{papers,sessions,chat,highlights,review,export}.py
    app/ingest/{arxiv,openreview,upload}.py
    app/parsing/{grobid_client,tei_to_blocks,pymupdf_fallback,normalize}.py
    app/grounding/{claude_citations,id_tags,quote_match,rects}.py
    app/llm/{base,anthropic_provider,openai_compat_provider,schemas}.py + prompts/
    app/agents/{highlighter,socratic,opinion_extractor,synthesizer}.py
    app/db/{models,session}.py   app/tracing/{events,export_schema}.py
  frontend/ (pnpm, Vite proxy /api → :8000)
    src/pdf/{PdfPane.tsx,pdf-setup.ts}  src/chat/{ChatPane,CitationChip}.tsx
    src/review/{OpinionBoard,ReviewEditor,ProvenanceHover}.tsx
    src/api/types.ts      # generated from FastAPI OpenAPI (openapi-typescript, MIT)
  data/                   # gitignored: pdfs/, app.db
```

**One-command run:** `make dev` runs `docker compose up -d grobid`, then `concurrently` (npm, MIT) starts `uv run uvicorn app.main:app --reload` and `pnpm dev`. `docker compose --profile full up` is for collaborators who don't want local toolchains.

**Persistence.** SQLite in WAL mode with SQLModel 0.0.48 (on SQLAlchemy 2.1.6), plus Alembic 1.20.0 if needed. Tables:
- `paper`, `page`, `block` (kind, section, text, boxes JSON)
- `session`, `event` (append-only trace: messages, selections, clicks, dialogue acts)
- `model_call` (provider, model, request hash, usage, latency)
- `citation` (event → sentence span, method, score)
- `highlight` (origin system/user, category, sentence IDs)
- `opinion_unit`, `review_sentence`, `provenance_link`

**Export schema idea.** Top-level keys:
- `schema_version`
- `session`
- `paper_index` (parser name and version, pages, sentences with boxes)
- `highlights`
- `events`
- `opinion_units`
- `review.sentences[].provenance`
- `model_calls`

Make each highlight exportable as a W3C Web Annotation with a `TextQuoteSelector` (exact/prefix/suffix) plus a custom PDF-box selector.

---

## 3. Risks and gotchas

- **Reviewing policy (product-level).** ARR guidelines say reviewers must not upload a submitted manuscript "or any part of it" to a non-privacy-preserving generative tool. They also say generative assistance may not be used to create the first draft. Implications:
  - Demo with public arXiv papers or accepted OpenReview papers.
  - Offer a local-model mode (Ollama or vLLM through the OpenAI-compatible path).
  - Frame synthesis as organizing the reviewer's own opinion units.
  - ACL demo calls say open-source systems are "of special interest".
- **OpenReview access.** The docs now say "You need an OpenReview account to use the API". My unauthenticated requests to `api2.openreview.net/notes` and `openreview.net/pdf?id=` got **HTTP 403 `ChallengeRequiredError`** on 2026-10-22. In openreview-py 2.9.1, a client created without credentials or the `OPENREVIEW_*` environment variables simply doesn't log in, but plan on authenticating:
  - `OpenReviewClient(baseurl='https://api2.openreview.net', username, password)`
  - `get_note(forum_id)`, then `content['title']['value']`
  - `get_attachment(field_name='pdf', id=…)`
  - `get_all_notes(forum=…)` for replies
  - Non-interactive MFA is supported via `mfa_code_provider` (PR #3272).
  - Keep credentials server-side and always offer manual upload as a fallback.
- **arXiv.**
  - `https://arxiv.org/pdf/<id>` returned 200, `application/pdf`, with `Access-Control-Allow-Origin: *`. Fetch on the server anyway, since you need to parse and cache it.
  - The API terms allow at most one request every 3 seconds on a single connection, and you must not re-serve e-prints unless the license allows it.
  - Python client: `arxiv` 4.0.1.
- **GROBID on Apple Silicon.** Use the `-crf` tag. `-full` is amd64-only and slow under emulation. Give Docker at least 4GB. Coordinates follow the CropBox (falling back to MediaBox), so normalize PDFs where the two differ.
- **Two-column reading order.** GROBID handles it. pdfplumber's default extraction sorts by position, and PyMuPDF raw output isn't reading order, so build reading order from GROBID and use PyMuPDF only for coordinates.
- **Ligatures, hyphenation and Unicode.** Watch for ﬁ/ﬂ ligatures, soft hyphens, real hyphens such as "state-of-the-art", math-italic Unicode, Greek letters, and quote/dash variants. LLMs also "clean up" quotes: they drop `[12]` citation markers or rewrite math as LaTeX. This is why ID-based citations come first. Open Paper's `textNormalization.ts` shows the normalization tables you'll need.
- **Equations, tables, figures.** Their text layers are garbled. Highlight GROBID `formula` and `figure` areas instead of matching strings.
- **Scanned PDFs.** Claude can't cite PDFs without extractable text. Detect a low character count per page and either refuse or run OCR (Docling has OCR). ACL papers are born-digital, so this is low priority.
- **Coordinate systems.** Lector uses a top-left origin in scale-1 viewport pixels or percent. GROBID uses PDF units with a top-left origin. Docling may use `BOTTOMLEFT`. Store percentages and test rotated pages.
- **pdf.js worker.**
  - The worker version must match `pdfjs-dist`.
  - Lector needs pdfjs-dist `^5.5.207`, but npm's latest is 6.4.299, so pin 5.x.
  - With react-pdf, set `workerSrc` in the same module that renders the viewer.
  - In Next.js, the viewer needs `dynamic(…, {ssr:false})`.
- **Claude API constraints.**
  - Citations can't be combined with `output_config.format`, so use separate calls.
  - On Opus 5.5 and Sonnet 5.5, forced `tool_choice` returns 400; use `auto` plus strict tools, or structured outputs.
  - Sampling parameters such as temperature are rejected on current models, so log model ID and prompt hashes for reproducibility.
  - Cache the paper document to cut cost across chat turns.
- **Licenses.**
  - AGPL: PyMuPDF, Open Paper.
  - Model weights: Marker (OpenRAIL-M), Nougat (CC-BY-NC).
  - MinerU requires attribution.
  - Peerispect and Scim repos have **no license**, so don't copy their code.

---

## 4. Existing codebases worth borrowing from

| Repo | Stars | License | Last push | What to reuse |
|---|---|---|---|---|
| [khoj-ai/openpaper](https://github.com/khoj-ai/openpaper) | 507 | **AGPL-3.0** | 2026-10-05 | Closest match: Next.js 15 + FastAPI + Celery + Postgres + S3, built on react-pdf-highlighter-extended. Reuse the quote → text-layer matching (`client/src/components/pdf-viewer/findTextPosition.ts`, `textNormalization.ts`) and its highlight data model. Copy code only if your project is AGPL; otherwise reimplement. |
| [allenai/marg-reviewer](https://github.com/allenai/marg-reviewer) | 65 | Apache-2.0 | 2026-03-05 | Multi-agent review-generation prompts, a docker-compose demo, and alignment metrics (`review_worker/paper_align_eval_repro.py`) for evaluation |
| [Cinnamon/kotaemon](https://github.com/Cinnamon/kotaemon) | 25.8k | Apache-2.0 | 2026-07-14 | Highlights citations in the PDF.js viewer with a span-level fuzzy ratio (`libs/ktem/ktem/assets/js/pdf_viewer.js`). Useful as a simple baseline. |
| [infiniflow/ragflow](https://github.com/infiniflow/ragflow) | 92.6k | Apache-2.0 | 2026-10-21 | Highlights chunk positions with react-pdf-highlighter ^6.1. Reference only (heavy). |
| [allenai/papermage](https://github.com/allenai/papermage) | 815 | Apache-2.0 | 2024-11 | The data model: entities that hold both spans and boxes, with cross-layer lookups |
| [allenai/scholarphi](https://github.com/allenai/scholarphi) / [pdf-component-library](https://github.com/allenai/pdf-component-library) | 428 / 93 | Apache-2.0 / none in repo (npm says Apache-2.0) | 2023-07 / 2024-02 | Layered overlay architecture of Semantic Reader (stale) |
| [rayfok/scim](https://github.com/rayfok/scim) | 40 | none | 2024-01 | Idea only: faceted highlight categories |
| [Reviewerly-Inc/Peerispect](https://github.com/Reviewerly-Inc/Peerispect) | 3 | none | 2026-03-10 | Reference pipeline: OpenReview crawl → Docling → claim extraction → NLI |
| [LusunHCI/ReviewFlow](https://github.com/LusunHCI/ReviewFlow) | 0 | – | 2024-02 | **Empty repo**; code never released |
| [vercel/ai examples/next-fastapi](https://github.com/vercel/ai/tree/main/examples/next-fastapi), [vercel-labs/ai-sdk-preview-python-streaming](https://github.com/vercel-labs/ai-sdk-preview-python-streaming) | 27.4k / 363 | Apache-2.0 / none | 2026-10 / 2026-04 | Glue for streaming from Python into `useChat` |
| [Future-House/paper-qa](https://github.com/Future-House/paper-qa) | 9.4k | Apache-2.0 | 2026-10-20 | Library for answering questions over scientific documents with citations |

MuPDF WebViewer's "AI Citation" feature (`text.locateSource()`) is a commercial reference design for the same quote → rectangle problem. I didn't check its license.

---

## References

**PDF parsing**
- GROBID: https://github.com/grobidOrg/grobid
- GROBID coordinates: https://grobid.readthedocs.io/en/latest/Coordinates-in-PDF/
- GROBID Docker: https://grobid.readthedocs.io/en/latest/Grobid-docker/
- GROBID Python client: https://github.com/grobidOrg/grobid-client-python
- PyMuPDF: https://github.com/pymupdf/PyMuPDF
- PyMuPDF `Page` API: https://pymupdf.readthedocs.io/en/latest/page.html
- pymupdf4llm: https://github.com/pymupdf/pymupdf4llm
- pdfplumber: https://github.com/jsvine/pdfplumber
- Docling: https://github.com/docling-project/docling
- Docling provenance (docling-core source): https://github.com/docling-project/docling-core/blob/main/docling_core/types/doc/common/reference.py
- Docling benchmark paper: https://arxiv.org/html/2501.17887
- Marker: https://github.com/datalab-to/marker
- MinerU: https://github.com/opendatalab/MinerU
- MinerU license: https://github.com/opendatalab/MinerU/blob/master/LICENSE.md
- Nougat: https://github.com/facebookresearch/nougat
- papermage: https://github.com/allenai/papermage
- s2orc-doc2json: https://github.com/allenai/s2orc-doc2json
- science-parse: https://github.com/allenai/science-parse

**Quote matching**
- RapidFuzz: https://github.com/rapidfuzz/RapidFuzz
- fuzzysearch: https://github.com/taleinat/fuzzysearch
- MuPDF AI Citation: https://webviewer-docs.mupdf.com/ai
- W3C Web Annotation Data Model: https://www.w3.org/TR/annotation-model/

**Frontend**
- Lector: https://github.com/anaralabs/lector
- react-pdf: https://github.com/wojtekmaj/react-pdf
- react-pdf-highlighter: https://github.com/agentcooper/react-pdf-highlighter
- react-pdf-highlighter-extended: https://github.com/DanielArnould/react-pdf-highlighter-extended
- react-pdf-viewer (archived): https://github.com/react-pdf-viewer/react-pdf-viewer
- PDF.js: https://github.com/mozilla/pdf.js
- EmbedPDF: https://github.com/embedpdf/embed-pdf-viewer
- PDFSlick: https://github.com/pdfslick/pdfslick

**Chat and backend**
- AI SDK stream protocol: https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol
- Vercel AI SDK: https://github.com/vercel/ai
- assistant-ui: https://github.com/assistant-ui/assistant-ui
- FastAPI SSE: https://fastapi.tiangolo.com/tutorial/server-sent-events/
- sse-starlette: https://github.com/sysid/sse-starlette

**LLM**
- Claude Citations: https://platform.claude.com/docs/en/build-with-claude/citations
- Claude structured outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Anthropic OpenAI-SDK compatibility: https://platform.claude.com/docs/en/api/openai-sdk
- LiteLLM: https://github.com/BerriAI/litellm
- LiteLLM citations PR: https://github.com/BerriAI/litellm/pull/8382
- LiteLLM compromise write-up: https://www.netspi.com/blog/executive-blog/ai-ml-pentesting/litellm-supply-chain-compromise/
- Ollama OpenAI compatibility: https://github.com/ollama/ollama/blob/main/docs/api/openai-compatibility.mdx

**Ingestion**
- openreview-py: https://github.com/openreview/openreview-py
- OpenReview "Using the API": https://docs.openreview.net/getting-started/using-the-api.md
- OpenReview "Get all notes": https://docs.openreview.net/how-to-guides/data-retrieval-and-modification/how-to-get-all-notes-for-submissions-reviews-rebuttals-etc.md
- arXiv API terms of use: https://info.arxiv.org/help/api/tou.html
- arxiv.py: https://github.com/lukasschwab/arxiv.py

**Persistence and tooling**
- SQLModel: https://github.com/fastapi/sqlmodel
- uv: https://github.com/astral-sh/uv
- openapi-typescript: https://github.com/openapi-ts/openapi-typescript
- concurrently: https://github.com/open-cli-tools/concurrently

**Policy and venue**
- ARR reviewer guidelines: https://aclrollingreview.org/reviewerguidelines
- ACL 2026 demo call: https://2026.aclweb.org/calls/system_demonstration/
- Peerispect paper: https://arxiv.org/pdf/2604.17667
- ReviewFlow paper: https://arxiv.org/pdf/2402.03530
- Scim paper: https://arxiv.org/pdf/2205.04561