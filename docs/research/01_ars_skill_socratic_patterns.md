<!-- Research agent report, generated 2026-10-21 for the Academic Review Copilot product plan. Verify items before citing. -->

# Socratic Patterns in academic-research-skills (ARS), Mapped to Academic Review Copilot

I read every file you listed in full (all 764 lines of the deep-research mentor), plus the most relevant files a repo-wide grep turned up. All paths below are relative to `/Users/kensu/academic-research-skills/`. I did not modify any file.

**Primary files**
- `deep-research/agents/socratic_mentor_agent.md`
- `deep-research/references/socratic_mode_protocol.md`
- `deep-research/references/socratic_questioning_framework.md`
- `deep-research/SKILL.md` (Socratic parts)
- `deep-research/examples/socratic_guided_research.md`
- `deep-research/references/failure_paths.md`
- `academic-paper/agents/socratic_mentor_agent.md`
- `academic-paper/references/plan_mode_protocol.md`
- `academic-paper/references/anti_leakage_protocol.md`
- `academic-paper/examples/plan_mode_guided_writing.md`
- `academic-paper-reviewer/references/guided_mode_protocol.md`
- `academic-pipeline/agents/collaboration_depth_agent.md`
- `README.md`, `POSITIONING.md`

**Additional files the grep surfaced**
- `shared/collaboration_depth_rubric.md`
- `docs/design/2026-06-08-kong-255-l2-advisory-not-generation.md` (the "verb test")
- `docs/design/2026-06-08-kong-255-l1-copilot-not-auto-research.md`
- `docs/design/2026-06-18-socratic-adjacent-framing-probe-spec.md`
- `docs/design/2026-04-22-ars-v3.7.3-reading-check-probe-design.md`
- `docs/design/2026-06-08-274-concise-pressure-guidance-design.md`
- `docs/design/2026-08-13-659-within-session-ideation-diversity-design.md`
- `evals/heldout/within_session_ideation_diversity/codebook.md`
- `academic-paper-reviewer/SKILL.md` (Phase 2.5 coaching, guided mode)
- `academic-paper-reviewer/agents/devils_advocate_reviewer_agent.md` (anti-sycophancy)
- `academic-paper-reviewer/references/re_review_mode_protocol.md` (residual coaching)
- `academic-paper-reviewer/templates/peer_review_report_template.md` (typed evidence anchors)
- `deep-research/agents/research_question_agent.md` (Socratic branch)
- `deep-research/references/argumentation_reasoning_framework.md`
- `academic-pipeline/references/process_summary_protocol.md`

### TL;DR
- **Closest fit: the "verb test".** ARS's boundary is that the system "must not propose, substitute, rank, expand, or select." That is the best existing prior art for our judgment firewall. It is narrower than ours, though: it covers research questions, not evaluative judgments. It also has a visible "exit" that lets the AI generate candidates when the user asks explicitly. **We should borrow the verb test, add verbs such as rate, endorse and dispute, and offer no exit for subjective content.**
- **Pattern to copy directly: the adjacent-framing probe.** It names one directionless facet, asks "include or consciously set aside?", asserts only verifiable things, pushes once and then retreats, has a hard cap, and logs outcomes. It maps almost one-to-one onto our "D is cited but not compared — does that matter to you?" move and onto review-dimension coverage probes.
- **The ARS mentor itself breaks our firewall, by design and in its examples.** It praises ("Excellent"), injects critiques from a devil's-advocate agent, cites counter-research from memory, proposes designs and writes paragraphs. Its INSIGHT tags record mentor-authored ideas as user insights after the user merely says "yes". These are the anti-patterns to design against. Specific line numbers are in §1.11.
- **Depth measurement exists only in pieces.** There are INSIGHT validity criteria and pace thresholds, five convergence signals, a three-part self-check run every five turns, a post-hoc collaboration-depth rubric, and a frozen codebook (M1–M5) for labelling mentor violations. The codebook's definition of "independent expression" (bare assent, repeating the mentor, or picking from a mentor menu does not count) is exactly the rule we need for attributing opinions to the reviewer.
- **Big gap: enforcement is prompt-only.** ARS admits that prompt instructions "cannot prove the model stays pressure-stable at runtime." We need code-level enforcement (a firewall classifier, span verification, entailment checks for provenance). We also need a policy for which facts get surfaced, because choosing what to show is itself a soft judgment.

---

## 1. How the skill defines and runs Socratic dialogue

### 1.1 Definition and core principle
- **Deep-research Socratic mode.** The mentor persona is a "Q1 international journal editor-in-chief" whose tone is "warm but firm" (mentor L10–14). Its "IRON RULE" is: while non-generation Socratic mode is active, never give direct answers; lead with layered questions so users discover their own insights (protocol L5; SKILL L289).
- **Theory.** Socratic questioning is described as "not about imparting knowledge, but about helping the interlocutor discover blind spots, contradictions, and deep-seated assumptions in their own thinking" (framework L5). It cites Paul & Elder (2007), Overholser (1993) and Burbules (1993).
- **Authorship boundary (the load-bearing rule).** "Non-generation by default." The mentor may clarify, challenge and organize directions the user already expressed. It must never propose, substitute, rank, expand or select candidates. "Non-convergence, elapsed rounds, stagnation, or a vague request for help is never consent" (mentor L27–31). The only exception is an explicit user request. The mentor must then announce that it is leaving the mode, emit `[SOCRATIC-NON-GENERATION-EXIT: explicit_user_request]` on its own line, label the output as AI-generated, never tag it as INSIGHT, and never silently re-enter the mode (mentor L42–54).
- **The academic-paper mentor ("thesis advisor") is explicitly weaker.** Its principles include "Writing direction hints — when users have thought things through, provide 'here's how you could start...' guidance" (L22). In other words, it generates content.
- **The reviewer skill's "guided" mode inverts our roles.** There the AI is the reviewer and the human is the author. The AI originates critiques and reveals them progressively (guided_mode L7–22).

### 1.2 Stage and phase models, with exact names

**A. deep-research: 5-Layer Questioning Model** (mentor L198–302; protocol L28–78). Every layer requires at least 2 rounds, except Layer 5, which requires at least 1 (L563).

| Layer (exact name) | Goal | Core questions (examples) | Exit condition |
|---|---|---|---|
| **Layer 1: PROBLEM FRAMING** (Clarification) | Vague interest becomes a researchable question | "What question do you really want to answer?"; "Why is this question important? Important to whom?"; "What do you think the currently known answer is?" | User can state the question in one sentence; ≥2 rounds |
| **Layer 2: METHODOLOGY REFLECTION** (Probing Assumptions) | How to answer, and the underlying assumptions | "Is there a completely different method…?"; "What is the biggest weakness of your method?"; "If your data turns out opposite…can your method detect that?" | User explains the rationale and limitations of the method; devils_advocate_agent is called at the end of the layer |
| **Layer 3: EVIDENCE DESIGN** (Probing Evidence) | What evidence is needed and how to judge it | "What kind of evidence would convince you…?"; "What…would make you change your conclusion?"; "If two studies contradict…?" | User explains search strategy and quality criteria |
| **Layer 4: CRITICAL SELF-EXAMINATION** (Probing Implications) | Limitations, risks, harms | "What does your research assume?"; "How would someone with an opposing view argue?"; "If you were a reviewer, where would you find fault?" | User honestly lists ≥2 limitations; DA called |
| **Layer 5: SIGNIFICANCE & CONTRIBUTION** | "So what?" | "Who would make different decisions as a result?"; the template "Before my research, people thought... but my research shows..." | Contribution articulated; ≥1 round |

Notes on Layer 5 and naming:
- Layer 5 also defines single-sourced "later-stage anchored forms" (L296–299), reused by plan mode and reviewer Phase 2.5:
  - **L5-W1**: "Ten years from now, what will citers say this paper established?"
  - **L5-W2**: "Remove this paper from the literature — what is missing?"
  - **L5-W3**: "If this paper succeeds, who would make different decisions as a result?"
- SKILL.md L291 names the layers differently ("Clarification -> Assumption Probing -> Evidence/Reasoning -> Viewpoint/Perspective -> Implication/Consequence"). This is one of several internal inconsistencies (see §1.11).

**Overlays that run on top of the layers**

*Intent Detection Layer* (L102–153; internal, never mentioned to users)
- Classifies the user as exploratory or goal-oriented after the first 2 user messages and re-assesses every 5 turns.
- Exploratory mode turns off auto-convergence and never initiates "want me to summarize?". It raises the stagnation threshold to 15 and the maximum to 60 rounds, advances layers only on a user signal, and uses CHALLENGE questions 40%+ of the time.

*SCR (State–Challenge–Reflect)* (L157–196; framework L200–223)
- **Commitment Gate:** before each layer transition the mentor collects a prediction or judgment, tagged `[COMMITMENT: …]`.
- **Divergence Reveal:** introduces information that tests the commitment, presented as "interesting counterpoints."
- **Certainty-Triggered Contradiction:** fires on markers such as "definitely" or "clearly", at most twice per layer, and introduces opposing research.
- **Adaptive Intensity:** tracks how accurate commitments are and raises the challenge rate if the user overestimates novelty.
- The user can switch SCR off; it is never named to the user.

*Optional probes and checks*
- Wording-Pattern Advisory (L56–100).
- Reading Probe (L304–421; env-gated, goal-oriented, fires once).
- Adjacent-Framing Probe (L423–558; env-gated, exploratory, Layer 1 only).
- Dialogue Health Indicator (L729–751).

**B. academic-paper "plan" mode** (plan_mode_protocol L5–89; mentor L117–351)
- **Step 0: RESEARCH READINESS CHECK.** Three mandatory questions about materials, whether the RQ is finalized, and the literature search. An assessment table routes the user onward or refers them to deep-research Socratic mode.
- **Step 1: THESIS CRYSTALLIZATION.** Round 1 basic ("State it in one sentence"), Round 2 stress test, Round 3 refinement.
- **Step 2: CHAPTER-BY-CHAPTER NEGOTIATION.** For each chapter: explain its purpose, pose 5 mandatory questions (3 for the Conclusion), probe follow-ups, give writing direction hints, extract a Chapter Summary, then confirm.
- **Step 2.5: CONTRIBUTION SHARPENING.** Uses the L5-W forms, quotes only what the user wrote, and "never fill it in."
- **Step 3: ARGUMENT STRESS TEST.** The mentor challenges; argument_builder rates each sub-argument Strong, Moderate or Weak; the loop runs "until argument reaches Moderate or above."

**C. academic-paper-reviewer**
- *Guided mode* (guided_mode L15–22), in order:
  1. Journal-Fit Reviewer opens: genuine strengths ("never manufactured praise"), then the most critical structural issue.
  2. Wait for the author's response.
  3. Progressive revelation of further issues.
  4. Methodology focus (Reviewer 1).
  5. Domain perspective (Reviewer 2).
  6. Cross-disciplinary challenge (Reviewer 3).
  7. Devil's Advocate.
  8. Wrap up with a Revision Roadmap.
- *Phase 2.5 REVISION COACHING* (SKILL L157–178):
  1. Overall positioning
  2. Core issue focus
  3. Contribution framing probe (L5-W)
  4. **Explicit author triage** (`will_address` / `wont_address` / `not_on_point`, "with no inferred work order")
  5. Counter-argument response
  6. Implementation planning

  Skippable with "just fix it."
- *Residual coaching after re-review* (re_review L260–271): Gap analysis, Root cause diagnosis, Trade-off decisions, Action plan; at most 5 rounds.

### 1.3 Question taxonomy
1. **Four tagged types** (mentor L625–642; academic-paper mentor L455–486). Every question must carry one tag.
   - `[Q:CLARIFY]`: reduce ambiguity, sharpen definitions and scope.
   - `[Q:PROBE]`: dig into assumptions, reasoning, evidence.
   - `[Q:STRUCTURE]`: organize, connect ideas, build frameworks.
   - `[Q:CHALLENGE]`: test robustness, counter-perspectives.

   *Balance rules:*
   - Layers 1–2 are ≥70% CLARIFY/PROBE.
   - Layer 3 is ≥40% STRUCTURE.
   - Layers 4–5 are ≥60% CHALLENGE/STRUCTURE.
   - Any 3 consecutive questions include ≥2 types; after 4 of the same type, switch.

   Plan mode has a per-chapter High/Medium/Low distribution table and requires at least one question of each type per chapter.
2. **Six Paul–Elder types** (framework L9–81), each with question patterns: Clarification; Probing Assumptions; Probing Rationale and Evidence; Questioning Viewpoints and Perspectives; Probing Implications and Consequences; Questioning the Question.
3. **Question banks** (framework L85–133): RQ clarification, methodology probing, literature positioning, analytical reasoning, conclusions and limitations, contribution.
4. **Strategies** (framework L137–179): Funnel (open to precise), Mirror (restate, then follow up), Counterfactual, Analogy (draws on other domains, importing outside claims), Strategic Silence.
5. **FINER as guiding questions, not scores** in Socratic mode (research_question_agent L139), 2–3 questions per dimension. The RQ Summary records "User Self-Assessment" for each FINER dimension, i.e. the user's own judgments (L194–199).
6. **Toulmin decomposition** (argumentation framework L7–18): "socratic_mentor_agent: Guide users through Toulmin decomposition of their own arguments" (L67). The components are Claim, Data, Warrant, Backing, Qualifier, Rebuttal.

### 1.4 Turn-level rules
- **Shape of a turn:** acknowledge with 1–2 sentences of affirmation or restatement, then ask 1–2 focused questions; 200–400 words (mentor L19–20; guided_mode L26).
- Every response must contain at least one question; stay under 400 words; withhold evaluation (L757–759).
- When to give information: "Timely direction hints" about literature *directions* only, no citations (L22, L760). Plan mode adds writing direction hints after the user has thought things through.
- One adjacent facet at a time, never a menu (L498).
- Plan mode violates the 1–2 question rule: it lists 5 mandatory questions, then says "Start with question 1" (example L115–121).
- Language follows the user; technical terms stay in English (L654–657).
- Internal machinery (SCR, probes, health checks) is never named to the user. If asked "is this a test?", the mentor answers at the meta level without leaking the mechanism (L373, L530).

### 1.5 Handling user answers

| User behavior | Skill's response | Source |
|---|---|---|
| Superficial | "Why?", "So what?", "What if it were the opposite?", "What if that's not the case?" | mentor L21 |
| Vague term | "What do you mean by 'X'?", "Can you give a specific example?", "What does X include/exclude?" | framework L15–21 |
| Uncertain or hesitant | Strategic silence: "Take your time…what exactly are you unsure about? Is it the question itself, or your position on the question?" | framework L176–179 |
| Too broad | "If you could only answer one aspect…which would you choose? Why?" | mentor L214 |
| Oscillating between directions (non-convergence) | List only the user's directions, chronologically, in the user's words, unranked; offer (A) continue on a direction *the user* picks, (B) switch mode with the exit marker, (C) pause | failure_paths L197–214 |
| Overconfident or certain | Certainty-Triggered Contradiction ("I've seen research that argues the opposite") | mentor L185–190 |
| "No limitations" | "Every study has limitations. Would you be willing to think about where the most vulnerable part…is?" | mentor L271 |
| Only supportive evidence | "Is there any finding that would make you abandon this…?" | mentor L252 |
| Off-topic | "Gently guide back to the main point" | guided_mode L29 |
| Asks for a direct answer | Gently decline and explain the value of guided thinking; generate only after an explicit request and the visible exit | mentor L644–652 |
| Declines a probe | Acknowledge briefly; **no penalty** to any signal or classification | mentor L362–367 |
| Says a surfaced facet is not relevant | "One push, then retreat": accept immediately, never re-surface | mentor L523–528 |
| Pushes back on a finding (DA context) | Score the rebuttal 1–5; concede only at ≥4; no consecutive concessions; "Pressure is not evidence" | DA agent L401–431 |
| Discomfort leads mentor to soften a probe | Health check "Conflict Avoidance": restate the original probe from a different angle | mentor L738 |
| Paraphrase of a cited paper (reading probe) | Record it; "The Mentor does NOT judge accuracy"; acknowledge in ≤15 words, no praise | mentor L354–356 |

### 1.6 Convergence and termination
- **Five signals** (L605–615):
  - S1 Thesis Clarity: a one-sentence RQ, stated spontaneously, without hedges.
  - S2 Counterargument Awareness: ≥2 counterarguments raised unprompted.
  - S3 Methodology Rationale: why this method over the alternatives.
  - S4 Scope Stability: the core question unchanged for 3 rounds.
  - S5 Self-Calibration: later commitments are more accurate.
- **Rules** (L617–623):
  - ≥3 signals means CONVERGED: compile INSIGHTs into a summary.
  - All of S1–S4 means FULLY CONVERGED: end immediately, whatever the layer.
  - S1–S4 without S5 still converges, with a calibration note.
- **Auto-end conditions** (L582–601), whichever comes first:
  1. All layers done with ≥3 INSIGHTs each.
  2. ≥3 signals.
  3. Stagnation: 10 rounds without a new INSIGHT (goal-oriented) or 15 (exploratory).
  4. Maximum 40 rounds (goal-oriented) or 60 (exploratory).
  5. The user ends; output is produced with incomplete layers marked.
  6. The user switches mode.
- **Pace thresholds** (L567–571):
  - Ideal is 1 INSIGHT per 2–3 turns; below 1 per 5, use "Let me reframe this from a different angle..."
  - Forced advancement after 8 turns in a layer.
  - Layer N past N+3 turns with fewer than 3 INSIGHTs: recommend full mode.
- **Plan mode** (academic-paper mentor L408–451):
  - Signals C1 Thesis Clarity, C2 Chapter Coherence, C3 Evidence Mapping, C4 Limitation Honesty, C5 Self-Calibration, each rated Yes/Partial/No.
  - A chapter converges at ≥3 of 4 "Yes".
  - Over 5 rounds on one chapter: summarize and confirm.
  - Over 8: offer to skip the chapter, switch to outline-only mode, or take a break.
  - Over 30 total: suggest outline-only.
  - Typical session: 20–30 rounds.
- **Exploratory mode** gives the user control of the ending. Prohibited phrases: "natural stopping point," "shall I write this up?", "we've covered a lot," "to wrap up" (L145–153).

### 1.7 State tracking
- **Transcript-visible tags:** `[INSIGHT: …]`, `[COMMITMENT: …]`, `[READING-PROBE: …]`, `[ADJACENT-PROBE: surfaced=…, outcome=considered|declined|deferred]`, `[HEALTH-CHECK: Turn X | Agreement: Y/5 | …]`, `[DA-REBUTTAL: …]`, `[WORDING_PATTERN_ADVISORY]`, and the exit marker.
- **Re-derive state each turn from the transcript**, never from memory: "Do not rely on memory of prior reasoning between turns — only on tokens actually visible in the transcript" (L326).
- **Mid-process checkpoint** (academic-paper mentor L498–508): `[PLAN MODE CHECKPOINT]` lists completed, in-progress and remaining chapters, convergence status and the INSIGHT Collection; resumable. failure_paths F7 covers saving progress and the re-entry phrase.
- **Final artifacts:** Research Plan Summary with sections compiled per layer from INSIGHTs plus a complete INSIGHT list (L674–711). The Chapter Summary has a **"User Confirmed: Yes / needs modification"** field (academic-paper mentor L357–372). The RQ Summary has "Excluded" and "To be confirmed" scope fields (research_question_agent L201–204).

### 1.8 Scoring and rubrics for depth and engagement
1. **INSIGHT validity** (L573–580). These do *not* count: restating the RQ, agreeing with the mentor without adding substance, listing facts not connected to the RQ, repeating an earlier point, surface remarks ("this is interesting").
2. **Pace:** INSIGHTs per turn, as above.
3. **Convergence signals** S1–S5 and C1–C5, as above.
4. **Collaboration Depth Rubric** (`shared/collaboration_depth_rubric.md`; consumed post-hoc by `collaboration_depth_agent`, advisory, never blocks). Each dimension is scored 0–10:
   - **Delegation Intensity:** whole-task handoffs versus scattered micro-asks.
   - **Cognitive Vigilance:** the user challenges, verifies and pushes back on AI output. This is the highest-impact path, β=0.437.
   - **Cognitive Reallocation:** freed capacity is reinvested in higher-order work.

   These synthesize into Zone 1 (no AI use), Zone 2 (shallow, the worst outcome) or Zone 3 (deep, rare). Anti-sycophancy discipline: no score ≥7 without a turn citation; at least 2 forced "could have gone deeper" moments; re-audit any Zone 3 call; descriptive language only. If a stage has fewer than 5 user turns, the agent reports `insufficient_evidence` rather than guessing.
5. **Collaboration Quality Evaluation** (process_summary_protocol L77–138). Scores the *user* 1–100 on six dimensions (Direction Setting, Intellectual Contribution, Quality Gatekeeping, Iteration Discipline, Delegation Efficiency, Meta-Learning) and includes "Human vs AI Value-Add."
6. **AI Self-Reflection metrics** (L140–198): DA concession rate, health alerts by type, intent transitions, probe decline rates, and a sycophancy risk band (LOW/MEDIUM/HIGH). It must state that the AI grading itself is ironic.
7. **Codebook for mentor-violation labels** (codebook L19–79):
   - A1 "independent expression": bare assent, near-verbatim repetition of the mentor, or picking from a mentor menu does not count.
   - M1: legal directionless facet.
   - M2: mentor proposes a formed framing or hypothesis (violation).
   - M3: option inflation (listing ≥2 candidates).
   - M4: ranking or substitution.
   - M5: premature convergence.

   Metrics are reported separately and never averaged into one score.

### 1.9 Anti-leakage and non-imposition rules
- **Verb test** (Kong L2): never propose, substitute, rank, expand or select. The rationale: "even when the scholar 'approves,' their judgment is anchored on AI-supplied options they did not author."
- **Wording advisory is a surface-only check:** "I am not judging the idea; I am only flagging the wording." No rewrite unless the user asks (L91–100).
- **Adjacent probe:** a directionless facet ("names WHERE to look, never WHAT will be found"). Facet names that encode a mechanism, an outcome or a valence are banned (L509). It asserts only verifiable things, offers include-or-set-aside, never a menu, has a hard cap of 2 that are ≥3 rounds apart, and requires different facet kinds in a row (L482–492).
- **Banned evaluative phrases** in probe and acknowledgment turns: "correct," "right," "wrong," "good answer," "well said," "make sure," "verify," "prove" (L379–396).
- **Anti-pattern #6, "Shallow Socratic mode":** answers disguised as questions (SKILL L542).
- **Knowledge Isolation Directive** (anti_leakage L39–57): prefer session materials over parametric memory, flag `[MATERIAL GAP]` instead of filling from memory, and do not introduce references. It is **switched off in plan and Socratic modes**: "exploratory — LLM knowledge is expected" (L31).
- **Step 2.5:** when the user cannot articulate a contribution, "record the open contribution question…never fill it in" (academic-paper mentor L321).
- **Reviewer skill:** "Synthesizer cannot fabricate review comments" (reviewer SKILL L185). Strengths are never manufactured (#574). Severity is set by decision impact alone.

### 1.10 Failure modes ARS guards against

| Failure mode | Guard |
|---|---|
| Sycophancy and persistent agreement | Health check: if the mentor affirmed in 4 of the last 5 turns, inject a CHALLENGE question (L737). Rationale at L749. |
| Softening under pushback | Conflict Avoidance check (L738); DA rebuttal scoring and "Pressure is not evidence" (DA L405–431) |
| Premature closure | Intent detection plus anti-premature-closure rules (L145–153), M5 label |
| Idea generation creep | Verb test, exit marker, F1/F6 non-generation handling |
| Frame-lock | Adjacent probe; DA "Unexamined Premise" check |
| Leading questions | Anti-pattern #6 |
| Graded or test-like feel | Banned phrases; no penalty for declining; probes never framed as tests |
| Option menus and ranking | F6 lists unranked directions in the user's words; M3/M4 labels |
| Non-convergence dead end | F1/F6: (A) continue, (B) switch, (C) pause; F7 save and resume |
| Fabrication from memory | Knowledge isolation (writing modes only), `[MATERIAL GAP]` |
| Self-contradicting thresholds | 2026-07-04 audit merged auto-end rules into one authority per file |

### 1.11 Where ARS violates its own principles, and our firewall

These are the most useful concrete negative examples for our design.

**deep-research example (`socratic_guided_research.md`)**
- L176–178: the mentor declares "That's actually a very valuable finding," then tags an INSIGHT that contains *the mentor's* evaluation ("This hypothesis doesn't make the research meaningless; rather, it would change the direction of policy recommendations").
- L180–183 → L195: the mentor proposes a paired design ("you could intentionally pair cases…"). The user replies "Yes, paired design makes a lot of sense." The idea is recorded as user INSIGHT #9. That is a textbook A1 "bare assent" attribution error.
- L139–141 and L210–212: the DA injects mentor-side critiques (social-desirability bias, political sensitivity).
- L154, L167, L258: evaluative praise ("excellent strategy," "Your attitude is excellent," "a very powerful research positioning… an impactful study"). The last is a significance judgment.

**plan-mode example (`plan_mode_guided_writing.md`)**
- L204–206 and L384–388: the mentor writes the user's paragraphs.
- L213–233: the mentor draws a literature map, asks "Correct?", and the user says "Yes."
- L480–515: argument-strength ratings.
- L283: "PSM is the standard approach."

**Mentor agent file**
- The model reply for declining a direct answer (L647) itself contains an evaluation: "I think your second idea actually has a lot of potential."

**Framework's own Mirror example**
- L153–154: the mirror adds an interpretation ("direct causal relationship") and suggests counterexamples, so it is not a faithful mirror.

**Internal inconsistencies**
- Layer names differ between SKILL L291 and the agent file.
- Intent re-assessment is "every 5 turns" (L126) but README L303 says "every 3 turns."
- The framework table says "15-round limit" (L194) versus 40/60 in the agent.
- Stagnation is defined three ways: L569 "N+3", L571 "8 turns", L620 "10/15".
- F1 triggers at "Layer 1 exceeds 5 rounds."
- The stagnation message uses "reached a natural stopping point" (L620), a phrase banned in exploratory mode (L148).
- The 12-round example ends without meeting "≥3 INSIGHTs per layer."

**Lesson:** put thresholds in code, in one place, and lint the prompts.

---

## 2. Key verbatim snippets worth reusing
Paths are relative to `/Users/kensu/academic-research-skills/`; line numbers are 1-based.

**Q1. Non-generation boundary.** `deep-research/agents/socratic_mentor_agent.md:27-31`
> Socratic mode is **non-generation by default**. The Mentor may clarify, challenge, and organize the research directions the user has already expressed, but it must not propose, substitute, rank, expand, or select candidate research questions for the user. Non-convergence, elapsed rounds, stagnation, or a vague request for help is never consent to generate candidates.

**Q2. Verb test, operational form.** `docs/design/2026-06-08-kong-255-l2-advisory-not-generation.md:42-45`
> The verb test is the operational check. A change is on the advisory side only if it *surfaces a pattern in what the scholar already wrote* and *hands the judgment back to the scholar*. It crosses into generation the moment ARS supplies the candidate the scholar then merely approves.

**Q3. Why approval is not ownership.** Same file, `:68-70`
> Generating a candidate displaces ownership: even when the scholar "approves," their judgment is anchored on AI-supplied options they did not author.

**Q4. Non-convergence handling.** `socratic_mentor_agent.md:35-36, 39-40`
> 1. Summarize only directions and preferences already expressed by the user; identify unresolved choices instead of filling them in. … 3. Do not turn the summary into a menu, FINER-score alternatives, or ask the user to select among AI-authored questions.

**Q5. Unranked, user-worded summary.** `deep-research/references/failure_paths.md:207`
> Summarize the directions the user has expressed, in the order they were expressed and in the user's wording. Do not rank them, do not pre-fill option (A) with a system pick, and do not FINER-score them; the choice among them is the user's

**Q6. Never fill in.** `academic-paper/agents/socratic_mentor_agent.md:321`
> If the user articulates a contribution, record `[INSIGHT: contribution_claim]` in the user's words; otherwise record the open contribution question and carry it into Step 3 — never fill it in. Questions only — never propose, substitute, rank, expand, or select a contribution claim

**Q7. Turn shape and probing triggers.** `socratic_mentor_agent.md:19-21`
> 2. **Response structure**: First acknowledge the user's thinking (1-2 sentences of affirmation or restatement) → Then pose focused follow-up questions (1-2 questions)
> 3. **Response length control**: 200-400 words; keep it brief, precise, and leave thinking space for the user
> 4. **Deep probing triggers**: When the user's response is superficial, use "Why?", "So what?", "What if it were the opposite?", "What if that's not the case?"

(Adapt: drop "affirmation.")

**Q8. Quality standards.** `socratic_mentor_agent.md:757-759`
> 1. **Every response must contain at least one question** — a response without a question violates the Socratic principle
> 2. **Keep responses under 400 words** — past that, you're lecturing; stay terse and leave thinking space
> 3. **Withhold evaluation** — ask "why" and "then what" instead of judging ideas as good or bad

**Q9. Shallow Socratic anti-pattern.** `deep-research/SKILL.md:542`
> **Shallow Socratic mode** | Giving answers disguised as questions ("Wouldn't you say X is true?") | Ask genuine questions that expose assumptions; never lead to predetermined conclusions

**Q10. Non-evaluative acknowledgment.** `socratic_mentor_agent.md:354, 356`
> The user offers any content that references the paper — even if vague, even if arguably wrong. The Mentor does NOT judge accuracy.
> - Action: Acknowledge in ≤ 15 words. Do not praise, do not evaluate, do not grade. Example: `Got it — noted. Let's move into evidence.`

(For us: the no-evaluation part applies to *opinions*; reviewer statements of *fact* are checked.)

**Q11. Why praise is harmful.** `socratic_mentor_agent.md:396`
> Rationale: evaluative language turns the probe into a sycophancy hook — user answers well → Mentor praises → user feels graded. The probe is an observation, not a grading.

**Q12. No penalty for declining.** `socratic_mentor_agent.md:365`
> Decline carries **no penalty**: it does NOT count toward **Persistent-Agreement**, **Conflict-Avoidance**, or **Premature-Convergence** indicators, does NOT shift any **convergence signal**, and does NOT affect **intent classification**.

**Q13. Legal shape of the adjacent probe.** `socratic_mentor_agent.md:496-498`
> The ONLY legal shape: surface an adjacent **facet name** + ask whether to include or consciously exclude it. Ends in a question mark; contains NO formed RQ / hypothesis / conclusion. Surface ONE facet at a time — never a menu.

**Q14. Directionless, two-sided closure.** `socratic_mentor_agent.md:509, 511-512`
> The facet name must be **directionless**: it names WHERE to look, never WHAT will be found.
> The closing question is fixed as "include OR consciously set aside" — this hands the decision fully back to the user; do not hint which is right.

**Q15. Assert only what is verifiable.** `socratic_mentor_agent.md:514-517`
> The probe asserts only two VERIFIABLE things: (i) the user has not mentioned this facet (checkable against the transcript), (ii) the facet is adjacent to the topic. It asserts NOTHING about the facet's value — no novelty claims, no quality comparisons, no "you should."

**Q16. One push, then retreat.** `socratic_mentor_agent.md:523-526`
> **One push, then retreat.** If the user says the facet is already considered, not relevant, or that they want to stay in their frame, ACCEPT immediately — do not argue, do not re-surface the same facet. The user is the domain expert; the LLM's internal knowledge does not override their "not relevant."

**Q17. Violation trigger phrases.** `socratic_mentor_agent.md:557-558`
> The moment a probe contains "you could research X", "X is better / more novel", or "consider A, B, or C", it is a violation. Only the GOOD row is legal.

**Q18. Noun-swap test for generic wording.** `socratic_mentor_agent.md:87`
> The operative judgment is the noun-swap test: phrasing is shell-like when it would survive swapping its nouns for any other field's nouns without losing meaning.

**Q19. Advisory template.** `socratic_mentor_agent.md:91-94`
> `[WORDING_PATTERN_ADVISORY]` Your phrasing "<user excerpt>" resembles a common AI-typical research-question shell: <WPxx pattern family>. I am not judging the idea; I am only flagging the wording. What term, mechanism, site, or tension would a specialist in your field use instead?

**Q20. Anti-premature closure.** `socratic_mentor_agent.md:147-153`
> In exploratory mode, the following are **prohibited**: - Suggesting that the discussion "has reached a natural stopping point" - Asking "shall I write this up?" or "want me to summarize?" - Using phrases like "we've covered a lot" or "to wrap up" - Compressing layers to "move things along"
> The user decides when exploration is done. The mentor's job is to keep deepening, not to close.

**Q21. What is not an insight.** `socratic_mentor_agent.md:575-580`
> An INSIGHT must be a genuinely new understanding or connection. The following do NOT qualify: - Restating the research question in different words - Agreeing with the mentor's suggestion without adding substance - Listing known facts without connecting them to the RQ - Repeating a point already made in an earlier turn - Surface-level observations ("this is important" / "this is interesting")

**Q22. Question-type balance.** `socratic_mentor_agent.md:641-642`
> - Every 3 consecutive questions should include at least 2 different types
> - If 4+ consecutive questions are the same type → intentionally switch to a different type

**Q23. Health check against sycophancy.** `socratic_mentor_agent.md:737-738, 749`
> | **Persistent Agreement** | You have agreed with or affirmed the user's position in 4+ of the last 5 turns without introducing a counter-perspective | … | Inject a `[Q:CHALLENGE]` question … |
> | **Conflict Avoidance** | You softened or withdrew a probing question after the user expressed discomfort or pushback | … | Restate the original probing question in a different form …|
> Language models are trained to produce responses that humans rate highly. In a Socratic dialogue, this creates a perverse incentive: agreeing with the user feels "high quality" to the training signal, but it violates the Socratic principle.

**Q24. State from the transcript only.** `socratic_mentor_agent.md:326`
> … are prompt-level conceptual variables, not runtime state. At each turn after dialogue begins, re-derive them from the conversation transcript … Do not rely on memory of prior reasoning between turns — only on tokens actually visible in the transcript.

**Q25. Mirror and strategic silence.** `deep-research/references/socratic_questioning_framework.md:149-150, 177-178`
> Strategy 2: Mirror Strategy — Restate the user's words, then follow up.
> "Take your time. You just said 'actually I'm not sure' — what exactly are you unsure about? Is it the question itself, or your position on the question?"

**Q26. Pressure is not evidence.** `academic-paper-reviewer/agents/devils_advocate_reviewer_agent.md:429`
> **Pressure is not evidence.** Repeated pushback, appeals to authority or status, or bare requests to soften a finding do **not** by themselves change it … With no new evidence or reasoning that directly addresses the finding's stated basis, briefly restate the finding once and stop: do not expand caveats, apologize repeatedly, or retract a correct finding to preserve agreement.

(For us: apply to *facts* only.)

**Q27. Independent expression rule for provenance.** `evals/heldout/within_session_ideation_diversity/codebook.md:21-30`, plus `docs/design/2026-08-13-659-...:22-23`
> `yes` only when an actor turn states a relation, contrast, boundary, or object of inquiry that maps to one precommitted … framing … using enough substance to stand without the mentor's preceding words. The following are `no`: - `yes`, `that sounds good`, or another bare assent; - verbatim or near-verbatim repetition of a mentor-made formulation without a new actor-owned relation; - selecting an item from a mentor-made menu;
> A model-originated question, hypothesis, mechanism, ranking, or option is never credited as scholar-originated, even if the actor agrees with it.

**Q28. Absence anchors.** `academic-paper-reviewer/templates/peer_review_report_template.md:113, 271`
> An `absence:` anchor uses the exact grammar `absence: <where> — expected <item>; checked <surfaces>`
> An `absence` anchor is only checkable if it names where you looked — "the paper never states X" requires "checked Methods, Limitations, appendix".

**Q29. Knowledge isolation.** `academic-paper/references/anti_leakage_protocol.md:47, 49`
> 1. PREFER session materials over your parametric knowledge for all factual claims … 3. If the materials do not cover a topic the outline requires, flag it as [MATERIAL GAP] rather than filling from memory

**Q30. Descriptive scoring discipline.** `shared/collaboration_depth_rubric.md:135-136, 138`
> 1. **Evidence requirement**: no dimension score ≥ 7 ("High") without at least one specific dialogue-turn citation … 2. **Forced counter-enumeration**: before finalizing scores, the agent lists ≥ 2 moments where the user could have gone deeper … 4. **Descriptive language only**: no "great job!", no "needs improvement!". Report observed pattern + specific citable evidence.

**Q31. State-authority test.** `docs/design/2026-06-08-kong-255-l1-copilot-not-auto-research.md:45-47`
> Does this change let ARS create, select, execute, or advance a **research object of record** … **without** an explicit scholar-authored seed or scholar confirmation after inspecting the relevant state?

---

## 3. Mapping to Academic Review Copilot

### 3.1 Pattern-by-pattern verdicts

| # | ARS pattern | Verdict | How or why |
|---|---|---|---|
| 1 | Non-generation default and verb test (Q1–Q3) | **Borrow, then extend** | Firewall rule: the system must never **propose, substitute, rank, expand, select, rate, endorse, or dispute** an evaluative judgment (novelty, significance, severity, sufficiency, score, decision). Apply Q31 as our design-review test, with "review object of record" meaning opinion, weakness, severity, score or recommendation. |
| 2 | Visible exit marker `[SOCRATIC-NON-GENERATION-EXIT]` | **Adapt: no exit for subjective content** | ARS lets the AI generate when the user asks explicitly; we must not. Keep the visible-marker idea for (a) logging refusals (`[FIREWALL: subjective_request_declined type=novelty]`) and (b) labelling system-drafted prose during synthesis ("assembled from your statements U12, U17"). |
| 3 | Turn shape: acknowledge, then 1–2 questions, 200–400 words, always a question (Q7, Q8) | **Adapt** | The acknowledgment becomes a *neutral faithful mirror*, never affirmation. Ask 1 question by default (2 at most). Cap at about 80–200 words for time-pressed experts, longer only when quoting located evidence. Exception to "always a question": a pure fact lookup the reviewer asked for may simply be answered. |
| 4 | Probing triggers "Why? / So what? / opposite?" | **Adapt: re-anchor to the paper** | "What in the paper leads you to that?", "Which result or section is that based on?", "How much does this bear on the paper's main claim, in your view?", "If the authors addressed X, would your assessment change?" |
| 5 | "Timely direction hints" about literature; Analogy strategy | **Reject** | Brings in outside-paper, unverifiable knowledge and sets the agenda. Replace with in-paper LOCATE. |
| 6 | INSIGHT tagging | **Adapt into an OPINION ledger** | Store *verbatim* reviewer spans with utterance IDs, not mentor paraphrases. ARS's paraphrases embellish (§1.11). Admission requires Q21 plus A1 independent expression (Q27): "yes", repeating the system, or picking from a system menu never counts. |
| 7 | Wording-pattern advisory and noun-swap test (Q18, Q19) | **Adapt into a Specificity Advisory for review comments** | Fire on generic review shells that would survive swapping in any other paper ("lacks novelty," "more experiments are needed," "well written," "not convincing," "limited evaluation"). Template: "Your phrasing '<excerpt>' would fit almost any paper. I'm not judging the point, only its specificity. Which result, section, or prior work do you have in mind?" No rewrite; does not block. This is a check on form, not content. |
| 8 | Intent detection (exploratory vs goal-oriented) | **Adapt** | Reviewer profile: time budget, experience (first-time vs senior), and preference (thorough walk-through vs targeted). Default to goal-oriented with standard convergence. Keep anti-premature-closure in the sense that the reviewer decides when to stop (Q20). |
| 9 | SCR Commitment Gate | **Adapt, strongly recommended** | Use it as an **anti-anchoring device**: at each stage, collect the reviewer's own take *before* surfacing paper facts. Example: "Before I pull anything up: how convinced are you so far by the experimental support for claim C1?" Tag `[COMMITMENT]`. Never expose the terminology. |
| 10 | Divergence Reveal | **Adapt** | After the commitment, surface **paper-grounded facts only**, covering both what the paper provides and what it omits. Use neutral framing (Q14 two-sided closure). Never use external literature. |
| 11 | Certainty-Triggered Contradiction ("I've seen research that argues the opposite") | **Reject as written; adapt narrowly** | Fires only when certainty attaches to a *factual* claim about the paper ("it clearly beats all baselines on every dataset"), which triggers a VERIFY against Table X. When certainty attaches to an *opinion* ("clearly novel"), ask PROBE ("what in the paper makes that clear to you?"); never counter it. |
| 12 | Adaptive Intensity and S5 Self-Calibration | **Reject** | Requires the system to judge whether the reviewer's judgments are "accurate," which is a subjective verdict. Only factual accuracy may be tracked (count of statement checks contradicted by the paper). |
| 13 | 5-layer model | **Adapt into stages S0–S5** | See §3.2. |
| 14 | ≥2 rounds per layer; forced advancement; stagnation and max thresholds | **Adapt and move into code** | Experts need lower minimums (≥1 elicitation per mandatory form slot, skip allowed) and shorter caps. Define the numbers once in the state machine; ARS's prose thresholds contradict each other (§1.11). |
| 15 | Convergence signals S1–S4 and C1–C4 | **Adapt** | R1–R6 in §3.5. These are criteria about *process and form*, not content. |
| 16 | Four-type question taxonomy plus balance rules (Q22) | **Adapt** | Keep CLARIFY, PROBE and STRUCTURE. Split CHALLENGE into PERSPECTIVE (the *reviewer* generates the counter-view) and TENSION (a paper-grounded fact). Add VERIFY, LOCATE, COVERAGE, COMMIT. See §3.3. |
| 17 | Paul–Elder six types and question banks | **Borrow the templates, re-word** | The clarification, assumption, evidence ("Is this evidence sufficient?" asked *to* the reviewer), viewpoint ("How might the authors respond?") and implication patterns all work as elicitation. Drop the "your research" wording. |
| 18 | Mirror and Strategic Silence (Q25) | **Borrow; mirror must be faithful** | The mirror restates the reviewer's words and adds no interpretation (unlike ARS's own example at framework L153–154). Strategic silence works as-is for "I'm not sure." |
| 19 | Counterfactual strategy | **Adapt** | Ask the reviewer: "If the paper had included D in Table 2, would your assessment change?" This is legitimate because the reviewer supplies the answer. |
| 20 | Reading probe | **Adapt** | (a) In S0, ask which sections the reviewer has read closely; no penalty (Q12). (b) Unlike ARS (Q10), we **do** statement-check the reviewer's factual paraphrases of the paper. We never evaluate their opinions. Borrow the banned-phrase list for acknowledgments and extend it. |
| 21 | Adjacent-framing probe (Q13–Q17) | **Borrow structure; adapt content into two probe types** | **COVERAGE probe:** one review dimension not yet discussed (reproducibility details, the comparison set, ethics/limitations, data licensing), include-or-set-aside, hard cap (≤2 per stage, ≥3 turns apart), one push then retreat, log `outcome`. **GAP probe:** "The paper compares A, B, C; D, cited in §2, does not appear in Table 2 (checked §4, Table 2, App. B). Does that matter for your assessment, or not?" It asserts only verifiable facts (Q15, Q28). Use the venue checklist (ARR form or Responsible NLP checklist) as the external "table of contents" anchor ARS lacked; this reduces LLM salience bias. A high decline rate signals miscalibration. |
| 22 | Dialogue Health Indicator (Q23) | **Adapt; run every turn, in code** | "Persistent agreement" becomes **evaluative drift**: any system turn that agrees, disagrees, praises or rates (target: zero). "Conflict avoidance" becomes **fact retraction under pressure**. Keep **premature convergence**. Add **surfacing imbalance** (only omissions or negatives surfaced) and **loaded-question** detection. Run a post-generation checker every turn, not a self-check every 5 turns. |
| 23 | Auto-end conditions | **Adapt** | §3.6. |
| 24 | Research Plan Summary; Chapter Summary with "User Confirmed" | **Borrow the confirmation field; adapt content** | The review draft gets per-sentence provenance and per-section confirmation. Unaddressed slots are marked `[NOT ADDRESSED BY REVIEWER]` and never filled (Q6). |
| 25 | Plan mode's "5 mandatory questions per chapter" | **Adapt** | Review-form fields become mandatory elicitation slots, asked one at a time, with the checklist shown in a side panel (not 5 questions in one turn as in the plan example). |
| 26 | Writing direction hints; mentor-authored paragraphs | **Reject** | Content generation. During synthesis, the system may arrange *only the reviewer's* content into form structure. |
| 27 | Argument Stress Test with Strong/Moderate/Weak ratings | **Reject ratings; adapt into a Toulmin completeness check** | For each reviewer weakness, check whether these are *present*: claim (reviewer), data (paper anchor), warrant (reviewer's "why it matters"), qualifier (reviewer's severity/confidence), suggestion. Presence, never quality. |
| 28 | L5-W1/W2/W3 contribution forms | **Borrow as significance elicitation** | "Remove this paper from the literature — what is missing, in your view?" "If the paper's claims hold, who would do something differently?" These elicit and do not supply. |
| 29 | Knowledge Isolation Directive (Q29) | **Borrow and make always-on** | ARS switches it off in Socratic mode; we must not. Every system fact cites a paper span. If the paper does not cover something: `[NOT IN PAPER]`, never filled from memory. Reviewer claims about outside literature are stored as *reviewer-asserted, unverified*. |
| 30 | Typed evidence anchors (text/table/figure/equation/dataset/absence) and absence grammar (Q28) | **Borrow as-is** | Schema for fact-ledger spans; quotes ≤25 words; an absence anchor must list the surfaces checked. |
| 31 | Reviewer "guided" mode (AI reveals its own critiques) | **Reject content origination; borrow pacing** | Our progressive revelation applies to *facts*, one issue at a time. Borrow the 200–400-word limit and "gently guide back." Its example question ("Do you think this sampling strategy can capture X?") is still loaded; ours must not presuppose a flaw. |
| 32 | Explicit author triage (`will_address`/`wont_address`/`not_on_point`, no inferred order) | **Adapt** | The reviewer triages each surfaced observation: `affects_my_assessment` / `does_not_affect` / `not_relevant` / `need_more_info`. No system ranking. |
| 33 | "just fix it" skip | **Adapt** | "Let me just write it" opens a free-text form entry. The system then only statement-checks facts and gives specificity advisories; it never fills anything in. |
| 34 | DA Attack Intensity Preservation; "Pressure is not evidence" (Q26) | **Adapt to facts only; reject rebuttal scoring** | The system holds no opinions to defend. When the reviewer disputes a system fact, re-verify against the paper. If it is supported, restate once with the anchor and stop. If wrong, correct it and log. Scoring the reviewer's arguments 1–5 is rejected as a subjective judgment. |
| 35 | Collaboration Depth Rubric (Q30) | **Adapt for research evaluation and optional advisory** | Cognitive Vigilance (the reviewer verifies or corrects system facts) maps directly. Delegation Intensity splits in two: delegating judgment is refused by design; delegating objective work is fine. Reallocation: did freed time go into judgments? Keep the anti-sycophancy discipline. Do not show it in-product by default. |
| 36 | Collaboration Quality Evaluation (scores the user 1–100) | **Reject in-product** | Grading reviewers is out of scope and alienating; at most log it for research. |
| 37 | AI Self-Reflection metrics | **Adapt** | Firewall refusals, evaluative-drift alerts, fact retractions, surfacing balance, coverage-probe decline rate, provenance-entailment failures. |
| 38 | Codebook A1 and M1–M5 (Q27) | **Borrow as the evaluation codebook for the demo** | Extend with M6 evaluative acknowledgment, M7 loaded question, M8 unanchored fact, M9 synthesis embellishment (a draft sentence not entailed by its cited utterance), M10 fact retracted under pressure. Two blinded judges plus an adjudicator; never average into one score. |
| 39 | State re-derived from transcript tags (Q24) | **Adapt** | Keep real server-side state (JSON, below) and emit tags only for audit. Never rely on model memory. |
| 40 | Mid-process checkpoint (F7) | **Borrow** | Save and resume a review session. |
| 41 | Shallow-Socratic anti-pattern (Q9) | **Borrow; extend** | Ban rhetorical or leading questions and questions whose framing implies a verdict ("Isn't the lack of D a serious problem?"). |
| 42 | F6 "directions in the user's words, unranked, user picks" (Q5) | **Borrow** | When the reviewer goes back and forth on their stance, list their own stated positions chronologically and verbatim, then ask which they hold. Never suggest one. |

### 3.2 Proposed stage design (understanding → evidence → critique → synthesis)

| Stage | Derived from | Goal | Opening move | Allowed system acts | Mandatory slots (ARR-style) | Exit |
|---|---|---|---|---|---|---|
| **S0 SETUP** | Plan Step 0, intent detection, reading probe | Load paper (span index), venue form; get reviewer profile | "Which sections have you read closely so far? Roughly how much time do you have?" (no penalty) | Profile capture | — | Paper parsed, form selected |
| **S1 UNDERSTANDING** | Layer 1 (+ Thesis Crystallization) | Reviewer states the paper's claims and contributions *in their own words* | COMMIT first: "In 2–3 sentences, what does the paper claim to contribute?" | VERIFY reviewer's summary against spans (supported / contradicted / not found, with quote); LOCATE on request; extract the paper's *own* contribution statements verbatim (objective) only after the commitment | Paper summary | Reviewer summary exists; every factual mismatch resolved (accepted or disputed with a reason); claim list confirmed |
| **S2 EVIDENCE** | Layers 2+3 | Per core claim: what evidence the paper provides; reviewer judges sufficiency | COMMIT: "How convinced are you so far that the evidence supports C1, and why?" | LOCATE; objective setup inventory (datasets, baselines, metrics, seeds, variance, significance tests, as reported); GAP probes with absence anchors; inconsistency facts (abstract number differs from table); covers both provided and omitted | Soundness rationale; per-claim sufficiency (reviewer's) | Each core claim has a reviewer judgment or explicit skip; all surfaced observations triaged |
| **S3 CRITIQUE** | Layer 4 | Reviewer's strengths and weaknesses, severity, suggestions | "What do you see as the paper's main strengths? And its main weaknesses?" | Toulmin completeness check; Specificity Advisory; COVERAGE probe (≤2); PERSPECTIVE ("How might the authors respond?"); VERIFY factual parts of each weakness | Strengths; weaknesses; questions to authors; missing references (reviewer-asserted) | R2 + R3 met, or explicit skip |
| **S4 SIGNIFICANCE & OVERALL** | Layer 5, L5-W | Novelty, significance, excitement, scores, confidence: all reviewer's | L5-W2 adapted | Facts only: the paper's own novelty claims (quoted); closest work the *paper* cites and how the *paper* says it differs (quoted). Score–text consistency check on the *reviewer's own* statements, neutral: "You rated Soundness 4 and wrote '…' (U23). Keep both as they are?" | All scores, confidence, overall recommendation | All scores entered by the reviewer; R1 + R4 |
| **S5 SYNTHESIS & CONFIRM** | Research Plan Summary, Chapter Summary "User Confirmed", Step 2.5 | Assemble the review only from the ledgers | "Here is a draft assembled from your statements; every sentence links to its source." | Arrange and lightly edit reviewer text; entailment check per sentence; no added evaluative adjectives; flag `[NOT ADDRESSED BY REVIEWER]` | Per-section confirmation | Reviewer confirms every section |

**Rules that apply across all stages**
- The reviewer may jump to any stage; the system may suggest finishing the current one *once*.
- Every system fact carries a span ID.
- Each turn passes through the firewall checker.
- Refusal-and-redirect template (adapted from L644–652, without its evaluative leak): "That assessment is yours to make — the review should reflect your judgment. What I can do: [objective help, e.g., quote the paper's stated novelty claims (§1) and the closest prior work it cites (§2)]. Having seen those, how would you characterize it?"

### 3.3 Question taxonomy for the copilot

| Tag | Purpose | Example | Legal? |
|---|---|---|---|
| `CLARIFY` | Sharpen a vague term in the reviewer's statement | "When you say 'weak evaluation', do you mean the datasets, the baselines, or the metrics?" | yes |
| `PROBE` | Ask for the reviewer's grounds | "Which result is that based on?" | yes |
| `STRUCTURE` | Link opinions; map them to form fields | "Is this the same concern you raised about Table 3, or a separate one?" | yes |
| `PERSPECTIVE` | The reviewer generates the counter-view | "How might the authors respond to that?" | yes (the reviewer authors it) |
| `TENSION` | Juxtapose a paper fact with a reviewer statement | "You said all baselines are outperformed; Table 4 row 3 shows a lower score on X. How does that bear on your point?" | yes, if paper-anchored and two-sided |
| `VERIFY` | Report a statement-check outcome | "The paper does report 3 seeds (§5.1, footnote 4)." | yes (fact) |
| `LOCATE` | Find evidence on request | "Ablations are in Table 5 and App. C." | yes |
| `COVERAGE` | Raise an un-discussed form dimension | "You haven't touched on reproducibility details. Bring it into scope, or set it aside?" | yes (directionless) |
| `COMMIT` | Elicit a judgment or rating | "How would you rate soundness, and why?" | yes |
| *(banned)* | Leading, menu, ranking, rating | "Isn't the missing baseline a major flaw?" / "Is it A, B or C that bothers you?" / "This seems like your strongest point." | no |

**Balance:** borrow Q22.
- S1: CLARIFY/VERIFY-heavy.
- S2: PROBE/LOCATE/TENSION.
- S3: STRUCTURE/PERSPECTIVE/COVERAGE.
- S4: COMMIT/PROBE.

### 3.4 Handling vague, shallow, contradictory and off-track answers

| Answer | Move |
|---|---|
| Generic phrasing ("lacks novelty") | Specificity Advisory (noun-swap test), then PROBE "relative to which prior work?" |
| Bare assent to a system fact ("yes") | Records acceptance of the fact only. Follow with COMMIT "Does that matter for your assessment, or not? How?" No opinion is recorded until the reviewer independently expresses one (A1). |
| "I'm not sure" | Strategic silence (Q25): "Is it the paper's evidence you're unsure about, or how much weight to give it?" |
| Factually wrong claim about the paper | VERIFY with a quote, neutral wording, no "wrong/incorrect". Ask whether to revise. |
| Disputes a system fact | Re-check; if supported, restate once with the anchor and stop (Q26); if not, correct and log. |
| Stance oscillates | F6 pattern (Q5): list their own stated positions verbatim and chronologically; ask which they hold. |
| Off-track (e.g., discussing an unrelated paper) | Gently return to the current slot. |
| Asks the system's opinion | Refusal-and-redirect template; log the refusal. |
| Declines a probe or skips a slot | Accept with no penalty (Q12, Q16); mark the slot `skipped`. |
| Wants to type freely | Free-text entry, then fact checks and specificity advisories only (pattern 33). |

### 3.5 Measuring engagement and depth
- **In-dialogue convergence signals** (process and form only):
  - **R1 Stance Clarity:** the reviewer can state their overall assessment in one sentence, without hedges.
  - **R2 Two-sided Coverage:** ≥1 strength and ≥1 weakness stated, or an explicit "none."
  - **R3 Grounded Rationale:** every major opinion has a paper anchor plus a warrant.
  - **R4 Stance Stability:** overall stance unchanged for 3 turns.
  - **R5 Form Coverage:** every mandatory slot addressed or explicitly skipped.
  - **R6 Triage Complete:** every surfaced observation triaged.
  - *Converged* = R5 + R6 + ≥2 of R1–R4.
- **Pace** (adapting the INSIGHT pace): new A1-qualifying opinion-ledger entries per turn. If none for 4 consecutive turns, reframe once, then offer F6-style options (move on / write directly / pause).
- **Post-hoc metrics:**
  - Share of opinions with anchors; share with warrants.
  - Assent-only ratio.
  - Reviewer verifications and corrections of system facts (Cognitive Vigilance).
  - Judgment-delegation attempts (refusals).
  - Observations triaged versus surfaced.
  - Coverage-probe decline rate.
  - Edit distance between the synthesized review and the reviewer's utterances.
  - Entailment-failure count.
- **Research evaluation:** the extended codebook (pattern 38) with blinded judges. Use the rubric's anti-sycophancy discipline (Q30) for any reviewer-facing feedback.

### 3.6 Termination criteria
These numbers are proposals; keep them in a single config.
1. Converged per R-signals: offer synthesis. Never auto-start it in "thorough" mode; the reviewer decides (Q20).
2. Per-stage soft cap of about 6 turns: summarize *the reviewer's own points*, then offer (A) continue, (B) move on, (C) write directly.
3. Stagnation: 4 turns without a new ledger entry, handled as in §3.5.
4. Global cap of about 30 turns, or the time budget: offer synthesis with open slots marked.
5. The reviewer ends: synthesize with `[NOT ADDRESSED BY REVIEWER]` markers; never fill anything in.
6. Checkpoint and resume (F7).

### 3.7 Anti-leakage and firewall rules, consolidated for the system prompt
1. Verb test, extended (pattern 1).
2. Assert only what is checkable against the paper text or the transcript (Q15). Every fact carries a span; absences name the surfaces checked (Q28).
3. No praise, agreement, disagreement or rating in acknowledgments; use an extended banned list: "great/excellent/insightful/valid/fair point/strong/weak/I agree/good catch/significant (as evaluation)/novel/convincing."
4. No leading questions, no menus of critiques, no ranking of the reviewer's points (Q9, Q17).
5. Knowledge isolation is always on (Q29).
6. Provenance admits only independent reviewer expression (Q27).
7. Facts stay stable under pressure; opinions are never contested (Q26, adapted).
8. Surfacing is checklist-driven and covers both what the paper provides and what it omits; one item at a time; capped; logged.

### 3.8 Minimal state schema sketch (derived from ARS tags and checkpoints)
```json
{
  "stage": "S2",
  "turn": 14,
  "profile": { "time_budget_min": 30, "experience": "senior", "intent": "goal" },
  "fact_ledger": [
    { "id": "F7", "type": "absence", "locator": "Table 2",
      "expected": "baseline D (cited §2.3)", "checked": ["§4", "Table 2", "App. B"],
      "kind": "omits", "surfaced_turn": 11,
      "triage": { "label": "affects_my_assessment", "utterance": "U12" } }
  ],
  "opinion_ledger": [
    { "id": "O4", "slot": "weaknesses", "utterances": ["U12", "U13"],
      "verbatim": "…", "anchors": ["F7"], "warrant_present": true,
      "reviewer_severity": "major", "independent": true }
  ],
  "commitments": [{ "stage": "S2", "utterance": "U10" }],
  "statement_checks": [
    { "utterance": "U9", "verdict": "contradicted", "facts": ["F3"],
      "resolution": "reviewer_revised" }
  ],
  "slots": { "summary": "addressed", "soundness": "open", "reproducibility": "skipped" },
  "probes": { "coverage_count": 1, "last_probe_turn": 8,
              "outcomes": [{ "dimension": "reproducibility", "outcome": "declined" }] },
  "convergence": { "R1": false, "R2": true, "R3": "partial", "R4": false, "R5": false, "R6": true },
  "health": { "evaluative_drift": 0, "fact_retractions": 0, "premature_convergence": 0,
              "surfacing_balance": { "provides": 3, "omits": 4 } },
  "refusals": [{ "turn": 6, "type": "novelty_verdict" }],
  "scores": { "soundness": null }
}
```

---

## 4. Gaps: what we need that ARS does not provide
1. **Runtime firewall enforcement.** ARS is prompt-only and says so: such instructions "do not, and cannot, prove the model stays pressure-stable at runtime" (`docs/design/2026-06-08-274-concise-pressure-guidance-design.md`). We need a fact-vs-opinion classifier on every system turn, regex and lint checks for banned phrases and leading questions, and a regenerate-or-block path.
2. **A boundary taxonomy between objective and subjective.** ARS never defines it for evaluation content. Borderline cases need worked examples:
   - "No significance test is reported" is objective; "the gain is small" is subjective.
   - "D is cited but not in Table 2" is objective; "D is a necessary baseline" is subjective.
   - "The datasets are standard" relies on outside knowledge and popularity, so it is borderline.
   - "The method differs from X in Y" is objective as a textual difference; "meaningfully different" is subjective.
3. **Policy for which facts to surface.** Choosing which facts to show is a soft judgment. ARS acknowledges this only for the adjacent probe (majority-favour bias) and defers the fix to an "external anchor." We need deterministic, checklist-driven inventories, coverage of both provided and omitted items, and logging of everything surfaced and withheld.
4. **Paper grounding infrastructure.** PDF-to-span segmentation, stable span IDs, retrieval, verified quoting (string-match quotes against the source), table and figure value extraction, and verification of absence claims across all sections. ARS defines anchor *grammar* but not the dialogue-time machinery.
5. **Statement checking of reviewer claims.** We need a three-way verdict (supported / contradicted / not found in paper) with quotes. ARS's reading probe explicitly does *not* check accuracy.
6. **Synthesis with verifiable provenance.** ARS's summaries are mentor paraphrases with no utterance IDs, and they embellish (§1.11). We need per-sentence utterance links, an entailment or edit-distance gate, a diff view, and per-section reviewer confirmation.
7. **Venue review-form schema.** The ARR fields (summary, strengths, weaknesses, comments/questions, soundness, excitement, overall, confidence, reproducibility, ethics, missing references) and their mapping to stages and slots. ARS's stages are designed for research planning and paper writing.
8. **Score–text consistency checks** on the reviewer's own statements, phrased neutrally. Not present in ARS.
9. **A designed anti-anchoring order.** The commitment gate exists for pedagogy, not to protect independent judgment; we need commitment-before-summary ordering plus a way to measure anchoring (e.g., an A/B test of showing the summary first versus asking first).
10. **An expert, time-boxed user model.** ARS targets novices: the adjacent probe "deliberately serves exploratory novice researchers" and sessions run 40–60 rounds. Reviewers need about 15–30-minute sessions; probes must respect expertise ("one push, then retreat" becomes the default).
11. **Unverifiable outside-paper claims.** When the reviewer says "this was done in Smith 2023," we need a labelled "reviewer-asserted, unverified" state and optional consented retrieval. ARS's knowledge isolation is off in Socratic mode and has no reviewer-side counterpart.
12. **Confidentiality and LLM-use policy.** Manuscripts under review are confidential, and venue rules on LLM use in reviewing apply. Local running helps. ARS's cross-model consent gate (send nothing externally without explicit consent naming the provider and content) is a reusable pattern, but there is no reviewer-specific policy.
13. **Evaluation protocol for the demo.** ARS gives a synthetic-actor codebook. We need a real-reviewer user study (leakage rate, provenance accuracy, review specificity and quality, time, perceived ownership) with consent and ethics review; ARS itself notes that "any study of real scholars requires a new protocol."
14. **Tone and constructiveness assistance** that does not become a judgment of the paper (e.g., flagging toxic wording in the reviewer's draft as a style matter). Not addressed in ARS.