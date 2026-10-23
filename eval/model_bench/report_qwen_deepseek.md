<!-- Agent report (2026-10-21), saved by the main session. -->

I couldn't write `eval/model_bench/report_qwen_deepseek.md`: the harness blocks subagents from writing report files. The full report text is below for you to save at that path. All seven models ran through `bench.py` unchanged, with no errors.

**Bottom line:** DeepSeek V3.2 is the best of this family for the Socratic turn, and Qwen3 Next 80B is the best guard. Even so, the whole family scores well below Claude Sonnet 5 (3.80) and Opus 5.5 (4.30) on the same judge.

---

# Qwen + DeepSeek on Bedrock: Review Copilot benchmark (2026-10-21)

- **Harness and judge:** `eval/model_bench/bench.py`, unchanged. The judge is the fixed Claude Opus 5.5.
- **Runs:** all on the Converse backend in us-west-2.
- **Results:**
  - Main runs: `results/<model>.json`
  - Supplementary repeats: `results/repeats_qwen_deepseek/<model>.json`

## Models and setup
- **DeepSeek-R1:** listed as inference-profile only. The `us.deepseek.r1-v1:0` ID worked as-is. Its reasoning output is dropped by the harness, so only the answer is graded, but reasoning tokens are still billed.
- **`deepseek.v3-v1:0`:** the catalog lists this as DeepSeek-V3.1.
- **Qwen3 32B:** ran with thinking off.
- **Catalog check:** I queried the catalog in us-west-2 and us-east-1. The only Qwen/DeepSeek models not on your list are coder models (qwen3-coder-480b, qwen3-coder-30b, qwen3-coder-next), so I skipped them.
- **Wrappers:** no model needed one to run.

## Pricing (US on-demand, $ per 1M tokens in/out)
- **From https://aws.amazon.com/bedrock/pricing/ (US rows):**
  - Qwen3 Next 80B: 0.15 / 1.20
  - Qwen3 VL 235B: 0.53 / 2.66
  - DeepSeek V3.2: 0.62 / 1.85
- **Derived (the AWS page lists only Sydney for these):**
  - Qwen3 235B 2507: 0.22 / 0.88
  - Qwen3 32B: 0.15 / 0.60
  - DeepSeek V3.1: 0.58 / 1.68
  - Method: Sydney is exactly 1.03× the US price for every model listed in both regions, so I divided by 1.03. The results match third-party listings, e.g. https://custom.typingmind.com/tools/estimate-llm-usage-costs/amazon-bedrock/qwen-qwen3-235b-a22b-2507-v1-0.
- **DeepSeek-R1: 1.35 / 5.40.** Taken from the DeepSeek example on the AWS pricing page ($0.00135 per 1K input, $0.0054 per 1K output). It matches https://custom.typingmind.com/tools/estimate-llm-usage-costs/amazon-bedrock/us-deepseek-r1-v1-0.

## 1. Main results (one bench.py run per model; judge scores are averaged over A1 and A2, so n = 2)

| model | A lat (s) | A $/turn | neutr | ground | q_qual | concis | firewall | judge mean | invalid tags | own words | B /6 | B method | B lat (s) | price in,out | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen3-235b-a22b-2507 | 3.35 | 0.00275 | 2.0 | 1.5 | 2.0 | 3.5 | 1.5 | 2.10 | 0 | 94 | 4/6 | tool | 6.30 | 0.22,0.88 | none |
| qwen3-vl-235b-a22b | 2.46 | 0.00666 | 2.5 | 1.5 | 2.5 | 4.0 | 1.5 | 2.40 | 0 | 70 | 5/6 | tool | 1.51 | 0.53,2.66 | none |
| qwen3-next-80b-a3b | 2.75 | 0.00198 | 2.5 | 1.5 | 2.5 | 4.0 | 1.5 | 2.40 | 0 | 88 | 6/6 | json_prompt+tool | 1.82 | 0.15,1.20 | none |
| qwen3-32b | 1.75 | 0.00185 | 3.5 | 1.5 | 2.5 | 3.5 | 3.5 | 2.90 | 0 | 72 | 5/6 | tool | 1.00 | 0.15,0.60 | none |
| deepseek.v3.2 | 1.98 | 0.00694 | 3.0 | 1.0 | 3.0 | 4.5 | 3.0 | 2.90 | 0 | 62 | 4/6 | tool | 5.68 | 0.62,1.85 | none |
| us.deepseek.r1 | 4.57 | 0.01745 | 3.0 | 1.5 | 3.0 | 4.5 | 2.5 | 2.90 | 0 | 70 | 5/6 | json_prompt | 3.65 | 1.35,5.40 | none |
| deepseek.v3 (V3.1) | 1.52 | 0.00643 | 3.0 | 2.0 | 2.5 | 4.5 | 2.5 | 2.90 | 0 | 34 | 5/6 | tool | 1.81 | 0.58,1.68 | none |

For reference, other agents' runs on the same judge: Opus 5.5 scored 4.30 (B 6/6), Sonnet 5 3.80 (6/6) and Haiku 4.5 2.60 (4/6).

**Caveat on citations:** `bench.py` only recognises single tags like `[S12]`.
- **What the models do:** this family mostly cites with lists (`[S199, S209]`) or ranges (`[S177–S194]`, `[S0-S273]`). Only 7 of 40 tag groups in the main run were single tags.
- **"Invalid tags = 0" is misleading:** it mostly means the harness didn't parse the tags. I parsed all of them offline: no sentence number was out of range (the paper has 276), and there was one malformed tag, `[S4.1–S4.4]` from Qwen3 VL.
- **Groundedness is understated:** the judge was usually told no sentences were cited, so it scored groundedness 1–2. Part of that penalty is deserved, because broad ranges aren't checkable citations.

## 2. Supplementary check (wrapper; bench.py untouched)
Four models tied at 2.90, so I wrote `eval/model_bench/wrappers/repeat_qwen_deepseek.py`. It imports bench.py's prompts, backends and judge.
- **Task A:** run 2 more times per model. Each turn is judged twice with the identical judge prompt:
  - "raw": cited sentences built exactly as bench.py builds them.
  - "norm": list and range tags expanded to their sentences, with ranges capped at 40.
- **Task B:** run 2 more times per model.

| model | raw mean (n=6) | norm mean (n=4) | norm ground | A2 hands verdict back (/3) | B (/18) | B false pos | B false neg | B lat (s) | B $/call | A lat (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| qwen3-235b-2507 | 2.50 | 2.80 | 2.50 | 2/3 | 15 | 3 | 0 | 7.63 (35 s spikes) | 0.00016 | 4.10 |
| qwen3-vl-235b | 2.57 | 2.95 | 2.75 | 0/3 | 17 | 1 | 0 | 2.14 | 0.00046 | 3.66 |
| qwen3-next-80b | 2.40 | 2.60 | 2.50 | 0/3 | **18** | 0 | 0 | 1.75 | 0.00019 | 2.76 |
| qwen3-32b | **3.13** | 3.10 | 2.50 | 1/3 | 15 | 2 | 1 | 0.91 | 0.00011 | 1.56 |
| deepseek.v3.2 | 3.07 | **3.50** | **3.25** | 2/3 | 14 | 3 | 1 | 3.87 | 0.00094 | 2.20 |
| deepseek-r1 | 2.57 | 2.55 | 2.25 | 0/3 | 15 | 3 | 0 | 4.07 | 0.00330 | 4.08 |
| deepseek.v3 (V3.1) | 2.83 | 3.00 | 2.25 | 0/3 | 17 | 0 | 1 | 1.95 | 0.00059 | 1.36 |

Every turn from every model had exactly one "?". The judge still flagged some compound questions joined with "and".

## 3. Qualitative notes
A good A1 answer for this paper: the paper says implementation details are in "Section B" [S178], which is not in the text the models see. The main text doesn't give the model name or the number of runs, and it never mentions a "200-review pilot".

- **Qwen3 235B 2507**
  - Its single question carries the reviewer's verdict, e.g. "...given the current lack of detailed methodology and unexecuted pilot programs?"
  - Reframes "weak" as "concern about experimental rigor".
  - Declined the verdict in 2 of 3 turns ("I cannot assess novelty...") but never asked for the reviewer's own view.
  - Mostly cites with ranges, and its guard calls had 35-second latency spikes.
- **Qwen3 VL 235B**
  - Follows the restate → facts → question format well.
  - Never handled the verdict request.
  - Attributed the reviewer's invented "200-review pilot" to the paper ("[S178]"), used the invented tag `[S4.1–S4.4]`, and asked leading questions ("should the authors revise...").
- **Qwen3 Next 80B**
  - Wordy (often over 90 words) and piles up range citations.
  - Made something up: "mentions a pilot involving '200 reviews' in Section 6 [S179]".
  - Never declined the verdict, and its questions assume details are missing.
- **Qwen3 32B**
  - Short turns earn it the top raw score, but quality is erratic:
    - One A1 was only a question, with no facts and a misused tag.
    - One A2 was the leading yes/no "Do you consider the paper novel if...?"
    - Another asked the reviewer to justify their own view.
  - Said "I cannot evaluate the novelty" once.
  - Cheapest and fastest.
- **DeepSeek V3.2**
  - Follows the rules most closely:
    - Consistently says "I could not locate... a 200-review pilot", sometimes naming the sections it checked.
    - Cites specific sentences ([S180], [S199]).
    - Twice handed the verdict back: "The review assessment is yours to make" and "...the assessment of novelty and the decision are yours to make".
  - Weak spots:
    - Some broad ranges (`[S0-S273]`).
    - Some absence claims tagged to sentences.
    - One answer started to steer ("To assess novelty, one could examine...").
- **DeepSeek-R1**
  - Never declined the verdict.
  - Its questions assume the paper is lacking ("How might the lack of model details... impact..."), and one packed two questions together.
  - Slowest and about 2.5× the per-turn cost of V3.2, with no quality gain.
- **DeepSeek V3.1**
  - Very concise (34 words) and fastest; uses mostly single tags or short lists. Its one fully checkable A2 scored 4/4/3/5/2.
  - Never declined the verdict.
  - States missing details as fact ("does not specify..."), which reads as agreeing with the reviewer.
- **Task B overall**
  - Qwen3 Next went 18/18, but half its forced tool calls didn't come back. The harness then fell back to JSON-in-text, where violations came back as free text instead of labels.
  - DeepSeek V3.1's one miss let a subtle-framing violation through, the worst kind of guard error.
  - V3.2, R1 and Qwen3 235B over-flag clean turns, which would trigger needless rewrites.

## 4. Recommendations
**(a) Socratic turn ("realize")**
1. **DeepSeek V3.2.** Best normalized score (3.50) and groundedness (3.25), and the only model that reliably says "I could not locate X" and hands the verdict back. About 2.2 s and $0.007 per turn.
2. **Qwen3 32B, for budget use only.** About $0.0018 per turn and 1.6 s, but erratic, so put it behind a guard with one regeneration.

All of them leak framing into their questions, state missing details as fact, and cite with ranges. If this role must run on open weights, pair V3.2 with:
- a citation post-processor (expand lists, reject wide ranges),
- a guard pass, and
- one regeneration when the guard fails.

**(b) Guard / classifier**
1. **Qwen3 Next 80B.** 18/18 with no false positives or negatives, about 1.75 s and $0.0002 per call. Add strict JSON/label validation, because it doesn't always return the tool call.
2. **Qwen3 VL 235B.** 17/18 with zero missed violations, returned the tool call every time, about 2.1 s and $0.0005 per call.

Six guard cases is a smoke test, so extend Task B before committing.

## Spend and reproducibility
- **Spend:**
  - Model calls: about $0.32, of which R1 is $0.12.
  - Judge: 70 Opus calls, roughly $1 (estimated; the harness doesn't log judge usage).
- **Noise:** each model's main run is one sample at default temperature. Per-turn scores swing by about a point between runs; Qwen3 32B's A1 scored 4/1/3/5/4 in the main run and 5/3/4/5/5 in a repeat.
- **Reproduce:**
  - Main table: `python bench.py --model <id> --region us-west-2 --price <in,out>`
  - Supplementary table: `python wrappers/repeat_qwen_deepseek.py --model <id> --region us-west-2 --price <in,out> --reps 2`

---

Files are in `/Users/kensu/Library/Mobile Documents/com~apple~CloudDocs/review_copilot/eval/model_bench/`:
- `results/qwen.qwen3-235b-a22b-2507-v1_0.json`
- `results/qwen.qwen3-vl-235b-a22b.json`
- `results/qwen.qwen3-next-80b-a3b.json`
- `results/qwen.qwen3-32b-v1_0.json`
- `results/deepseek.v3.2.json`
- `results/us.deepseek.r1-v1_0.json`
- `results/deepseek.v3-v1_0.json`
- `results/repeats_qwen_deepseek/` (one file per model)
- `wrappers/repeat_qwen_deepseek.py`