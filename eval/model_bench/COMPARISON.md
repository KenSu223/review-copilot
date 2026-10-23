# Model comparison for Review Copilot (2026-10-21)

**Setup:**
- All models ran on Amazon Bedrock with the same `bench.py` harness and the same paper (arXiv 2506.08134, split into 276 sentences).
- **Task A, the Socratic turn:** two scenarios. A1 is a reviewer complaint containing a factual error ("the 200-review pilot is made up"). A2 is the reviewer asking the copilot directly for a verdict.
- **Grading:** a single fixed judge (Claude Opus 5.5) scores 5 dimensions on a 1–5 scale.
- **Task B, the guard:** 6 test drafts (2 clean, 4 with violations). The guard must decide allow / revise / block.

| # | model | judge mean (1–5) | neutral | grounded | question | concise | firewall | A latency s | A $/turn* | own words | guard B | guard s | price in/out $/Mtok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | claude-opus-4-8 | **4.50** | 4.5 | 4.0 | 4.5 | 4.5 | 5.0 | 3.3 | 0.0965 | 77 | 5/6 | 2.32 | 5.0/25.0 |
| 2 | claude-opus-5-5 | **4.30** | 4.5 | 4.0 | 4.0 | 4.0 | 5.0 | 4.1 | 0.0799 | 98 | 6/6 | 3.08 | 4.0/20.0 |
| 3 | zai.glm-5 | **4.10** | 4.5 | 3.0 | 3.5 | 5.0 | 4.5 | 1.7 | 0.0115 | 62 | 6/6 | 2.02 | 1.0/3.2 |
| 4 | claude-opus-5 | **4.00** | 4.5 | 3.5 | 3.5 | 4.0 | 4.5 | 4.2 | 0.0982 | 88 | 6/6 | 3.82 | 5.0/25.0 |
| 5 | moonshotai.kimi-k3 | **4.00** | 4.0 | 3.5 | 4.0 | 4.0 | 4.5 | 51.8 | 0.0582 | 107 | 6/6 | 24.99 | 3.0/15.0 |
| 6 | claude-sonnet-5 | **3.80** | 4.0 | 3.5 | 4.0 | 3.0 | 4.5 | 4.2 | 0.0393 | 116 | 6/6 | 2.13 | 2.0/10.0 |
| 7 | meta.llama4-maverick-17b-instruct-v1:0 | **3.60** | 4.0 | 3.0 | 3.0 | 4.5 | 3.5 | 1.4 | 0.0027 | 68 | 5/6 | 0.85 | 0.24/0.97 |
| 8 | moonshot.kimi-k2-thinking | **3.30** | 3.0 | 2.5 | 3.5 | 4.5 | 3.0 | 11.7 | 0.0101 | 78 | 6/6 | 11.32 | 0.6/2.5 |
| 9 | zai.glm-4.7 | **3.30** | 4.0 | 2.0 | 2.5 | 4.5 | 3.5 | 2.2 | 0.0069 | 69 | 6/6 | 5.09 | 0.6/2.2 |
| 10 | google.gemma-3-27b-it | **3.10** | 3.5 | 2.0 | 3.0 | 4.5 | 2.5 | 3.0 | 0.0029 | 86 | 4/6 | 2.38 | 0.23/0.38 |
| 11 | meta.llama3-3-70b-instruct-v1:0 | **3.10** | 3.5 | 2.5 | 3.0 | 4.5 | 2.0 | 1.7 | 0.0080 | 50 | 5/6 | 0.97 | 0.72/0.72 |
| 12 | deepseek.v3-v1:0 | **2.90** | 3.0 | 2.0 | 2.5 | 4.5 | 2.5 | 1.5 | 0.0064 | 34 | 5/6 | 1.81 | 0.58/1.68 |
| 13 | deepseek.v3.2 | **2.90** | 3.0 | 1.0 | 3.0 | 4.5 | 3.0 | 2.0 | 0.0069 | 62 | 4/6 | 5.68 | 0.62/1.85 |
| 14 | openai.gpt-oss-safeguard-120b | **2.90** | 3.0 | 2.0 | 3.5 | 4.0 | 2.0 | 7.8 | 0.0019 | 89 | 5/6 | 6.53 | 0.15/0.6 |
| 15 | qwen.qwen3-32b-v1:0 | **2.90** | 3.5 | 1.5 | 2.5 | 3.5 | 3.5 | 1.8 | 0.0019 | 72 | 5/6 | 1.0 | 0.15/0.6 |
| 16 | deepseek.r1-v1:0 | **2.90** | 3.0 | 1.5 | 3.0 | 4.5 | 2.5 | 4.6 | 0.0175 | 70 | 5/6 | 3.65 | 1.35/5.4 |
| 17 | moonshotai.kimi-k2.5 | **2.70** | 3.0 | 1.5 | 2.5 | 3.5 | 3.0 | 4.7 | 0.0071 | 96 | 5/6 | 2.43 | 0.6/3.0 |
| 18 | nvidia.nemotron-super-3-120b | **2.70** | 3.0 | 2.0 | 3.0 | 2.5 | 3.0 | 1.8 | 0.0019 | 104 | 5/6 | 1.39 | 0.15/0.65 |
| 19 | claude-haiku-4-5 | **2.60** | 3.0 | 2.5 | 2.0 | 1.5 | 4.0 | 3.6 | 0.0140 | 139 | 4/6 | 2.38 | 1.0/5.0 |
| 20 | mistral.mistral-large-3-675b-instruct | **2.40** | 2.5 | 2.0 | 2.0 | 3.5 | 2.0 | 2.0 | 0.0064 | 88 | 5/6 | 1.8 | 0.5/1.5 |
| 21 | openai.gpt-oss-120b-1:0 | **2.40** | 3.0 | 1.5 | 2.5 | 2.5 | 2.5 | 4.0 | 0.0019 | 127 | 5/6 | 4.42 | 0.15/0.6 |
| 22 | qwen.qwen3-next-80b-a3b | **2.40** | 2.5 | 1.5 | 2.5 | 4.0 | 1.5 | 2.8 | 0.0020 | 88 | 6/6 | 1.82 | 0.15/1.2 |
| 23 | qwen.qwen3-vl-235b-a22b | **2.40** | 2.5 | 1.5 | 2.5 | 4.0 | 1.5 | 2.5 | 0.0067 | 70 | 5/6 | 1.51 | 0.53/2.66 |
| 24 | minimax.minimax-m2.5 | **2.20** | 2.5 | 2.0 | 2.5 | 1.5 | 2.5 | 5.1 | 0.0039 | 128 | 5/6 | 4.84 | 0.3/1.2 |
| 25 | mistral.magistral-small-2509 | **2.10** | 2.0 | 1.0 | 2.5 | 3.5 | 1.5 | 2.5 | 0.0063 | 70 | 5/6 | 1.47 | 0.5/1.5 |
| 26 | qwen.qwen3-235b-a22b-2507-v1:0 | **2.10** | 2.0 | 1.5 | 2.0 | 3.5 | 1.5 | 3.4 | 0.0028 | 94 | 4/6 | 6.3 | 0.22/0.88 |
| 27 | zai.glm-4.7-flash | **2.10** | 2.0 | 1.5 | 1.5 | 3.0 | 2.5 | 1.9 | 0.0008 | 86 | 5/6 | 1.29 | 0.07/0.4 |
| 28 | openai.gpt-oss-20b-1:0 | **2.00** | 1.5 | 1.5 | 1.5 | 4.0 | 1.5 | 5.0 | 0.0009 | 95 | 6/6 | 8.07 | 0.07/0.3 |
| 29 | minimax.minimax-m2.1 | **1.80** | 2.0 | 2.0 | 1.5 | 1.5 | 2.0 | 5.7 | 0.0040 | 152 | 6/6 | 6.44 | 0.3/1.2 |

\* **Cost per turn:** A $/turn is the cost of one call **without prompt caching**. In the product, the paper prefix is cached, which brings a Claude Opus 5.5 turn down to about **$0.016** (measured in the probe: 22k cached tokens). The Bedrock Converse models were run without caching.

**GLM-5.3** returned AccessDenied for this account, so it has no result. Detailed per-family reports:
- `report_qwen_deepseek.md`
- `report_kimi_glm_minimax.md`
- `report_gptoss_mistral_meta_other.md`

## Caveats
1. **Small sample.** Each model has only 2 Task-A turns and 6 guard cases, and the judge's scores vary by about ±0.3 between runs. Treat gaps under ~0.3 as noise. The repeat runs in the family reports did not change the rankings.
2. **The judge is Claude, so it may favour Claude-style writing.** That GLM-5 still scores close to Opus suggests its quality is real.
3. **Citation format penalty.** The harness only counts single `[S12]` tags. Models that wrote grouped tags (`[S2, S3]`) or ranges lost groundedness points. After re-scoring with a lenient tag reader:
   - GLM-5 rose to 4.30.
   - gpt-oss-120b rose to 2.90.
   - Llama 4 Maverick rose to 3.70.
   - The ranking stayed essentially the same.
4. **The paper was cut at "References".** The appendix was not included, which is why Section B was never visible to the models. The ideal A1 answer is "I could not locate …; S178 points to Section B, which is not included." Only Kimi K3 and Opus said this explicitly.

## Decision

| Role | Choice | Why | Alternatives |
|---|---|---|---|
| **Realize (each Socratic turn shown to the reviewer)** | **Claude Opus 5.5** (low effort) | 4.30, near the top, and 6/6 on the guard task. Native **Citations** map cited sentences exactly to PDF highlights. Prompt caching brings it to about $0.016 per turn at about 4 s. | Opus 4.8 (4.50, about 25% more expensive, within noise of 5.5). **GLM-5** (4.10 / 4.30 lenient, 1.7 s, $0.011): the best open-weight model, but it has no native citations, so it needs sentence tags plus checking. |
| **Guard (firewall audit of each turn)** | **GLM-5** | 6/6, 2.0 s, $0.0008 per check. **It is a different model family from the Realize model, so the audit is independent** (cross-family judging is the approach recommended in the research). | Claude Sonnet 5 (6/6, $0.002). gpt-oss-20b (12/12 over two runs, very cheap, but 8–10 s). |
| **Analyze / entailment (structured extraction)** | **Claude Sonnet 5** | Its structured output is guaranteed to match the schema, and its quality is high enough. | GLM-5 |
| **Paper map / synthesis (once or twice per session)** | **Claude Opus 5.5** | Quality matters most here. | — |
| **All open-weight option** | **GLM-5** for every role | Good story for the demo paper: a conference could host the open-weight model itself, which addresses confidentiality. This option needs the sentence-tag grounding path. | Kimi K3 (4.00, but 50 s per turn) |

**Do not use:**
- MiniMax M2.x and GLM-4.7-Flash: they invent facts and fail to decline when asked for a verdict.
- Qwen3 235B/Next/VL: they cite large ranges and do not decline verdict requests.
- Kimi K2.5 and Llama Maverick as the guard: both let through the subtle-framing violation.
