<!-- Agent report (2026-10-21), saved by the main session. -->

I couldn't create `eval/model_bench/report_kimi_glm_minimax.md`: the environment blocks report files from subagents, and I didn't route around that. The full report is below, ready to save at that path. The benchmark itself is done: 8 of the 9 models ran cleanly, and GLM-5.3 is blocked for this account.

---

# Model bench: Moonshot Kimi, Z.AI GLM, MiniMax on Bedrock

Date: 2026-10-21. Harness: `eval/model_bench/bench.py` (not modified). Region: us-west-2, Converse API. Judge: Claude Opus 5.5 (fixed). Raw results: `eval/model_bench/results/<model>.json`.

## 1. Results (harness numbers)

Judge scores are averaged over A1 and A2. "Invalid tags" counts tags whose number is 276 or higher; the paper has 276 tagged sentences. In the B method column, `tool:tool` means the model made the required tool call, so its output was checked against the schema. `json_prompt` means it skipped the tool and the harness pulled JSON out of free text.

| model | A lat (s) | A $/turn | neut | grnd | q_qual | conc | firewall | judge mean | invalid tags | own words | B /6 | B method | B lat (s) | price $/Mtok in,out | errors |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **zai.glm-5** | **1.72** | 0.01147 | **4.5** | 3.0 | 3.5 | **5.0** | **4.5** | **4.10** | 0 | **62** | 6/6 | tool:tool | 2.02 | 1.00, 3.20 | 0 |
| global.moonshotai.kimi-k3 | 51.77 | 0.05816 | 4.0 | **3.5** | **4.0** | 4.0 | **4.5** | 4.00 | 0 | 107 | 6/6 | tool:tool | 24.99 | 3.00, 15.00 (Global CRIS) | 0 |
| moonshot.kimi-k2-thinking | 11.74 | 0.01011 | 3.0 | 2.5 | 3.5 | 4.5 | 3.0 | 3.30 | 0 | 78 | 6/6 | json_prompt, tool:tool | 11.32 | 0.60, 2.50 | 0 |
| zai.glm-4.7 | 2.25 | 0.00692 | 4.0 | 2.0 | 2.5 | 4.5 | 3.5 | 3.30 | 0 | 69 | 6/6 | json_prompt, tool:tool | 5.09 | 0.60, 2.20 | 0 |
| moonshotai.kimi-k2.5 | 4.68 | 0.00706 | 3.0 | 1.5 | 2.5 | 3.5 | 3.0 | 2.70 | 0 | 96 | 5/6 | tool:tool | 2.43 | 0.60, 3.00 | 0 |
| minimax.minimax-m2.5 | 5.11 | 0.00391 | 2.5 | 2.0 | 2.5 | 1.5 | 2.5 | 2.20 | 0 | 128 | 5/6 | tool:tool | 4.84 | 0.30, 1.20 | 0 |
| zai.glm-4.7-flash | 1.93 | **0.00084** | 2.0 | 1.5 | 1.5 | 3.0 | 2.5 | 2.10 | 0 | 86 | 5/6 | tool:tool | **1.29** | 0.07, 0.40 | 0 |
| minimax.minimax-m2.1 | 5.72 | 0.00396 | 2.0 | 2.0 | 1.5 | 1.5 | 2.0 | 1.80 | 0 | 152 | 6/6 | tool:tool | 6.44 | 0.30, 1.20 | 0 |
| zai.glm-5.3 | - | - | - | - | - | - | - | - | - | - | n/a | - | - | 1.68, 5.28 | 8 (all calls) |

**GLM-5.3 did not run.** Every call returned "AccessDeniedException: zai.glm-5.3 is not available for this account ... contact AWS Sales". I tried `global.zai.glm-5.3` and `us.zai.glm-5.3` in both us-west-2 and us-east-1, and both profiles are listed as active. It is an account-level block, not a model-ID or region problem. Its result file `results/global.zai.glm-5.3.json` shows "0/6", but that is a non-result, not a score.

Kimi K3 worked through `global.moonshotai.kimi-k3`, the cheaper global profile. All other models ran on their plain model IDs.

### Extra metrics (computed outside the harness)

| model | grouped/range tag uses | re-graded grnd / mean | B $/case | B misses | key labels correct /4 | free-text labels | A output tokens (A1, A2) |
|---|---|---|---|---|---|---|---|
| zai.glm-5 | 2 | **4.0 / 4.30** | 0.00082 | - | 3 | 0 | 101, 86 |
| kimi-k3 | 3 | 3.5 / 3.70 | 0.01574 | - | **4** | 0 | 2084, 1285 (reasoning) |
| kimi-k2-thinking | 3 | 2.5 / 3.50 | 0.00295 | - | 2 | 5 | 1614, 1164 (reasoning) |
| glm-4.7 | 1 | 2.0 / 3.40 | 0.00037 | - | 1 | 6 | 104, 87 |
| kimi-k2.5 | 4 | 2.5 / 2.70 | 0.00056 | subtle_framing passed as **allow** (missed violation) | 2 | 0 | 126, 149 |
| minimax-m2.5 | 6 | 2.5 / 2.20 | 0.00084 | clean draft flagged (false alarm) | **4** | 0 | 675, 447 |
| glm-4.7-flash | 5 | 1.0 / 2.00 | 0.00007 | clean draft flagged (false alarm) | 1 | 1 | 69, 186 |
| minimax-m2.1 | 7 | 2.5 / 2.00 | 0.00100 | - | 2 | 0 | 787, 433 |

- **Citation-parsing quirk.** The harness only recognises single tags like `[S12]`. Grouped tags like `[S0, S28]` and ranges like `[S177-S210]` are dropped, so the judge is told nothing was cited and usually lowers groundedness. Every model here used them at least once. I wrote `wrappers/rejudge_tolerant_tags.py`, which imports `bench.py`, reads those tags too, and re-grades the existing Task-A texts with the same judge and prompt. The models are not re-run. The ranking barely changes; the biggest shift is GLM-5's A2 groundedness, from 2 to 4.
- **Judge noise.** Re-grading three turns whose tags were already single gave score changes of 0.0, 0.0 and -0.4. With only two Task-A turns per model, gaps of about 0.3 in the overall mean are within noise.
- **Key labels.** For four of the flagged cases I checked that the guard named the expected violation. "Free-text labels" means the model skipped the tool call and wrote labels outside the allowed list.
- **Spend.** The 8 model runs cost $0.34, of which Kimi K3 was $0.21. The 34 Opus judge calls are not metered; I estimate roughly $0.4–0.7.

### Prices

Source: https://aws.amazon.com/bedrock/pricing/, fetched 2026-10-21, Standard tier, US regions.

| model | input / output $ per 1M tokens |
|---|---|
| Kimi K3 | 3.00 / 15.00 global (US-only profile: 3.30 / 16.50) |
| Kimi K2.5 | 0.60 / 3.00 |
| Kimi K2 Thinking | 0.60 / 2.50 |
| GLM 5.3 | 1.68 / 5.28 global (US-only profile: 1.848 / 5.808) |
| GLM 5 | 1.00 / 3.20 |
| GLM 4.7 | 0.60 / 2.20 |
| GLM 4.7 Flash | 0.07 / 0.40 |
| MiniMax M2.5 | 0.30 / 1.20 |
| MiniMax M2.1 | 0.30 / 1.20 |

Kimi K3 and K2-Thinking are billed for hidden reasoning tokens. The harness correctly leaves that reasoning out of the graded text.

## 2. Notes on the Task-A texts

Checked against the paper text the models saw: it never mentions a "200-review pilot", and Section B is only referred to in [S178]; its content is not included.

- **GLM-5:**
  - One question per turn and the shortest answers.
  - A2 declines the verdict well ("those judgments are yours to make").
  - A1 uses "I could not locate ... in Sections 6, B, or the tables", but claims to have checked Section B, which it never saw. It also puts four tags at the end of one sentence instead of one per claim.
  - Both questions mildly assume the answer ("What additional experimental details would you need..."); it never uses "what, if any".
- **Kimi K3:**
  - Best grounding. It says outright that Section B is not in the text and names the sections it checked.
  - A2 declines the verdict cleanly ("yours to make, not mine"), gives three facts with one tag each, and asks one "what, if anything" question, though the question has a second clause tacked on.
  - A1 is slightly over 90 words, and its question could read as implying the reviewer was wrong.
  - Slow and pricey: 39–65 s and about $0.06 per turn.
- **Kimi K2-Thinking:**
  - Short, with one question per turn.
  - A2 never hands the decision back to the reviewer, slips in a judgment ("...but only 0.632"), and attaches a claim to [S258] that the sentence doesn't support.
  - A1 adopts the reviewer's framing ("experiments lack detail") and doesn't say which sections it checked.
- **GLM-4.7:**
  - Short and neutral, but citations are shaky: in A2, "illustrative experiments" isn't supported by the sentences cited, and there is a typo ("the_ACCEPT").
  - Its A1 question pushes the work back onto the reviewer ("Could you specify which sections ... you checked").
  - It does decline the verdict.
- **Kimi K2.5:**
  - Cites huge ranges as padding (e.g. [S177-S210]).
  - In A2 it quotes ICML position-paper guidelines that aren't in the paper.
  - Its questions carry judgments and assumptions ("sufficiently differentiated ... to merit the urgency claim").
- **MiniMax M2.5:**
  - Wordy (about 128 words), with range tags and its own guesses ("which implies multiple runs").
  - A2 never says the decision is the reviewer's; instead it lists "core contributions" and adds outside filler ("Conference novelty expectations vary").
- **GLM-4.7-Flash:**
  - Made up a fact: it says Section 6.3 "nominally" describes a "200-review pilot", citing [S183, S186]. No such pilot exists.
  - Uses judgment words in its own voice ("severity", "crisis", "limited") and asks a closed, leading yes/no question.
- **MiniMax M2.1:**
  - Worst of the group. A1 asks no question at all and ends with a judgment: "The reviewer would be justified in finding these omissions problematic..."
  - Both turns dump lists of 4–5 facts with range tags.

## 3. Recommendation

**(a) User-facing Socratic turn ("realize"): GLM-5.**
- It has the best judge mean (4.10, or 4.30 when grouped tags are read), the fastest replies (1.7 s), and costs $0.011 per turn.
- Its weak spots can be fixed in the prompt: ask for "what, if any" wording, one tag per claim, and no claims about sections that aren't in the text.
- Runner-up is Kimi K3, about equal in quality (4.00, best grounding), but 30x slower and 5x pricier per turn. It only makes sense for background or "second opinion" turns.
- Avoid MiniMax M2.1/M2.5 and GLM-4.7-Flash for this role.

**(b) Guard/classifier: GLM-5.**
- 6/6 at 2.0 s and $0.0008 per case, always via the tool call, with 3 of 4 key labels right.
- Budget fallback: GLM-4.7, also 6/6 at $0.0004 per case. It sometimes skips the tool and its labels are weak (1/4), so it works as a pass/flag gate but gives the revise step little to go on.
- Kimi K3 got every verdict and label right, but 25 s and $0.016 per case is too slow and expensive to run on every turn.
- Don't use Kimi K2.5 as the guard: it let through a draft that broke the rules (subtle_framing), which is the unsafe kind of miss.
- GLM-4.7-Flash is only usable as a cheap first filter that passes doubtful cases up to a stronger model.
- Caveat: Task B has only 6 cases and 5 of 8 models scored 6/6, so label quality and speed decided this ranking.

---

Files are in `/Users/kensu/Library/Mobile Documents/com~apple~CloudDocs/review_copilot/eval/model_bench/`:
- `results/global.moonshotai.kimi-k3.json`
- `results/moonshotai.kimi-k2.5.json`
- `results/moonshot.kimi-k2-thinking.json`
- `results/zai.glm-5.json`
- `results/zai.glm-4.7.json`
- `results/zai.glm-4.7-flash.json`
- `results/minimax.minimax-m2.5.json`
- `results/minimax.minimax-m2.1.json`
- `results/global.zai.glm-5.3.json` (errors only)
- `wrappers/rejudge_tolerant_tags.py` and its output in `wrappers/rejudge_out/`