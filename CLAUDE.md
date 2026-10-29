# Academic Review Copilot: Project Context

> This is the persistent context for the project: core ideas, research questions, the plan, and decisions made so far.
> Last updated: 2026-10-28 (redesign implemented). Update this file whenever the plan changes.
> Related files:
> - `docs/prior_art_report.md`: full related-work survey (about 120 items)
> - `docs/motivation_draft.md`: English motivation and contributions draft, with team notes
> - `papers/`: downloaded PDFs (local only, gitignored)
> - `docs/product_plan.md`: the product build plan; this is the current phase
> - `docs/conversation_redesign.md`: agreed redesign of the dialogue flow (2026-10-28); supersedes `product_plan.md` §2.3–2.8
> - `docs/research/01–04`: research reports on Socratic patterns from the local ARS skill, Socratic method and elicitation, UI/UX plus review forms plus demo-track requirements, and the tech stack

## 0. Current phase (updated 2026-10-21) — READ FIRST

- **Pivot**: build an end-to-end, locally runnable **product** first. Each collaborator builds their own version, then the team compares and picks one route.
- **Target**: an ACL-family **System Demonstrations** track. Research novelty is not required, but an evaluation is mandatory.
  - The nearest deadline is **NAACL 2027 (2026-12-04)**.
  - The ACL 2027 demo call is not out yet.
- **No training or fine-tuning.** Use off-the-shelf LLM APIs (default Claude; OpenAI-compatible endpoints for open models) via prompts and pipelines. The RL and training plan in §6 is **deferred**, kept only for a possible later research paper.
- **The build plan is `docs/product_plan.md`**: Socratic design, UI, pipeline, stack, evaluation, and build order. Research backing is in `docs/research/01–04`.
- Planned stack: FastAPI, React/Vite/TS, Lector, GROBID, SQLite.
- Per-turn pipeline: Analyze → Policy (code) → Realize (Claude Citations over sentence blocks) → Guard.
- **LLM access (tested 2026-10-21)**: Amazon Bedrock Messages-API endpoint.
  - Call it with `Anthropic(base_url="https://bedrock-mantle.us-east-1.api.aws/anthropic", api_key=$AWS_BEARER_TOKEN_BEDROCK)`. The key lives in `.env` (gitignored, chmod 600).
  - Available models: `anthropic.claude-opus-5-5`, `-opus-5`, `-opus-4-8`, `-sonnet-5`, `-haiku-4-5`. Sonnet 5.5, Haiku 5.5, and Fable 5.1 return 404.
  - Chosen models:
    - Realize and statement check: **Opus 5.5 at effort low**.
    - Analyze, entailment: **Sonnet 5 at effort low**.
    - Guard: **GLM-5** (Bedrock Converse; a different model family from the generator), chosen from the 29-model benchmark in `eval/model_bench/COMPARISON.md`.
    - Paper map and synthesis: Opus 5.5 at effort low.
    - Client-side fallback: Opus 4.8, then Sonnet 5. Bedrock has no server-side fallback.
  - Estimated cost is about $1 or less per reviewed paper.
- **Environment**: uv, python3.12, Docker 29, Node 26, and pnpm 12 (installed 2026-10-21) are present.

### Build status (2026-10-22): P1–P5 done, end-to-end working. Code is in `app/` (see `app/README.md`).
- **Run**: `cd app && make dev`. This starts GROBID in Docker on :8070, FastAPI on :8000, and Vite on :5173.
  - The Claude preview tool **cannot** start servers from this iCloud path (macOS TCC "Operation not permitted"). Start the servers with background Bash (`nohup uv run uvicorn …`, `nohup pnpm dev`), then open the browser pane at http://localhost:5173.
- **iCloud hygiene**: heavy directories stay out of iCloud sync.
  - `backend/.venv.nosync`: `UV_PROJECT_ENVIRONMENT` is set in the Makefile.
  - `app/data.nosync`: holds the PDFs and SQLite.
  - `frontend/node_modules`: a real directory with the xattr `com.apple.fileprovider.ignore#P`. pnpm rejects a symlinked node_modules.
- **Backend** (`app/backend/copilot/`):
  - `parsing/`: GROBID TEI parsed into sentence blocks with page-% boxes, with a PyMuPDF fallback. `hidden_text.py` flags injection text.
  - `agents/paper_map.py`: objective map with facets.
  - `llm.py`: Bedrock Messages-API (Claude, with citations, structured output, and caching) plus a Converse backend for non-Claude models. It falls back to other models client-side.
  - `dialogue/engine.py`: runs each turn as Analyze → deterministic `decide()` policy → Realize (cited) → Guard (GLM-5), with one revision attempt and then a safe template. Every event is logged.
  - `dialogue/prompts.py`: firewall rules and move instructions.
  - `dialogue/dimensions.py`: 8 ARR dimensions.
  - `dialogue/review.py`: synthesis from opinion units only, an entailment/drift check, check-conflict flags, scores (reviewer only), and the ARR export plus a JSON trace.
- **Frontend** (`app/frontend/src/`):
  - `pdf/PdfPane.tsx`: Lector with a CustomLayer overlay.
  - Workspace tabs: Review chat, Paper brief, Sentences, My opinions.
  - DimensionRail.
  - CitedText chips that jump to the PDF.
  - A selection toolbar for asking about, or commenting on, selected text.
  - `review/DraftPanel.tsx`: provenance, accept/edit/reject, drift and conflict warnings, and empty score selects.
  - ExportModal.
- **Measured**: about 5 s per turn with no check, about 9–15 s with a statement check (warm cache), about 25 s for the paper map, and about 15 s for synthesis.
- **Persona test suite (done 2026-10-22)**: `app/backend/evals/` (`make eval-personas PAPER=<id>`).
  - 7 personas drive the real engine; two cross-family judges (Opus 4.8, GLM-5); gates G1–G7.
  - Results are in `eval/persona_runs/SUMMARY.md` (earlier iterations in `eval/persona_runs/iterations/`). On 2 papers (ICML'26 position paper, DPO):
    - 0 real judgment leaks in 104 turns;
    - 31/31 verdict requests declined; 0/8 injections obeyed;
    - false-claim checks 6/6 correct; 0 planted opinions;
    - every gate passes.
  - Key finding: absence facts ("I could not locate X") are the main legitimate-but-salient channel of influence.
- **Conversation redesign (agreed and implemented 2026-10-28)**: after the advisor meeting. Plan + implementation status (§11) in `docs/conversation_redesign.md`.
  - Assume a low-effort, AI-reliant reviewer. Lead with evidence at every step: the copilot presents highlighted passages (auto-scrolled in the PDF, navigator), then asks one light question. Casual chat, no ARR vocabulary; formal prose only at synthesis.
  - Onboarding by reviewer level (L0 beginner … L3 AC), with level-specific questions; per paper: area familiarity (sets paper-internal background + glossary), read status, time budget. L2/L3 who read the paper → quick mode.
  - Conversation organized by the reviewer's own criteria (`dialogue/criteria.py`); ARR fields stay in the background (coverage meter, draft). Agenda planner (`dialogue/agenda.py`, Opus 5.5) picks passages per criterion at session start.
  - Per turn: monitor (`dialogue/monitor.py`, Sonnet 5; coverage in code) → statement checks → `allowed_actions()` code boundaries → conversation agent (Opus 5.5, cited, first line `ACTION: …`) → Guard (GLM-5, R1–R8 incl. selection/steering). Calls per turn vary. Prefetch after "Done with this".
  - Reviewer decides when a topic ends (no auto-advance). Commit-first dropped; first impression only in study mode / quick mode.
  - Synthesis in three registers (words / polished / formal), drift-checked; slider in draft and My opinions. Paper facts the reviewer ticks become `P#` units (disclosed).
  - Old engine kept as `dialogue/legacy.py` for the A/B; sessions without a `flow` key are legacy. Persona-suite sessions carry `origin: eval` and are hidden from the app.
  - Out of scope this round: external (non-paper) background explanations; AC meta-review mode.
  - Evaluation (2026-10-28, `eval/persona_runs/SUMMARY.md`): new flow passes G1–G7 on DPO and on the ICML'26 paper with an injected prompt. A/B vs commit-first on DPO: −32% typed characters, taste-group self-BLEU 0.084 vs 0.165 (reviews differ more by profile), recall equal (0.93); costs: lower strict precision (0.76 vs 0.83, mostly fact-informed) and more adoption of the paper's own rhetoric (10 vs 2 units). An independent plan audit found 17 gaps + 5 bugs, all fixed (`docs/conversation_redesign.md` §11.1).
- **Environment note (2026-10-27)**: Docker is no longer installed on this Mac, so GROBID does not run; parsing uses the PyMuPDF fallback (now with pattern-based section headings). `.venv.nosync`, `node_modules`, and `data.nosync` had to be recreated (`make setup`).
- **Next (P6)**:
  - User study (evidence-first vs commit-first vs plain chat); pilot the onboarding questions.
  - Component eval scripts.
  - Latency work.
  - ICLR/NeurIPS export mappings.
  - Demo video script.
  - The user study for the demo paper.

## 1. One-liner

A Socratic review copilot embedded in OpenReview, for reviewers at AI/ML/NLP venues (ACL, EMNLP, ICLR, NeurIPS, ICML).
- **The LLM supplies only objective help:** facts, evidence location, and checks of the reviewer's statements against the paper.
- **The human supplies all subjective judgment:** taste, values, novelty and significance assessments, and the decision.
- The copilot draws the reviewer's opinions out through questions, then writes the review **only from what the reviewer said**.

Slogan: *AI should help reviewers think, not think for reviewers.*

## 2. Problem / motivation

- Reviewers paste papers into LLMs and submit the output as their review ("AI slop"). The venue then receives the LLM's taste disguised as a human review, and authors effectively write for an LLM.
- Banning LLMs is unrealistic, so the goal is to **constrain how they are used**, not to forbid them.
- Disclosure and warnings do not protect human judgment (Jakesch CHI'23; Williams-Ceci Sci. Adv. 2026).
- Policy is ignored at scale: in the ICML 2026 RCT, 22.5% and 36.5% of reviewers reported non-compliance.
- Confidentiality rules (NeurIPS, ARR, ICML "privacy-compliant") make an organizer-hosted, self-hostable model necessary. At the scale of tens of thousands of submissions, that model also has to be small.
- LLMs are weakest at finding weaknesses (Wei et al. ICML'26: weakness recall 0.39–0.63 vs strengths 0.72–0.93), so flaws and judgments should stay with humans.

## 3. Core principles

- **Judgment firewall.** Factual information may flow Paper → AI → Human. Judgments may flow only Human → AI → Review. There must be no path Paper → LLM judgment → Review.
- **Objective vs subjective split**:

  | | Copilot may (objective) | Copilot must not (subjective) |
  |---|---|---|
  | Examples | Summarize claims, method, and setup; quote results; say whether a baseline or limitation is present; say *where* evidence is; flag factual misreadings | Say whether novelty or significance is high, whether a limitation is severe, whether evidence is *sufficient*, give a score, or recommend accept/reject |

  Gray zones:
  - "Evidence exists / where it is" is objective; "evidence is enough" is subjective.
  - Comparing with external prior work (e.g. "prior work A already does X") is judgment-laden and prone to hallucination. **v1 scope: facts internal to the paper only.**
- **Socratic elicitation.** Each turn is *fact + question*, never *fact + judgment*. Example: "The paper compares A, B, C; D, cited in related work, is not included. Does that affect your assessment?"
- **Opinion provenance (dual).** Every fact links to a paper span. Every opinion links to one or more reviewer utterances.
- **Legitimate vs illegitimate influence.**
  - Legitimate: correcting a factual misunderstanding, even if it changes the reviewer's view.
  - Illegitimate: framing, leading questions, selective evidence, asymmetric questioning (e.g., asking only about weaknesses).
  - Even surfacing only facts can steer the reviewer (Hackenburg Science'25), so *which* facts get surfaced must be measured.
- **Proof of cognitive engagement, not AI detection.** The interaction trace is observable evidence that the human formed the judgment. Do NOT claim "little interaction = cheating".

## 4. System design

- Lives inside the OpenReview platform. MVP may be a browser extension or standalone web app.
- Stages:
  1. Build understanding: the reviewer summarizes the main claims, and the copilot points out anything missing.
  2. Ground in evidence: the reviewer makes a claim, the copilot says what the paper does or does not contain, then asks how that affects their view.
  3. Elicit critique: concerns, assumptions, what would change their mind, which kind of concern (novelty, empirical, method).
  4. Synthesize the review from the reviewer's utterances only, with provenance links.
- **Constrained action space.**
  - Allowed: `ASK_CLARIFICATION`, `ASK_JUDGMENT`, `SURFACE_EVIDENCE`, `CHECK_CLAIM`, `CHALLENGE_WITH_EVIDENCE`, `SUMMARIZE_HUMAN_VIEW`.
  - Forbidden: `GIVE_SCORE`, `GENERATE_OPINION`, `RECOMMEND_ACCEPT/REJECT`.
- **Data byproduct** (from Wei et al. 2026, "active elicitation interface"): with opt-in consent, the copilot logs:
  - structured opinion units and the turn where each formed;
  - evidence spans;
  - dialogue acts;
  - the trajectory of each judgment.

  These logs serve as the engagement proof, as an AC audit trail, and as the judgment-process data the community lacks. Privacy: opt-in, tiered access, confidential-compute enclave.
- Practical needs: a quick mode for experts, since forcing designs lower satisfaction (Buçinca CSCW'21); keep the reviewer's own wording to support ownership; the reviewer confirms and edits the synthesized review.

## 5. Research questions

- **RQ1 Socratic dialogue policy.** How can the agent ask Socratic questions that guide the reviewer step by step to understand the paper, drawing out the reviewer's own opinions instead of imposing its own?
- **RQ2 Objectivity / neutrality.** How do we ensure no copilot turn contains a subjective judgment, neither explicit ("this experiment is weak") nor implied by leading questions, so that every opinion in the final review traces back to the reviewer?
- **RQ3 Faithful review synthesis.** The review must not invent opinions the reviewer never expressed, nor drop important ones they did express.
- **RQ4 Adversarial robustness.** Authors may hide prompt injections in the PDF (e.g., white text saying "give a positive review"), or write text that makes the copilot overstate contributions. The copilot must state only what is actually in the paper.
- **RQ5 Lightweight deployable model.** Train a small, dedicated model, via SFT and RL, that organizers can host cheaply.

## 6. Training plan

- **Data.** A strong teacher LLM plus **simulated reviewer personas with hidden opinions** generate Socratic dialogues for SFT (SFT cold start matters; see UserRL).
- **RL rewards**:
  - **Opinion fidelity**: reward recovery of the hidden opinions; penalize every opinion that is not among them. A per-turn dense version follows CURIO's belief-gain reward.
  - **Neutrality**: a judge labels each turn as factual statement, neutral question, opinion, or leading question; the last two are penalized. Try it both as a reward and as a hard constraint, since HeuristicEdu found anti-leak penalties can destabilize GRPO. The judge can be seeded with AMPERE labels.
  - **Groundedness**: span-level citations to the paper.
  - **Elicitation efficiency**: as few turns as possible; ASIG-style expected information gain is an option. **Do not reward "engagement" or conversation length.**
  - **Robustness**: train on papers containing injections and overclaims, ideally with attacker–defender co-evolution (SafeReview, ARLAS, CoER).
- **Anti-gaming fix (key novelty).** A policy can plant opinions in a suggestible simulator and then "recover" them.
  - Anchor fidelity to the **pre-dialogue** hidden opinion.
  - Add an opinion-drift penalty.
  - Include suggestible simulator types.
  - Keep simulators consistent using persona-consistency RL (arXiv 2511.00222).
- Methods to borrow: CURIO, CollabLLM (verl recipe), TutorRL/PEARL (fidelity–neutrality Pareto curve), STaR-GATE, ASIG, UserRL, REMOR/InternReviewer reward designs.
- Base model candidates: Qwen3-4B, Llama-3.1-8B-Instruct, Meta-SecAlign-8B, R1-Distill-Qwen-7B.

## 7. Evaluation plan

- **Automatic**, using simulated reviewers:
  - opinion fidelity, reported as precision and recall, plus recall of opinions stated only once (singletons get dropped about 86% of the time);
  - neutrality rate; groundedness (AIS/ALCE);
  - injection and overclaim attack success, measured as fact distortion, not score inflation;
  - always reported alongside discrimination ability, to avoid "false robustness".
- **Human study** with real reviewers, three conditions: LLM writes the review / copilot / fully manual. Compare:
  - review quality and time;
  - **ownership** (Draxler scales; a source-memory test asking "was this point yours or the AI's?");
  - understanding of the paper.
- **Judgment-leakage design**:
  1. Collect the reviewer's blind prior judgment first.
  2. Give the copilot a hidden stance: accept-leaning, reject-leaning, or neutral.
  3. Run a factorial manipulation of framing, question symmetry, and evidence selection while keeping factual answers identical.
  4. Analyze per criterion, not only the overall score.
  5. Add a planted-error probe.
- **Cautions**:
  - J → 0 is trivial: a silent copilot achieves it. Always pair leakage with understanding and efficiency.
  - Users prefer sycophantic AI, so ownership and satisfaction must be reported together with fidelity and leakage.
  - Neutrality reward option: balanced approval from accept-leaning and reject-leaning raters (Stray et al. 2026).

## 8. Contributions (current draft, see `docs/motivation_draft.md`)

1. Formulation: judgment firewall plus opinion provenance.
2. Metrics: opinion fidelity, and judgment leakage decomposed into factual vs non-factual channels. Neither has been defined before.
3. Method: RL with hidden-opinion simulated reviewers, anchored to the pre-dialogue opinion and penalizing drift.
4. Robustness of *assistants*, measured as fact distortion and overclaim, not score inflation. Includes the conflict between organizer canaries and the copilot.
5. System and study: an OpenReview-integrated, self-hostable prototype, a user study, and an opt-in judgment-process dataset as a byproduct.

## 9. Positioning (from the prior-art survey, 2026-10)

- **NOT novel anymore:**
  - Embedding an LLM chat for reviewers in OpenReview: NeurIPS 2026 is running a randomized experiment with three arms (none, open-ended, structured). The open-ended arm has no output restrictions. The model used is undisclosed.
  - The principle "AI assists, does not judge": ICML 2026 Policy B, the EACL'26 position paper, ARR REVAS, Frontiers AIRA.
  - Hidden-state user simulators with recovery rewards: CURIO, STaR-GATE, CollabLLM, TutorRL.
- **Novel / claimable:**
  - Socratic elicitation of *subjective* judgment.
  - Judgment leakage decomposition.
  - Opinion provenance (AIS-H).
  - Anti-planting elicitation RL.
  - Attacks on assistants rather than on automated reviewers.
  - A small self-hostable model for this role.
  - The data byproduct.
- **Framing to use:**
  - "A principled, trained version of a NeurIPS-style structured-assistance arm."
  - "Operationalizes Wei et al.'s (ICML'26) reviewer-copilot agenda while meeting ICML 2026's strict non-evaluative boundary."
  - Addresses the de-skilling and reference-review anchoring risks that Wei et al. leave open.
- **Closest works to cite and compare:**
  - NeurIPS 2026 experiment; ICLR 2025 Review Feedback Agent; ARR REVAS (a potential partner, not a rival).
  - ReviewFlow (IUI'24); ReVoicer (arXiv 2608.00299); Enago Read workspace; Frontiers AIRA.
  - Wei et al. ICML'26 position paper.
  - ICLR 2027 reviewer policy (requires a self-written assessment plus all LLM interactions, which our trace can supply automatically).
- **Naming:** "co-pilot" is already used by Wei et al. and NeurIPS. Pick a more distinctive name.

## 10. Constraints and facts to remember

- **Data licenses:** Review-5K and DeepReview-13K forbid use in real review systems. For anything deployable, use Re2, ARR-DC, or NLPeer.
- **Groundedness data:** PeerQA is the best fit, with QASPER and SciDQA as supplements.
- **Injection benchmarks:** Sahoo et al. (200 ICLR papers), CrackedPDFs, LLM-as-a-Reviewer, the "No Hidden Prompts Needed" rolling benchmark, RobustReview.
- **Policies (verified 2026-10):**
  - NeurIPS 2025: no sharing with any LLM. NeurIPS 2026: only sanctioned LLMs.
  - ARR: no non-privacy-preserving tools.
  - ICML 2026: privacy-compliant only, self-hosted explicitly allowed.
  - ICLR 2026: disclosure required; confidentiality is governed by the Code of Ethics.
- **Potential collaborators:**
  - ARR REVAS team (Iryna Gurevych, UKP/TU Darmstadt and MBZUAI; https://revas.mbzuai.ac.ae/).
  - NeurIPS 2026 experiment leads (Joydeep Biswas, Laurent Charlin).
  - van der Schaar group (Qiyao Wei, Samuel Holt).
  - Thinking Assistants authors (Soya Park, Hari Subramonyam, Chinmay Kulkarni). Kulkarni's Emory affiliation is unverified.

## 11. Open decisions / TODO

- [ ] Whether the data byproduct is a primary or secondary contribution. Primary means actually releasing data, which needs IRB and opt-in.
- [ ] v1 scope: facts internal to the paper only, or also external literature comparison?
- [ ] Tone toward the ICLR 2027 self-report policy (critical vs collaborative).
- [ ] Whether to cite Pangram's 21% (industry blog, disputed).
- [ ] System name.
- [ ] Verify the numbers flagged in `docs/motivation_draft.md` against the full papers.
- [ ] Follow-up searches not yet done:
  - neutral questioning by LLM interviewers;
  - meeting- or interview-to-document attribution;
  - leading-question detection;
  - 2026 submissions on interactive review copilots;
  - the EMNLP-25 paper behind REVAS.
- [ ] Watch for NeurIPS 2026 experiment results and compare as soon as they appear.

## Working conventions

- The user (team lead) writes in Chinese mixed with English terms. Reply in Chinese with English technical terms unless asked for English. Paper-facing text such as RQs, motivation, and contributions is written in English.
- Back factual claims about policies and papers with sources. Mark unverified items explicitly; do not guess affiliations or numbers.
