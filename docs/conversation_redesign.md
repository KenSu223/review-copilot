# Conversation Redesign: Evidence-Led, Preference-Driven Dialogue

> Date: 2026-10-28 · Status: **implemented (phases A–H), see §11**
> Source: advisor meeting notes (2026-10) and the team discussion that followed.
> Supersedes the conversation flow in `product_plan.md` §2.3–2.8: the fixed order of ARR dimensions, commit-first openers, and auto-advance.
> Still in force: the judgment firewall (`product_plan.md` §2.2) and the non-leading question rules (§2.9).

## 0. Summary

Two principles drive the redesign.

1. **Low friction, low stakes.** Assume the reviewer is unmotivated and leans on AI. If the copilot asks them to produce something from nothing, the effort is about the same as reading the paper and writing the review alone, so they will not use it, or they will cheat. The copilot therefore leads with evidence at every step:
   - it finds the relevant passages;
   - it highlights them in the PDF and scrolls there;
   - it asks one light question about them.

   The conversation should feel like chatting about a paper, not like filling in an ARR form. Turning the chat into formal review text happens at the end.
2. **Faithful to the reviewer's own taste.** Reviewers differ in what they think makes a good paper. Onboarding collects that, and the copilot chooses which evidence to show and what to ask from it.

Division of labor:

| The copilot does (objective, tedious) | The reviewer does (requires a human) |
|---|---|
| Read the paper, find and locate evidence, check the reviewer's factual statements, track what the review still needs, turn casual remarks into review prose | Form and state opinions, decide when a topic is done, confirm what gets recorded, set scores |

## 1. Advisor notes, synthesized

| Note | Where it lands |
|---|---|
| "The authors experimented with these 5 models, what do you think about it?" | The standard turn shape: present, then ask (§5.1) |
| If the reviewer does not want to look for evidence, the model presents it | Evidence cards with automatic highlighting and scrolling (§5.1) |
| "What makes a strong paper to you? Clarity? Where do you look for clarity? Can I quote you on that?" | Onboarding questions (§4), just-in-time preference questions, and capture pills (§5.3) |
| Make the conversation low stakes; organize what they need to look at first | Preference-driven agenda (§5.2), casual register (§5.3) |
| A bar in the opinions feature: how faithful vs. professional | Faithful-to-professional slider (§6) |
| Do not ask "is this sufficient"; ask how they value something, where they look for it, and help them locate it | Question style (§5.3), "where to look" defaults (§4.4) |
| Reviewers write a better version with the platform; different people write different reviews, each faithful to their own opinions | Evaluation goals (§9) |
| Reviewers decide when they are done with a section | No auto-advance (§5.5) |
| Different help for different expertise | Reviewer levels (§4.1) and level-adaptive presentation (§5.6) |
| How to keep someone from fatiguing, so they stay themselves and still review well | Fatigue measures (§5.7) |
| One-time personal preference information at onboarding | Reviewer profile (§4) |

## 2. Current behavior (as of 2026-10-27)

| Aspect | Current behavior |
|---|---|
| Opening | The first message is the Summary opener: *"Before I show anything from the paper: in 2–3 sentences, how would you describe what this paper claims to contribute?"* (`dialogue/dimensions.py`) |
| Order | Fixed sequence of 8 ARR dimensions: Summary → Soundness → Strengths → Weaknesses → Excitement → Reproducibility → Limitations & ethics → Overall |
| Facts | Every dimension opens with `commit_open`, whose instruction says "Do NOT show any paper facts yet". Paper facts appear (`surface_facts`, up to 3) only after the reviewer states a view |
| Pacing | A dimension auto-advances after at most 5 turns (`MAX_TURNS_PER_DIM`) or after one confirmation |
| PDF | Evidence is highlighted and scrolled to only when the reviewer clicks a citation chip |
| Next question | Chosen by `decide()`, a deterministic rule table in code. The LLM only phrases the move that code picked |

The commit-first design was deliberate. It avoided anchoring and collected a blind prior for measuring judgment leakage. But it asks for an opinion before giving anything to react to, at every dimension, which is exactly the friction the advisor flagged.

LLM calls per turn today:

| Call | Model | Purpose | When |
|---|---|---|---|
| Analyze | Sonnet 5 (structured) | Classify the reviewer's message; extract opinion units and factual claims | Every typed reviewer message (skipped for chip clicks and dimension starts) |
| Statement check | Opus 5.5 (citations) | Check a factual claim against the paper | 0–2 per turn, only when the reviewer made a factual claim |
| Realize | Opus 5.5 (citations) | Write the copilot's message for the move code chose | Every turn |
| Guard | GLM-5 | Audit the draft against the firewall rules | Every turn; one revision allowed (adds Realize + Guard) |

A typical turn is therefore 3 calls, but the range is 2–7. The calls do not decide where the conversation goes; `decide()` does.

## 3. Decisions (2026-10-28)

1. **Organization.** The conversation is organized by the reviewer's own criteria. ARR fields live in the background and appear only in the draft.
2. **Reviewer levels.** At entry the reviewer picks a level, from beginner to AC (L0–L3). Each level gets its own onboarding questions.
3. **Per-paper questions.** For each paper the copilot asks about area familiarity, whether the reviewer has read the paper, and the time budget. Familiarity sets how much background to give.
4. **Preference-chosen opening.** What the copilot presents first is chosen from the reviewer's preferences. There is no fixed abstract/intro/contributions opener.
5. **Dynamic next step.** An LLM conversation agent decides the next step dynamically. Code only enforces hard boundaries.
6. **No commit-first.** It is replaced by an optional *first impression*: off by default, on in study mode, and a natural entry point in quick mode.
7. **Faithful-to-professional slider.** Confirmed as the meaning of the advisor's "bar".
8. **Confirmed paper facts.** Paper facts the reviewer explicitly confirms may enter the review. They are marked as confirmed paper facts and disclosed.
9. **Background scope.** Background for beginners stays paper-internal in v1. Any external explanation would be a separate, labeled feature and is out of scope for now.
10. **No AC meta-review mode in this round.** ACs use the tool as senior reviewers.

## 4. Onboarding

### 4.1 Reviewer levels (first screen, self-reported, editable)

| Level | Description shown to the user |
|---|---|
| L0 Beginner | This is one of my first reviews |
| L1 Some experience | I've reviewed a few papers |
| L2 Experienced | I review regularly for major venues |
| L3 AC / senior | I've served as an area chair or senior reviewer |

### 4.2 Level-specific questions (one-time, stored in the profile)

**L0 Beginner.** Do not ask about taste: most beginners cannot answer "what makes a strong paper", and being asked makes the task feel high-stakes.
1. *What would help you most?* [Understand the paper first] [Know what a review asks for] [Put my thoughts into words]
2. **Starter lens.** In plain language, list what the ARR review form asks about: whether the claims are supported, whether the paper is clear, whether it is reproducible, whether limitations are discussed, and so on. Then ask *"Which would you feel comfortable starting with?"* These aspects come from the venue's form, not from the LLM's taste.
3. **Taste emerges during the conversation.** After the reviewer has reacted to a few cards, the copilot may ask: *"You've commented on how clearly things are explained a few times. Want me to remember that as something you look at?"* If the reviewer confirms, it is added to the profile.

**L1 Some experience.**
1. *When you read a paper, what do you usually pay attention to?* Up to 3 criteria (§4.4).
2. For each one, *where do you usually look?* Pre-filled with the defaults in §4.4 and editable.
3. *How should I help?* [Guide me step by step] [Show me evidence, I'll react]

**L2 Experienced.**
1. *What makes a paper strong to you?* Rank up to 3 criteria.
2. For each one, *where do you look?* Pre-filled and editable.
3. Optional: *anything that is usually a deal-breaker for you?*
4. Mode: [Show me evidence, I'll react] [Quick mode]

**L3 AC / senior.**
1. *In a line or two, what do you weigh most when judging a paper?* Free text or chips.
2. Quick mode by default.

If the reviewer skips onboarding at any level, preferences are asked just in time, the first time a topic comes up.

### 4.3 Per-paper questions (all levels)

1. *How familiar are you with this paper's area?* [New to it] [Know the basics] [Work nearby] [Work in this area]
2. *Have you read the paper yet?* [Not yet] [Skimmed] [Read it]. L2 and L3 reviewers who have read it start in quick mode.
3. *Time budget:* [15] [30] [60] minutes. This sets the number of cards.

Familiarity sets the amount of background:

| Familiarity | Background (paper-internal only in v1) |
|---|---|
| New to it | A background card before anything else: the paper's own preliminaries and problem setup, highlighted. Key terms are defined from the paper's own text. Hovering over a term shows its definition |
| Know the basics | Term definitions on hover |
| Work nearby | Pointers to how the authors position the work in their related-work section |
| Work in this area | None |

### 4.4 Criteria and default "where to look"

These are defaults for the reviewer to edit. The agenda planner (§5.2) maps them onto actual sentences in each paper.

| Criterion | Default places to look |
|---|---|
| Clear story and writing | Abstract, problem statement, contribution statements, method overview, Figure 1, notation and definitions |
| Rigorous experiments | Main results tables, baselines, metrics, seeds / variance / significance, experimental setup |
| New idea | The paper's own novelty claims, contrasts drawn in related work |
| Practical usefulness | Motivation, application settings, efficiency or cost results |
| Theory | Assumptions, theorem statements, proofs (often in the appendix) |
| Analysis and ablations | Ablation sections, error analysis, qualitative examples |
| Reproducibility | Code and data availability, hyperparameters, compute, appendix details |
| Honest limitations | Limitations section, failure cases, ethics statement |

### 4.5 Profile storage

- **`ReviewerProfile`** holds:
  - the level;
  - the ranked criteria, each with its "where to look" locations;
  - optional deal-breakers;
  - the help style;
  - criteria learned just in time;
  - a timestamp.
- **Snapshot.** Each review session stores a snapshot of the profile it used, in the trace.
- **The profile never enters the review text.** It only decides what the copilot shows and asks.

## 5. The conversation

### 5.1 Evidence cards

The basic unit of the conversation is an **evidence card**, not an ARR dimension. A card has:
- **Evidence.** 1–3 highlighted passages, plus 1–2 sentences of objective description, each with a citation.
- **A question.** One light, open question about the passages.
- **Automatic PDF behavior.** When the card appears, the PDF highlights its passages and scrolls to the first one. A small "1/3" navigator moves between them, so the reviewer never has to search the PDF.
- **A "why you're seeing this" tag**, e.g. *Because you said clarity matters to you*. This is for transparency, and it makes the source of the selection visible.
- **A reading-time estimate**, e.g. "~1 min read".

The turn shape is always *present, then ask*. For example: *"They compare 5 models on 3 tasks [cite]. What do you make of this?"*

### 5.2 Preference-driven agenda

- **Selection is driven by the profile.** At session start, an **agenda planner** reads the whole paper together with the reviewer's profile and per-paper answers. It selects sentences from anywhere in the paper that bear on each of the reviewer's criteria, a sentence here and a sentence there, and groups them into cards. Cards are ordered by the reviewer's ranking.
- **No fixed opener.** The first card belongs to the reviewer's top criterion. Two reviewers of the same paper get different openings.
- **The orientation card is optional.** Showing what the paper says it contributes is just one card type. It is used only when preferences call for it: an L0 reviewer who chose "understand the paper first", a reviewer new to the area, or one who has not read the paper.
- **Summary comes later.** The ARR Summary field is covered later through the monitor (§5.4). It is often easiest at the end, once the reviewer has seen the paper: *"Here's what the authors say they contribute [cites]. How would you put it?"*
- **The agenda is a plan, not a script.** The conversation agent revises it as the conversation goes.

Illustration (not a real paper):

| | Reviewer A (clarity first) | Reviewer B (rigor first) |
|---|---|---|
| First card | The method-overview sentence, the Figure 1 caption, and the sentence that defines the key notation | The headline result as stated in the abstract, the main results table caption, and the sentence that describes seeds or variance |
| First question | "How did this read to you?" | "What do you make of this table?" |

Selection rules, enforced by code and audited by the Guard:
- Every selected block id must exist.
- For each criterion, a card shows what the paper provides. Where the criterion calls for it, the card also shows what could not be located, naming the sections checked.
- The planner records why each block was selected, and the reason goes into the trace.
- Selection must depend on relevance to the reviewer's criteria, never on whether the evidence makes the paper look good or bad.

### 5.3 Casual register

- **No ARR vocabulary in the chat.** Topics are named by the paper's content ("this table", "how they explain the method"), never as "Soundness" or "Weaknesses".
- **Prompt rewrite.** Messages are conversational and short, with at most about 60 words of the copilot's own prose besides quoted evidence. The non-leading rules still hold. The current "what, if anything..." phrasing sounds formal and should become natural questions that still presuppose nothing:
  - *"What do you make of this?"*
  - *"How did this read to you?"*
  - *"Anything here you liked, or that bugs you?"* (both sides asked together)

  The Guard prompt is updated to accept casual wording. Rules R1–R7 are unchanged.
- **Low-effort reactions.** Chips: [Looks good] [Mixed] [Something's off] [Not sure] [Show me more] [Skip]. A chip click gets a light follow-up: *"Any reason? One line is fine."*
- **Capture pills ("Can I quote you on that?").** When the reviewer voices a view casually, an inline pill appears: *Noted: "pretty clear, the derivation is neat" → Clarity (+)* [Edit] [Don't record]. This replaces the formal confirm turn at the end of each dimension. It can be undone with one click, and it is the reviewer's confirmation point for provenance.

### 5.4 Agents, and who decides what

| Role | What it does | When it runs | Initial model |
|---|---|---|---|
| **Monitor** | Extracts opinion units and factual claims from the reviewer's message. Updates the coverage map of ARR fields (covered / partial / missing). Reports which fields are missing and whether there is enough for a full review | Every reviewer message | Sonnet 5 (structured) |
| **Conversation agent** | Decides the next step and writes the message | Every turn | Opus 5.5 |
| **Evidence finder / statement checker** | Tools the conversation agent uses to locate evidence for a point or to check a reviewer's factual claim, with citations | Only when needed | Opus 5.5 (citations) |
| **Guard** | Audits every outgoing message (wording and evidence selection) before the reviewer sees it | Every outgoing message | GLM-5 |
| **Agenda planner** | Builds the initial agenda from the profile and the paper (§5.2) | Session start, and whenever the reviewer changes preferences | Opus 5.5 |

The conversation agent chooses the next step **dynamically**, from:
- following up on what the reviewer just said;
- presenting a card, from the agenda or from newly found evidence;
- answering a factual question;
- reporting a statement check;
- bridging to a missing field;
- reconciling two of the reviewer's statements;
- declining a verdict request and redirecting;
- offering to wrap up a topic;
- offering to open the draft.

Bridges are symmetric. When no weakness has been recorded, the copilot might say: *"Earlier you said the method section was easy to follow (T3). Was there anything you'd want the authors to change, or that gave you pause?"* When no strength has been recorded, it asks the mirror question.

**The LLM decides what to do next; code decides what is never allowed.** Code enforces:
- **Allowed actions only.** `GIVE_SCORE`, `GENERATE_OPINION` and `RECOMMEND_ACCEPT/REJECT` do not exist.
- **The Guard on every message.** Every outgoing message passes the Guard, with one revision and then a safe fallback.
- **Real citations.** Every citation must point to an existing block.
- **Field gaps, never content.** The monitor may say *which field* is missing, never *what content* to add ("no weakness recorded yet" is allowed; "they should criticize the baselines" is not).
- **Symmetry counters.** Bridges toward strengths and toward weaknesses are counted, and so are presence facts and absence facts.
- **No pestering.** After a skip, the same point is not raised again, and repeated probes are capped.
- **Reviewer-controlled endings.** A topic ends only when the reviewer says so.
- **Full logging.** Every decision and its stated rationale is logged in the trace.

**The number of calls varies by turn:**

| Situation | Calls |
|---|---|
| Reviewer clicks a reaction chip; agent follows up | agent + Guard |
| Reviewer states an opinion; agent follows up | monitor + agent + Guard |
| ...and the message includes a factual claim | monitor + statement check(s) + agent + Guard |
| Agent decides to present newly found evidence | monitor + evidence finder + agent + Guard |
| Guard asks for a revision | one more agent call and one more Guard call |

Implementation note: on the Claude API, citations and structured outputs cannot be combined in one request. A step that must both decide and write cited text is therefore either split in two, or emits its decision as a tagged first line, the way the statement checker already emits `VERDICT:`.

Latency:
- Status updates stream while the steps run.
- The next agenda card is pre-generated while the reviewer reads the current one.

### 5.5 The reviewer decides when a topic ends

- **No auto-advance.** When the monitor sees a topic as covered, the agent may *offer* *"Move on, or stay on this?"* The reviewer chooses [Done with this] or [Keep going].
- **Agenda rail.** It replaces the top DimensionRail. It lists upcoming cards, which the reviewer can reorder, skip, or mark done, next to a small coverage meter for the ARR fields.
- **"Ready to draft" is always available.** Missing fields are flagged as *not addressed* in the draft and never filled in for the reviewer.

### 5.6 Level-adaptive presentation

| | L0 Beginner | L1 Some experience | L2 Experienced | L3 AC / senior |
|---|---|---|---|---|
| Who leads | Copilot, step by step | Copilot; reviewer can skip | Shared | Reviewer |
| Orientation card | Always | If chosen or not yet read | If not yet read | No |
| Evidence per card | 2–3 passages + one plain-language line of context | 1–3 passages | 1–2 passages, terse | On request |
| Agenda source | Starter lens + ARR gaps | Attention criteria + ARR gaps | Ranked taste + ARR gaps | Free-text first, then gaps |
| Review-field explanations | When a field first comes up, citing the ARR reviewer guidelines | On request | No | No |
| Structure prompts ("what / where / why it matters"; structure only, never content) | Yes | Yes | No | No |

**Quick mode** (default for L3, optional for L2):
1. The reviewer first writes freely in a "dump your thoughts" box.
2. The copilot splits the text into opinion units, each shown as a capture pill.
3. Factual statements in it are checked against the paper.
4. The monitor reports the missing fields.
5. Evidence cards are shown only for those gaps.

### 5.7 Fatigue

- **Budgeted length.** The time budget sets the number of cards, and progress is shown: *"~5 cards left, about 8 min"*.
- **Light answers.** One-line answers are always enough, and no question is asked twice.
- **Pause and resume** at any time.
- **Visible progress.** A live "Your review so far: N points" panel shows the review taking shape.

### 5.8 Optional first impression

Commit-first is gone. In its place, once per paper, the copilot can ask before showing anything: *"Any first impression of this paper? One line is fine, or skip."*

- **Normal use: off.** It adds friction.
- **Study mode: on.** It provides the blind prior needed to measure judgment leakage (CLAUDE.md §7).
- **Quick mode: on as the natural entry point.** Reviewers who have already read the paper start by writing down their thoughts.

## 6. Synthesis

- **Faithful-to-professional slider** in My opinions and in the Draft, with three settings:
  - **Your words:** verbatim; only typos are fixed.
  - **Polished:** grammar and review register; same claims, same intensity.
  - **Formal:** ARR style.

  It can be set globally or per sentence. Every rewrite goes through the existing entailment / polarity / intensity drift check, and drift is flagged.
- **Confirmed paper facts.** A paper fact enters the review only after an explicit confirmation action, never from silence or a bare "ok". It gets its own provenance type, *paper fact, confirmed by reviewer at T#*. The export's AI-use disclosure states that the review includes paper-stated content located by the tool and confirmed by the reviewer.
- **Unchanged:**
  - synthesis uses only opinion units and confirmed facts;
  - every sentence has provenance;
  - sentences are accepted, edited, or rejected one by one;
  - only the reviewer sets scores.
- **Confidence score.** It is never pre-filled. The reviewer's own familiarity answer (§4.3) is shown next to it as a reminder.

## 7. Firewall risks and mitigations

| Risk | Mitigation |
|---|---|
| Leading with evidence brings anchoring back | Selection depends on the profile and the coverage needs, never on the LLM's view of the paper. Each card states why it is shown, and every selection is logged. Study mode collects a first impression for measuring leakage |
| Absence facts are the strongest influence channel (persona-suite finding) | Absence facts appear only for criteria the reviewer chose, always next to presence facts, as a neutral checklist |
| A dynamic planner steers toward criticism or praise | Symmetry counters in code. The Guard audits selection as well as wording, with a new rule: *steering toward a specific critique or praise*. Persona-suite regression before and after the change |
| The monitor's gap reports become content suggestions | The monitor reports fields, not content. Bridges are symmetric |
| A casual tone loosens the Guard | Prompts and the Guard are changed together and checked with the persona suite |
| Beginners are the most suggestible and see the most evidence | L0 agendas come from the ARR form's starter lens, not from LLM choices. Strict presence/absence symmetry. A new "suggestible beginner" persona |
| A lazy reviewer clicks [Looks good] throughout and the review is thin | This is correct behavior: the review reflects only what the reviewer said, and thin fields are flagged. The system lowers friction; it does not manufacture opinions |

## 8. Implementation phases

| Phase | Content | Main files |
|---|---|---|
| A. Profile and onboarding | `ReviewerProfile` table and API; level screen and level-specific questions; per-paper questions; profile snapshot per session | `db.py`, `main.py`, new `Onboarding.tsx` |
| B. Agenda planner | Criteria and default locations (§4.4); session-start planner over the paper and the profile; block-id validation; selection rationale in the trace | new `dialogue/criteria.py` (replaces `dimensions.py` as the conversation structure; ARR fields kept for synthesis), new `dialogue/agenda.py` |
| C. Evidence cards in the UI | A `focus` payload on messages; automatic highlight and scroll; "1/3" navigator; "why you're seeing this" tag | `Workspace.tsx`, `PdfPane.tsx`, `ChatPanel.tsx` |
| D. Conversation agent and monitor | Monitor (extraction plus coverage); a dynamic agent that chooses among the allowed steps; code boundaries (§5.4); no auto-advance; Agenda rail | `dialogue/engine.py`, `dialogue/prompts.py`, `DimensionRail.tsx` → `AgendaRail.tsx` |
| E. Casual register | Rewrite `FIREWALL_RULES`, the move instructions, and the Guard; reaction chips; capture pills | `prompts.py`, `ChatPanel.tsx`, `LedgerPanel.tsx` |
| F. Synthesis | Mapping casual remarks to ARR fields; three-level slider with drift checks; confirmed-fact provenance; disclosure text | `dialogue/review.py`, `DraftPanel.tsx`, `LedgerPanel.tsx` |
| G. Level adaptation and fatigue | The presentation table in §5.6; quick mode; time budget and progress; optional first impression and study mode | `engine.py`, frontend |
| H. Evaluation | New personas, A/B comparison, latency (§9) | `evals/` |

- **Order.** A and B come first; C and D are the core; E follows directly.
- **Deadline.** The NAACL 2027 demo deadline is 2026-12-04, so the target is to have A–E running end to end first. F and G depend on the remaining time. H starts as soon as D works.

## 9. Evaluation changes

- **New personas:**
  - *lazy*: one-line answers, wants to finish quickly;
  - *casual talker*;
  - *suggestible beginner*;
  - a set of personas with the same hidden opinions but different taste profiles.
- **Friction metrics:**
  - characters typed by the reviewer;
  - turns and time to finish;
  - drop-off rate.
- **Diversity with fidelity.** Reviewers with different profiles who review the same paper should produce different reviews (self-BLEU across reviewers), while each review stays faithful to its own hidden opinions (precision and recall). This is the advisor's "different people write different reviews, each faithful to their own opinions".
- **A/B comparison.** Commit-first (the current version) against evidence-first (this design), comparing:
  - leakage: the rate of `adopted_copilot_framing`;
  - friction.

  This trade-off is itself a reportable result.
- **User study.** Compare the two flows within subjects, or add the new flow as a condition. Study mode collects the first impression.

## 10. Still open

- **Onboarding wording.** The questions above are drafts. Pilot them with 2–3 people per level.
- **Criteria.** The criteria list and the default "where to look" locations need review.
- **Latency.** A per-turn latency budget, and whether the monitor can run in parallel with the agent's first step.
- **Persona gates.** Whether the persona-suite gate thresholds need adjusting for the casual register.

## 11. Implementation status (2026-10-28)

All phases are implemented. Code is in `app/`; the developer map is in `app/README.md`.

| Phase | What was built | Where |
|---|---|---|
| A. Profile and onboarding | `ReviewerProfile` table and `GET/PUT /api/profile`; level-first onboarding with the questions of §4.2 per level, editable later; study-mode toggle; per-paper questions (§4.3) before each new session; the profile snapshot and per-paper answers are stored in the session and logged (`session_start`) | `db.py`, `main.py`, `criteria.py`, `onboarding/Onboarding.tsx`, `workspace/PaperSetup.tsx` |
| B. Agenda planner | One structured call per session (in the background) over the whole paper + profile + per-paper answers; cards per criterion spread by rank and time budget; passages capped by level; block ids validated; absence items only on the reviewer's criteria; reserve cards for the other fields (no absence items); orientation / background / positioning cards and a paper-internal glossary when the answers call for them; the plan and every card's reason are logged (`agenda` event) | `dialogue/agenda.py` |
| C. Evidence cards in the UI | Messages carry a `focus` (block ids, topic, why, reading time); the PDF highlights and scrolls automatically; a navigator steps through the passages; the evidence tag reopens them | `workspace/Workspace.tsx`, `ChatPanel.tsx` |
| D. Agent and monitor | Monitor = one structured extraction call on typed messages (chip clicks skip it) + coverage computed in code; `allowed_actions()` enforces the boundaries of §5.4; the agent chooses one allowed step and writes it in one cited call (first line `ACTION: …`, validated before the Guard); Guard R1–R8 with one revision and fallback templates; no auto-advance; the topic rail replaces the dimension rail; prefetch of the step after *Done with this* | `dialogue/monitor.py`, `engine.py`, `prompts.py`, `workspace/AgendaRail.tsx` |
| E. Casual register | Casual firewall prompt (one question, never two joined by "and"; no telling the reviewer what to check; no form vocabulary in the chat); reaction chips; "Noted" capture pills with edit / undo | `prompts.py`, `ChatPanel.tsx` |
| F. Synthesis | Every draft sentence in three registers (words / polished / formal) with a drift check per register; global and per-sentence slider; the same slider in *My opinions* (rephrase on demand, cached, drift-checked); confirmed paper facts as `P#` units with their own provenance and a disclosure sentence; the Confidence score shows the reviewer's familiarity answer as a reminder | `dialogue/review.py`, `review/DraftPanel.tsx`, `workspace/LedgerPanel.tsx` |
| G. Levels and fatigue | Level rules in the agent context (§5.6); first-time reviewers get form-field notes when a field is first bridged to; quick mode for L3, or for L2/L3 who have read the paper; budget-driven card count and progress; first impression in study mode; "remember this criterion?" after two comments on an unlisted criterion | `engine.py`, `criteria.py`, frontend |
| H. Evaluation | Persona suite runs on both flows (`--flows evidence,commit_first`); new personas (lazy, casual, suggestible beginner, a taste group sharing hidden opinions); friction metrics; self-BLEU diversity of the taste group's drafts; A/B table. The previous engine is kept as `legacy.py` for this comparison | `app/backend/evals/`, `eval/persona_runs/` |

Implementation notes and deviations from the text above:
- **Evidence finder.** §5.4 lists an evidence finder as a separate tool. In the build, the conversation agent reads the whole paper as a cited document, so locating new evidence happens inside its own cited call; the statement checker remains a separate call. Calls per turn: chip click → agent + Guard; typed message → monitor + agent + Guard; + statement checks when the reviewer states facts; + one agent and one Guard call on a revision.
- **Agenda revision.** The agent revises the plan by choosing among the next three planned cards, presenting new evidence on the open topic, and bridging with reserve cards; the reviewer reorders, skips, or jumps from the rail.
- **Bridges.** Each review field is bridged to at most once (no pestering), and code picks the target field; the agent decides whether to bridge at all.
- **Opening.** The first card shown always follows the plan order (orientation / background first when called for, otherwise the top criterion), also after a first impression.
- **Profiles in evals.** Sessions with an explicit profile (the persona suite) never write learned criteria back to the saved profile, and persona-suite sessions are hidden from the app.
- **Earlier sessions.** Sessions from the previous version keep working on the legacy engine; the setup screen offers to reopen them.

### 11.1 Independent plan audit and fixes (2026-10-28)

After the first build, a separate agent audited the code against §0–§10 without seeing §11. It reported 17 gaps and
5 likely runtime bugs, and all were fixed:
- **Firewall coverage.** Statement-check text now passes the Guard too, keeping only quoted evidence if it fails. A
  Guard failure is retried once and then falls back to a template; nothing is sent unaudited. The Guard now sees the
  card's passages, the planner's reason, and its not-found items. A Guard pass over the agenda neutralizes evaluative
  titles and drops one-sided or speculative absence items.
- **Confirmed facts only (§6).** Synthesis no longer uses statement-check evidence on its own. Check cards have a
  "Use this evidence in my review" control that creates a confirmed `P#` fact.
- **Absences (§7).** Absence items appear only for criteria the reviewer chose, and never outnumber the facts shown.
- **Re-planning (§5.4).** A criterion the reviewer states or agrees to remember mid-session adds planned cards for it.
- **Answers that now change behavior (§4.2, §5.6).**
  - L0 "what would help most": *understand* adds background and a glossary; *form* adds form notes when a card first
    touches a review part; *words* asks for the missing what / where / why.
  - L1 *guided* vs *evidence* help styles now differ, and L1 has an orientation option.
  - Form questions ("what goes under soundness?") are answered on request from the form descriptions; who leads
    differs by level.
- **Reviewer control and fatigue.** Cards carry *Done with this*, and the rail can end the current topic. A reaction
  no longer forces a follow-up. The agent may pick any of the next six planned cards. Each topic has a turn budget,
  after which only "move on?" remains (*Keep going* resets it). Declined remember-offers are not repeated.
- **Audit trail.** The agent states a short reason for each step (`WHY:`); it is logged and never shown.
- **Small items.**
  - Every card has at most 3 passages.
  - The summary card always exists.
  - Unaddressed fields appear as "not addressed" in the draft.
  - Pills use plain names, not ARR names.
  - Glossary terms also work inside cited spans.
- **Runtime bugs fixed.**
  - Planning interrupted by a restart is restarted.
  - Clicks never count as a first impression.
  - Prefetched steps carry a fingerprint, and agenda edits invalidate them.
  - The paper's contributions load lazily if the map was late.
  - The "show more" fallback no longer claims to show passages.

The first full persona run (before these fixes) is kept in `eval/persona_runs/iterations/20261028-202611-pre-audit/`.

### 11.2 Evaluation round (2026-10-28)

Results and the full iteration log are in `eval/persona_runs/SUMMARY.md`. In short:
- **Gates.** With the final code, all gates G1–G7 pass on both test papers: DPO, and the ICML'26 position paper with an injected hidden prompt.
- **A/B on DPO.** Compared with the commit-first flow, reviewers typed about a third less, and the taste group's drafts overlapped about half as much (self-BLEU 0.084 vs 0.165). Recall was unchanged (0.93). The costs:
  - lower strict precision (0.76 vs 0.83), mostly fact-informed opinions about the passages shown;
  - more adoption of the paper's own rhetoric (10 vs 2 units).
- **Prompt and routing changes from the runs.**
  - No rebuttal connectives when reporting facts (the planting channel).
  - Quote and attribute the paper's own evaluative wording.
  - Do not repeat the card's reason in the message.
  - Requests to produce evaluative content ("list the weaknesses") route to decline-and-redirect.
  - The Guard sees the text of every cited sentence.
- **Open questions for the human study.** How much of the extra fact-informed opinion and paper-framing adoption appears with real reviewers, and whether topics outside the profile need an earlier, symmetric bridge.
