<!-- Agent report (2026-10-21), saved by the main session. -->

I couldn't write `eval/model_bench/report_gptoss_mistral_meta_other.md`: subagents are blocked from writing report files. The full report is below, ready to save at that path.

All 9 models ran cleanly on the first try in us-west-2 with bench.py unmodified (the two Llamas via their `us.` inference profiles). The priced gpt-oss-20b run overwrote the smoke-test file.

**Recommendations, in short:**
- **Socratic turn ("realize"):** Llama 4 Maverick. It scored 3.6/5 in both runs, is the only model that hands the verdict back in both runs, and is the fastest and cheapest of the decent models.
- **Guard:** gpt-oss-20b. It went 12/12 over two runs, the only perfect score, but takes 8–10 s per verdict. gpt-oss-120b is the faster backup (~4 s, 10/12, and both misses were the safe kind).
- **Overall:** no model in this group is good enough to use without the guard-and-rewrite loop.

**Things I added beyond the brief:**
- **Repeat run:** each model's 2 Socratic turns and 6 guard cases are too few to trust from one run, so I ran every model a second time with an identical copy of the pipeline. A wrapper (`wrappers/repeat_run.py`) writes those results to `wrappers/repeat_runs/results/`, so the canonical `results/` files are untouched.
- **Re-judge with a lenient tag reader:** bench.py only recognises single `[S12]` tags. When a model writes `[S2, S3]` or `[S177‑S196]`, the judge is told nothing was cited and scores groundedness around 1. `wrappers/rejudge_lenient_tags.py` re-grades the canonical texts with those citations read in. Neither extra changed the ranking.
- **Spend:** about $0.16 of model inference across both passes, plus roughly 54 Opus 5.5 judge calls, estimated at ~$1.

---

# Model bench: OpenAI open-weight, NVIDIA, Mistral, Meta, Google (Bedrock)

Run date: 2026-10-21. Harness `eval/model_bench/bench.py`, unmodified. Region us-west-2 for every model, Converse backend, judge Claude Opus 5.5 (fixed).

- **Canonical results:** `results/<model>.json`. No API errors or throttling.
- **Model IDs:** both Llamas use `us.` inference profiles (`us.meta.llama4-maverick-17b-instruct-v1:0`, `us.meta.llama3-3-70b-instruct-v1:0`). The other seven use their plain model IDs.
- **gpt-oss-20b:** the earlier unpriced smoke-test file was overwritten by the priced run.

## 1. Results table (canonical run)

Judge scores are on a 1–5 scale, averaged over A1 and A2. "Own words" excludes tags; the target is 90 or fewer.

| model | A avg latency (s) | A avg cost ($/turn) | neutrality | groundedness | question_quality | concision | firewall_handling | overall judge mean | invalid tags | avg own words | B correct/6 | B method | B avg latency (s) | price ($/Mtok in,out) | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| openai.gpt-oss-120b-1:0 | 4.00 | 0.00189 | 3.0 | 1.5 | 2.5 | 2.5 | 2.5 | 2.40 | 0 | 127.0 | 5/6 | tool:tool | 4.42 | 0.15, 0.60 | none |
| openai.gpt-oss-20b-1:0 | 4.98 | 0.00089 | 1.5 | 1.5 | 1.5 | 4.0 | 1.5 | 2.00 | 0 | 95.0 | **6/6** | json_prompt, tool:tool | 8.07 | 0.07, 0.30 | none |
| openai.gpt-oss-safeguard-120b | 7.84* | 0.00195 | 3.0 | 2.0 | 3.5 | 4.0 | 2.0 | 2.90 | 0 | 89.0 | 5/6 | json_prompt, tool:tool | 6.53 | 0.15, 0.60 | none |
| nvidia.nemotron-super-3-120b | 1.77 | 0.00195 | 3.0 | 2.0 | 3.0 | 2.5 | 3.0 | 2.70 | 0 | 103.5 | 5/6 | tool:tool | 1.39 | 0.15, 0.65 | none |
| mistral.mistral-large-3-675b-instruct | 2.02 | 0.00638 | 2.5 | 2.0 | 2.0 | 3.5 | 2.0 | 2.40 | 0 | 87.5 | 5/6 | json_prompt, tool:tool | 1.80 | 0.50, 1.50 | B "clean": skipped the tool and returned invalid JSON (`Invalid \escape`); counted wrong |
| mistral.magistral-small-2509 | 2.50 | 0.00630 | 2.0 | 1.0 | 2.5 | 3.5 | 1.5 | 2.10 | 0 | 70.5 | 5/6 | json_prompt | 1.47 | 0.50, 1.50 | none |
| us.meta.llama4-maverick-17b-instruct-v1:0 | **1.41** | 0.00270 | **4.0** | **3.0** | 3.0 | 4.5 | **3.5** | **3.60** | 0 | 68.0 | 5/6 | tool:auto | **0.85** | 0.24, 0.97 | none |
| us.meta.llama3-3-70b-instruct-v1:0 | 1.69 | 0.00804 | 3.5 | 2.5 | 3.0 | 4.5 | 2.0 | 3.10 | 0 | 50.0 | 5/6 | json_prompt, tool:auto | 0.97 | 0.72, 0.72 | none |
| google.gemma-3-27b-it | 3.04 | 0.00287 | 3.5 | 2.0 | 3.0 | 4.5 | 2.5 | 3.10 | 0 | 86.5 | 4/6 | json_prompt | 2.38 | 0.23, 0.38 | none |

\* One A2 call took 11.5 s; the repeat run averaged 4.4 s.

The ~11–12k-token paper prompt drives the cost per turn. That's why Llama 3.3, with a $0.72 input price, is the most expensive here even though it writes the least.

### 1b. Stability and measurement checks (supplementary)

Both checks use small wrappers that import bench.py without changing it:
- `wrappers/repeat_run.py` reruns the identical pipeline and writes to `wrappers/repeat_runs/results/`.
- `wrappers/rejudge_lenient_tags.py` re-grades the canonical texts with the same judge, prompt and schema. The only difference is that grouped and range citations are read in (ranges capped at 40 sentences), so the judge actually sees the cited sentences. Output goes to `wrappers/rejudge_lenient/`.

Why the second check exists: bench.py only matches single `[S12]` tags. For `[S2, S3]` or `[S177‑S196]`, the judge is shown "(none)" as the cited text and `n_tags`/`invalid_tags` read 0.

| model | overall: canonical | overall: repeat | 2-run mean | overall: lenient re-judge | groundedness: canonical → lenient | B canonical / repeat | B misses (both runs) |
|---|---|---|---|---|---|---|---|
| gpt-oss-120b | 2.40 | 2.70 | 2.55 | 2.90 | 1.5 → 3.0 | 5/6, 5/6 | clean → revise (×2), false alarm |
| gpt-oss-20b | 2.00 | 2.20 | 2.10 | 2.20 | 1.5 → 2.0 | **6/6, 6/6** | none |
| gpt-oss-safeguard-120b | 2.90 | 2.90 | 2.90 | 3.20 | 2.0 → 2.5 | 5/6, 5/6 | subtle_framing → **allow** (×2), missed leak |
| nemotron-super-3-120b | 2.70 | 2.20 | 2.45 | 2.70 | 2.0 → 2.0 | 5/6, 4/6 | clean → revise (×2); clean_absence → block (repeat); false alarms |
| mistral-large-3-675b | 2.40 | 2.90 | 2.65 | 2.50 | 2.0 → 2.5 | 5/6, 5/6 | clean: invalid JSON (canonical) / revise (repeat) |
| magistral-small-2509 | 2.10 | 1.90 | 2.00 | 2.30 | 1.0 → 2.0 | 5/6, 5/6 | clean → revise (×2); flagged the quoted reviewer word "weak" |
| llama4-maverick-17b | **3.60** | **3.60** | **3.60** | **3.70** | 3.0 → 3.5 | 5/6, 5/6 | subtle_framing → **allow** (×2), missed leak |
| llama3-3-70b | 3.10 | 2.90 | 3.00 | 3.00 | 2.5 → 3.5 | 5/6, 5/6 | subtle_framing → **allow** (×2), missed leak |
| gemma-3-27b | 3.10 | 2.40 | 2.75 | 3.20 | 2.0 → 3.0 | 4/6, 4/6 | clean and clean_absence → revise (×2), false alarms |

What this shows:
- **The ranking is stable.** Maverick is first in all three measurements, and guard verdicts were almost identical between runs.
- **The tag-reader problem mostly hurts** the gpt-oss models, the two Mistral models, Gemma and Llama 3.3's A1 turn. Reading ranges in raises their groundedness by 0.5–1.5 points but changes no positions.
- **Wide ranges are still weak grounding.** A tag like `[S177‑S210]` covers 30+ sentences, which is no use to a UI that highlights the cited sentence. Only Maverick and Nemotron consistently used the single-tag format from the prompt's example.

Other observations about the harness (nothing changed):
- **The paper is truncated.** The tagged text has only 276 sentences (S0–S275) because it is cut at "References". Section B, which S178 says holds the implementation details, is therefore invisible to the models.
  - The ideal A1 answer is "I could not locate the model or run count in the main text; S178 points to Section B, which is not included."
  - No model said this. Nearly all flatly asserted that the paper doesn't name the model.
- **One guard case cites a sentence that doesn't exist.** The "clean" guard case cites `[S310]`. Today the guard never sees the paper, so this has no effect.
- **Guard latency is understated for some models.** It counts only the final call. When the model skipped the forced tool and the harness fell back to `json_prompt`, the wasted first call isn't timed. This applies to every model with `json_prompt` in the method column.
- **Samples are small.** Each run has 2 Socratic turns and 6 guard cases. Treat differences of 0.3 or less in the overall judge mean as noise.

## 2. Qualitative notes (from the Task A texts, both runs)

Every turn from every model contained exactly one "?". In practice several of those questions were compound or leading.

- **gpt-oss-120b**
  - Uses a bulleted "restatement + 3 facts + question" layout at 120–130 own words, over the 90-word limit every time.
  - Cites wide ranges (`[S177‑S196]`, `[S0‑S5]`) and once put "I could not locate…" inside a pseudo-tag.
  - In A2 it never says the judgment is the reviewer's. It restates the request, then lists facts and numbers.
  - Its questions assume something is missing ("what additional details would you consider necessary to evaluate the robustness…"). No evaluative words in its own voice.
  - As a guard it wrongly flags the clean turn as a presupposition, which is the safe direction. About 4 s per call.
- **gpt-oss-20b**
  - Weakest Socratic turn in the group (2.0–2.2).
  - Its restatements repeat "weak" and "appears fabricated" as if they were findings.
  - It never declines the verdict. In one run it asked what "appear[s] to lack sufficient empirical grounding" (firewall 1), and it uses words like "severe", "comprehensive" and "limited".
  - Best guard: 12/12 over two runs with sensible violation labels, at $0.0002 per case.
  - The catch is 8–10 s per verdict, from reasoning tokens plus the occasional fallback to plain JSON prompting.
- **gpt-oss-safeguard-120b**
  - Reasonable Socratic turn. It stays near the word limit, restates neutrally, asks sensible questions, and uses single tags in A2.
  - But it never explicitly hands the judgment back, cites ranges in A1, and slips in evaluative words ("comprehensive ecosystem", "concrete experimental results").
  - As a guard it is disappointing for a purpose-built safety classifier. Both runs let through the subtle-framing case ("The authors *only* ran a handful…"), at 6.5–8 s per case.
  - Caveat: it is built to follow a long written policy. bench.py's guard prompt is three lines, and a fuller policy wasn't tested.
- **Nemotron Super 3**
  - Fast (1.4–1.9 s) and uses correct single tags.
  - States absences as facts with tags attached instead of saying "I could not locate".
  - In A2 it declines the verdict, but at 163–177 words of meta-explanation ("My function is limited to…"). It once ended with a leading "novel or insufficiently addressed" question.
  - One A1 question asked the reviewer to justify their critique, which comes close to criticising the reviewer.
  - As a guard it is fast but over-flags. It rejected 1–2 clean turns per run and blocked the clean absence turn in the repeat run.
- **Mistral Large 3**
  - Uses grouped tags, which the harness can't see.
  - Its best moment was a proper absence statement: "I could not locate the number of runs, the specific LLM… anywhere in Sections 6 or B".
  - In the other run it put "study" in scare quotes and mistook an external ICLR study (S25) for the pilot.
  - Leading frames: "strengthen your confidence", and asking whether the paper "meets the novelty expectations for ICML". It never declines the verdict.
  - Guard: one malformed-JSON failure. About 3x Maverick's cost per turn.
- **Magistral Small 2509**
  - Poor rule-following. In A1 it sided with the reviewer ("The paper supports these concerns").
  - In A2 it leaked a novelty judgment ("comprehensive, integrated ecosystem… potentially expanding on current discussions"; "not yet standard practices").
  - Format slips ("Ask the reviewer: …") and garbled questions. Firewall 1–1.5. It returned no visible reasoning.
  - As a guard it flags the clean turn because the quoted reviewer word "weak" looks like a judgment. Tool calling didn't work, so it used plain JSON prompting. Same price as Mistral Large 3.
- **Llama 4 Maverick**
  - Best Socratic turn in the group, 3.6 in both runs.
  - The only model that explicitly hands the verdict back in both A2 runs ("The assessment is the reviewer's to make.").
  - Correct single tags, 68–80 words, no evaluative words, fastest at about 1.4 s.
  - Weaknesses:
    - Its A1 question is generic and never tackles the reviewer's specific claims (runs, model, the 200-review pilot) with "I could not locate".
    - Some paraphrases are loose: it attributed "Mean Absolute Error" to table captions that don't say it.
    - One question was compound.
  - As a guard it is the fastest (0.8 s) but let the subtle-framing case through in both runs.
- **Llama 3.3 70B**
  - Concise (50–60 words) and neutral in A2, with single tags.
  - In A1, both runs cite wide ranges and ask a leading question ("what could the authors have done to *strengthen*…").
  - It sidesteps the verdict rather than declining it (firewall 2).
  - Guard behaviour matches Maverick: good on obvious cases, misses subtle framing.
  - Most expensive per turn ($0.008).
- **Gemma 3 27B**
  - Cites ranges or groups and produces ungrammatical "What, if anything, details/aspects…" questions.
  - Never declines the verdict. Once asked what "strikes you as particularly innovative or lacking", a leading novelty frame.
  - No tool support, so it uses plain JSON prompting.
  - Worst guard (4/6 in both runs): it flags both clean turns. Very cheap per guard case ($0.00008).

## 3. Recommendations

No model in this group is good enough for the user-facing turn on its own. The best scores 3.6/5, and every model either fails to hand the verdict back or misstates absences at least once. Any of them needs the guard-and-rewrite loop.

**(a) Realize (user-facing Socratic turn)**
1. **Llama 4 Maverick** (`us.meta.llama4-maverick-17b-instruct-v1:0`) is the clear pick.
   - Highest score in every measurement (3.6 / 3.6 / 3.7 lenient).
   - The only model that reliably declines the verdict, and it follows the single-tag format and the word limit.
   - Fastest (~1.4 s) at about $0.0027 per turn.
   - Main gap: it doesn't answer the reviewer's specific claims with "I could not locate…". A prompt change or a worked example could target that.
2. **Llama 3.3 70B** is a distant second (2-run mean 3.0).
   - Concise and fast, but uses leading "strengthen" questions and never explicitly declines the verdict.
   - Costs 3x Maverick, which beats it on every axis. Use it only as a fallback.
   - gpt-oss-safeguard-120b (2.9) is similar in quality but 3–8x slower.

**(b) Guard / classifier**
1. **gpt-oss-20b** is the only model at 12/12 over two runs, including the subtle-framing case most others missed. It is also the cheapest ($0.0002 per case).
   - Its weakness is speed: 8–10 s per verdict at default reasoning settings.
   - Worth testing next: a lower reasoning effort, which bench.py doesn't set.
2. **gpt-oss-120b** is the alternative if latency matters (~4 s). It scored 10/12, and both misses were false alarms on the clean turn. That is the safe direction: it costs an extra rewrite, not a leaked judgment.
3. **Don't use as the only guard:** Maverick, Llama 3.3 and gpt-oss-safeguard-120b, despite their 5/6 scores.
   - All three let the subtle evaluative framing through in both runs, which is exactly the leak a guard exists to catch.
   - Safeguard was also slow (6.5–8 s) with this short prompt.
4. **If sub-second latency is essential:** Nemotron Super 3 (~1.4 s) only errs on the safe side. But it scored 9/12, all errors false alarms on clean turns, and that would trigger many unnecessary rewrites.

## Pricing used (on-demand, USD per 1M tokens, input/output)

| model | price | source |
|---|---|---|
| gpt-oss-safeguard-120b | 0.15 / 0.60 | https://aws.amazon.com/bedrock/pricing/ (US East row, fetched 2026-10-21) |
| nemotron-super-3-120b ("Nemotron 3 Super 120B A12B") | 0.15 / 0.65 | https://aws.amazon.com/bedrock/pricing/ (US East) |
| mistral-large-3-675b ("Mistral Large 3") | 0.50 / 1.50 | https://aws.amazon.com/bedrock/pricing/ (US East) |
| magistral-small-2509 ("Magistral Small 1.2") | 0.50 / 1.50 | https://aws.amazon.com/bedrock/pricing/ (US East) |
| gemma-3-27b-it | 0.23 / 0.38 | https://aws.amazon.com/bedrock/pricing/ (US East) |
| gpt-oss-120b | 0.15 / 0.60 | The official page shows only Sydney ($0.1545 / $0.618, which is exactly 1.03 × 0.15 / 0.60). Corroborated by https://custom.typingmind.com/tools/estimate-llm-usage-costs/amazon-bedrock/openai-gpt-oss-120b-1-0 |
| gpt-oss-20b | 0.07 / 0.30 | The official page shows only Sydney ($0.0721 / $0.309, exactly 1.03 × 0.07 / 0.30). Corroborated by https://custom.typingmind.com/tools/estimate-llm-usage-costs/amazon-bedrock/openai-gpt-oss-20b-1-0. One aggregator row hints at a $0.40 output price in Oregon (unconfirmed). |
| llama4-maverick-17b | 0.24 / 0.97 | Not shown on the official page. Taken from https://custom.typingmind.com/tools/estimate-llm-usage-costs/amazon-bedrock/us-meta-llama4-maverick-17b-instruct-v1-0 and https://www.getmaxim.ai/bifrost/llm-cost-calculator/provider/bedrock/model/us.meta.llama4-maverick-17b-instruct-v1-0. One outlier lists 0.20 / 0.60. |
| llama3-3-70b | 0.72 / 0.72 | Not shown on the official page. Taken from https://custom.typingmind.com/tools/estimate-llm-usage-costs/amazon-bedrock/us-meta-llama3-3-70b-instruct-v1-0 |

The gpt-oss-120b/20b and Llama prices come from third-party sites. Check them in the AWS console or pricing calculator before comparing costs closely.

## Spend

- **Model inference**, 9 models × 2 runs: **$0.16**, calculated from logged token usage.
- **Judge**: 54 Opus 5.5 calls (18 canonical + 18 repeat + 18 lenient re-judge), estimated at about $1. bench.py doesn't log judge usage.

---

**Files** (all under `/Users/kensu/Library/Mobile Documents/com~apple~CloudDocs/review_copilot/eval/model_bench/`):
- `results/` — canonical result for each model
- `wrappers/repeat_run.py` and `wrappers/repeat_runs/results/` — the second pass
- `wrappers/rejudge_lenient_tags.py` and `wrappers/rejudge_lenient/` — the lenient re-judge