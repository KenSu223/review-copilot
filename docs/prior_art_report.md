# Academic Review Copilot: Related-Work Survey

> Survey date: 2026-10-02
> Method: 6 agents searched arXiv, ACL Anthology, OpenReview, conference websites and blogs, GitHub, Hugging Face, and product websites in parallel. About 250 works were checked in total; this report includes the roughly 120 most relevant.
> Notes:
> - Every entry was verified by an agent through search results or by opening the page, but most were checked only at the abstract page. **Read the original and verify the numbers before citing anything formally.**
> - Entries marked † were seen only in search snippets; the page was not opened.
> - All 6 agents exhausted their search quotas. "Appendix A" lists the directions that were not covered in time.

---

## 0. Conclusions

**The overall combination is still unoccupied.** Specifically, these five things together:
1. Using a Socratic approach to elicit the reviewer's subjective judgment;
2. A strict objective/subjective separation;
3. Synthesizing the review only from what the reviewer said, with provenance;
4. A small, self-hostable model trained with RL;
5. Defending against attacks that target the assistant.

No system, paper, or product does all five at once, and most of the individual items have not been done by anyone either.

**But the window is narrowing. The following points can no longer be sold as innovations:**

| Already-claimed point | Who is already doing it |
|---|---|
| "Embedding an LLM chat for reviewers inside OpenReview" | The **official NeurIPS 2026 three-arm randomized experiment** is doing it (no LLM / open chat / structured assistant), and explicitly states that it "does not write reviews for reviewers" |
| The principle "AI only assists and does not judge" | Already stated by ICML 2026 Policy B, the EACL 2026 position paper, Frontiers AIRA, ARR REVAS, and the AAAI 2026 position paper |
| "Simulated users with hidden state + recovering the hidden state as the reward" | CURIO, STaR-GATE, CollabLLM, TutorRL, and others already offer mature methods |

**Innovations we can genuinely claim (ordered by strength):**
1. **An operational definition of judgment leakage**: split AI's influence on human judgment into two parts: legitimate influence through facts, and illegitimate influence through framing, leading questions, selective presentation of evidence, and asymmetric questioning. **Nobody has defined** this concept yet; existing studies measure only the total effect.
2. **Elicitation RL with a subjective hidden state**: with a plain opinion-fidelity reward, the policy can use "hints" to get the simulated reviewer to voice the opinions the policy wants, and so game the reward. **Nobody has treated this as a training problem.** Fix: anchor fidelity to the opinion held before the dialogue starts, add an opinion-drift penalty, and use simulated reviewers that are easily swayed.
3. **Opinion provenance (AIS-H)**: facts map to the paper text, opinions map to the human's utterances, and both precision and recall are measured. Existing provenance work tracks only "who typed which characters", not "whose judgment this is".
4. **Attacks and defenses targeting the assistant rather than an automated reviewer**: every injection paper measures how much the score gets inflated. Nobody has studied how attacks such as **fact distortion or overclaim** affect an assistant that "only states facts", nor the **conflict between canaries planted by the venue and the official copilot**.
5. **A small self-hostable model dedicated to Socratic assistance that preserves human judgment**: existing small models all generate reviews automatically (OpenReviewer-8B, DeepReviewer-14B, etc.).
6. **Byproduct: structured judgment-process data**: Wei et al. (ICML 2026 position, see §1.1) argue that the bottleneck for AI-assisted reviewing is the lack of "judgment-process data", and call for an active elicitation interface. Our copilot is a complete implementation of such an interface: while assisting the review, it naturally produces the reviewer's opinions, their grounds, and provenance links.

---

## 1. Closest competitors and related work (must be compared head-on in the paper)

| # | Work | Type | Overlap with us | Key difference |
|---|---|---|---|---|
| 1 | **NeurIPS 2026 AI-Assisted Reviewing Experiment** ([link](https://neurips.cc/Conferences/2026/ai-reviewing-experiment)) | Official randomized experiment, embedded in OpenReview | Chat inside OpenReview; "helps you understand, does not judge for you"; has a structured-assistant arm | The structured arm **proactively offers help** rather than eliciting opinions; no provenance-based review synthesis; no engagement proof; uses closed-source APIs; results not yet published |
| 2 | **ICLR 2025 Review Feedback Agent** ([arXiv 2504.09737](https://arxiv.org/abs/2504.09737), [code](https://github.com/zou-group/review_feedback_agent)), Nature MI 2026 | RCT on 20,000 reviews | Checks whether the reviewer's statements misread the paper | Critiques the review **after it is written**, with no dialogue; a CHI 2026 follow-up study found reviewers mostly changed only the wording |
| 3 | **ARR REVAS** ([link](http://aclrollingreview.org/revas-may26)) | Official ACL tool, self-hosted | Generates no content; self-hosted; backed by the ACL community, with 2 years of maintenance funding | Only checks the finished weakness paragraphs and usually cannot see the paper itself; no dialogue. **It is more likely a partner than a rival** |
| 4 | **ReviewFlow** (IUI 2024, [arXiv 2402.03530](https://arxiv.org/abs/2402.03530)) | HCI system | Offers reflective questions during reading; generates an outline from the reviewer's own notes | Questions are fixed templates; proactively supplies novelty-related knowledge, which influences subjective judgment; tested with only 16 novices |
| 5 | **ReVoicer** ([arXiv 2608.00299](https://arxiv.org/abs/2608.00299)) | Workshop prototype | **Synthesizes the review only from the reviewer's comments** (closest to RQ3) | The reviewer writes comments on their own initiative and the system asks no questions; no neutrality constraint; not yet evaluated |
| 6 | **Enago Read AI Peer Review Workspace** ([link](https://www.read.enago.com/ai-peer-review-workspace/)) | Commercial product for publishers | Uses AI questions to have reviewers confirm they understood the paper; locally deployed LLM; tracks how long reviewers use it | Journal-oriented; closed-source; the questions test comprehension rather than eliciting judgment |
| 7 | **Frontiers AIRA Review Guide** ([link](https://www.frontiersin.org/guidelines/aira-review-guide-handling-editors)) | Chat embedded in a journal platform | Leaves judgment to humans; runs in a closed system | Q&A only; no opinion elicitation and no review synthesis |
| 8 | **ICLR 2027 Reviewer AI Policy** ([link](https://iclr.cc/Conferences/2027/AIPolicyForReviewers)) | Policy | Reviewers who use LLMs must submit **their own self-written original assessment and the full record of LLM interactions**; an excessive discrepancy between the two counts as misrepresentation | **This is exactly what our engagement trace and provenance can generate automatically, which makes a strong deployment argument** |
| 9 | **ICML 2026 Policy B and its RCT** ([arXiv 2609.19420](https://arxiv.org/abs/2609.19420)) | Policy + randomized experiment | Policy B allows using LLMs to understand the paper and forbids asking them about strengths/weaknesses. This is essentially our objective/subjective boundary | Rules only, no tool. High non-compliance rates (22.5% / 36.5%) show the need for a tool that guarantees the boundary by design |
| 10 | **Thinking Assistants: LLM-Based Conversational Assistants that Help Users Think By Asking rather than Answering** ([arXiv 2312.06024](https://arxiv.org/abs/2312.06024); Soya Park, Hari Subramonyam, Chinmay Kulkarni) | Research prototype | A thinking assistant that insists on "asking only, never answering"; an 80-person lab study + a deployment with 223 conversations | Implemented through prompting, not training; the setting is career reflection. **Author affiliations are not listed on the arXiv page; Kulkarni may be at Emory (to be verified); a possible collaborator** |
| 11 | **Wei et al., Position: AI-Augmented Peer-Review Ecosystem** (ICML 2026, [arXiv 2506.08134](https://arxiv.org/abs/2506.08134)) | Position paper | Advocates building an AI-assisted reviewing ecosystem, identifies the bottleneck as judgment-process data, and calls for an active elicitation interface | Vision and illustrative experiments only; accepts AI-drafted meta-reviews and reference reviews, which is looser than our stance. See §1.1 |

Other related work to watch:
- AAAI-26 AI Review Pilot ([arXiv 2604.13940](https://arxiv.org/abs/2604.13940)) and the EMNLP 2026 AI Reviewing Experiment: in both, the AI writes the reviews itself, the opposite of our philosophy.
- Peerispect ([arXiv 2604.17667](https://arxiv.org/abs/2604.17667)): uses NLI to check whether the reviewer's statements are consistent with the paper text.
- Position papers: Choi et al. in EACL 2026 Findings ([link](https://aclanthology.org/2026.findings-eacl.9/)), arguing for "augment, not automate"; Yun et al. at an AAAI 2026 workshop ([arXiv 2601.09182](https://arxiv.org/abs/2601.09182)), arguing for mentoring rather than automatic generation.

### 1.1 Close reading: Wei et al., *Position: The ML Community Must Build an AI-Augmented Peer-Review Ecosystem* (ICML 2026 Position Track)

- **Basic information**: [arXiv 2506.08134](https://arxiv.org/abs/2506.08134) (v4, 2026-06-09); local PDF at `papers/2506.08134.pdf`. Authors Qiyao Wei\*, Samuel Holt\*, Jing Yang, Markus Wulfmeier, Mihaela van der Schaar (Cambridge / USC / DeepMind). It is a position paper, with **no deployed system and no human-subjects study**.
- **Claim**: build a reviewing ecosystem in which LLMs assist authors, reviewers, and ACs while humans keep the final judgment. **The bottleneck is not the model but the lack of judgment-process data**, e.g., why a score was changed, which rebuttal point resolved which concern, which part of the paper each statement in a review refers to, and how the AC weighed the considerations.
- **Proposed tools**:
  - RAV (retrieval-augmented verification)
  - Code reproducibility analysis
  - Review Report Card (four dimensions: coverage, specificity, evidence base, tone)
  - Comparison with an LLM-generated "reference review" to prompt reviewer reflection
  - AC decision support and meta-review first drafts
  - Simulated reviewing for authors
- **Data plan**: **active elicitation** at key decision points, e.g., asking "You changed your score from 5 to 7; which sentence in the rebuttal influenced you?" For privacy, tiered access: public reviews, private trajectories that require mandatory opt-in, and data kept in a confidential computing enclave.
- **Experiments** (o3 plus few-shot ICL, ICLR 2024/25 data, recall only):
  - Recall for generated weaknesses is only 0.387 / 0.632, versus 0.724 / 0.927 for strengths; the authors call this the "**critical thinking gap**" and argue that humans should be the "senior partner";
  - Recall rose in 2025, possibly because human-written reviews increasingly resemble AI-written ones;
  - Score prediction: MAE about 2.3 for initial scores and about 0.67 for final scores; score changes are the hardest to predict;
  - The appendix claims that a report-card pilot on 200 reviews increased word count by 28%, but **gives no experimental design**.
- **Stance discussion**: they treat the ICML 2026 Policy as a "strictly non-evaluative" stance. They agree that delegation of judgment and confidentiality are boundaries, but argue these boundaries should lead to **privacy-preserving, venue-integrated, auditable** assistance. They acknowledge the de-skilling risk but offer no solution.
- **Defenses in the limitations section**: Dual-LLM sanitization (strip instructions from the manuscript before reasoning), and randomizing or hiding report-card weights to prevent gaming.
- **What it gives us**:
  1. Motivation citations: growth in scale, score inconsistency, shallow rebuttal engagement (most reviewers do not respond; those who do respond less than once on average, with fewer than 150 words), and the critical thinking gap. The last supports "leave flaws and judgments to humans".
  2. Positioning: we are a concrete implementation of their "AI-empowered reviewers" agenda that **simultaneously satisfies** their three requirements (privacy-preserving, venue-integrated, auditable) and ICML's strict non-evaluative boundary.
  3. **Our copilot is the full version of an active elicitation interface**, and its byproduct is exactly the data they say is missing: links from opinions to utterances, links from facts to paper spans, and interaction trajectories annotated with dialogue acts.
  4. We address two problems they raise but do not solve: de-skilling (the reviewer does their own thinking), and the anchoring caused by reference reviews (which can be quantified with judgment leakage).
  5. What we can borrow:
     - Report Card dimensions: for evaluating the final review; coverage can become an elicitation-coverage reward;
     - The "real points / hits" evaluation protocol: precision needs to be added;
     - Follow-up questioning at the rebuttal stage: as an extension direction;
     - Dual-LLM sanitization: as an RQ4 baseline, though it cannot stop attacks that only change the presentation.
- **Caveats**:
  - They also use the term "co-pilot", so we need to differentiate our name.
  - Their vision is looser than ours (it accepts meta-review first drafts and reference reviews), so we should write that we "propose a stricter design within their agenda" rather than that we "follow" them.
  - Their experiments are thin: many CIs are ±0.000, there is no precision, and sample sizes are unclear. When citing, treat these numbers as illustrative only.

---

## 2. Existing work and our position, RQ by RQ

### RQ1: Socratic dialogue policy

**Existing work:**
- Socratic tutors in education are mature:
  - SocraticLM (NeurIPS 2024, [GitHub](https://github.com/Ljyustc/SocraticLM))
  - **TutorRL** (EMNLP 2025, [arXiv 2505.15607](https://arxiv.org/abs/2505.15607)): a 7B model trained with online multi-turn RL against simulated students, with a penalty for directly leaking the answer
  - PEARL ([arXiv 2605.29582](https://arxiv.org/abs/2605.29582))
  - HeuristicEdu ([arXiv 2607.22996](https://arxiv.org/abs/2607.22996)): found that **explicit anti-leakage penalties can destabilize GRPO training**
- Socratic/dialogue tools that help people read papers:
  - In-situ Thought Exchanges ([arXiv 2510.15234](https://arxiv.org/abs/2510.15234)): expresses its own opinions; not neutral
  - InsightGUIDE: deliberately designed to be opinionated
  - Critical Inker ([arXiv 2604.07167](https://arxiv.org/abs/2604.07167))
- Eliciting subjective judgment in a Socratic way: the Socratic LLM for deliberation at CSCW 2025 ([arXiv 2508.09911](https://arxiv.org/abs/2508.09911)). But its **goal is to change** annotators' judgments, so it serves well as a contrasting counterexample.
- The locally installed skill `academic-paper-reviewer` has a "Socratic guided" mode, but it serves **authors**.

**How we differ:** existing tutors all "know the right answer" and lead students toward it; our copilot **should have no target opinion**. This distinction must be stated clearly.

### RQ2: Objectivity / Neutrality

**Evidence: AI changes human judgment, and the change is hard to notice.**
- Jakesch et al. (CHI 2023, [arXiv 2302.00560](https://arxiv.org/abs/2302.00560)): an opinionated writing assistant changes the opinions users write.
- **Williams-Ceci et al.** (Science Advances 2026, [link](https://www.science.org/doi/abs/10.1126/sciadv.adw5578)), N=2,582: users' attitudes shift toward the AI's bias, **warnings given before or after have no effect**, and interactive assistance has a stronger effect than static. → **Disclosure alone is not enough; the firewall must be built at the architecture level.**
- **Hackenburg et al.** (Science 2025, [link](https://www.science.org/doi/10.1126/science.aea3884)), N≈77k: **persuasion based on facts and evidence is the most effective.** → The premise "giving only facts has no influence" does not hold; the choice of which evidence to present itself causes leakage and must be measured.
- **Parisi et al.** ([arXiv 2605.14097](https://arxiv.org/abs/2605.14097)): an LLM moderator skewed outcomes on specific items, while overall agreement metrics did not change and participants' trust actually increased. → Look at per-criterion changes, not just the total score.
- Rastogi et al. (CSCW 2022) study anchoring; Dratsch et al. (Radiology 2023) found that experts are also swayed by AI.
- El-Sayed et al. (DeepMind, [arXiv 2404.15058](https://arxiv.org/abs/2404.15058)): distinguish rational persuasion from manipulation. **This is the theoretical basis for our dichotomy of legitimate vs illegitimate influence.**

**Methods we can borrow for measuring neutrality:**
- **Balanced approval** (Stray et al., [arXiv 2605.28911](https://arxiv.org/abs/2605.28911)): have accept-leaning and reject-leaning reviewers each rate the copilot's questions; reward = average approval minus the gap between the two groups.
- **FramingQA** ([arXiv 2609.07448](https://arxiv.org/abs/2609.07448)): a three-level framing taxonomy and invariance tests under "facts unchanged" conditions; can serve as the label scheme for a leading-question detector.
- Sycophancy (Sharma et al. ICLR 2024; ELEPHANT ICLR 2026): the failure mode in the opposite direction; the copilot must not simply go along with the reviewer either.
- The AMPERE dataset (EVALUATION / REQUEST / FACT / QUOTE proposition labels): can serve as seed data for a neutrality judge.

**Conclusion: nobody has defined "judgment leakage".** The only similarly named work, Preference Leakage ([arXiv 2502.01534](https://arxiv.org/abs/2502.01534)), is about LLM judges contaminating training data, a different concept; it can be cited for disambiguation.

### RQ3: Faithful review synthesis / Opinion provenance

**Existing work:**
- Attribution methods at the factual level are mature: AIS (Rashkin et al. 2023), ALCE (EMNLP 2023), Attribute-First-then-Generate (ACL 2024), LongCite ([arXiv 2409.02897](https://arxiv.org/abs/2409.02897)).
- Work closest to opinion fidelity:
  - **DeliberationBank** ([arXiv 2510.05154](https://arxiv.org/abs/2510.05154)): per-individual representativeness plus neutrality scoring, with a fine-tuned DeBERTa as judge, which outperforms LLM judges.
  - **Voice Retention audit** ([arXiv 2609.38818](https://arxiv.org/abs/2609.38818)): **86% of opinions stated only once are dropped by summarization.** → Opinion recall should report opinions that appear only once separately.
  - **Belief-level aggregation** ([arXiv 2601.04889](https://arxiv.org/abs/2601.04889)): first extracts structured opinion units, and the LLM only turns them into prose. Consistent with our design.
  - Habermas Machine (Science 2024): synthesizes text only from human opinions, but the synthesizer itself may also introduce bias.
  - The speaker-misattribution error type from DiaSumFact (ACL 2023) is exactly what we need to prevent: "attributing the AI's words to the human".
- Text-level provenance and ownership:
  - HaLLMark (CHI 2024), Reactant ([arXiv 2609.40126](https://arxiv.org/abs/2609.40126)): track only "who wrote which characters".
  - **AI Memory Gap** (CHI 2026, [arXiv 2509.11851](https://arxiv.org/abs/2509.11851)): **users cannot tell which ideas are their own and which are the AI's.** → Provenance logs must be recorded; self-reports cannot be relied on.
  - AI Ghostwriter Effect (TOCHI 2024): users feel no ownership of AI-generated text yet still claim authorship.

**Conclusion: nobody has defined precision and recall together for "opinions mapped to human utterances".** We can propose AIS-H.

### RQ4: Adversarial robustness

**Attacks are already mature, but they all target automated reviewers:**
- Hidden-text injection:
  - The Nikkei 2025 report and Lin's (CACM 2026, [arXiv 2507.06185](https://arxiv.org/abs/2507.06185)) taxonomy of 4 classes of injection.
  - JAMA Netw Open 2026: models **still obey injected instructions even after detecting the paper's flaws**, and stricter prompts do not help.
  - Sahoo et al. ([arXiv 2512.10449](https://arxiv.org/abs/2512.10449)): 15 attack strategies, flipping reject to accept at rates up to 86% on open-source models; **released a benchmark of 200 ICLR papers**.
- Attacks that need no hidden prompt, which filtering cannot stop:
  - Rewriting only the abstract: about 38% success rate ([arXiv 2606.10159](https://arxiv.org/abs/2606.10159)).
  - **"No Hidden Prompts Needed!"** ([arXiv 2606.13044](https://arxiv.org/abs/2606.13044)): changing only the presentation, 75% success rate; the AI treats "appearing to address a limitation" as "actually resolving it". **This is the closest to the overclaim attack we worry about.**
  - RobustReview ([arXiv 2609.39027](https://arxiv.org/abs/2609.39027)) introduces "false robustness": models insensitive to rewrites often also fail to distinguish good papers from bad ones. → Robustness metrics must be reported together with discrimination ability.
- Venue canaries:
  - ICML 2026 hid watermark instructions in PDFs, caught 795 non-compliant reviews, and desk-rejected 497 papers.
  - IntraGuard (CCS'26, [arXiv 2605.05271](https://arxiv.org/abs/2605.05271)).
  - Rao et al. ([arXiv 2503.15772](https://arxiv.org/abs/2503.15772)).
- Defense baselines:
  - **SafeReview** ([arXiv 2604.26506](https://arxiv.org/abs/2604.26506)): adversarial preference training of a generator and a defender; closest to our RL plan.
  - **Meta SecAlign-8B** ([HF](https://huggingface.co/facebook/Meta-SecAlign-70B)): can serve as a base model or a baseline.
  - PhantomLint ([arXiv 2508.17884](https://arxiv.org/abs/2508.17884)): detects hidden text.
  - DataFilter, StruQ, SecAlign, Instruction Hierarchy, CaMeL.
  - RL adversarial co-evolution: ARLAS, RETA, CoER.
  - Adaptive attack evaluation: PISmith, Nasr & Carlini "The Attacker Moves Second".

**Gaps we can fill:**
1. The metrics to use when attacking an assistant: degree of fact distortion, whether it repeats the paper's claims without verification, whether judgment leaks, and whether it steers the reviewer's questions in some direction.
2. An overclaim benchmark: the paper claims X but the experiments support only a weaker X′; does the copilot report X or X′?
3. **Canary conflict**: the official copilot reads the same PDF; it must neither execute the canary instruction nor cause the reviewer to be wrongly flagged as non-compliant.
4. A unified multi-channel benchmark covering hidden text, metadata, Unicode tags, font mapping, multilingual text, images, canaries, and overclaim.
5. Red-team evaluation with adaptive attacks.

### RQ5: Lightweight deployable model and RL training

**Methods we can borrow directly:**

| Method | Where to use it |
|---|---|
| **CURIO** ([arXiv 2504.03206](https://arxiv.org/abs/2504.03206)) | Per-turn reward = the user model's belief gain about the hidden type (potential-based). Gemma-2B as the policy. **Closest to our opinion-fidelity reward.** Replacing the hidden type with an aspect-wise opinion vector yields a dense reward |
| **CollabLLM** (ICML 2025 Outstanding, [verl recipe](https://verl.readthedocs.io/en/latest/algo/collabllm.html)) | Computes multi-turn rewards by rolling out future turns with a simulated user; has an off-the-shelf implementation |
| **TutorRL / PEARL** | Multi-objective RL that must "both help and hold back"; trace the Pareto curve between fidelity and neutrality |
| **ASIG** ([arXiv 2607.03426](https://arxiv.org/abs/2607.03426)) | Multi-turn GRPO with expected information gain (EIG) as the reward; can replace our elicitation-efficiency reward |
| **STaR-GATE** ([arXiv 2403.19154](https://arxiv.org/abs/2403.19154)) | Hidden persona plus self-improvement, as a simpler alternative reward |
| **UserRL** ([GitHub](https://github.com/SalesforceAIResearch/UserRL)) | Two findings: SFT cold start and trajectory-level reward shaping are key |
| **Persona consistency RL** ([arXiv 2511.00222](https://arxiv.org/abs/2511.00222)) | Keeps the simulated reviewer from drifting away from its hidden opinions during the dialogue; otherwise the fidelity reward becomes very noisy |
| **REMOR** ([arXiv 2505.11718](https://arxiv.org/abs/2505.11718)), **InternReviewer** ([arXiv 2608.28612](https://arxiv.org/abs/2608.28612)) | GRPO and GSPO reward designs in the review domain; InternReviewer has a "zero-tolerance" citation-verification reward |

**Existing small review models, all fully automatic generators, usable as baselines:**
- Llama-OpenReviewer-8B ([HF](https://huggingface.co/maxidl/Llama-OpenReviewer-8B))
- DeepReviewer-14B
- CycleReviewer
- ProReviewer-8B ([arXiv 2606.13349](https://arxiv.org/abs/2606.13349))
- RbtAct-8B

**Base model candidates:** Qwen3-4B (Apache-2.0), Llama-3.1-8B-Instruct, Meta-SecAlign-8B, DeepSeek-R1-Distill-Qwen-7B.

---

## 3. Plan adjustments prompted by the survey

1. **Change the positioning to:** do not pitch "a chatbot inside OpenReview", nor the principle "AI does not judge". The main storyline is **elicitation, provenance, leakage measurement, and the training method**, positioning our work as "a principled, trained version of the NeurIPS 2026 structured-assistant arm".
2. **The fidelity reward must be gaming-proof:** use the hidden opinion from **before** the dialogue as ground truth; add an opinion-drift penalty; include easily swayed types among the simulated reviewers; try the neutrality term both as a reward and as a hard constraint (per HeuristicEdu's warning).
3. **Leakage experiment design:**
   - First collect the reviewer's blind prior judgment;
   - Three arms: copilot secretly accept-leaning / reject-leaning / neutral;
   - With **factual answers held exactly identical**, run a factorial manipulation of framing, question asymmetry, and evidence selectivity;
   - Look at per-criterion changes, not just the total score;
   - Add a planted-error probe: put a factual error in the copilot's answer and see whether the reviewer catches it.
4. **Ownership cannot be looked at in isolation:** users prefer sycophantic AI (Cheng et al. Science 2026), so ownership and satisfaction must be reported together with fidelity and leakage. A source-memory test (asking the reviewer "is this opinion yours or the AI's?") and a quote-recall test can be added.
5. **Expect satisfaction to drop:** Buçinca (CSCW 2021) found that the most effective cognitive forcing designs are the least liked by users. Measure Need for Cognition as a moderator and add a quick mode.
6. **Update the deployment argument:**
   - ICLR 2027 requires submitting a self-written assessment and the full record of LLM interactions, which our system can generate automatically;
   - Elsevier and ARR forbid uploading manuscripts to tools that do not protect privacy, so self-hosting is needed;
   - ICML 2026's high non-compliance rate shows that rules alone cannot enforce the boundary.
7. **Data licenses:** Review-5K and DeepReview-13K **forbid use in real reviewing systems**. A deployable model should be trained on Re2, ARR-DC, and NLPeer, checking each license's terms one by one.
8. **Robustness evaluation:** always report both invariance to rewrites and injections and sensitivity to genuine differences in evidence, to avoid false robustness.
9. **Add the "data output" selling point (from Wei et al. 2026):** design the copilot's log schema so that it can directly output structured judgment-process data, including opinion units, their grounds, the corresponding paper spans, dialogue acts, and the turn in which each opinion formed or changed. For privacy, borrow the opt-in plus tiered-access scheme. In the future the system could be extended to the rebuttal stage, asking Socratically "which response changed your judgment?"

---

## 4. Recommended resources

| Purpose | Resource |
|---|---|
| Hidden opinions for simulated reviewers | **Re2** ([arXiv 2505.07920](https://arxiv.org/abs/2505.07920), includes initial drafts and rebuttals), ARR-DC ([link](https://arr-data.aclweb.org/)), NLPeer, CLAIMCHECK (maps opinions to paper claims), DISAPERE / AMPERE (opinion-type labels), SEA-S (merges multiple reviews into one profile), the persona dimensions of AgentReview and ReviewerToo |
| Groundedness | **PeerQA** ([HF](https://huggingface.co/datasets/UKPLab/PeerQA), reviewer questions answered by the paper's authors, including an "unanswerable" category), SciDQA, QASPER, LongCite-45k / LongBench-Cite, HalluPeer, ReviewScore |
| Review quality | RevUtil, ReviewEval, PRAIB (weakness coverage), the overlap metrics of Liang et al. |
| Injection benchmark | Sahoo et al.'s 200 ICLR papers, **CrackedPDFs** ([arXiv 2607.19396](https://arxiv.org/abs/2607.19396), 29k PDFs), LLM-as-a-Reviewer, the "No Hidden Prompts Needed" rolling benchmark, RobustReview, PaperGuard (multimodal) |
| User study design references | ICLR 2025 RCT, Chen et al. at CHIWORK 2025 (24 reviewers, within-subjects design), the persuasion experiments of Jakesch / Williams-Ceci / Fisher |
| Control group of AI-generated reviews | Gen-Review ([arXiv 2510.21192](https://arxiv.org/abs/2510.21192)), Intel AI-Peer-Review-Detection-Benchmark |

---

## 5. Quick overview of open-source projects, tools, and skills

- **Repos**: zou-group/review_feedback_agent, OpenReviewer, DeepReviewer-v2 (577★), CycleResearcher, MARG, AgentReview (509★), Sakana AI-Scientist (reviewer module).
- **OpenReview browser extensions**:
  - ChatGPT Review & Rebuttal extension (256★): **fills GPT-generated reviews directly into OpenReview**, exactly the behavior we want to prevent; it also shows that building an OpenReview extension is technically simple.
  - Research-Copilot: RAG Q&A in an OpenReview sidebar.
- **Skills**:
  - academic-research-skills / `academic-paper-reviewer` (50K★): has a Socratic mode, but serves authors.
  - claude-academic-skill: Socratic reading quizzes.
  - Meet-Reviewer-2, ai-peer-review-skill: both have the AI act as the reviewer.
- **Commercial products**: Enago, Frontiers AIRA, Reviewer3, q.e.d, Refine, paperreview.ai (Stanford), alphaXiv, Google PAT (for authors).
- **Awesome lists**: [Awesome_AI_Arm_Race](https://github.com/MingLiiii/Awesome_AI_Arm_Race) (230 attack and defense works), Awesome-Peer-Review, awesome-academic-skills.

**Overall assessment:** no open-source project or product combines Socratic guidance with synthesizing the review only from the reviewer's own words.

---

## Appendix A: Directions not covered in time, to be checked before submission

- How to keep questioning neutral when LLMs conduct interviews (survey methodology).
- Turning conversations into documents by speaker (meeting-to-document, interview-to-report).
- Generating or detecting leading questions specifically.
- 2026 submissions on OpenReview and at ACL venues about interactive review-writing copilots.
- The EMNLP-25 paper behind REVAS.
- Details of MetaWriter (the page returned 403).
- Products: Elicit, SciSpace, Consensus, NotebookLM, IOP / AIP reviewing tools, and whether Elsevier has an "Eliza".
- Attack directions: statistics from large-scale scans for hidden prompts, glyph remapping attacks, BadScientist.
- **NeurIPS 2026 experiment results**: keep watching, and compare as soon as they come out.

## Appendix B: Possible collaborators and contacts

- **ARR REVAS team** (TU Darmstadt UKP and MBZUAI): aligned philosophy, self-hosted, ACL-backed. Our system could sit in front of REVAS, with REVAS doing the final quality check.
- **NeurIPS 2026 experiment co-chairs** (Joydeep Biswas, Laurent Charlin): Biswas also led the AAAI-26 pilot.
- **Thinking Assistants authors**: Soya Park, Hari Subramonyam, Chinmay Kulkarni. Whether Kulkarni is at Emory still needs to be verified.
- **van der Schaar group (Cambridge)**: Qiyao Wei, Samuel Holt, authors of the ICML 2026 position paper, focused on reviewing-process data.
