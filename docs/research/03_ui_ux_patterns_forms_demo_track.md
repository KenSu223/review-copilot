<!-- Research agent report, generated 2026-10-21 for the Academic Review Copilot product plan. Verify items before citing. -->

# Academic Review Copilot: UI/UX design research report (2026-10-21)

**Verification:** Unless marked *(secondary)*, I or a research sub-agent read every item below on a primary page (arXiv abstract, HTML or PDF, ACL Anthology, an official call, GitHub, or a product help page). Items I couldn't find or verify are listed at the end of Section 5.

## Key findings to read first

1. **There is close prior work you will need to position against.**
   - **ReVoicer** (arXiv 2608.00299, Jul 2026, IEEE ISMAR 2026 Alt'ISMAR workshop) already treats the reviewer as the only source of judgment. It annotates passages as you read, checks rubric coverage (covered / partial / missing), and drafts the review only from the reviewer's comments. It has **no user evaluation yet**.
   - **Judgment-Grounded Expansion** (arXiv 2606.23233, Lu, Qu & Gurevych, preprint) expands a reviewer's evaluative claim into candidate review comments.
   - **Not found in either system:** round-by-round Socratic elicitation, checking reviewer statements against the paper with PDF evidence, and sentence-level provenance back to chat turns. Those are your differentiators.
2. **ARR's reviewer policy limits what the product can say it does.** The ARR guidelines state:
   - "it is not permitted to use generative assistance to create the first draft."
   - The reviewer must "write the content and argument of the review by themselves."
   - It is "reasonable to use writing assistance to paraphrase the review."
   - Reviewers must not upload the manuscript "into a non-privacy preserving generative tool."

   So describe synthesis as organizing and paraphrasing the reviewer's own utterances, not as drafting the review. Also check whether sending the PDF to the Claude API counts as "privacy-preserving" under ARR and venue policy, and consider a local-model fallback.
3. **The next open demo deadline is NAACL 2027, on Dec 4, 2026.** It is the strictest call:
   - Submissions with no evaluation "will be desk rejected."
   - It explicitly rejects submissions whose main contribution is "'vibe coding' a demo, wrapping existing APIs, or assembling off-the-shelf models" without substantive contribution.
   - Generative AI use must be disclosed in the Acknowledgements.
   - The ACL 2027 demo call page currently says only "Coming soon!".
4. **Verifying reviewer statements is still unreliable, so show evidence rather than a bare verdict.** Peerispect reaches 0.88–0.905 accuracy on a synthetic benchmark but at best **0.287** on 150 realistic review claims.
5. **Timing and clutter are the two documented failure modes.**
   - The ICLR 2025 feedback agent arrived after submission and felt "like a critic." In the CHI 2026 follow-up, 78.4% of reviewers considered revising but only 56.9% did.
   - ReviewFlow: 68.8% found the AI features distracting. Section-level cues scored 3.8 for usefulness versus 1.6 for phrase-level cues.
   - Scim and ScholarPhi both reduced the number of colors and highlights after testing.

---

## 1. Pattern library

Priority: **M** = must, **S** = should, **C** = could (for the MVP and demo).

### A. Paper view and system highlights

| # | Pattern | Source | How we'd use it | Pri |
|---|---|---|---|---|
| A1 | Fixed facet-to-color mapping, at most 4 facets, legend always visible in the header, same mapping in every paper | Scim (Objective=green, Novelty=orange, Method=blue, Result=red); ScholarPhi replaced multiple colors with one | 4 facets: **Claim / Method-Setup / Result-Evidence / Stated limitation**. Legend with counts in the PDF toolbar. | M |
| A2 | Low-contrast background fills, not underlines or dimming the rest of the page | Scim (underlines were "too subtle," dimming was distracting) | All system highlights use translucent fills. | M |
| A3 | Separate color family for AI marks vs. user marks, with an inactive/active pair for the focused one | Open Paper `highlightColors.ts` (assistant violet #EDE9FE / #A78BFA); Synergi grey bar for user clips | Three layers: facet highlights (pale), **"evidence for the current turn"** (strong, active), the reviewer's own highlights (separate hue). | M |
| A4 | A toggle per facet plus a density slider with live counts; local +/− in the margin on hover | Scim; Semantic Reader production settings (number and opacity); CiteSee per-type toggles | Toggles in the MVP; slider later. Default to a sparse, evenly spread set. | M (toggles) / S (slider) |
| A5 | Facet-colored markers on the scrollbar | Scim | Shows where claims and results cluster. Also marks the evidence locations cited in the chat. | S |
| A6 | Sidebar list of highlights grouped by section; clicking scrolls the PDF | Scim highlight browser (opened 9.3 times per reader); Threddy clips | "Paper map" tab next to the chat: a list of claims with their evidence locations. | S |
| A7 | Key-question index with short answer gists that jump to the passages | Paper Plain (clear favorite feature); Open Paper starter questions | Objective "Paper brief": What is claimed? What data? Which baselines? What limitations do the authors state? Every answer is a jump link. No judgments. | S |
| A8 | Cover figures and tables, and align with the author's own contribution lists | Scim failure analysis | The claim extractor must include the numbered contribution list and table and figure captions. | S |
| A9 | Compact tooltips (at most half the page width, 4 lines); "Defined here"; details go in the sidebar | ScholarPhi | Term and symbol definitions on hover. | C |

### B. Grounded Q&A and evidence

| # | Pattern | Source | How we'd use it | Pri |
|---|---|---|---|---|
| B1 | Citation chip: hover to preview the quote, click to jump, highlight the span, Back to return | NotebookLM; Open Paper `CustomCitationLink`; ScholarPhi "page N"; Qlarify evidence card | Every factual sentence in chat and in the draft carries a chip like `[p.6 ¶2]` or `[Tab.3]`. | M |
| B2 | Anchor only to verbatim quotes, validated by normalized string match; discard anchors that don't match | AnchoredAI (unmatched anchors treated as hallucinations); Open Paper `findTextPosition.ts`; papermage spans and boxes; VISA (VLM-predicted boxes fail zero-shot) | The model returns quotes; the backend resolves them to papermage sentence boxes and drops anything that fails to match. No unverified chip is ever shown. | M |
| B3 | "Ask" restricted to paper facts, citing section and page, and refusing to critique | ReVoicer "Ask" | The objective-help channel. Requests for opinions are bounced back as Socratic questions. | M |
| B4 | Selection toolbar: Ask / Note / Check | Open Paper; ReVoicer floating toolbar; ReviewFlow light-bulb; alphaXiv highlight-to-ask *(secondary)* | Selecting text in the PDF gives **Ask about this · Check my statement · Note**. | M |
| B5 | Statement check as a card: reviewer quote + label + evidence passages; the reviewer decides | Peerispect labels (Supported / Partially supported / Contradicted / Undetermined); ICLR agent "Reviewer comment: / Feedback to the reviewer:" pairs; InkSync Verified / Incorrect / Not sure | Inline check card under a reviewer turn: 4-state label, 1–3 evidence chips, and actions [Keep] [Revise my statement] [Dismiss]. | M |
| B6 | Select a sub-span of the output to get finer attribution | LAQuer (ACL 2025; 54% less source text to read than sentence-level citations) | In the editor, selecting part of a sentence shows exactly which paper span supports it. | C |

### C. Socratic elicitation

| # | Pattern | Source | How we'd use it | Pri |
|---|---|---|---|---|
| C1 | One question per turn, 2–3 sentences, probe before advising; keep a path for plain factual answers | Thinking Assistants (users who wanted answers got frustrated) | Each turn: objective context with chips, then one open question. Factual questions get direct answers. | M |
| C2 | Quick-reply chips (2–4) with escape hatches | Claude Agent SDK AskUserQuestion (2–4 options, "Other" free text, can be dismissed); InkSync "Not sure" | Chips are **symmetric stance scales or meta-actions** ([Convinced] [Partly] [Not convinced] [Not sure] / [Show evidence] [Skip] [Go deeper]), always followed by "why?". **Never pre-written opinions.** | M |
| C3 | Review dimensions as the question scaffold, prompts at section level | ReviewFlow section cues (importance / novelty / validity / clarity; rated 3.8 vs 1.6 for phrase-level) | Dimensions map to ARR fields (Section 3). Questions are tied to paper sections, not individual phrases. | M |
| C4 | Elicit judgment before revealing any synthesis | MetaWriter (decision required before the draft is shown); JGE (starts from the reviewer's claim) | Synthesis unlocks per dimension only after the reviewer has stated a position. Scores are always typed by the reviewer. | M |
| C5 | No "answer for me" or "Expand" buttons that invent content | Scraft "answer the question for me" (an anti-pattern for us); ReviewFlow participants feared "Expand" would add content they didn't intend | Explicit design rule; mention it in the paper. | M |
| C6 | The reviewer controls depth: Go deeper / Next dimension / edit the plan | ExploreSelf (user decides depth; pin or reword themes); ChatGPT deep research's editable plan *(secondary)* | Dimension plan is editable at the start (reorder, mark N/A, e.g. Datasets). Each turn offers Go deeper / Next. | S |
| C7 | Questions anchored in the margin next to the paper section | AnchoredAI margin threads; ReviewFlow cues placed beside each section | Small margin badge "2 questions on §4" that opens the chat at that thread. | S |
| C8 | A "your turn" card format | Claude Code "Learning" output style ("Learn by Doing" card: Context / Your Task / Guidance) | Visual style for questions that need a substantive answer (e.g., "Your summary in 2 sentences"). | C |
| C9 | Switch modes mid-session | OpenAI Study mode toggle *(secondary; official page returned 403)*; Gemini Guided Learning in the Tools menu | Header switch between **Facts-only** (no questions) and **Socratic**. | C |

### D. Progress

| # | Pattern | Source | How we'd use it | Pri |
|---|---|---|---|---|
| D1 | Coverage per venue criterion as covered / partial / missing, with a one-line gap note | ReVoicer Rubric tab; REVAS guideline flags; ReviewFlow | Dimension rail of ARR fields with ●/◐/○ and a gap note (e.g., "Soundness: no stance yet on Table 3 variance"). | M |
| D2 | Turn timeline colored by dimension, with hover brushing | HaLLMark timeline (hover a prompt to highlight the linked text; click to pin) | Bottom strip T1…Tn. Hovering a turn highlights the draft sentences it produced. | S |
| D3 | Composition meter | HaLLMark pie chart; "Who Owns the Text?" proposed AI-share meter; Grammarly Authorship circle graph | "Draft: 62% your words / 31% paper facts / 7% connective (paraphrase)." | S |
| D4 | Objective quality checks on the reviewer's own text, during writing | REVAS (actionability, grounding, verifiability, tone; ARR heuristics H1–H17); ICLR agent (vague / misunderstanding / unprofessional); CHI 2026 study on timing | Gentle flags, for example "Weakness 2 has no evidence anchor" or "This matches heuristic H5: 'Results do not beat the latest SOTA.'" Shown before export, not after. | S |

### E. Provenance and the review editor

| # | Pattern | Source | How we'd use it | Pri |
|---|---|---|---|---|
| E1 | Two-channel encoding: paper fact vs. reviewer opinion | HaLLMark (orange = AI-written, green = AI-influenced); InkSync audit colors; IBM study (phrase-level highlighting preferred) | Facts: thin dotted underline in the facet color. Opinions: a left-gutter bar in the "reviewer" color. A toggle hides all marks. | M |
| E2 | Provenance chips hidden until hover, or kept in the gutter | NotebookLM / Perplexity numbered citations | `[p.4 ¶2]` for facts, `[T7]` for reviewer turns. A compact superscript in Draft view; full chips in Audit view. | M |
| E3 | Two-way brushing between draft sentence, chat turn, and PDF span | ReviewFlow (click an outline bullet: source notes highlighted and PDF scrolled); MetaWriter (hover a key sentence: source sentence highlighted in red); ReVoicer highlight-to-note links | Click a sentence and the PDF scrolls to its span while the chat scrolls to its turn. Hover a turn and its sentences light up. | M |
| E4 | Reviewer's exact words next to the synthesized sentence | ReviewFlow's distortion fear ("a little bit unclear" became "lack clarity"); LLM Asks, You Write | The provenance inspector shows the verbatim turn excerpt plus a drift check (intensity and polarity preserved?). | M |
| E5 | Proposed (gray) until accepted, provenance kept after acceptance and edits | "Who Owns the Text?" (provenance cues at the point of decision; its stated limitation is that provenance disappears after acceptance); InkSync Accept / Dismiss | Every synthesized sentence starts as proposed; Accept / Edit / Reject. Edits keep the link and are marked "edited by you." | M |
| E6 | Flag unsourced content | InkSync "Edit contains new unverified information"; AnchoredAI | Any sentence without a turn or span link gets a ⚠ and must be confirmed or deleted before export. | M |
| E7 | Separate clean Draft view and Audit view | InkSync Audit interface (caught up to 73% of inaccurate edits); Grammarly report and replay | A [Draft | Audit] toggle. Audit shows every chip, label, and check result. | S |
| E8 | Outline before prose; no verdict sentences | ReviewFlow (outline, not prose, by design); MetaWriter (decision-indicating sentences removed) | Synthesize bullets per ARR field first; turning them into prose is a separate step the reviewer triggers. | S |
| E9 | Friction against copying the draft wholesale | MetaWriter (draft hidden behind a toggle, similarity popup; self-BLEU rose, a sign of homogenization) | Per-sentence acceptance stands in for the toggle. | S |
| E10 | Export with a disclosure-ready provenance log | REVAS (an option in the ARR disclosure question); ICLR 2026 LLM-use field; Grammarly shareable report | Export the ARR text plus a JSON/HTML provenance report plus a suggested AI-use disclosure sentence. | S |

---

## 2. Recommended screens

### Screen 0: Setup (local)
- Drop a PDF and choose the target form: **ARR** (default), ICLR, or NeurIPS.
- Enter the API key. A privacy panel says what leaves the machine, and offers an optional local-model mode.
- In the background, parse the PDF with papermage into sentences with boxes, sections, figures, and tables (B2). Then run objective extraction: claims, contributions, experiments, stated limitations (A1, A8).
- *Rationale:* the ARR confidentiality clause; anchors must be precomputed and validated.

### Screen 1: Paper brief (optional, about 2 minutes)
- Shows the facet legend and a **key-question index** with answer gists that jump to passages (A7). Examples: "Main claims (5)", "Datasets", "Baselines", "Limitations the authors state".
- A banner says: *"Facts only. Your assessment comes next."*
- The reviewer edits the **dimension plan**: reorder, mark items N/A (C6).

### Screen 2: Review workspace (main screen)

**PDF pane (about 55% of the width).**
- Facet toggles with counts in the toolbar (A1, A4).
- Scrollbar markers (A5).
- The **active evidence** layer shows whichever chip is focused in the chat (A3).
- Selection toolbar: Ask / Check my statement / Note (B4).
- Margin badges mark where questions are anchored (C7).

**Conversation pane (about 45% of the width).**
- System turns follow C1: objective context with chips, one open question, then chips for stance or meta-actions (C2).
- Reviewer turns get an ID (T1…Tn) and are tagged with a dimension.
- Statement-check cards appear inline under the turns they check (B5).
- Factual questions are answered directly (B3).
- Tabs: Chat | Paper map (A6) | Notes.

**Dimension rail (top).** ARR fields with ●/◐/○ (D1). Clicking a field jumps to that thread or starts it.

**Turn timeline (bottom).** Colored by dimension, with brushing (D2).

```
+----------------------------------------------------------------------------------------------------+
| Review Copilot | "Paper title" (local) | Form: ARR v | Mode: [Socratic|Facts-only] | Saved | [Draft >] |
+----------------------------------------------------------------------------------------------------+
| Summary * | Strengths o | Weaknesses o | Soundness o | Excitement - | Reproducibility - | Ethics - |
| Comments -  | Confidence -  | Overall -         (* covered   o partial   - missing; click to jump)  |
+-------------------------------------------------+--------------------------------------------------+
| Facets [x]Claim 12 [x]Method 9 [x]Result 14 [ ]Limit 3 |  [Chat] [Paper map] [Notes]                 |
|  +--------------------------------------------+ |  +- T6 . Soundness ----------------------------+ |
|  | 4.2 Main Results                           |#| |  | Fact: Table 3 reports single-run numbers    | |
|  | [Claim fill] Our method improves ... by    | | |  | with no std [Tab.3]; App. B mentions 3      | |
|  |  2.1 points on average.                    |#| |  | seeds [p.12 1].                              | |
|  |                                            | | |  | How convinced are you that the Table 3      | |
|  | [ACTIVE EVIDENCE] Table 3: Results on ...  |#| |  | gains are reliable?                          | |
|  |                                            | | |  | (Convinced)(Partly)(Not convinced)(Not sure)| |
|  |  (?) 2 questions on 4.2                    | | |  | (Show evidence)(Skip)(Go deeper)             | |
|  +--------------------------------------------+ | |  +---------------------------------------------+ |
|   ^ scrollbar facet markers (#)                 |  You (T7): Not convinced. Gains look within     |
|                                                 |  noise and no seeds are reported.               |
|  select text -> [Ask] [Check my statement] [Note] |  +- Check: "no seeds are reported" ----------+ |
|                                                 |  | (o) Partially supported                     | |
|                                                 |  | App. B: "averaged over 3 seeds" [p.12 1]   | |
|                                                 |  | Table 3 shows no std [Tab.3]               | |
|                                                 |  | [Keep] [Revise my statement] [Dismiss]     | |
|                                                 |  +---------------------------------------------+ |
|                                                 |  [ Your view...                       ] [Send] |
+-------------------------------------------------+--------------------------------------------------+
| Timeline: T1 T2 T3 T4 T5 [T6 T7] T8 ...  (color = dimension; hover = highlight in PDF and draft)    |
+----------------------------------------------------------------------------------------------------+
```

**Key interactions:**
- Clicking a chip scrolls the PDF and pulses the evidence fill. Back returns you (B1).
- "Check my statement" works on any reviewer turn or PDF selection (B5).
- "Go deeper" asks a follow-up on the same dimension. "Next" moves on, and the rail updates (C6, D1).
- A dimension becomes ● only when the reviewer has stated a stance and given at least one reason.

**Elicitation order** (ARR-first): Summary (written by the reviewer, then checked against the paper) → Strengths → Weaknesses (numbered, as ARR asks) → Soundness → Excitement → Reproducibility / Datasets / Software → Limitations & ethics → Comments/Typos → Confidence → Overall.

### Screen 3: Synthesis and review editor
- **Left: the ARR form.** Each field holds proposed bullets, then prose on request (E8). Proposed sentences are gray until accepted (E5). Facts get a dotted underline with a `[p.x]` chip; opinions get a gutter bar with a `[Tn]` chip (E1, E2). Unsourced sentences get ⚠ (E6).
- **Score widgets are empty dropdowns that only the reviewer sets** (C4). No defaults, no suggestions, consistent with REVAS.
- **Right: provenance inspector** for the selected sentence (E3, E4):
  - the reviewer's verbatim turn
  - the paper span, with a jump link
  - the statement-check status
  - the drift check
- **Toolbar:** [Draft | Audit] (E7), composition meter (D3), objective quality flags (D4), and "Accepted 14/18."

```
+----------------------------------------------------------------------------------------------------+
| Review draft . ARR   View: [Draft|Audit]   Unsourced: 1 (!)   Accepted 14/18   Yours 62% . Paper 31% |
+--------------------------------------------------+-------------------------------------------------+
| Summary of Weaknesses                            | Provenance . sentence W1.2 (opinion)            |
| 1. | The reported gains may be within run-to-run | Your words (T7, Soundness):                     |
|    | variance [T7]; Table 3 reports no standard  |   "Not convinced. Gains look within noise..."   |
|    | deviation [Tab.3].                           | Paper: Table 3, no std  [jump]                  |
|    |                  [Accept] [Edit] [Reject]    | Check: (o) partially supported (App. B, 3 seeds)|
| 2. (!) no source . [Link to a turn] [Delete]     | Drift: "within noise" -> "may be within         |
| Soundness: [ -- choose -- v ]  (you set this)    |   variance": polarity ok, intensity ok          |
+--------------------------------------------------+-------------------------------------------------+
```

### Screen 4: Export
- **ARR:** plain text or Markdown laid out by the 17 form fields, ready to paste.
- **ICLR / NeurIPS:** remapped to their fields (Section 3.3). The reviewer must re-enter the scores.
- **Provenance report:** HTML or JSON with sentence → {turn | span}.
- A suggested **AI-use disclosure** sentence (E10).
- A pre-export checklist: no ⚠ remaining, all sentences accepted, every score set by the reviewer.

---

## 3. Review form specifications

### 3.1 ARR review form (https://aclrollingreview.org/reviewform)

The page is marked © 2026 and shows no cycle. Fields in order:

| # | Field | Type / scale (labels verbatim, sometimes abridged) | Notes for elicitation |
|---|---|---|---|
| 1 | Paper Summary | Free text; "help action editors and area chairs" understand the topic | The reviewer writes it; the system checks it against the paper |
| 2 | Summary of Strengths | Free text; main reasons to publish at a selective *ACL venue | Opinions only, each with a `[Tn]` link and optional span |
| 3 | Summary of Weaknesses | Free text; "Where possible, please number your concerns so authors may respond to them individually." | Export as a numbered list; run the H1–H17 heuristic check |
| 4 | Comments/Suggestions/Typos | Free text; improvements "other than addressing the concerns above" | Nice-to-haves go here (guidelines: weaknesses should not be "nice-to-have" items) |
| 5 | Reviewer Confidence | 1–5, integers. 5 "Positive that my evaluation is correct. I read the paper very carefully and am familiar with related work." · 4 "Quite sure. I tried to check the important points carefully." · 3 "Pretty sure, but there's a chance I missed something." · 2 "Willing to defend my evaluation, but it is fairly likely that I missed some details, didn't understand some central points, or can't be sure about the novelty of the work." · 1 "Not my area, or paper is very hard to understand. My evaluation is just an educated guess." | Reviewer only |
| 6 | Soundness | 1–5 with half-points (4.5, 3.5, 2.5, 1.5; half-points have no labels). 5 "Excellent: This study is one of the most thorough I have seen, given its type." · 4 "Strong: …sufficient support for all of its claims…" · 3 "Acceptable: …sufficient support for its main claims…" · 2 "Poor: Some of the main claims are not sufficiently supported…" · 1 "Major Issues: …not yet sufficiently thorough to warrant publication or is not relevant to ACL." | Guidelines: must be "justified by the text of the review". Warn if the score is low but no weakness is linked. |
| 7 | Excitement | 1–5 with half-points. 5 "Highly Exciting" · 4 "Exciting" · 3 "Interesting" · 2 "Potentially Interesting" · 1 "Not Exciting" (each with a recommend / attend gloss) | Guidelines: "orthogonal" to soundness; may "not necessarily come with explicit reasons" |
| 8 | Overall Assessment | 5 "Consider for Award" (up to top 2.5%) · 4.5 "Borderline Award" · 4 "Conference" · 3.5 "Borderline Conference" · 3 "Findings" · 2.5 "Borderline Findings" · 2 "Resubmit next cycle" · 1.5 "Resubmit after next cycle" · 1 "Do not resubmit" | Reviewer only; a composite of soundness, excitement, novelty, and impact |
| 9 | Best paper justification | Free text, required only if the Overall score is 5 or 4.5 | Conditional field |
| 10 | Limitations and Societal Impact | Free text: did the authors discuss these adequately? | The system can point to the paper's Limitations section (a fact) |
| 11 | Ethical Concerns | Free text; refers to the ACL Code of Ethics and the authors' ARR checklist | Reviewer only |
| 12 | Needs Ethics Review | Free text justification (guidelines: otherwise "None") | Reviewer only |
| 13 | Reproducibility | 1–5, integers. 5 "They could easily reproduce the results." · 4 "…mostly reproduce…sample variance" · 3 "…with some difficulty…parameters underspecified…" · 2 "…hard pressed…data…not available outside the author's institution" · 1 "…would not be able to reproduce the results here no matter how hard they tried." | The system lists objective facts first: code and data links, hyperparameters, seeds |
| 14 | Datasets | 1–5, only if datasets are released: 5 Enabling · 4 Useful · 3 Potentially useful · 2 Documentary · 1 "No usable datasets submitted." | Auto-suggest N/A if the paper releases no datasets (a fact) |
| 15 | Software | 1–5, only if software is released: same labels; 1 "No usable software released." | Same as above |
| 16 | Knowledge of/educated guess at author identity | 1–5: 5 violation of double-blind rules · 4 preprint/workshop · 3 contents of the submission · 2 social media/talk · 1 "I do not have even an educated guess…" | Reviewer only; never inferred by the system |
| 17 | (Optional) Conjecture as to author identity | Free text; "Authors will not see your response." | Reviewer only |

**Additions on the live form not shown on the static page:**
- The REVAS post (https://aclrollingreview.org/revas-may26) says "The review form includes a question about disclosure of use of AI tools by the reviewer" (visible to authors, with REVAS as an option). The exact field name isn't public.
- The guidelines also mention a reviewer checklist.

**Product implication:** add a free-text "AI-use disclosure" slot to the export.

**ARR policy constraints on the product** (https://aclrollingreview.org/reviewerguidelines): the first-draft prohibition, the privacy-preserving-tool requirement, and the acceptability of paraphrasing (quoted in key finding 2). Also: "Reviews are valued for their content rather than language", and reviewers should watch for hidden prompt injections in submissions. Your PDF ingestion should strip or flag injected instructions.

### 3.2 ICLR 2026 and NeurIPS 2025 for comparison

| | ICLR 2026 | NeurIPS 2025 (https://neurips.cc/Conferences/2025/ReviewerGuidelines) |
|---|---|---|
| Text fields | Summary · Strengths · Weaknesses · Questions *(field list from Camelo-Guerrero & Diaz-Rodriguez, https://arxiv.org/abs/2608.03659, which collected ICLR 2026 reviews through the OpenReview API; secondary)* | Summary · Strengths and Weaknesses (one field, covering Quality / Clarity / Significance / Originality) · Questions (3–5 actionable, with what would change your score) · Limitations ("yes" or suggestions) |
| Sub-scores | Soundness, Presentation, Contribution, each 1–4 (poor / fair / good / excellent) *(secondary)* | Quality, Clarity, Significance, Originality: "4 excellent, 3 good, 2 fair, 1 poor" |
| Overall | **{0, 2, 4, 6, 8, 10}**: 0 strong reject · 2 reject, not good enough · 4 marginally below the acceptance threshold · 6 marginally above · 8 accept, good paper · 10 strong accept *(secondary)*. ICLR 2024/2025 used {1, 3, 5, 6, 8, 10}. One blog says "borderline accept" moved from 6 to 5 in 2026, which conflicts with this; unresolved. | "6: Strong Accept, 5: Accept, 4: Borderline accept, 3: Borderline reject, 2: Reject, 1: Strong Reject" |
| Confidence | 1–5 *(secondary)* | 1–5 (5 absolutely certain … 1 educated guess) |
| Other | Official guide (https://iclr.cc/Conferences/2026/ReviewerGuide): "The review form will include a field to specify how you used LLMs, if at all"; separate Code of Ethics report (2 questions) | Ethical concerns flag; code-of-conduct acknowledgement; responsible-reviewing acknowledgement |

**Notes:**
- NeurIPS 2026 (https://neurips.cc/Conferences/2026/ReviewerGuidelines) keeps the same four criteria and adds **Contribution Types** (General, Theory, Use-Inspired, Concept & Feasibility, Negative Results). The form is the same for all types, but each type reads the criteria differently. The 2026 page doesn't list numeric scales.
- OpenReview's API returned a bot challenge, so I couldn't read the ICLR 2026 form directly. I did not try to get past the challenge.

### 3.3 Export mapping

| ARR | ICLR | NeurIPS |
|---|---|---|
| Paper Summary | Summary | Summary |
| Strengths / Weaknesses | Strengths / Weaknesses | Strengths and Weaknesses (merged, grouped by the 4 criteria) |
| Comments/Suggestions/Typos | Questions (partial) | Questions |
| Soundness (1–5, half-points) | Soundness (1–4) | Quality (1–4) |
| Excitement | Contribution (partial) | Significance / Originality |
| — | Presentation | Clarity |
| Overall (Findings tiers) | Rating | Overall (1–6) |
| Confidence | Confidence | Confidence |
| Limitations & Societal Impact | — | Limitations |
| Ethical Concerns / Needs Ethics Review | CoE report | Ethical concerns flag |
| Reproducibility / Datasets / Software | — | — |

**Do not convert scores between venues automatically.** The scales don't line up and the scores are subjective, so the reviewer re-enters them for the target venue.

---

## 4. ACL System Demonstrations

### 4.1 Requirements (all from fetched calls)

| | ACL 2026 | EMNLP 2026 | EACL 2027 | **NAACL 2027** |
|---|---|---|---|---|
| Deadline | Feb 27, 2026 (closed) | Jul 10, 2026 (closed) | Sep 23, 2026 (closed) | **Dec 4, 2026, AoE** (portal opens Nov 1; notification Feb 10, 2027; camera-ready Mar 3, 2027; conference Jun 1–5, 2027) |
| Main text | "no more than 6 pages (longer submissions will be desk rejected)" | "up to 6 pages" (desk reject if longer) | "up to 6 pages" | "no more than 6 pages" (desk reject if longer) |
| Appendix | "limited to 2 pages" | "maximum of 2 pages" | "unlimited space for references and informative appendices" | "limited to 2 pages" |
| References / ethics statement | Unlimited | Unlimited | Unlimited | Unlimited |
| Camera-ready | +1 page | +1 page | +1 page | +1 page |
| Video | "up to 2.5 minutes", required | "at most 2.5 minutes" | "at most 2.5 minutes"; link in the PDF and the OpenReview form | "up to 2.5 minutes"; captions or narration encouraged |
| Live demo / package | Link to a live demo or an installation package; missing links are desk rejected | Same ("strict requirement") | Same | Same, plus "Reviewers are expected to interact with the provided live demo or installable package" |
| Open source | "of special interest" | Same | Same | Not stated |
| Review mode | Single-blind (not anonymous) | Single-blind | Single-blind | Single-blind |
| Evaluation | No evaluation "may be desk rejected" | Same | Same; acceptable evidence: "user studies (of any size), automated simulations, benchmark results, expert evaluations, usage statistics, case studies, and qualitative feedback" | No evaluation "**will be desk rejected**" |
| Generative AI | — | — | — | Must be "fully disclosed in the Acknowledgements section" (example: built "with Claude Code") |
| Rebuttal | None | None | None | None |

- ACL 2027 (Kyoto): the demo call says "Coming soon!".
- ACL 2025 had the same 6 + 2 pages and 2.5-minute video.
- The ACL 2023 demo chairs report gives 155 submissions and 58 accepted.

**Reviewing criteria.**
- **Questions the paper must answer** (ACL 2026 and NAACL 2027): what problem the system solves; why it matters and what impact it has; what is novel; who the target audience is; how it works; how it compares with existing systems; how it is licensed; how it was evaluated (user studies or human evaluation?). Screenshots or diagrams are required.
- **EACL 2027 rubric:** Motivation, Fit & Novelty; Related Work & Contribution; System & Demonstration Description (including "quality and usability of the user interface"); Evaluation, Availability & Licensing; Presentation Quality.
- **NAACL 2027 "strong submissions"** show one or more of: "User studies or human evaluations with the intended target audience"; "Real-world deployment with documented usage"; "Systematic evaluation against baselines or existing tools"; "Novel technical contributions whose impact is measurable".
- **Best Demo:** "innovation, the contribution and the completeness of the live demo system."

### 4.2 Similar accepted demos and how they were evaluated

| System | Venue | What it does | Evaluation | Artifacts |
|---|---|---|---|---|
| **CARE** (UKP Lab) | ACL 2023 Demo, https://aclanthology.org/2023.acl-demo.28/ | Collaborative PDF reading and peer-review annotation, with NLP plug-ins and behaviour logging | **User study, N=11** (humanities and social-science researchers): 15-min onboarding, 40-min timed review of a 9-page F1000 paper, then swapping papers and deciding accept/reject from the other group's comments. PSSUQ-subset usability survey, free-text feedback, log analysis (200 comments; 17.5% deleted) | GitHub |
| **PaperMentor** | ACL 2026 Demo, https://aclanthology.org/2026.acl-demo.39/ | 12 agents plus a skill library from expert writing advice; posts inline Overleaf comments and leaves the writing to the author | **n=14 annotators**, 80 papers. Blind comparison against the same LLM (GPT-5.2) without the skill library. Binary validity / actionability / conciseness ratings, Mann–Whitney U. Actionable 90.6%, valid 67.5% | GitHub (AGPL-3.0), live demo, video |
| **OpenReviewer** | NAACL 2025 Demo, https://aclanthology.org/2025.naacl-demo.44/ | Llama-8B fine-tuned on 79K reviews; generates a full review (aimed at authors, and the opposite of our philosophy) | Automatic only, 400 papers. Recommendation matches at least one human reviewer 55.5% of the time vs 23.8% for the best general LLM. LLM-judge arena win rates of 60–76% | HF Space |
| **GraphMind** | EMNLP 2025 Demo, https://aclanthology.org/2025.emnlp-demos.21/ | Interactive novelty assessment for reviewers with traceable related-paper evidence | Automatic: labels compared with originality scores from ICLR/NeurIPS reviews across 4 LLMs and 2 baselines; GPT-4o pairwise judging of rationales. User study listed as future work | Site, video, GitHub |
| **Ai2 Scholar QA** | ACL 2025 Demo, https://aclanthology.org/2025.acl-demo.49/ | Literature synthesis with inline citations and evidence excerpts | Benchmark plus ablations plus 9-week deployment: 30.2k questions, 8,219 visitors, 85% positive thumbs, coding of 383 negative comments | Live site, GitHub, video |
| **SciTrue** | EACL 2026 Demo, https://aclanthology.org/2026.eacl-demo.27/ | Claim verification with sub-claim source attribution | 2 annotators, 300 attributions per system vs GPT-4o-search and Perplexity, 8 binary criteria, 90% agreement | scitrue.org |
| **TruthReader** | EMNLP 2024 Demo, https://aclanthology.org/2024.emnlp-demo.10/ | Document chat with inline citations | GPT-4 as judge on 88 examples, checked against 2 human experts on 264 items | — |

**Not demo papers:**
- ReviewFlow (IUI 2024): within-subjects, N=16 novices, expert-rated comprehensiveness.
- MetaWriter (CSCW 2024): within-subjects, N=32, plus self-BLEU homogenization.

Both are useful templates for the user study.

### 4.3 Suggested evaluation for our demo
1. **Component evaluation** (automatic plus a small human check, on public papers such as ICLR papers with public reviews):
   - Evidence-highlight precision and recall against human span annotations.
   - Statement-check accuracy on reviewer statements taken from public reviews (Peerispect-style labels; report the realistic set).
   - **Synthesis faithfulness:** percentage of opinion sentences entailed by a linked turn; percentage of unsourced sentences; the **rate of judgments the system originated** (sentences whose stance exceeds what the reviewer said). This is the metric only our system has.
2. **User study, within-subjects, N≈12–16 ML/NLP reviewers** (comparable to CARE, PaperMentor, ReviewFlow):
   - Conditions: our system vs. a baseline (PDF + form + generic chat LLM), or vs. an ablation without Socratic elicitation or provenance. The ablation also answers the "wrapping APIs" concern, as PaperMentor did.
   - Measures:
     - expert-rated review quality (ReviewFlow comprehensiveness; REVAS/RevUtil actionability, grounding, verifiability)
     - ownership and agency
     - SUS or PSSUQ
     - NASA-TLX
     - time
     - self-BLEU homogenization
3. **Ethics section:** confidentiality, the ARR first-draft rule, data flow to the API, and demos limited to public papers.

---

## 5. References

**Paper-reading interfaces**
- Semantic Reader: https://arxiv.org/abs/2303.14334 · https://cacm.acm.org/research/the-semantic-reader-project · https://www.semanticscholar.org/product/semantic-reader
- Scim: https://arxiv.org/abs/2205.04561
- ScholarPhi: https://arxiv.org/abs/2009.14237
- Paper Plain: https://arxiv.org/abs/2203.00130
- CiteSee: https://arxiv.org/abs/2302.07302
- Threddy: https://arxiv.org/abs/2208.03455
- Relatedly: https://arxiv.org/abs/2302.06754
- Synergi: https://arxiv.org/abs/2308.07517
- Qlarify: https://arxiv.org/abs/2310.07581
- PaperWeaver: https://arxiv.org/abs/2403.02939
- alphaXiv: https://www.alphaxiv.org · https://spectrum.ieee.org/alphaxiv
- Open Paper: https://github.com/khoj-ai/openpaper
- papermage: https://github.com/allenai/papermage
- NotebookLM citations: https://support.google.com/notebooklm/answer/16179559
- VISA: https://arxiv.org/abs/2412.14457

**Reviewer tools and studies**
- ReviewFlow: https://arxiv.org/abs/2402.03530
- ReVoicer: https://arxiv.org/abs/2608.00299
- Peerispect: https://arxiv.org/abs/2604.17667 · https://github.com/Reviewerly-Inc/Peerispect · https://app.reviewer.ly/app/peerispect
- ICLR 2025 Review Feedback Agent:
  - https://blog.iclr.cc/2024/10/09/iclr2025-assisting-reviewers/
  - https://blog.iclr.cc/2025/04/15/leveraging-llm-feedback-to-enhance-review-quality/
  - https://arxiv.org/abs/2504.09737
  - https://github.com/zou-group/review_feedback_agent
- CHI 2026 follow-up study: https://arxiv.org/abs/2602.13817
- REVAS: https://revas.mbzuai.ac.ae/ · https://aclrollingreview.org/revas-may26
- RevUtil: https://arxiv.org/abs/2509.04484
- MetaWriter: https://par.nsf.gov/servlets/purl/10523828 (DOI 10.1145/3637371)
- AnnotateGPT: https://github.com/onekin/AnnotateGPT · https://arxiv.org/abs/2412.00281 · https://chromewebstore.google.com/detail/annotategpt/gjocfhlnleefeikdcnebmohfkgckceip
- Judgment-Grounded Expansion: https://arxiv.org/abs/2606.23233
- NeurIPS 2026 AI reviewing experiment: https://neurips.cc/Conferences/2026/ai-reviewing-experiment
- ICML 2026 LLM-policy RCT: https://arxiv.org/abs/2609.19420
- AAAI-26 AI review pilot: https://arxiv.org/abs/2604.13940

**Provenance**
- HaLLMark: https://arxiv.org/abs/2311.13057
- LAQuer: https://aclanthology.org/2025.acl-long.746/ · https://arxiv.org/abs/2506.01187
- AnchoredAI: https://arxiv.org/abs/2509.16128
- InkSync: https://arxiv.org/abs/2309.15337
- "Who Owns the Text?" (point-of-decision provenance cues): https://arxiv.org/abs/2601.10236
- IBM factuality and attribution study: https://arxiv.org/abs/2405.20434
- Grammarly Authorship: https://www.grammarly.com/authorship
- Perplexity: https://www.perplexity.ai/hub/getting-started
- Elicit: https://support.elicit.com/en/articles/14759154-systematic-reviews-in-elicit · https://elicit.com/blog/living-documents-ai-ux

**Socratic and reflective conversation**
- Thinking Assistants: https://arxiv.org/abs/2312.06024
- Scraft: https://arxiv.org/abs/2304.10543
- ExploreSelf: https://arxiv.org/abs/2409.09662
- LLM Asks, You Write: https://openaccess-api.cms-conferences.org/articles/download/978-1-964867-71-7_29
- Textfocals: https://arxiv.org/abs/2403.01055
- OpenAI Study mode: https://openai.com/index/chatgpt-study-mode/ (403 when fetched; secondary: https://www.maginative.com/article/openai-launches-study-mode-for-chatgpt/)
- Claude for Education: https://www.anthropic.com/news/introducing-claude-for-education
- Claude Code output styles: https://code.claude.com/docs/en/output-styles
- Claude learning mode for all users (press only): https://engadget.com/ai/anthropic-brings-claudes-learning-mode-to-regular-users-and-devs-170018471.html
- Gemini Guided Learning: https://blog.google/outreach-initiatives/education/guided-learning/
- AskUserQuestion: https://code.claude.com/docs/en/agent-sdk/approvals
- ChatGPT deep research: https://help.openai.com/en/articles/10500283-deep-research-in-chatgpt
- Critical Inker: https://www.media.mit.edu/projects/critical-inker/overview/

**Review forms and policies**
- ARR review form: https://aclrollingreview.org/reviewform
- ARR reviewer guidelines: https://aclrollingreview.org/reviewerguidelines
- ARR changelog: https://aclrollingreview.org/changelog
- NeurIPS reviewer guidelines: https://neurips.cc/Conferences/2025/ReviewerGuidelines · https://neurips.cc/Conferences/2026/ReviewerGuidelines
- ICLR 2026 reviewer guide: https://iclr.cc/Conferences/2026/ReviewerGuide
- ICLR 2026 field data (secondary): https://arxiv.org/abs/2608.03659 · https://randomfeatures.substack.com/p/do-papers-submitted-later-receive

**Demo calls and demos**
- Calls:
  - ACL 2026: https://2026.aclweb.org/calls/system_demonstration/
  - EMNLP 2026: https://2026.emnlp.org/calls/demos/
  - EACL 2027: https://2027.eacl.org/calls/demos/
  - NAACL 2027: https://2027.naacl.org/calls/system_demonstration/
  - ACL 2027: https://2027.aclweb.org/calls/system_demonstration/
  - ACL 2025: https://2025.aclweb.org/calls/system_demonstration/
  - ACL 2023 demo chairs report: https://www.aclweb.org/adminwiki/index.php/2023Q3_Reports:_Demo_Chairs
- Demos:
  - CARE: https://aclanthology.org/2023.acl-demo.28/
  - PaperMentor: https://aclanthology.org/2026.acl-demo.39/
  - OpenReviewer: https://aclanthology.org/2025.naacl-demo.44/
  - GraphMind: https://aclanthology.org/2025.emnlp-demos.21/
  - Ai2 Scholar QA: https://aclanthology.org/2025.acl-demo.49/
  - SciTrue: https://aclanthology.org/2026.eacl-demo.27/
  - TruthReader: https://aclanthology.org/2024.emnlp-demo.10/

**Not found or only partly verified**
- **Not found:**
  - "Reactant" (not found after several searches).
  - A paper or UI details for Critical Inker (only a project-page description, and that fetch failed).
  - The exact name of ARR's AI-disclosure field.
- **Weaker sources than the rest:**
  - alphaXiv's "AI Chat on Paper" changelog entry returned 404; its chat UI details are third-party only.
  - The ICLR 2026 field list and scales come from secondary sources (see 3.2).
  - Claude's August 2025 learning-mode rollout: press coverage only.
  - The phrase "point-of-decision provenance" exists only as "provenance cues at the point of decision" in arXiv 2601.10236.
- **Partly verified:**
  - Peerispect's SIGIR '26 demo-track placement: the paper says SIGIR '26, but I found no official track listing. Its exact UI colors appear only in a figure.
  - REVAS's heuristic count: the site says 13, while ARR's post lists 10 of 17.
- **Mismatches with the brief:**
  - XtraGPT is ACL 2026 main track, not a demo.
  - "Paper Copilot" at EMNLP 2024 is actually titled "Arxiv Copilot."
  - ReviewFlow has no cross-section or cross-paper summaries.