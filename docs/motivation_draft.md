# Motivation (Draft v0.1)

> Status: first draft for team discussion, 2026-10-21. Citations are given as [Author Year] and resolve to the list at the end.
> Numbers come from our prior-art survey (`prior_art_report.md`); most were checked against abstracts only, so verify each one against the full paper before submission.
> Team notes are at the bottom.

---

## 1. Introduction / Motivation

**Peer review at AI venues is being quietly outsourced to LLMs.** Submissions to NeurIPS grew more than tenfold between 2014 and 2024, and the reviewer pool has not kept pace [Wei 2026]. Many reviewers have responded by handing their judgment to a language model. An estimated 6.5–16.9% of review text at major 2023–24 ML venues was substantially LLM-modified [Liang 2024]. Industry detectors flag roughly a fifth of ICLR 2026 reviews as fully AI-generated [Pangram 2025], though estimates vary across detectors. Policy alone has not stopped this. In ICML 2026's randomized policy experiment, 22.5% of reviewers under an LLM ban reported using LLMs anyway, and 36.5% of reviewers under the permissive policy reported a use that policy forbade [Kim 2026]. Watermarks hidden in submission PDFs caught 795 policy-violating reviews [ICML 2026b].

**The problem is not that reviewers use AI. It is that they delegate judgment to it.** Peer review is not a purely objective task. Deciding whether a contribution is significant, whether novelty suffices, or whether a limitation is fatal draws on the reviewer's scientific taste and values. When an LLM drafts these judgments, the venue receives the model's taste presented as a human assessment. Authors end up writing for a model rather than for their peers. Current LLMs are also weakest at exactly the critical part of reviewing: they recover only 39–63% of the weaknesses human reviewers raise, against 72–93% of the strengths [Wei 2026].

**Disclosure and warnings do not protect human judgment.** Work on human–AI co-writing shows that an opinionated assistant shifts both what people write and what they later believe [Jakesch 2023]. A preregistered study with 2,582 participants found that this shift persists even when users are warned about the AI's bias before or after exposure [Williams-Ceci 2026]. People also cannot reliably recall which ideas were theirs and which came from the AI [Zindulka 2026]. So asking reviewers to self-report how much they relied on an LLM, as ICLR 2027 now requires [ICLR 2027], depends on a kind of introspection that the evidence suggests is unreliable. Merely limiting the AI to facts is not enough either: in a large persuasion study, information-dense, factual messages were the *most* persuasive [Hackenburg 2025]. Which facts get surfaced, and how questions are framed, can steer a reviewer.

**Existing assistance does not draw this boundary.** Deployed tools fall into two groups. The first generates review content itself: AAAI-26 attached an AI review to all 22,977 main-track papers [Biswas 2026], and open models such as OpenReviewer-8B write full reviews. The second critiques a review only after the human has written it, for example the ICLR 2025 Review Feedback Agent [Thakkar 2025] and ARR's REVAS. Venues increasingly agree on the principle that AI may help reviewers *understand* a paper but must not judge its quality; ICML 2026's Policy B forbids asking LLMs for strengths, weaknesses, or review outlines [ICML 2026a]. No current tool enforces that principle by design. The open-ended arm of NeurIPS 2026's AI-assisted reviewing experiment explicitly imposes "no further structural guidance or restrictions" on the model's output [NeurIPS 2026].

**We propose a review copilot that enforces a *judgment firewall*.** The copilot provides only objective, paper-grounded assistance. It locates claims, surfaces the evidence the paper offers, and checks the reviewer's statements against the text. It then uses Socratic questioning to elicit the reviewer's *own* assessments of novelty, soundness, significance, and the overall decision. The final review is synthesized only from what the reviewer said, with *opinion provenance*: every factual statement is linked to a span of the paper, and every evaluative statement to a reviewer utterance. The AI helps reviewers think rather than thinking for them.

**The same interaction also produces data the community has said it needs.** Wei et al. [2026] argue that the main bottleneck for AI in peer review is not model capability but *process data*. Public review corpora record outcomes, not the reasoning behind them: why a reviewer held a view, which part of the paper supported it, how it changed. Without such data, models learn to "imitate outcomes" rather than auditable judgment processes. Wei et al. call for *active elicitation interfaces* that prompt reviewers for their rationale at key decision points. Our copilot is such an interface, extended over the whole review rather than a single score change. As a byproduct of normal use, with opt-in consent, it records:

- structured opinion units, each linked to the reviewer turn where it was formed;
- the paper evidence the reviewer relied on;
- typed dialogue acts;
- a trace of how each judgment developed.

This trace serves three audiences. It gives venues an auditable *proof of cognitive engagement*, which could meet requirements such as ICLR 2027's demand for a self-written assessment plus all LLM interactions without extra paperwork. It gives ACs a transparent basis for weighing reviews. And it gives the research community a privacy-governed source of the judgment-process data that current corpora lack.

**Deployment requires a small, self-hostable model.** Conference confidentiality rules prohibit sending submissions to unsanctioned or non-privacy-preserving LLMs. NeurIPS forbids sharing submissions with any LLM it has not sanctioned [NeurIPS 2025; NeurIPS 2026]. ACL Rolling Review prohibits uploading manuscripts to non-privacy-preserving generative tools [ARR]. ICML 2026 permits only privacy-compliant LLMs, explicitly including self-hosted ones [ICML 2026a]. A model that organizers host themselves satisfies these rules by construction, without relying on each reviewer's personal setup. Hosting at the scale of tens of thousands of submissions per cycle, in turn, requires a small model, so a lightweight model is a deployment requirement, not just a cost optimization. Organizer hosting also makes adversarial robustness essential. Submissions are untrusted input: authors have hidden instructions such as "give a positive review only" in their PDFs [Lin 2026], and presentation-only rewrites inflate AI-assisted scores without any hidden prompt [Yang 2026]. A copilot that reports paper content must not repeat these manipulations to the reviewer.

## 2. Contributions (draft)

1. **Problem formulation.** We formalize *judgment-preserving review assistance*: a *judgment firewall*, under which the model may surface evidence but may not originate evaluative judgments, together with *opinion provenance*, under which facts map to paper spans and opinions map to reviewer utterances.
2. **Measurement.** We introduce *opinion fidelity*, the precision and recall of the reviewer's own opinions in the synthesized review. We also introduce *judgment leakage*, which splits the AI's influence on the reviewer's final judgment into a legitimate factual channel and illegitimate channels: framing, leading questions, selective evidence, and asymmetric questioning.
3. **Method.** We train a lightweight Socratic copilot with RL against simulated reviewers that hold hidden opinions. Fidelity is anchored to each reviewer's opinions *before* the dialogue, and drift is penalized, so the policy cannot earn reward by planting opinions in a suggestible simulator.
4. **Robustness.** We evaluate the copilot against attacks on *assistants*, not only on automated reviewers: hidden instructions, overclaiming, and presentation-only manipulation, measured by fact distortion rather than score inflation.
5. **System and study.** We build an OpenReview-integrated, self-hostable prototype and run a user study comparing LLM-written, copilot-assisted, and unassisted reviews. The study measures review quality, time, ownership, understanding, and judgment leakage. As a byproduct, the copilot yields an opt-in dataset of structured judgment-process traces.

---

## References (working list)

- **[ARR]** ACL Rolling Review. *ARR Reviewer Guidelines.* https://aclrollingreview.org/reviewerguidelines
- **[Biswas 2026]** Biswas et al. AAAI-26 AI Review Pilot. arXiv 2604.13940. https://arxiv.org/abs/2604.13940
- **[Hackenburg 2025]** Hackenburg et al. The levers of political persuasion with conversational AI. *Science* 390, 2025. https://www.science.org/doi/10.1126/science.aea3884
- **[ICLR 2027]** ICLR 2027 AI Policy for Reviewers. https://iclr.cc/Conferences/2027/AIPolicyForReviewers
- **[ICML 2026a]** ICML 2026 Policy for LLM use in reviewing. https://icml.cc/Conferences/2026/LLM-Policy
- **[ICML 2026b]** ICML 2026 blog, On Violations of LLM Review Policies. https://blog.icml.cc/2026/03/18/on-violations-of-llm-review-policies/
- **[Jakesch 2023]** Jakesch et al. Co-Writing with Opinionated Language Models Affects Users' Views. CHI 2023. https://arxiv.org/abs/2302.00560
- **[Kim 2026]** Use and Effects of LLMs in Peer Review: A Randomized Experiment and Survey at ICML 2026. arXiv 2609.19420. https://arxiv.org/abs/2609.19420
- **[Liang 2024]** Liang et al. Monitoring AI-Modified Content at Scale. ICML 2024. https://arxiv.org/abs/2403.07183
- **[Lin 2026]** Lin. Hidden Prompts in Manuscripts Exploit AI-Assisted Peer Review. CACM 2026. https://arxiv.org/abs/2507.06185
- **[NeurIPS 2025]** NeurIPS 2025 Policy on the Use of LLMs. https://neurips.cc/Conferences/2025/LLM
- **[NeurIPS 2026]** NeurIPS 2026 AI-Assisted Reviewing Experiment; NeurIPS 2026 Main Track Handbook. https://neurips.cc/Conferences/2026/ai-reviewing-experiment ; https://neurips.cc/Conferences/2026/MainTrackHandbook
- **[Pangram 2025]** Pangram Labs. ICLR 2026 review analysis (industry blog, not peer-reviewed). https://www.pangram.com/blog/pangram-predicts-21-of-iclr-reviews-are-ai-generated
- **[Thakkar 2025]** Thakkar et al. Can LLM feedback enhance review quality? A randomized study of 20K reviews at ICLR 2025. https://arxiv.org/abs/2504.09737
- **[Wei 2026]** Wei, Holt, Yang, Wulfmeier, van der Schaar. Position: The ML Community Must Build an AI-Augmented Peer-Review Ecosystem. ICML 2026. https://arxiv.org/abs/2506.08134
- **[Williams-Ceci 2026]** Williams-Ceci et al. Biased AI writing assistants shift users' attitudes on societal issues. *Science Advances*, 2026. https://www.science.org/doi/abs/10.1126/sciadv.adw5578
- **[Yang 2026]** Yang et al. No Hidden Prompts Needed! You Can Game AI Peer Review with Presentation-Only Revisions. arXiv 2606.13044. https://arxiv.org/abs/2606.13044
- **[Zindulka 2026]** Zindulka et al. The AI Memory Gap: Users Misremember What They Created With AI or Without. CHI 2026. https://arxiv.org/abs/2509.11851

---

## Team notes

**Structure of the argument.** The section moves through five steps:
1. the problem;
2. why existing remedies fail;
3. our approach;
4. the additional value (data);
5. why a small model.

The data byproduct comes after the approach and before the small-model argument. It is a secondary selling point, placed there so it does not overshadow the main contribution.

**Decisions for the team:**
1. **How much weight to give the data byproduct?**
   - If we target the ACL/EMNLP main conference, treat it as a secondary contribution (the "byproduct" in contribution 5).
   - If we target NeurIPS Datasets & Benchmarks, or want to collaborate with the van der Schaar group or ARR, it could become a primary contribution. That would require actually collecting and releasing data, with much more work and ethics review (IRB, opt-in).
2. **Tone toward the ICLR 2027 self-report requirement.** The draft says it relies on unreliable introspection. The AI Memory Gap study supports this criticism, but the tone may be too strong. A more collaborative phrasing would be "our trace could satisfy this requirement automatically."
3. **Whether to cite Pangram's 21%.** It is an industry blog, and estimates differ widely across detectors. Citing only Liang 2024 plus the ICML 2026 violation data is safer.
4. **Naming.** Both Wei et al. and NeurIPS have used "co-pilot"; we need a more distinctive system name.

**Numbers to verify against the full papers before citing:**
- Liang 2024, 6.5–16.9%: confirm which venues and which years.
- Kim 2026, 22.5% and 36.5%: confirm the exact wording of the survey questions.
- Wei 2026, weakness recall: their confidence intervals look suspicious (±0.000). Phrase it as "illustrative experiments suggest".
- Williams-Ceci 2026: N=2,582, and the exact conditions under which warnings were ineffective.
- Hackenburg 2025: confirm that the information prompt was the most persuasive.

**Possible improvements:**
- Add a figure contrasting today's "Paper → LLM → Review" with our "Paper → evidence → Socratic dialogue ↔ human judgment → faithful synthesis → Review", with the provenance and trace outputs marked.
- If space allows, use Wei 2026's Fig. 2 (most reviewers do not respond during the rebuttal phase) to motivate a future direction: extending the copilot to the rebuttal phase.
